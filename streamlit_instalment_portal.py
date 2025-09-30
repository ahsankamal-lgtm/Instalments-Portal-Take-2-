# streamlit_ev_portal_nodb.py
import re
import streamlit as st

# ----------------------------
# Utility
# ----------------------------
def validate_cnic(cnic: str) -> bool:
    return bool(re.match(r"^\d{5}-\d{7}-\d{1}$", cnic.strip()))

def build_license(cnic: str, suffix: str) -> str:
    return f"{cnic} # {suffix.strip()}"

def validate_license_suffix(suffix: str) -> bool:
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

# ---------- Page 2 ----------
elif st.session_state.page == "scoring":
    st.header("Step 2 — Evaluation Inputs")

    net_salary = st.text_input("Net Salary (e.g., 50,000)")
    avg_balance = st.text_input("6-Month Avg Bank Balance (e.g., 30,000)")
    salary_consistency = st.number_input("Salary Credit Consistency (months out of 12)", 0, 12, 12)
    employer_type = st.selectbox("Employer Type", ["Govt", "MNC", "SME", "Startup"])
    job_tenure = st.number_input("Job Tenure (years)", 0, 50, 1)
    age = st.number_input("Age", 18, 70, 30)
    dependents = st.number_input("Number of Dependents", 0, 10, 0)
    residence = st.selectbox("Residence Type", ["Owned", "Rented"])
    bike_price = st.text_input("Bike Selling Price (e.g., 125,000)")
    outstanding_loan = st.text_input("Outstanding Loan Amount (e.g., 20,000)")

    if st.button("Calculate"):
        net_salary_int = parse_int_amount(net_salary)
        avg_balance_int = parse_int_amount(avg_balance)
        bike_price_int = parse_int_amount(bike_price)
        outstanding_loan_int = parse_int_amount(outstanding_loan)

        scores = {
            "income": income_score(net_salary_int, st.session_state.applicant["gender"]),
            "bank_balance": bank_balance_score(avg_balance_int),
            "salary_consistency": salary_consistency_score(salary_consistency),
            "employer_type": employer_type_score(employer_type),
            "job_tenure": job_tenure_score(job_tenure),
            "age": age_score(age),
            "dependents": dependents_score(dependents),
            "residence": residence_score(residence),
        }

        dti_r = dti_ratio(outstanding_loan_int, bike_price_int, net_salary_int)
        scores["dti"] = dti_score(dti_r)

        final_score = weighted_final_score(scores)
        decision_val = decision(final_score)
        reasons = generate_reasons(scores, dti_r, decision_val, st.session_state.applicant)

        st.session_state.scoring = {
            "scores": scores,
            "dti_ratio": dti_r,
            "final_score": final_score,
            "decision": decision_val,
            "reasons": reasons,
        }
        st.session_state.page = "results"
        st.experimental_rerun()

# ---------- Page 3 ----------
elif st.session_state.page == "results":
    st.header("Step 3 — Results")

    s = st.session_state.scoring["scores"]
    dti_r = st.session_state.scoring["dti_ratio"]
    final_score = st.session_state.scoring["final_score"]
    decision_val = st.session_state.scoring["decision"]
    reasons = st.session_state.scoring["reasons"]

    st.subheader("Scoring Breakdown")
    st.table({
        "Variable": [
            "Income Score (with gender adj.)",
            "Bank Balance Score",
            "Salary Consistency Score",
            "Employer Type Score",
            "Job Tenure Score",
            "Age Score",
            "Dependents Score",
            "Residence Score",
            "Debt-to-Income Ratio",
            "Debt-to-Income Score",
            "Final Score (0-100)",
            "Decision"
        ],
        "Value": [
            f"{s['income']:.1f}",
            f"{s['bank_balance']:.1f}",
            f"{s['salary_consistency']:.1f}",
            f"{s['employer_type']:.1f}",
            f"{s['job_tenure']:.1f}",
            f"{s['age']:.1f}",
            f"{s['dependents']:.1f}",
            f"{s['residence']:.1f}",
            f"{dti_r:.3f}",
            f"{s['dti']:.1f}",
            f"{final_score:.1f}",
            decision_val
        ]
    })

    st.subheader("Reasons")
    for r in reasons:
        st.write(f"- {r}")

    if st.button("New Application"):
        st.session_state.page = "applicant"
        st.session_state.applicant = {}
        st.session_state.scoring = {}
        st.experimental_rerun()
