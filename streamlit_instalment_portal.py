# streamlit_ev_installment_portal.py

import re
import webbrowser
import streamlit as st

# -----------------------------
# Utility functions
# -----------------------------
def validate_cnic(cnic: str) -> bool:
    return bool(re.match(r"^\d{5}-\d{7}-\d{1}$", cnic.strip()))

def validate_license(cnic: str, license_num: str) -> bool:
    """Check license follows CNIC # XXX format"""
    pattern = rf"^{re.escape(cnic)} # \d{{3}}$"
    return bool(re.match(pattern, license_num.strip()))

def open_google_maps(address: str, area: str, city: str):
    full_address = f"{address}, {area}, {city}"
    url = f"https://www.google.com/maps/search/?api=1&query={full_address.replace(' ', '+')}"
    webbrowser.open_new_tab(url)

# -----------------------------
# Scoring Functions
# -----------------------------
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
        return 999
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

def generate_reasons(scores, dti_val, final_decision):
    reasons = []

    if scores["income"] >= 80:
        reasons.append("Strong income level.")
    elif scores["income"] >= 60:
        reasons.append("Moderate income level.")
    else:
        reasons.append("Low income level.")

    if scores["bank_balance"] >= 100:
        reasons.append("Bank balance fully meets requirement.")
    elif scores["bank_balance"] >= 50:
        reasons.append("Bank balance is borderline.")
    else:
        reasons.append("Insufficient bank balance.")

    if scores["dti"] >= 100:
        reasons.append("Low debt-to-income ratio.")
    elif scores["dti"] >= 70:
        reasons.append("Moderate debt-to-income ratio.")
    else:
        reasons.append("High debt-to-income ratio, risky.")

    if final_decision == "Approve":
        reasons.append("Profile fits approval criteria.")
    elif final_decision == "Review":
        reasons.append("Profile is borderline, requires manual review.")
    else:
        reasons.append("Profile does not meet lending criteria.")

    return reasons

# -----------------------------
# Streamlit App Layout
# -----------------------------
st.set_page_config(page_title="Wavetec EV Installment Scoring", layout="wide")
st.title("Wavetec Electric Bike Installment Portal")

if "page" not in st.session_state:
    st.session_state.page = "applicant"
if "applicant" not in st.session_state:
    st.session_state.applicant = {}
if "scoring" not in st.session_state:
    st.session_state.scoring = {}
if "result" not in st.session_state:
    st.session_state.result = {}

# ---------- Page 1: Applicant Info ----------
if st.session_state.page == "applicant":
    st.header("Step 1 — Applicant Information")

    col1, col2 = st.columns(2)
    first_name = col1.text_input("First Name", value=st.session_state.applicant.get("first_name", ""))
    last_name = col2.text_input("Last Name", value=st.session_state.applicant.get("last_name", ""))

    address = st.text_input("Address", value=st.session_state.applicant.get("address", ""))
    area = st.text_input("Area", value=st.session_state.applicant.get("area", ""))
    city = st.text_input("City", value=st.session_state.applicant.get("city", ""))

    if st.button("View on Google Maps"):
        if address and area and city:
            open_google_maps(address, area, city)

    cnic = st.text_input("CNIC (format: 12345-1234567-1)", value=st.session_state.applicant.get("cnic", ""))
    driving_license = st.text_input("Driving License (CNIC # XXX)", value=st.session_state.applicant.get("driving_license", ""))

    electricity_bills_submitted = st.radio("Electricity Bills Submitted?", ["Yes", "No"], index=0)
    g_col1, g_col2 = st.columns(2)
    guarantor_male = g_col1.checkbox("Male Guarantor Present", value=st.session_state.applicant.get("guarantor_male", False))
    guarantor_female = g_col2.checkbox("Female Guarantor Present", value=st.session_state.applicant.get("guarantor_female", False))
    gender = st.selectbox("Gender", ["Male", "Female"], index=0)

    if st.button("Validate & Continue"):
        errors = []
        if not first_name.strip():
            errors.append("First name is required.")
        if not last_name.strip():
            errors.append("Last name is required.")
        if not address.strip() or not area.strip() or not city.strip():
            errors.append("Full address (address, area, city) is required.")
        if not cnic.strip() or not validate_cnic(cnic):
            errors.append("CNIC is invalid (format: 12345-1234567-1).")
        if not driving_license.strip() or not validate_license(cnic, driving_license):
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
                "area": area.strip(),
                "city": city.strip(),
                "cnic": cnic.strip(),
                "driving_license": driving_license.strip(),
                "electricity_bills_submitted": electricity_bills_submitted == "Yes",
                "guarantor_male": guarantor_male,
                "guarantor_female": guarantor_female,
                "gender": gender,
            }
            st.session_state.page = "scoring"
            st.experimental_rerun()

