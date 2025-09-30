# streamlit_ev_portal.py
import re
import streamlit as st

# -----------------------------
# Validation helpers
# -----------------------------
def validate_cnic(cnic: str) -> bool:
    return bool(re.match(r"^\d{5}-\d{7}-\d{1}$", cnic.strip()))

def validate_license(license_number: str, cnic: str) -> bool:
    """License must follow CNIC + #XXX format"""
    pattern = f"^{re.escape(cnic)} #[0-9]{{3}}$"
    return bool(re.match(pattern, license_number.strip()))

def parse_int_amount(text: str) -> int:
    if text is None:
        return 0
    s = str(text).replace(",", "").strip()
    try:
        return int(float(s))
    except Exception:
        return 0

# -----------------------------
# Scoring functions
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

def bank_balance_score(balance, installment_amount):
    return min((balance / (3 * installment_amount)) * 100, 100)

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
        return 99
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

def generate_reasons(scores, dti_value, decision_val, applicant):
    reasons = []

    # Income
    if scores["income"] >= 80:
        reasons.append("Strong income level.")
    elif scores["income"] >= 60:
        reasons.append("Moderate income level.")
    else:
        reasons.append("Low income level.")

    # Bank balance
    if scores["bank_balance"] >= 100:
        reasons.append("Bank balance fully meets requirement.")
    elif scores["bank_balance"] >= 60:
        reasons.append("Bank balance borderline.")
    else:
        reasons.append("Insufficient bank balance.")

    # DTI
    if dti_value <= 0.5:
        reasons.append("Low debt-to-income ratio.")
    elif dti_value <= 1:
        reasons.append("Moderate debt-to-income ratio.")
    else:
        reasons.append("High debt-to-income ratio, risky.")

    # Guarantors
    if not (applicant.get("guarantor_male") and applicant.get("guarantor_female")):
        reasons.append("Missing required male/female guarantors.")

    # Electricity bills
    if not applicant.get("electricity_bills_submitted"):
        reasons.append("Electricity bills not submitted.")

    # Final decision pointer
    if decision_val == "Approve":
        reasons.append("Profile fits approval criteria.")
    elif decision_val == "Review":
        reasons.append("Borderline case, manual review advised.")
    else:
        reasons.append("Does not meet approval criteria.")

    return list(dict.fromkeys(reasons))  # remove duplicates

# -----------------------------
# Streamlit App
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

# -------- Page 1: Applicant Info --------
if st.session_state.page == "applicant":
    st.header("Step 1 — Applicant Information")

    col1, col2 = st.columns(2)
    first_name = col1.text_input("First Name", value=st.session_state.applicant.get("first_name", ""))
    last_name = col2.text_input("Last Name", value=st.session_state.applicant.get("last_name", ""))
    address = st.text_area("Residential Address", value=st.session_state.applicant.get("address", ""))

    cnic = st.text_input("CNIC (12345-1234567-1)", value=st.session_state.applicant.get("cnic", ""))

    # License auto-prefix with CNIC
    license_suffix = st.text_input("Driving License Suffix (XXX)", value="")
    driving_license = f"{cnic} #{license_suffix}" if cnic and license_suffix else ""

    electricity_bills_submitted = st.radio("Electricity Bills Submitted?", ["Yes", "No"])
    g_col1, g_col2 = st.columns(2)
    guarantor_male = g_col1.checkbox("Male Guarantor", value=False)
    guarantor_female = g_col2.checkbox("Female Guarantor", value=False)
    gender = st.selectbox("Gender", ["Male", "Female"])

    if st.button("Validate & Continue"):
        errors = []
        if not validate_cnic(cnic):
            errors.append("Invalid CNIC format.")
        if not validate_license(driving_license, cnic):
            errors.append("Driving license must match CNIC # XXX format.")
        if not (guarantor_male and guarantor_female):
            errors.append("Two guarantors required (at least one female).")

        if errors:
            for e in errors:
                st.error(e)
        else:
            st.session_state.applicant = {
                "first_name": first_name,
                "last_name": last_name,
                "address": address,
                "cnic": cnic,
                "driving_license": driving_license,
                "electricity_bills_submitted": (electricity_bills_submitted == "Yes"),
                "guarantor_male": guarantor_male,
                "guarantor_female": guarantor_female,
                "gender": gender,
            }
            st.session_state.page = "scoring"
            st.experimental_rerun()

