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

def build_license(cnic: str, suffix: str) -> str:
    """Combine CNIC + suffix into final Driving License format"""
    return f"{cnic} # {suffix.strip()}"

def validate_license_suffix(suffix: str) -> bool:
    """Suffix must be exactly 3 alphanumeric characters"""
    return bool(re.match(r"^[A-Za-z0-9]{3}$", suffix.strip()))

def parse_int_amount(text: str) -> int:
    if text is None:
        return 0
    s = str(text).replace(",", "").strip()
    try:
        return int(float(s))
    except Exception:
        return 0

# ----------------------------
# Scoring functions (same as before)
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

    # Driving license suffix only
    license_suffix = st.text_input("Driving License Suffix (3 characters, e.g. 123 or ABC)")
    if cnic:
        st.caption(f"Final License will be: {cnic} # {license_suffix}")

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
        if not validate_license_suffix(license_suffix):
            errors.append("License suffix must be exactly 3 alphanumeric characters.")

        if not (guarantor_male and guarantor_female):
            errors.append("Two guarantors required (at least one female).")

        if errors:
            for e in errors:
                st.error(e)
        else:
            final_license = build_license(cnic, license_suffix)
            st.session_state.applicant = {
                "first_name": first_name.strip(),
                "last_name": last_name.strip(),
                "address": address.strip(),
                "cnic": cnic.strip(),
                "driving_license": final_license,
                "gender": gender,
                "electricity_bills_submitted": (electricity_bills_submitted == "Yes"),
                "guarantor_male": guarantor_male,
                "guarantor_female": guarantor_female,
            }
            st.session_state.page = "scoring"
            st.experimental_rerun()
