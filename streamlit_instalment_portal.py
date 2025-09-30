# streamlit_instalment_portal.py
import re
import os
from datetime import datetime

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text

# ----------------------------
# Configuration / DB credentials
# ----------------------------
# You can override by setting an environment variable DATABASE_URL (recommended).
# Example DATABASE_URL: mysql+pymysql://ahsan:ahsan@321@3.17.21.91/ev_installment_project
USE_ENV_DB = True
DATABASE_URL = os.getenv("DATABASE_URL")

# If DATABASE_URL not set, build from provided credentials below:
DB_USER = "ahsan"
DB_PASS = "ahsan@321"
DB_HOST = "3.17.21.91"
DB_NAME = "ev_installment_project"
DB_DRIVER = "pymysql"  # ensure pymysql is in requirements

if not DATABASE_URL:
    # URL encode password if needed (simple shortcut)
    DATABASE_URL = f"mysql+{DB_DRIVER}://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}"

# SQLAlchemy engine
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

# Ensure table on app start (safe to call)
try:
    ensure_table()
except Exception:
    # Avoid raising if DB temporarily unreachable; errors will be surfaced when saving
    pass

# ----------------------------
# Utility functions & scoring model
# ----------------------------
def validate_cnic(cnic: str) -> bool:
    return bool(re.match(r"^\d{5}-\d{7}-\d{1}$", cnic.strip()))

def parse_int_amount(text: str) -> int:
    """Accept strings with or without commas; return int (0 if invalid)."""
    if text is None:
        return 0
    s = str(text).replace(",", "").strip()
    try:
        return int(float(s))
    except Exception:
        return 0

# New weighted scoring model (integrated from your provided code)
def income_score(net_salary, gender):
    """Return income score scaled 0-100 (female +10% cap 100)."""
    if net_salary < 50000:
        base_score = 0.0
    elif 50000 <= net_salary < 70000:
        base_score = 0.4
    elif 70000 <= net_salary < 90000:
        base_score = 0.6
    elif 90000 <= net_salary < 110000:
        base_score = 0.8
    else:
        base_score = 1.0

    # female boost +10%
    if gender and gender.lower().startswith("f"):
        base_score = min(base_score * 1.1, 1.0)

    return base_score * 100.0

def debt_to_income(outstanding, bike_price, net_salary):
    if net_salary <= 0:
        return 999.0  # super-high (worst)
    return (outstanding + bike_price) / net_salary

def weighted_score(inputs):
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
    total = 0.0
    for k, v in inputs.items():
        w = weights.get(k, 0.0)
        total += (v * w)
    return total

def decision_text(final_score):
    if final_score >= 70:
        return "Approve"
    elif 50 <= final_score < 70:
        return "Review"
    else:
        return "Reject"

def generate_reasons(inputs, inc_score, dti_ratio, dti_score, final_score, decision):
    """Return short bullet points (list) explaining decision"""
    reasons = []

    # Income based
    if inc_score >= 80:
        reasons.append("Strong income score.")
    elif inc_score >= 60:
        reasons.append("Moderate income score — acceptable.")
    else:
        reasons.append("Low income score; below preferred threshold.")

    # Balance
    bank_balance = inputs.get("bank_balance", 0)
    if bank_balance >= 100:
        reasons.append("Bank balance meets or exceeds 3× installment requirement.")
    elif bank_balance >= 50:
        reasons.append("Bank balance is borderline relative to installment requirement.")
    else:
        reasons.append("Insufficient bank balance to cover 3× installment.")

    # DTI
    if dti_ratio < 0.3:
        reasons.append("Low debt-to-income ratio.")
    elif dti_ratio < 0.6:
        reasons.append("Moderate debt-to-income ratio.")
    else:
        reasons.append("High debt-to-income ratio; repayment capacity is strained.")

    # Guarantors
    if not (applicant_state.get("guarantor_male") and applicant_state.get("guarantor_female")):
        reasons.append("Guarantor requirement not fully met (need both male and female guarantors).")

    # Electricity bills
    if not applicant_state.get("electricity_bills_submitted"):
        reasons.append("Electricity bills not submitted for address verification.")

    # Decision-specific extra line
    if decision == "Approve":
        reasons.append("Overall profile meets Wavetec lending criteria.")
    elif decision == "Review":
        reasons.append("Profile is borderline: manual review recommended for supporting documents.")
    else:
        reasons.append("Profile does not meet lending criteria; reject to mitigate risk.")

    # Return short bullet points
    # Remove duplicates and empty
    cleaned = []
    for r in reasons:
        r = r.strip()
        if r and r not in cleaned:
            cleaned.append(r)
    return cleaned

