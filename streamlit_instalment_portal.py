# streamlit_ev_portal.py
import re
import os
from datetime import datetime

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text

# ----------------------------
# Configuration / DB credentials
# ----------------------------
USE_ENV_DB = True
DATABASE_URL = os.getenv("DATABASE_URL")

DB_USER = "ahsan"
DB_PASS = "ahsan@321"
DB_HOST = "3.17.21.91"
DB_NAME = "ev_installment_project"
DB_DRIVER = "pymysql"

if not DATABASE_URL:
    DATABASE_URL = f"mysql+{DB_DRIVER}://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}"

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# ----------------------------
# Helper: Create table if not exists
# ----------------------------
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    address VARCHAR(255),
    cnic VARCHAR(20) UNIQUE NOT NULL,
    driving_license VARCHAR(50),
    electricity_bills_submitted BOOLEAN,
    gender ENUM('Male','Female') NOT NULL,
    guarantor_male BOOLEAN NOT NULL,
    guarantor_female BOOLEAN NOT NULL,
    net_salary INT NOT NULL,
    avg_balance INT NOT NULL,
    installment_amount INT NOT NULL,
    bike_type VARCHAR(50),
    bike_price INT,
    outstanding_loan INT,
    income_score FLOAT,
    bank_balance_score FLOAT,
    salary_consistency_score FLOAT,
    employer_type_score FLOAT,
    job_tenure_score FLOAT,
    age_score FLOAT,
    dependents_score FLOAT,
    residence_score FLOAT,
    dti_ratio FLOAT,
    dti_score FLOAT,
    final_score FLOAT,
    decision VARCHAR(20),
    decision_reasons TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;
