# streamlit_app.py

import streamlit as st
import re
import urllib.parse

# -----------------------------
# Utility Functions
# -----------------------------
def validate_cnic(cnic: str) -> bool:
    """Check CNIC format XXXXX-XXXXXXX-X"""
    return bool(re.match(r"^\d{5}-\d{7}-\d{1}$", cnic))

def generate_license_number(cnic: str, suffix: str) -> str:
    """License format = CNIC # XXX"""
    return f"{cnic} #{suffix}"

def income_score(net_salary, gender):
    """Income score with female boost"""
    if net_salary < 50000:
        base_score = 0
    elif 50000 <= net_salary < 70000:
        base_score = 40
    elif 70000 <= net_salary < 90000:
        base_score = 60
    elif 90000 <= net_salary < 110000:
        base_score = 80
    else:
        base_score = 100

    if gender == "F":
        base_score *= 1.1

    return min(base_score, 100)

def bank_balance_score(balance):
    return min((balance / 30000) * 100, 100)

def salary_consistency_score(months):
    return min((months / 12) * 100, 100)

def employer_type_score(employer):
    mapping = {"Govt": 100, "MNC": 80, "SME": 60, "Startup": 40}
    return mapping.get(employer, 0)

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
    return 60

def dependents_score(dep):
    if dep <= 1:
        return 100
    elif dep == 2:
        return 70
    else:
        return 40

def residence_score(res):
    return 100 if res == "Owned" else 60

def dti_ratio(outstanding, bike_price, net_salary):
    if net_salary <= 0:
        return 99
    return (outstanding + bike_price) / net_salary

def dti_score(ratio):
    if ratio <= 0.5:
        return 100
    elif ratio <= 1:
        return 70
    else:
        return 40

def weighted_score(components):
    weights = {
        "income": 0.40,
        "bank": 0.30,
        "salary_consistency": 0.04,
        "employer": 0.04,
        "tenure": 0.04,
        "age": 0.04,
        "dependents": 0.04,
        "residence": 0.05,
        "dti": 0.05,
    }
    total = sum(components[k] * weights[k] for k in weights)
    return total

def final_decision(score):
    if score >= 70:
        return "Approve"
    elif score >= 50:
        return "Review"
    else:
        return "Reject"

def decision_reasons(components, score, decision):
    reasons = []
    if components["income"] < 50:
        reasons.append("Low or moderate income level.")
    else:
        reasons.append("Income level is satisfactory.")

    if components["bank"] >= 100:
        reasons.append("Bank balance fully meets requirement.")
    else:
        reasons.append("Bank balance is below recommended threshold.")

    if components["dti"] <= 50:
        reasons.append("Low debt-to-income ratio, safe profile.")
    elif components["dti"] <= 70:
        reasons.append("Moderate debt-to-income ratio.")
    else:
        reasons.append("High debt-to-income ratio, risky.")

    reasons.append(f"Overall profile fits {decision} criteria.")
    return reasons

# -----------------------------
# Streamlit UI
# -----------------------------
st.set_page_config(page_title="Electric Bike Loan Scoring Portal", layout="centered")

page = st.sidebar.radio("Navigation", ["Applicant Information", "Evaluation", "Results"])

if page == "Applicant Information":
    st.title("Applicant Information")

    first_name = st.text_input("First Name")
    last_name = st.text_input("Last Name")

    cnic = st.text_input("CNIC Number (XXXXX-XXXXXXX-X)")
    if cnic and not validate_cnic(cnic):
        st.error("CNIC must be in format XXXXX-XXXXXXX-X")

    license_suffix = st.text_input("License Number (last 3 digits after #)")
    license_number = generate_license_number(cnic, license_suffix) if cnic and license_suffix else ""

    guarantors = st.radio("Do you have 2 guarantors (at least 1 female)?", ["Yes", "No"])

    address = st.text_input("Address")
    area = st.text_input("Area")
    city = st.text_input("City")

    if address and area and city:
        full_address = f"{address}, {area}, {city}"
        maps_url = f"https://www.google.com/maps/search/{urllib.parse.quote(full_address)}"
        st.markdown(f"[View Location on Google Maps]({maps_url})", unsafe_allow_html=True)

    gender = st.radio("Gender", ["M", "F"])

    st.info("Proceed to the **Evaluation** tab to continue.")

elif page == "Evaluation":
    st.title("Evaluation Criteria")

    net_salary = st.number_input("Net Salary", min_value=0, step=1000)
    bank_balance = st.number_input("Average 6M Bank Balance", min_value=0, step=1000)
    salary_months = st.number_input("Salary credited (months out of 12)", min_value=0, max_value=12, step=1)
    employer = st.selectbox("Employer Type", ["Govt", "MNC", "SME", "Startup"])
    job_years = st.number_input("Job Tenure (years)", min_value=0, step=1)
    age_val = st.number_input("Age", min_value=18, step=1)
    dependents = st.number_input("Number of Dependents", min_value=0, step=1)
    residence = st.radio("Residence Status", ["Owned", "Rented"])
    bike_type = st.selectbox("Bike Type", ["EV-1", "EV-125"])
    bike_price = st.number_input("Bike Price", min_value=0, step=1000)
    outstanding = st.number_input("Outstanding Loan", min_value=0, step=1000)

    st.info("Proceed to the **Results** tab to view the evaluation outcome.")

elif page == "Results":
    st.title("Evaluation Results")

    # Compute scores only if data entered
    if "net_salary" in locals() and net_salary > 0:
        income = income_score(net_salary, gender)
        bank = bank_balance_score(bank_balance)
        sal_cons = salary_consistency_score(salary_months)
        emp = employer_type_score(employer)
        tenure = job_tenure_score(job_years)
        age_s = age_score(age_val)
        dep = dependents_score(dependents)
        res = residence_score(residence)
        dti_r = dti_ratio(outstanding, bike_price, net_salary)
        dti_s = dti_score(dti_r)

        components = {
            "income": income,
            "bank": bank,
            "salary_consistency": sal_cons,
            "employer": emp,
            "tenure": tenure,
            "age": age_s,
            "dependents": dep,
            "residence": res,
            "dti": dti_s,
        }

        final = weighted_score(components)
        decision = final_decision(final)
        reasons = decision_reasons(components, final, decision)

        st.subheader("Scores Breakdown")
        st.write(f"**Income Score:** {income:.1f}")
        st.write(f"**Bank Balance Score:** {bank:.1f}")
        st.write(f"**Salary Consistency Score:** {sal_cons:.1f}")
        st.write(f"**Employer Type Score:** {emp}")
        st.write(f"**Job Tenure Score:** {tenure}")
        st.write(f"**Age Score:** {age_s}")
        st.write(f"**Dependents Score:** {dep}")
        st.write(f"**Residence Score:** {res}")
        st.write(f"**Debt-to-Income Ratio:** {dti_r:.2f}")
        st.write(f"**Debt-to-Income Score:** {dti_s}")
        st.write(f"**Final Weighted Score:** {final:.1f}")
        st.write(f"**Decision:** {decision}")

        st.subheader("Decision Reasons")
        for r in reasons:
            st.write(f"- {r}")

    else:
        st.warning("Please complete the Evaluation inputs first.")
