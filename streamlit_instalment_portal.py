# streamlit_app.py

import streamlit as st
import urllib.parse

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

    if gender == "F":
        base_score *= 1.1

    return min(base_score, 100)


def bank_balance_score(balance):
    """Score for average 6M bank balance"""
    return min((balance / 30000) * 100, 100)


def salary_consistency_score(months):
    """Score for salary credit consistency"""
    return min((months / 12) * 100, 100)


def employer_type_score(employer):
    mapping = {"Govt": 100, "MNC": 80, "SME": 60, "Startup": 40}
    return mapping.get(employer, 0)


def job_tenure_score(years):
    if years >= 3:
        return 100
    elif years >= 1:
        return 70
    else:
        return 40


def age_score(age):
    return 100 if 25 <= age <= 55 else 60


def dependents_score(dep):
    if dep <= 1:
        return 100
    elif dep == 2:
        return 70
    else:
        return 40


def residence_score(res):
    return 100 if res == "Owned" else 60


def dti_score(outstanding, bike_price, net_salary):
    if net_salary <= 0:
        return 0
    ratio = (outstanding + bike_price) / net_salary
    if ratio <= 0.5:
        return 100
    elif ratio <= 1:
        return 70
    else:
        return 40, ratio
    return 0, ratio


def final_weighted_score(scores):
    """Weighted scoring framework"""
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
    if scores["income"] < 50:
        reasons.append("Income level is on the lower side.")
    else:
        reasons.append("Income level is acceptable.")
    if scores["bank_balance"] < 100:
        reasons.append("Bank balance does not fully meet requirement.")
    else:
        reasons.append("Bank balance fully meets requirement.")
    if scores["dti"] < 70:
        reasons.append("High debt-to-income ratio, risky.")
    else:
        reasons.append("Debt-to-income ratio within acceptable limits.")
    if decision_text == "Approve":
        reasons.append("Profile fits approval criteria.")
    elif decision_text == "Review":
        reasons.append("Profile requires manual review due to mixed factors.")
    else:
        reasons.append("Profile rejected due to high risk factors.")
    return reasons


# -----------------------------
# Streamlit UI
# -----------------------------
st.set_page_config(page_title="Electric Bike Finance Portal", layout="centered")

st.title("Electric Bike Finance Portal")

# Navigation Tabs
tabs = st.tabs(["Applicant Information", "Evaluation", "Results"])

# -----------------------------
# Applicant Information
# -----------------------------
with tabs[0]:
    st.subheader("Applicant Information")

    first_name = st.text_input("First Name")
    last_name = st.text_input("Last Name")

    cnic = st.text_input("CNIC Number (XXXXX-XXXXXXX-X)")
    license_suffix = st.text_input("License Suffix (last 3 digits after #)")
    license_number = f"{cnic}#{license_suffix}" if cnic and license_suffix else ""

    guarantors = st.radio("Are two guarantors available (1 female required)?", ["Yes", "No"])

    address = st.text_input("Street Address")
    area = st.text_input("Area")
    city = st.text_input("City")

    if st.button("View Location on Google Maps"):
        if address and area and city:
            full_address = f"{address}, {area}, {city}"
            encoded = urllib.parse.quote_plus(full_address)
            maps_url = f"https://www.google.com/maps/search/?api=1&query={encoded}"
            st.markdown(f"[Click here to view location on Google Maps]({maps_url})", unsafe_allow_html=True)
        else:
            st.error("Please complete Address, Area, and City before viewing on Maps.")

    gender = st.radio("Gender", ["M", "F"])

    applicant_valid = all([first_name, last_name, cnic, license_suffix, guarantors == "Yes", address, area, city, gender])

    if applicant_valid:
        st.success("Applicant information completed. Please proceed to the Evaluation tab.")
    else:
        st.info("Please complete all fields to proceed.")


# -----------------------------
# Evaluation
# -----------------------------
with tabs[1]:
    st.subheader("Evaluation Inputs")

    if not applicant_valid:
        st.warning("Please complete Applicant Information first.")
    else:
        net_salary = st.number_input("Net Salary", min_value=0, step=1000)
        bank_balance = st.number_input("Average 6M Bank Balance", min_value=0, step=1000)
        salary_consistency = st.number_input("Salary credited (months out of 12)", min_value=0, max_value=12, step=1)
        employer_type = st.selectbox("Employer Type", ["Govt", "MNC", "SME", "Startup"])
        job_tenure = st.number_input("Job Tenure (years)", min_value=0, step=1)
        age = st.number_input("Age", min_value=18, step=1)
        dependents = st.number_input("Number of Dependents", min_value=0, step=1)
        residence = st.radio("Residence Type", ["Owned", "Rented"])
        bike_type = st.selectbox("Bike Type", ["EV-1", "EV-125"])
        bike_price = st.number_input("Bike Price", min_value=0, step=1000)
        outstanding_loan = st.number_input("Outstanding Loan", min_value=0, step=1000)

        # Calculate Scores
        scores = {
            "income": income_score(net_salary, gender),
            "bank_balance": bank_balance_score(bank_balance),
            "salary_consistency": salary_consistency_score(salary_consistency),
            "employer_type": employer_type_score(employer_type),
            "job_tenure": job_tenure_score(job_tenure),
            "age": age_score(age),
            "dependents": dependents_score(dependents),
            "residence": residence_score(residence),
        }

        dti_val = (outstanding_loan + bike_price) / net_salary if net_salary > 0 else 0
        if dti_val <= 0.5:
            scores["dti"] = 100
        elif dti_val <= 1:
            scores["dti"] = 70
        else:
            scores["dti"] = 40

        final = final_weighted_score(scores)
        decision_text = decision(final)
        reasons = decision_reasons(scores, decision_text)

        st.session_state["results"] = {
            "scores": scores,
            "dti_val": dti_val,
            "final": final,
            "decision_text": decision_text,
            "reasons": reasons,
        }

        st.success("Evaluation completed. Please proceed to the Results tab.")


# -----------------------------
# Results
# -----------------------------
with tabs[2]:
    st.subheader("Results")

    if "results" not in st.session_state:
        st.warning("Please complete the Evaluation first.")
    else:
        res = st.session_state["results"]

        st.write("### Score Breakdown")
        st.write(f"**Income Score:** {res['scores']['income']:.1f}")
        st.write(f"**Bank Balance Score:** {res['scores']['bank_balance']:.1f}")
        st.write(f"**Salary Consistency Score:** {res['scores']['salary_consistency']:.1f}")
        st.write(f"**Employer Type Score:** {res['scores']['employer_type']:.1f}")
        st.write(f"**Job Tenure Score:** {res['scores']['job_tenure']:.1f}")
        st.write(f"**Age Score:** {res['scores']['age']:.1f}")
        st.write(f"**Dependents Score:** {res['scores']['dependents']:.1f}")
        st.write(f"**Residence Score:** {res['scores']['residence']:.1f}")
        st.write(f"**Debt-to-Income Ratio:** {res['dti_val']:.2f}")
        st.write(f"**Debt-to-Income Score:** {res['scores']['dti']:.1f}")

        st.write("### Final Results")
        st.write(f"**Final Weighted Score:** {res['final']:.1f}")
        st.write(f"**Decision:** {res['decision_text']}")

        st.write("### Decision Reasons")
        for r in res["reasons"]:
            st.write(f"- {r}")