# ---------- Page 2: Scoring ----------
elif st.session_state.page == "scoring":
    st.header("Step 2 — Scoring Inputs")

    net_salary = st.number_input("Net Salary (PKR)", min_value=0, step=1000)
    bank_balance = st.number_input("Average 6-month Bank Balance (PKR)", min_value=0, step=1000)
    months_consistent = st.slider("Salary Consistency (months out of 12)", 0, 12, 12)
    employer_type = st.selectbox("Employer Type", ["Govt", "MNC", "SME", "Startup"])
    job_tenure_years = st.number_input("Job Tenure (years)", min_value=0, step=1)
    age = st.number_input("Age (years)", min_value=18, step=1)
    dependents = st.number_input("Number of Dependents", min_value=0, step=1)
    residence_type = st.selectbox("Residence Type", ["Owned", "Rented"])

    bike_type = st.selectbox("Bike Type", ["EV-1", "EV-125"])
    bike_price = st.number_input("Bike Price (PKR)", min_value=0, step=1000)
    outstanding_loan = st.number_input("Outstanding Loan (PKR)", min_value=0, step=1000)

    if st.button("Calculate Score"):
        inc = income_score(net_salary, st.session_state.applicant["gender"])
        bal = bank_balance_score(bank_balance)
        sal_cons = salary_consistency_score(months_consistent)
        emp = employer_type_score(employer_type)
        job_ten = job_tenure_score(job_tenure_years)
        age_s = age_score(age)
        dep_s = dependents_score(dependents)
        res_s = residence_score(residence_type)
        dti_val = dti_ratio(outstanding_loan, bike_price, net_salary)
        dti_s = dti_score(dti_val)

        scores = {
            "income": inc,
            "bank_balance": bal,
            "salary_consistency": sal_cons,
            "employer_type": emp,
            "job_tenure": job_ten,
            "age": age_s,
            "dependents": dep_s,
            "residence": res_s,
            "dti": dti_s,
        }

        final = weighted_final_score(scores)
        final_dec = decision(final)
        reasons = generate_reasons(scores, dti_val, final_dec)

        st.session_state.result = {
            "scores": scores,
            "dti_val": dti_val,
            "final": final,
            "decision": final_dec,
            "reasons": reasons,
        }
        st.session_state.page = "results"
        st.experimental_rerun()

# ---------- Page 3: Results ----------
elif st.session_state.page == "results":
    st.header("Step 3 — Results & Decision")
    result = st.session_state.result

    st.subheader("Output Variables")
    for k, v in result["scores"].items():
        st.write(f"**{k.replace('_', ' ').title()} Score:** {v:.1f}")
    st.write(f"**Debt-to-Income Ratio:** {result['dti_val']:.2f}")
    st.write(f"**Final Weighted Score:** {result['final']:.1f}")
    st.write(f"**Decision:** {result['decision']}")

    st.subheader("Decision Reasons")
    for r in result["reasons"]:
        st.write("•", r)

    if st.button("New Applicant"):
        st.session_state.page = "applicant"
        st.session_state.applicant = {}
        st.session_state.scoring = {}
        st.session_state.result = {}
        st.experimental_rerun()