# ----------------------------
# Streamlit UI - Multi-step flow
# ----------------------------
st.set_page_config(page_title="Wavetec EV Installment Scoring", layout="wide")
st.title("Wavetec Electric Bike Installment Portal")
st.markdown("Professional portal for assessing applicants for Wavetec electric bike installments. "
            "Please fill applicant information and proceed to scoring.")

# Session state holders
if "page" not in st.session_state:
    st.session_state.page = "applicant"
if "applicant" not in st.session_state:
    st.session_state.applicant = {}
if "scoring" not in st.session_state:
    st.session_state.scoring = {}
# For reasoning to see guarantor/ebills status in generator
applicant_state = st.session_state.applicant

# ---------- Page 1: Applicant details ----------
if st.session_state.page == "applicant":
    st.header("Step 1 — Applicant Information (required)")

    col1, col2 = st.columns(2)
    first_name = col1.text_input("First name", value=st.session_state.applicant.get("first_name", ""))
    last_name = col2.text_input("Last name", value=st.session_state.applicant.get("last_name", ""))
    address = st.text_area("Residential address", value=st.session_state.applicant.get("address", ""))
    cnic = st.text_input("CNIC (format: 12345-1234567-1)", value=st.session_state.applicant.get("cnic", ""))
    driving_license = st.text_input("Driving license number", value=st.session_state.applicant.get("driving_license", ""))
    electricity_bills_submitted = st.radio("Electricity bills submitted?", ["Yes", "No"],
                                           index=0 if st.session_state.applicant.get("electricity_bills_submitted", True) else 1)
    # Guarantors: two checkboxes (male + female)
    st.write("Guarantors (must have two — at least one female)")
    g_col1, g_col2 = st.columns(2)
    guarantor_male = g_col1.checkbox("Male guarantor present", value=st.session_state.applicant.get("guarantor_male", False))
    guarantor_female = g_col2.checkbox("Female guarantor present", value=st.session_state.applicant.get("guarantor_female", False))

    gender = st.selectbox("Applicant gender", ["Male", "Female"], index=0 if st.session_state.applicant.get("gender", "Male") == "Male" else 1)

    # Confirm / validation
    if st.button("Validate & Continue"):
        errors = []
        if not first_name.strip():
            errors.append("First name is required.")
        if not last_name.strip():
            errors.append("Last name is required.")
        if not address.strip():
            errors.append("Address is required.")
        if not cnic.strip() or not validate_cnic(cnic):
            errors.append("CNIC is required and must be in 12345-1234567-1 format.")
        if not driving_license.strip():
            errors.append("Driving license number is required.")
        # guarantor check
        if not (guarantor_male and guarantor_female):
            errors.append("Two guarantors required; at least one must be female.")

        if errors:
            for e in errors:
                st.error(e)
        else:
            # store applicant info
            st.session_state.applicant = {
                "first_name": first_name.strip(),
                "last_name": last_name.strip(),
                "address": address.strip(),
                "cnic": cnic.strip(),
                "driving_license": driving_license.strip(),
                "electricity_bills_submitted": (electricity_bills_submitted == "Yes"),
                "guarantor_male": guarantor_male,
                "guarantor_female": guarantor_female,
                "gender": gender,
            }
            st.success("Applicant information saved. Proceed to scoring.")
            st.session_state.page = "scoring"
            st.experimental_rerun()

