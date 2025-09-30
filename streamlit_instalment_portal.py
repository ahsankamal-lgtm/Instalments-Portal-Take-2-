# streamlit_app.py

import streamlit as st
import re
import webbrowser

# -----------------------------
# Utility Functions
# -----------------------------

def income_score(net_salary, gender):
    """Calculate income score with female adjustment"""
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

    if gender == "Female":
        base_score = min(base_score * 1.1, 100)
    return base_score


def bank_balance_score(balance):
    return min((balance / 30000) * 100, 100)


def salary_consistency_score(months):
    return min((months / 12) * 100, 100)


def employer_type_score(employer):
    mapping = {"Govt": 100, "MNC": 80, "SME": 60, "Startup": 40}
    return mapping.get(employer, 60)


def job_tenure_score(years):
    if years >= 3:
        return 100
    elif 1 <= years < 3:
        return 70
    else:
        return 40


def age_score(age):
    return 100 if 25 <= age <= 55 else 60


def dependents_score(dependents):
    if dependents <= 1:
        return 100
    elif dependents == 2:
        return 70
    else:
        return 40


def residence_score(res):
    return 100 if res == "Owned" else 60


def dti_ratio(outstanding, bike_price, net_salary):
    if net_salary <= 0:
        return float("inf")
    return (outstanding + bike_price) / net_salary


def dti_score(ratio):
    if ratio <= 0.5:
        return 100
    elif ratio <= 1:
        return 70
    else:
        return 40


def weighted_score(scores):
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
    if final_score >= 75:
        return "Approve"
    elif final_score >= 60:
        return "Review"
    else:
        return "Reject"


def decision_reasons(scores, decision_text):
    reasons = []
    if scores["income"] < 60:
        reasons.append("Moderate or low income level.")
    else:
        reasons.append("Strong income profile.")
    if scores["bank_balance"] >= 100:
        reasons.append("Bank balance fully meets requirement.")
    else:
        reasons.append("Insufficient bank balance.")
    if scores["dti"] < 70:
        reasons.append("High debt-to-income ratio, risky.")
    else:
        reasons.append("Debt-to-income ratio acceptable.")
    if decision_text == "Approve":
        reasons.append("Profile fits approval criteria.")
    elif decision_text == "Review":
        reasons.append("Borderline case, manual review recommended.")
    else:
        reasons.append("Fails key eligibility checks.")
    return reasons


# -----------------------------
# Streamlit App
# -----------------------------

st.set_page_config(page_title="Electric Bike Loan Portal", layout="centered")
st.title("Electric Bike Loan Scoring Portal")

# Navigation
page = st.sidebar.radio("Navigation", ["Applicant Info", "Scoring", "Results"])

# Session state
if "applicant_data" not in st.session_state:
    st.session_state.applicant_data = {}
if "scores" not in st.session_state:
    st.session_state.scores = {}
if "final_score" not in st.session_state:
    st.session_state.final_score = 0
if "decision" not in st.session_state:
    st.session_state.decision = ""

# -----------------------------
# Applicant Info Page
# -----------------------------
if page == "Applicant Info":
    st.subheader("Applicant Information")

    cnic = st.text_input("CNIC Number (xxxxx-xxxxxxx-x)")
    gender = st.selectbox("Gender", ["Male", "Female"])
    net_salary = st.number_input("Net Salary", min_value=0, step=1000, format="%d")
    avg_balance = st.number_input("Average 6M Bank Balance", min_value=0, step=1000, format="%d")

    salary_months = st.number_input("Salary Consistency (Months, 0–12)", min_value=0, max_value=12, step=1)
    employer = st.selectbox("Employer Type", ["Govt", "MNC", "SME", "Startup"])
    job_tenure_years = st.number_input("Job Tenure (Years)", min_value=0, step=1)
    age = st.number_input("Age", min_value=18, step=1)
    dependents = st.number_input("Number of Dependents", min_value=0, step=1)
    residence = st.selectbox("Residence", ["Owned", "Rented"])

    bike_type = st.selectbox("Bike Type", ["EV-1", "EV-125"])
    bike_price = st.number_input("Bike Price", min_value=0, step=1000, format="%d")
    outstanding = st.number_input("Outstanding Loan", min_value=0, step=1000, format="%d")

    # Address fields
    address = st.text_input("Street Address")
    area = st.text_input("Area")
    city = st.text_input("City")

    if st.button("View on Google Maps"):
        query = f"{address}, {area}, {city}"
        maps_url = f"https://www.google.com/maps/search/?api=1&query={query.replace(' ', '+')}"
        st.markdown(f"[Open in Google Maps]({maps_url})", unsafe_allow_html=True)

    license_number = st.text_input("Driving License Number (CNIC # XXX)")
    if license_number and not re.match(rf"^{cnic} #\d{{3}}$", license_number):
        st.error("License number must match CNIC # XXX format.")

    if st.button("Save Applicant Info"):
        st.session_state.applicant_data = {
            "cnic": cnic,
            "gender": gender,
            "net_salary": net_salary,
            "avg_balance": avg_balance,
            "salary_months": salary_months,
            "employer": employer,
            "job_tenure_years": job_tenure_years,
            "age": age,
            "dependents": dependents,
            "residence": residence,
            "bike_type": bike_type,
            "bike_price": bike_price,
            "outstanding": outstanding,
            "address": address,
            "area": area,
            "city": city,
            "license_number": license_number,
        }
        st.success("Applicant info saved. Move to Scoring page.")

# -----------------------------
# Scoring Page
# -----------------------------
elif page == "Scoring":
    if not st.session_state.applicant_data:
        st.warning("Please fill Applicant Info first.")
    else:
        st.subheader("Scoring Evaluation")
        d = st.session_state.applicant_data

        income = income_score(d["net_salary"], d["gender"])
        bank = bank_balance_score(d["avg_balance"])
        salary_cons = salary_consistency_score(d["salary_months"])
        employer_s = employer_type_score(d["employer"])
        tenure = job_tenure_score(d["job_tenure_years"])
        age_s = age_score(d["age"])
        dep_s = dependents_score(d["dependents"])
        res_s = residence_score(d["residence"])
        ratio = dti_ratio(d["outstanding"], d["bike_price"], d["net_salary"])
        dti_s = dti_score(ratio)

        scores = {
            "income": income,
            "bank_balance": bank,
            "salary_consistency": salary_cons,
            "employer_type": employer_s,
            "job_tenure": tenure,
            "age": age_s,
            "dependents": dep_s,
            "residence": res_s,
            "dti": dti_s,
        }

        final = weighted_score(scores)
        dec = decision(final)

        st.session_state.scores = scores
        st.session_state.final_score = final
        st.session_state.decision = dec

        st.success("Scoring complete. Move to Results page.")

# -----------------------------
# Results Page
# -----------------------------
elif page == "Results":
    if not st.session_state.scores:
        st.warning("Please run scoring first.")
    else:
        st.subheader("Results")

        for k, v in st.session_state.scores.items():
            st.write(f"**{k.replace('_',' ').title()} Score:** {v:.1f}")

        d = st.session_state.applicant_data
        ratio = dti_ratio(d["outstanding"], d["bike_price"], d["net_salary"])
        st.write(f"**Debt-to-Income Ratio:** {ratio:.2f}")
        st.write(f"**Final Score:** {st.session_state.final_score:.1f}")
        st.write(f"**Decision:** {st.session_state.decision}")

        st.markdown("### Decision Reasons")
        for reason in decision_reasons(st.session_state.scores, st.session_state.decision):
            st.write(f"- {reason}")
