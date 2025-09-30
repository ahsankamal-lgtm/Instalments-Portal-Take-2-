# streamlit_ev_portal.py

import re
import os
from datetime import datetime

import streamlit as st
from sqlalchemy import create_engine, text

# ----------------------------
# DB Config
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
    salary_consistency INT,
    employer_type VARCHAR(20),
    job_tenure INT,
    age INT,
    dependents INT,
    residence VARCHAR(20),
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
        st.error(f"DB error: {e}")

try:
    ensure_table()
except Exception:
    pass

# ----------------------------
# Utility & Scoring Functions
# ----------------------------
def validate_cnic(cnic: str) -> bool:
    return bool(re.match(r"^\d{5}-\d{7}-\d{1}$", cnic.strip()))

# Scoring functions (from framework)
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
    if 25 <= age <= 55:
        return 100
    else:
        return 60

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

def dti_score_fn(dti):
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
    total = 0
    for k, v in scores.items():
        total += v * weights[k]
    return total

def decision(final_score):
    if final_score >= 70:
        return "Approve"
    elif 50 <= final_score < 70:
        return "Review"
    else:
        return "Reject"

# ----------------------------
# Streamlit Multi-Step App
# ----------------------------
st.set_page_config(page_title="Wavetec EV Loan Scoring Portal", layout="wide")
st.title("Wavetec EV Loan Scoring Portal")

if "page" not in st.session_state:
    st.session_state.page = "applicant"
if "applicant" not in st.session_state:
    st.session_state.applicant = {}
if "scoring" not in st.session_state:
    st.session_state.scoring = {}
if "result" not in st.session_state:
    st.session_state.result = {}

# --- Page 1: Applicant Info ---
if st.session_state.page == "applicant":
    st.header("Step 1 — Applicant Information")
    col1, col2 = st.columns(2)
    first_name = col1.text_input("First name", value=st.session_state.applicant.get("first_name", ""))
    last_name = col2.text_input("Last name", value=st.session_state.applicant.get("last_name", ""))
    address = st.text_area("Residential address", value=st.session_state.applicant.get("address", ""))
    cnic = st.text_input("CNIC (12345-1234567-1)", value=st.session_state.applicant.get("cnic", ""))
    driving_license = st.text_input("Driving License #", value=st.session_state.applicant.get("driving_license", ""))
    electricity_bills_submitted = st.radio("Electricity bills submitted?", ["Yes", "No"])
    g_col1, g_col2 = st.columns(2)
    guarantor_male = g_col1.checkbox("Male guarantor present")
    guarantor_female = g_col2.checkbox("Female guarantor present")
    gender = st.selectbox("Gender", ["Male", "Female"])

    if st.button("Continue"):
        errors = []
        if not first_name or not last_name: errors.append("Full name required")
        if not validate_cnic(cnic): errors.append("Invalid CNIC format")
        if not driving_license: errors.append("Driving license required")
        if not (guarantor_male and guarantor_female): errors.append("Both male & female guarantors required")

        if errors:
            for e in errors: st.error(e)
        else:
            st.session_state.applicant = {
                "first_name": first_name, "last_name": last_name,
                "address": address, "cnic": cnic, "driving_license": driving_license,
                "electricity_bills_submitted": electricity_bills_submitted == "Yes",
                "guarantor_male": guarantor_male, "guarantor_female": guarantor_female,
                "gender": gender,
            }
            st.session_state.page = "scoring"
            st.experimental_rerun()

# --- Page 2: Scoring Inputs ---
elif st.session_state.page == "scoring":
    st.header("Step 2 — Scoring Inputs")
    col1, col2, col3 = st.columns(3)
    net_salary = col1.number_input("Net Salary (PKR)", min_value=0, step=1000)
    bank_balance = col2.number_input("Avg 6-month Bank Balance (PKR)", min_value=0, step=1000)
    months_consistent = col3.number_input("Salary Consistency (months out of 12)", min_value=0, max_value=12, step=1)

    col4, col5, col6 = st.columns(3)
    employer_type = col4.selectbox("Employer Type", ["Govt", "MNC", "SME", "Startup"])
    job_tenure_years = col5.number_input("Job Tenure (years)", min_value=0, step=1)
    age = col6.number_input("Age (years)", min_value=18, step=1)

    col7, col8 = st.columns(2)
    dependents = col7.number_input("Dependents", min_value=0, step=1)
    residence_type = col8.selectbox("Residence", ["Owned", "Rented"])

    st.subheader("Loan Details")
    bike_type = st.selectbox("Bike Type", ["EV-1", "EV-125"])
    bike_price = st.number_input("Bike Price (PKR)", min_value=0, step=1000)
    outstanding_loan = st.number_input("Outstanding Loan (PKR)", min_value=0, step=1000)

    if st.button("Calculate"):
        # compute scores
        inc = income_score(net_salary, st.session_state.applicant["gender"])
        bal = bank_balance_score(bank_balance)
        sal_cons = salary_consistency_score(months_consistent)
        emp = employer_type_score(employer_type)
        job_ten = job_tenure_score(job_tenure_years)
        age_s = age_score(age)
        dep_s = dependents_score(dependents)
        res_s = residence_score(residence_type)
        dti_r = dti_ratio(outstanding_loan, bike_price, net_salary)
        dti_s = dti_score_fn(dti_r)

        scores = {
            "income": inc, "bank_balance": bal, "salary_consistency": sal_cons,
            "employer_type": emp, "job_tenure": job_ten, "age": age_s,
            "dependents": dep_s, "residence": res_s, "dti": dti_s
        }
        final = weighted_final_score(scores)
        dec = decision(final)

        st.session_state.result = {
            **scores,
            "dti_ratio": dti_r,
            "final_score": final,
            "decision": dec,
            "net_salary": net_salary,
            "avg_balance": bank_balance,
            "salary_consistency": months_consistent,
            "employer_type": employer_type,
            "job_tenure": job_tenure_years,
            "age": age,
            "dependents": dependents,
            "residence": residence_type,
            "bike_type": bike_type,
            "bike_price": bike_price,
            "outstanding_loan": outstanding_loan,
        }
        st.session_state.page = "results"
        st.experimental_rerun()