# -------- Page 2: Scoring --------
elif st.session_state.page == "scoring":
    st.header("Step 2 — Scoring")

    col1, col2 = st.columns(2)
    net_salary = col1.number_input("Net Salary (PKR)", min_value=0, step=1000)
    bank_balance = col2.number_input("Average 6M Bank Balance (PKR)", min_value=0, step=1000)

    months_consistent = st.slider("Salary Consistency (months)", 0, 12, 12)
    employer_type = st.selectbox("Employer Type", ["Govt", "MNC", "SME", "Startup"])
    job_tenure_years = st.number_input("Job Tenure (years)", min_value=0, step=1)
    age = st.number_input("Age", min_value=18, step=1)
    dependents = st.number_input("Dependents", min_value=0, step=1)
    residence_type = st.selectbox("Residence Type", ["Owned", "Rented"])

    installment_amount = st.number_input("Installment Amount (PKR)", min_value=1000, step=500, value=10000)
    bike_type = st.selectbox("Bike Type", ["EV-1", "EV-125"])
    bike_price = st.number_input("Bike Price (PKR)", min_value=0, step=1000)
    outstanding_loan = st.number_input("Outstanding Loan (PKR)", min_value=0, step=1000)

    if st.button("Calculate Score"):
        scores = {
            "income": income_score(net_salary, st.session_state.applicant.get("gender")),
            "bank_balance": bank_balance_score(bank_balance, installment_amount),
            "salary_consistency": salary_consistency_score(months_consistent),
            "employer_type": employer_type_score(employer_type),
            "job_tenure": job_tenure_score(job_tenure_years),
            "age": age_score(age),
            "dependents": dependents_score(dependents),
            "residence": residence_score(residence_type),
            "dti": dti_score(dti_ratio(outstanding_loan, bike_price, net_salary)),
        }

        final = weighted_final_score(scores)
        final_dec = decision(final)
        dti_val = dti_ratio(outstanding_loan, bike_price, net_salary)
        reasons = generate_reasons(scores, dti_val, final_dec, st.session_state.applicant)

        st.session_state.result = {
            "scores": scores,
            "final_score": final,
            "decision": final_dec,
            "dti_value": dti_val,
            "reasons": reasons,
        }
        st.session_state.page = "results"
        st.experimental_rerun()

# -------- Page 3: Results --------
elif st.session_state.page == "results":
    st.header("Step 3 — Results & Decision")

    result = st.session_state.result
    scores = result["scores"]

    st.subheader("Output Variables")
    st.write(f"Income Score (with gender adj.): {scores['income']:.1f}")
    st.write(f"Bank Balance Score: {scores['bank_balance']:.1f}")
    st.write(f"Salary Consistency Score: {scores['salary_consistency']:.1f}")
    st.write(f"Employer Type Score: {scores['employer_type']:.1f}")
    st.write(f"Job Tenure Score: {scores['job_tenure']:.1f}")
    st.write(f"Age Score: {scores['age']:.1f}")
    st.write(f"Dependents Score: {scores['dependents']:.1f}")
    st.write(f"Residence Score: {scores['residence']:.1f}")
    st.write(f"Debt-to-Income Ratio: {result['dti_value']:.2f}")
    st.write(f"Debt-to-Income Score: {scores['dti']:.1f}")
    st.markdown("---")
    st.write(f"Final Weighted Score: {result['final_score']:.1f}")
    st.write(f"Decision: **{result['decision']}**")

    st.subheader("Decision Reasons")
    for r in result["reasons"]:
        st.write("•", r)

    if st.button("New Applicant"):
        st.session_state.page = "applicant"
        st.session_state.applicant = {}
        st.session_state.scoring = {}
        st.session_state.result = {}
        st.experimental_rerun()