# ---------- Page 2: Scoring ----------
elif st.session_state.page == "scoring":
    st.header("Step 2 — Scoring Inputs")

    st.subheader("Financial inputs")
    col1, col2, col3 = st.columns(3)
    salary_text = col1.text_input("Net salary (PKR)", value=f"{st.session_state.scoring.get('net_salary', '')}")
    # show formatted preview
    parsed_salary = parse_int_amount(salary_text)
    if parsed_salary:
        col1.write(f"Entered: PKR {parsed_salary:,}")

    avg_balance_text = col2.text_input("Average 6-month bank balance (PKR)", value=f"{st.session_state.scoring.get('avg_balance', '')}")
    parsed_balance = parse_int_amount(avg_balance_text)
    if parsed_balance:
        col2.write(f"Entered: PKR {parsed_balance:,}")

    installment_amount = col3.number_input("Installment amount (PKR)", min_value=1000, step=500, value=int(st.session_state.scoring.get("installment_amount", 10000)))

    st.subheader("Behavioral & additional scores (use sliders)")
    salary_consistency = st.slider("Salary credit consistency (0-100)", 0, 100, int(st.session_state.scoring.get("salary_consistency", 80)))
    employer_type = st.slider("Employer type score (0-100)", 0, 100, int(st.session_state.scoring.get("employer_type", 70)))
    job_tenure = st.slider("Job tenure score (0-100)", 0, 100, int(st.session_state.scoring.get("job_tenure", 60)))
    age_score = st.slider("Age score (0-100)", 0, 100, int(st.session_state.scoring.get("age", 65)))
    dependents_score = st.slider("Dependents score (0-100)", 0, 100, int(st.session_state.scoring.get("dependents", 70)))
    residence_score = st.slider("Residence stability score (0-100)", 0, 100, int(st.session_state.scoring.get("residence", 75)))

    st.subheader("Loan & product details")
    bike_type = st.selectbox("Bike type", ["EV-1", "EV-125"], index=0 if st.session_state.scoring.get("bike_type", "EV-1") == "EV-1" else 1)
    bike_price = st.number_input("Bike price (PKR)", min_value=0, step=1000, value=int(st.session_state.scoring.get("bike_price", 0)))
    outstanding_loan = st.number_input("Outstanding loan amount (PKR)", min_value=0, step=1000, value=int(st.session_state.scoring.get("outstanding_loan", 0)))

    if st.button("Calculate Score"):
        # parse numeric amounts
        net_salary_val = parse_int_amount(salary_text)
        avg_balance_val = parse_int_amount(avg_balance_text)

        # store scoring inputs
        st.session_state.scoring = {
            "net_salary": net_salary_val,
            "avg_balance": avg_balance_val,
            "installment_amount": int(installment_amount),
            "salary_consistency": int(salary_consistency),
            "employer_type": int(employer_type),
            "job_tenure": int(job_tenure),
            "age": int(age_score),
            "dependents": int(dependents_score),
            "residence": int(residence_score),
            "bike_type": bike_type,
            "bike_price": int(bike_price),
            "outstanding_loan": int(outstanding_loan),
        }

        # Compute scores
        inc_score = income_score(net_salary_val, st.session_state.applicant.get("gender", "Male"))
        # bank balance normalized: bank_balance / (3 * installment) capped at 1.0, then *100
        bank_balance_norm = min(1.0, (avg_balance_val / (3 * installment_amount))) * 100.0
        dti_ratio = debt_to_income(outstanding_loan, bike_price, net_salary_val)
        # dti_score: higher ratio worse, produce 0-100 such that ratio 0 -> 100, ratio 1 -> 0; allow negative if >1
        dti_score = max(0.0, 100.0 - (dti_ratio * 100.0))

        inputs = {
            "income": inc_score,
            "bank_balance": bank_balance_norm,
            "salary_consistency": float(salary_consistency),
            "employer_type": float(employer_type),
            "job_tenure": float(job_tenure),
            "age": float(age_score),
            "dependents": float(dependents_score),
            "residence": float(residence_score),
            "dti": dti_score,
        }

        final = weighted_score(inputs)
        decision_val = decision_text(final)

        # Generate short bullet reasons
        applicant_state.update(st.session_state.applicant)  # ensure applicant_state reflects current
        reasons_list = generate_reasons(inputs, inc_score, dti_ratio, dti_score, final, decision_val)

        # Save results to session and go to results page
        st.session_state.result = {
            "inc_score": inc_score,
            "bank_balance_norm": bank_balance_norm,
            "dti_ratio": dti_ratio,
            "dti_score": dti_score,
            "inputs": inputs,
            "final_score": final,
            "decision": decision_val,
            "reasons": reasons_list,
            "bike_type": bike_type,
            "bike_price": bike_price,
            "outstanding_loan": outstanding_loan,
            "installment_amount": installment_amount
        }
        st.session_state.page = "results"
        st.experimental_rerun()