# --- Page 3: Results ---
elif st.session_state.page == "results":
    st.header("Step 3 — Results")
    r = st.session_state.result
    st.write(f"**Income Score:** {r['income']:.1f}")
    st.write(f"**Bank Balance Score:** {r['bank_balance']:.1f}")
    st.write(f"**Salary Consistency Score:** {r['salary_consistency']:.1f}")
    st.write(f"**Employer Type Score:** {r['employer_type']:.1f}")
    st.write(f"**Job Tenure Score:** {r['job_tenure']:.1f}")
    st.write(f"**Age Score:** {r['age']:.1f}")
    st.write(f"**Dependents Score:** {r['dependents']:.1f}")
    st.write(f"**Residence Score:** {r['residence']:.1f}")
    st.write(f"**Debt-to-Income Ratio:** {r['dti_ratio']:.2f}")
    st.write(f"**DTI Score:** {r['dti']:.1f}")
    st.markdown("---")
    st.write(f"**Final Score:** {r['final_score']:.1f}")
    st.write(f"**Decision:** {r['decision']}")

    if r['decision'] == "Approve":
        if st.button("Save to DB"):
            payload = {
                **st.session_state.applicant,
                **{
                    "net_salary": r['net_salary'],
                    "avg_balance": r['avg_balance'],
                    "salary_consistency": r['salary_consistency'],
                    "employer_type": r['employer_type'],
                    "job_tenure": r['job_tenure'],
                    "age": r['age'],
                    "dependents": r['dependents'],
                    "residence": r['residence'],
                    "bike_type": r['bike_type'],
                    "bike_price": r['bike_price'],
                    "outstanding_loan": r['outstanding_loan'],
                    "income_score": r['income'],
                    "bank_balance_score": r['bank_balance'],
                    "salary_consistency_score": r['salary_consistency'],
                    "employer_type_score": r['employer_type'],
                    "job_tenure_score": r['job_tenure'],
                    "age_score": r['age'],
                    "dependents_score": r['dependents'],
                    "residence_score": r['residence'],
                    "dti_ratio": r['dti_ratio'],
                    "dti_score": r['dti'],
                    "final_score": r['final_score'],
                    "decision": r['decision'],
                    "decision_reasons": f"Auto decision: {r['decision']}",
                }
            }
            insert_sql = text("""
            INSERT INTO data (
              first_name,last_name,address,cnic,driving_license,
              electricity_bills_submitted,gender,guarantor_male,guarantor_female,
              net_salary,avg_balance,salary_consistency,employer_type,job_tenure,age,dependents,residence,
              bike_type,bike_price,outstanding_loan,
              income_score,bank_balance_score,salary_consistency_score,employer_type_score,job_tenure_score,
              age_score,dependents_score,residence_score,dti_ratio,dti_score,final_score,
              decision,decision_reasons
            ) VALUES (
              :first_name,:last_name,:address,:cnic,:driving_license,
              :electricity_bills_submitted,:gender,:guarantor_male,:guarantor_female,
              :net_salary,:avg_balance,:salary_consistency,:employer_type,:job_tenure,:age,:dependents,:residence,
              :bike_type,:bike_price,:outstanding_loan,
              :income_score,:bank_balance_score,:salary_consistency_score,:employer_type_score,:job_tenure_score,
              :age_score,:dependents_score,:residence_score,:dti_ratio,:dti_score,:final_score,
              :decision,:decision_reasons
            );
            """)
            try:
                with engine.begin() as conn:
                    conn.execute(insert_sql, payload)
                st.success("Saved to DB ✅")
            except Exception as e:
                st.error(f"DB save failed: {e}")

    col1, col2 = st.columns(2)
    if col1.button("Back"):
        st.session_state.page = "scoring"; st.experimental_rerun()
    if col2.button("New Applicant"):
        st.session_state.page = "applicant"; st.session_state.applicant = {}; st.session_state.scoring = {}; st.session_state.result = {}; st.experimental_rerun()