"""

def ensure_table():
    try:
        with engine.begin() as conn:
            conn.execute(text(CREATE_TABLE_SQL))
    except Exception as e:
        st.error(f"Failed to ensure DB table exists: {e}")

try:
    ensure_table()
except Exception:
    pass

# ----------------------------
# Utility
# ----------------------------
def validate_cnic(cnic: str) -> bool:
    return bool(re.match(r"^\d{5}-\d{7}-\d{1}$", cnic.strip()))

def validate_license(cnic: str, license_str: str) -> bool:
    """Must match CNIC + ' # ' + 3 alphanumeric characters"""
    pattern = f"^{re.escape(cnic)} # [A-Za-z0-9]{{3}}$"
    return bool(re.match(pattern, license_str.strip()))

def parse_int_amount(text: str) -> int:
    if text is None:
        return 0
    s = str(text).replace(",", "").strip()
    try:
        return int(float(s))
    except Exception:
        return 0

# ----------------------------
# Scoring functions
# ----------------------------
def income_score(net_salary, gender):
    if net_salary < 50000:
        base = 0
    elif 50000 <= net_salary < 70000:
        base = 40
    elif 70000 <= net_salary < 90000:
        base = 60
    elif 90000 <= net_salary < 110000:
        base = 80
    else:
        base = 100
    if gender == "Female":
        base *= 1.1
    return min(base, 100)

def bank_balance_score(balance):
    return min((balance / 30000) * 100, 100)

def salary_consistency_score(months_consistent):
    return min((months_consistent / 12) * 100, 100)

def employer_type_score(employer_type):
    mapping = {"Govt": 100, "MNC": 80, "SME": 60, "Startup": 40}
    return mapping.get(employer_type, 0)

def job_tenure_score(years):
    if years >= 3:
        return 100
    elif 1 <= years < 3:
        return 70
    else:
        return 40

def age_score(age):
    return 100 if 25 <= age <= 55 else 60

def dependents_score(num_dependents):
    if num_dependents <= 1:
        return 100
    elif num_dependents == 2:
        return 70
    else:
        return 40

def residence_score(residence_type):
    return 100 if residence_type == "Owned" else 60

def dti_ratio(outstanding, bike_price, net_salary):
    if net_salary <= 0:
        return 2.0
    return (outstanding + bike_price) / net_salary

def dti_score(dti):
    if dti <= 0.5:
        return 100
    elif dti <= 1.0:
        return 70
    else:
        return 40

def weighted_final_score(scores):
    weights = {
        "income": 0.40,
        "bank_balance": 0.30,
        "salary_consistency": 0.04,
        "employer_type": 0.04,
        "job_tenure": 0.04,
        "age": 0.04,
        "dependents": 0.04,
        "residence": 0.05,
        "dti": 0.05,
    }
    return sum(scores[k] * weights[k] for k in weights)

def decision(final_score):
    if final_score >= 70:
        return "Approve"
    elif 50 <= final_score < 70:
        return "Review"
    else:
        return "Reject"

def generate_reasons(scores, dti_r, decision_val, applicant):
    reasons = []
    if scores["income"] < 60:
        reasons.append("Low income compared to benchmark ranges.")
    if scores["bank_balance"] < 100:
        reasons.append("Bank balance below recommended threshold.")
    if scores["salary_consistency"] < 100:
        reasons.append("Salary inflows inconsistent over 12 months.")
    if scores["employer_type"] < 80:
        reasons.append("Employer risk category not ideal.")
    if scores["job_tenure"] < 100:
        reasons.append("Short job tenure reduces stability.")
    if not (applicant.get("guarantor_male") and applicant.get("guarantor_female")):
        reasons.append("Guarantor requirement not fully met.")
    if not applicant.get("electricity_bills_submitted"):
        reasons.append("Electricity bills not submitted for verification.")
    if dti_r > 0.5:
        reasons.append("High debt-to-income ratio limits repayment capacity.")

    if decision_val == "Approve":
        reasons.append("Profile meets Wavetec criteria.")
    elif decision_val == "Review":
        reasons.append("Borderline case — manual review suggested.")
    else:
        reasons.append("Profile fails lending criteria.")
    return reasons

# ----------------------------
# Streamlit UI
# ----------------------------
st.set_page_config(page_title="Wavetec EV Installment Portal", layout="wide")
st.title("Wavetec Electric Bike Installment Portal")

if "page" not in st.session_state:
    st.session_state.page = "applicant"
if "applicant" not in st.session_state:
    st.session_state.applicant = {}
if "scoring" not in st.session_state:
    st.session_state.scoring = {}

# ---------- Page 1 ----------
if st.session_state.page == "applicant":
    st.header("Step 1 — Applicant Information")

    col1, col2 = st.columns(2)
    first_name = col1.text_input("First name")
    last_name = col2.text_input("Last name")
    address = st.text_area("Address")
    cnic = st.text_input("CNIC (12345-1234567-1)")
    gender = st.selectbox("Gender", ["Male", "Female"])
    driving_license = st.text_input("Driving License Number (auto-format after CNIC)")

    electricity_bills_submitted = st.radio("Electricity bills submitted?", ["Yes", "No"])
    g_col1, g_col2 = st.columns(2)
    guarantor_male = g_col1.checkbox("Male guarantor present")
    guarantor_female = g_col2.checkbox("Female guarantor present")

    if st.button("Continue"):
        errors = []
        if not first_name.strip():
            errors.append("First name required.")
        if not last_name.strip():
            errors.append("Last name required.")
        if not validate_cnic(cnic):
            errors.append("CNIC must match 12345-1234567-1 format.")
        if not validate_license(cnic, driving_license):
            errors.append("Driving license must match CNIC # XXX format.")

        if not (guarantor_male and guarantor_female):
            errors.append("Two guarantors required (at least one female).")

        if errors:
            for e in errors:
                st.error(e)
        else:
            st.session_state.applicant = {
                "first_name": first_name.strip(),
                "last_name": last_name.strip(),
                "address": address.strip(),
                "cnic": cnic.strip(),
                "driving_license": driving_license.strip(),
                "gender": gender,
                "electricity_bills_submitted": (electricity_bills_submitted == "Yes"),
                "guarantor_male": guarantor_male,
                "guarantor_female": guarantor_female,
            }
            st.session_state.page = "scoring"
            st.experimental_rerun()

# ---------- Page 2 ----------
elif st.session_state.page == "scoring":
    st.header("Step 2 — Scoring Inputs")

    col1, col2, col3 = st.columns(3)
    salary_text = col1.text_input("Net Salary (PKR)")
    parsed_salary = parse_int_amount(salary_text)
    if parsed_salary:
        col1.write(f"Entered: PKR {parsed_salary:,}")

    balance_text = col2.text_input("Average 6M Bank Balance (PKR)")
    parsed_balance = parse_int_amount(balance_text)
    if parsed_balance:
        col2.write(f"Entered: PKR {parsed_balance:,}")

    installment = col3.number_input("Installment (PKR)", min_value=1000, step=500, value=10000)

    months_consistent = st.slider("Salary consistency (months)", 0, 12, 12)
    employer_type = st.selectbox("Employer Type", ["Govt", "MNC", "SME", "Startup"])
    job_tenure = st.number_input("Job Tenure (years)", min_value=0, step=1)
    age = st.number_input("Age", min_value=18, step=1)
    dependents = st.number_input("Dependents", min_value=0, step=1)
    residence = st.selectbox("Residence", ["Owned", "Rented"])

    bike_type = st.selectbox("Bike Type", ["EV-1", "EV-125"])
    bike_price = st.number_input("Bike Price (PKR)", min_value=0, step=1000)
    outstanding = st.number_input("Outstanding Loan (PKR)", min_value=0, step=1000)

    if st.button("Calculate Score"):
        st.session_state.scoring = {
            "net_salary": parsed_salary,
            "avg_balance": parsed_balance,
            "installment": installment,
            "months_consistent": months_consistent,
            "employer_type": employer_type,
            "job_tenure": job_tenure,
            "age": age,
            "dependents": dependents,
            "residence": residence,
            "bike_type": bike_type,
            "bike_price": bike_price,
            "outstanding": outstanding,
        }
        st.session_state.page = "results"
        st.experimental_rerun()

# ---------- Page 3 ----------
elif st.session_state.page == "results":
    st.header("Step 3 — Results")

    a = st.session_state.applicant
    s = st.session_state.scoring

    inc = income_score(s["net_salary"], a["gender"])
    bank = bank_balance_score(s["avg_balance"])
    sal_cons = salary_consistency_score(s["months_consistent"])
    emp = employer_type_score(s["employer_type"])
    job = job_tenure_score(s["job_tenure"])
    age_s = age_score(s["age"])
    dep = dependents_score(s["dependents"])
    res = residence_score(s["residence"])
    dti_r = dti_ratio(s["outstanding"], s["bike_price"], s["net_salary"])
    dti_s = dti_score(dti_r)

    scores = {
        "income": inc,
        "bank_balance": bank,
        "salary_consistency": sal_cons,
        "employer_type": emp,
        "job_tenure": job,
        "age": age_s,
        "dependents": dep,
        "residence": res,
        "dti": dti_s,
    }
    final = weighted_final_score(scores)
    decision_val = decision(final)

    results_df = pd.DataFrame([
        ["Income Score (with gender adj.)", f"{inc:.1f}"],
        ["Bank Balance Score", f"{bank:.1f}"],
        ["Salary Consistency Score", f"{sal_cons:.1f}"],
        ["Employer Type Score", f"{emp:.1f}"],
        ["Job Tenure Score", f"{job:.1f}"],
        ["Age Score", f"{age_s:.1f}"],
        ["Dependents Score", f"{dep:.1f}"],
        ["Residence Score", f"{res:.1f}"],
        ["Debt-to-Income Ratio", f"{dti_r:.2f}"],
        ["Debt-to-Income Score", f"{dti_s:.1f}"],
        ["Final Score (0-100)", f"{final:.1f}"],
        ["Decision", decision_val],
    ], columns=["Output Variables", "Value"])

    st.table(results_df)

    st.subheader("Decision reasons")
    for r in generate_reasons(scores, dti_r, decision_val, a):
        st.write("•", r)

    if decision_val == "Approve":
        if st.button("Save approved applicant to DB"):
            payload = {
                "first_name": a["first_name"],
                "last_name": a["last_name"],
                "address": a["address"],
                "cnic": a["cnic"],
                "driving_license": a["driving_license"],
                "electricity_bills_submitted": a["electricity_bills_submitted"],
                "gender": a["gender"],
                "guarantor_male": a["guarantor_male"],
                "guarantor_female": a["guarantor_female"],
                "net_salary": s["net_salary"],
                "avg_balance": s["avg_balance"],
                "installment_amount": s["installment"],
                "bike_type": s["bike_type"],
                "bike_price": s["bike_price"],
                "outstanding_loan": s["outstanding"],
                "income_score": inc,
                "bank_balance_score": bank,
                "salary_consistency_score": sal_cons,
                "employer_type_score": emp,
                "job_tenure_score": job,
                "age_score": age_s,
                "dependents_score": dep,
                "residence_score": res,
                "dti_ratio": dti_r,
                "dti_score": dti_s,
                "final_score": final,
                "decision": decision_val,
                "decision_reasons": "\n".join(generate_reasons(scores, dti_r, decision_val, a)),
            }
            try:
                with engine.begin() as conn:
                    conn.execute(text("""
                    INSERT INTO data (
                      first_name, last_name, address, cnic, driving_license,
                      electricity_bills_submitted, gender,
                      guarantor_male, guarantor_female,
                      net_salary, avg_balance, installment_amount,
                      bike_type, bike_price, outstanding_loan,
                      income_score, bank_balance_score, salary_consistency_score,
                      employer_type_score, job_tenure_score, age_score, dependents_score,
                      residence_score, dti_ratio, dti_score, final_score,
                      decision, decision_reasons
                    ) VALUES (
                      :first_name, :last_name, :address, :cnic, :driving_license,
                      :electricity_bills_submitted, :gender,
                      :guarantor_male, :guarantor_female,
                      :net_salary, :avg_balance, :installment_amount,
                      :bike_type, :bike_price, :outstanding_loan,
                      :income_score, :bank_balance_score, :salary_consistency_score,
                      :employer_type_score, :job_tenure_score, :age_score, :dependents_score,
                      :residence_score, :dti_ratio, :dti_score, :final_score,
                      :decision, :decision_reasons
                    );
                    """), payload)
                st.success("Applicant saved to DB successfully.")
            except Exception as e:
                st.error(f"Failed to save: {e}")

    nav1, nav2 = st.columns(2)
    if nav1.button("Back"):
        st.session_state.page = "scoring"
        st.experimental_rerun()
    if nav2.button("New applicant"):
        st.session_state.page = "applicant"
        st.session_state.applicant = {}
        st.session_state.scoring = {}
        st.experimental_rerun()
