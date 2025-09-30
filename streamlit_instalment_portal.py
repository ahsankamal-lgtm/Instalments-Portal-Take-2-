# streamlit_app.py

import streamlit as st

# -----------------------------
# Scoring Functions
# -----------------------------

def income_score(net_salary, gender):
    """Categorize income with female adjustment"""
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
    """Bank balance relative to 30k target (3x EMI)"""
    return min((balance / 30000) * 100, 100)


def salary_consistency_score(months_consistent):
    """Salary credit regularity"""
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
        return 2.0  # worst case
    return (outstanding + bike_price) / net_salary


def dti_score(dti):
    if dti <= 0.5:
        return 100
    elif dti <= 1.0:
        return 70
    else:
        return 40


def weighted_final_score(scores):
    """Weighted average based on framework"""
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

# -----------------------------
# Streamlit App UI
# -----------------------------
st.set_page_config(page_title="Wavetec EV Loan Scoring Portal", layout="centered")

st.title("Wavetec EV Loan Scoring Portal")
st.markdown("This tool evaluates applicants for EV bike installment approval based on financial and demographic factors.")

# Applicant Inputs
st.subheader("Applicant Information")

net_salary = st.number_input("Net Salary (PKR)", min_value=0, step=1000, format="%d")
gender = st.selectbox("Gender", ["Male", "Female"])
bank_balance = st.number_input("Average 6-month Bank Balance (PKR)", min_value=0, step=1000, format="%d")

months_consistent = st.slider("Salary Consistency (months out of 12)", 0, 12, 12)
employer_type = st.selectbox("Employer Type", ["Govt", "MNC", "SME", "Startup"])
job_tenure_years = st.number_input("Job Tenure (years)", min_value=0, step=1)
age = st.number_input("Age (years)", min_value=18, step=1)
dependents = st.number_input("Number of Dependents", min_value=0, step=1)
residence_type = st.selectbox("Residence Type", ["Owned", "Rented"])

bike_type = st.selectbox("Bike Type", ["EV-1", "EV-125"])
bike_price = st.number_input("Bike Price (PKR)", min_value=0, step=1000, format="%d")
outstanding_loan = st.number_input("Outstanding Loan (PKR)", min_value=0, step=1000, format="%d")

# -----------------------------
# Calculations
# -----------------------------
income = income_score(net_salary, gender)
bank_bal = bank_balance_score(bank_balance)
salary_cons = salary_consistency_score(months_consistent)
employer = employer_type_score(employer_type)
job_ten = job_tenure_score(job_tenure_years)
age_s = age_score(age)
dep_s = dependents_score(dependents)
res_s = residence_score(residence_type)

dti = dti_ratio(outstanding_loan, bike_price, net_salary)
dti_s = dti_score(dti)

scores = {
    "income": income,
    "bank_balance": bank_bal,
    "salary_consistency": salary_cons,
    "employer_type": employer,
    "job_tenure": job_ten,
    "age": age_s,
    "dependents": dep_s,
    "residence": res_s,
    "dti": dti_s,
}

final = weighted_final_score(scores)
final_dec = decision(final)

# -----------------------------
# Output
# ---------------------