# ---------- Page 3: Results & DB save ----------
elif st.session_state.page == "results":
    st.header("Step 3 — Results & Decision")

    result = st.session_state.get("result", None)
    if not result:
        st.error("No scoring result found. Please go back and calculate.")
        if st.button("Back to scoring"):
            st.session_state.page = "scoring"
            st.experimental_rerun()
    else:
        st.subheader("Scores")
        st.write(f"Income score: {result['inc_score']:.1f}")
        st.write(f"Bank balance score (normalized): {result['bank_balance_norm']:.1f}")
        st.write(f"Debt-to-Income ratio: {result['dti_ratio']:.2f}")
        st.write(f"DTI score: {result['dti_score']:.1f}")
        st.write(f"Final weighted score: {result['final_score']:.1f}")
        st.write(f"Decision: {result['decision']}")

        st.subheader("Decision reasons")
        for r in result['reasons']:
            st.write("•", r)

        # If approved, offer to save to DB
        if result['decision'] == "Approve":
            if st.button("Save approved applicant to database"):
                # Build insert payload
                payload = {
                    "first_name": st.session_state.applicant.get("first_name"),
                    "last_name": st.session_state.applicant.get("last_name"),
                    "address": st.session_state.applicant.get("address"),
                    "cnic": st.session_state.applicant.get("cnic"),
                    "driving_license": st.session_state.applicant.get("driving_license"),
                    "electricity_bills_submitted": bool(st.session_state.applicant.get("electricity_bills_submitted")),
                    "gender": st.session_state.applicant.get("gender"),
                    "guarantor_male": bool(st.session_state.applicant.get("guarantor_male")),
                    "guarantor_female": bool(st.session_state.applicant.get("guarantor_female")),
                    "net_salary": int(st.session_state.scoring.get("net_salary", 0)),
                    "avg_balance": int(st.session_state.scoring.get("avg_balance", 0)),
                    "installment_amount": int(result.get("installment_amount", 0)),
                    "bike_type": result.get("bike_type"),
                    "bike_price": int(result.get("bike_price", 0)),
                    "outstanding_loan": int(result.get("outstanding_loan", 0)),
                    "income_score": float(result.get("inc_score", 0)),
                    "dti_ratio": float(result.get("dti_ratio", 0)),
                    "dti_score": float(result.get("dti_score", 0)),
                    "final_score": float(result.get("final_score", 0)),
                    "decision": result.get("decision"),
                    "decision_reasons": "\n".join(result.get("reasons", [])),
                }
                # Insert into DB
                insert_sql = text("""
                INSERT INTO data (
                  first_name, last_name, address, cnic, driving_license,
                  electricity_bills_submitted, gender,
                  guarantor_male, guarantor_female,
                  net_salary, avg_balance, installment_amount,
                  bike_type, bike_price, outstanding_loan,
                  income_score, dti_ratio, dti_score, final_score,
                  decision, decision_reasons
                ) VALUES (
                  :first_name, :last_name, :address, :cnic, :driving_license,
                  :electricity_bills_submitted, :gender,
                  :guarantor_male, :guarantor_female,
                  :net_salary, :avg_balance, :installment_amount,
                  :bike_type, :bike_price, :outstanding_loan,
                  :income_score, :dti_ratio, :dti_score, :final_score,
                  :decision, :decision_reasons
                );
                """)
                try:
                    with engine.begin() as conn:
                        conn.execute(insert_sql, payload)
                    st.success("Applicant saved to database successfully.")
                except Exception as e:
                    st.error(f"Failed to save to DB: {e}")

        # Navigation
        nav_col1, nav_col2 = st.columns(2)
        if nav_col1.button("Back to scoring"):
            st.session_state.page = "scoring"
            st.experimental_rerun()
        if nav_col2.button("New applicant"):
            # Reset session state to start fresh
            st.session_state.page = "applicant"
            st.session_state.applicant = {}
            st.session_state.scoring = {}
            st.session_state.result = {}
            st.experimental_rerun()
