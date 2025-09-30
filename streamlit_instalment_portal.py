# streamlit_app.py

import streamlit as st

# -----------------------------
# Utility Functions
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


def salary_consistency_score(months):
    return min((months / 12) * 100, 100)


def employer_type_score(emp_type):
    mapping = {"Govt": 100, "MNC": 80, "SME": 60, "Startup": 40}
    return mapping.get(emp_type, 0)


def job_tenure_score(years):
    if years >= 3:
        return 100
    elif years >= 1:
        return 70
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
    return 40


def residence_score(res):
    return 100 if res == "Owned" else 60


def dti_ratio(outstanding, bike_price, salary):
    if salary <= 0:
        return float("inf")
    return (outstanding + bike_price) / salary


def dti_score(ratio):
    if ratio <= 0.5:
        return 100
    elif ratio <= 1.0:
        return 70
    return 40


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
    return sum(inputs[k] * weights[k] for k in inputs)


def decision(final):
    if final >= 75:
        return "Approve"
    elif final >= 60:
        return "Review"
    return "Reject"


def decision_reasons(scores, decision_outcome):
    reasons = []
    if scores["income"] < 60:
        reasons.append("Moderate income level.")
    else:
        reasons.append("Strong income profile.")
    if scores["bank_balance"] >= 100:
        reasons.append("Bank balance fully meets requirement.")
    else:
        reasons.append("Bank balance below recommended threshold.")
    if scores["dti"] < 70:
        reasons.append("High debt-to-income ratio, risky.")
    else:
        reasons.append("Debt-to-income ratio acceptable.")
    if decision_outcome == "Approve":
        reasons.append("Overall profile fits approval criteria.")
    elif decision_outcome == "Review":
        reasons.append("Borderline profile, requires manual review.")
    else:
        reasons.append("Profile does not meet lending standards.")
    return reasons


# -----------------------------
# Streamlit App
# -----------------------------
st.set_page_config(page_title="Electric Bike Loan Scoring Portal", layout="centered")
st.title("⚡ Electric Bike Loan Scoring Portal")

page = st.sidebar.radio("Navigate", ["Applicant Information", "Evaluation", "Results"])

# -----------------------------
# Page 1: Applicant Information
# -----------------------------
if page == "Applicant Information":
    st.header("Applicant Information")

    cnic = st.text_input("CNIC Number", placeholder="e.g. 42101-1234567-1")
    last_three = st.text_input("Driving License (Last 3 Digits)", placeholder="e.g. 123")
    license_number = f"{cnic}#{last_three}" if cnic and last_three else ""

    net_salary = st.number_input("Net Salary", min_value=0, step=1000)
    gender = st.selectbox("Gender", ["Male", "Female"])
    bank_balance = st.number_input("Average 6M Bank Balance", min_value=0, step=1000)
    salary_consistency = st.number_input("Salary Consistency (months out of 12)", 0, 12, 12)
    employer_type = st.selectbox("Employer Type", ["Govt", "MNC", "SME", "Startup"])
    job_tenure = st.number_input("Job Tenure (years)", min_value=0, step=1)
    age = st.number_input("Age", min_value=18, step=1)
    dependents = st.number_input("Dependents", min_value=0, step=1)
    residence = st.selectbox("Residence", ["Owned", "Rented"])

    bike_type = st.selectbox("Bike Type", ["EV-1", "EV-125"])
    bike_price = st.number_input("Bike Price", min_value=0, step=1000)
    outstanding_loan = st.number_input("Outstanding Loan", min_value=0, step=1000)

    st.subheader("Address Information")
    address = st.text_input("Street Address")
    area = st.text_input("Area")
    city = st.text_input("City")

    if address and area and city:
        maps_url = f"https://www.google.com/maps/search/?api=1&query={address}+{area}+{city}"
        st.markdown(f"[📍 View Location on Google Maps]({maps_url})", unsafe_allow_html=True)

    st.session_state.update({
        "cnic": cnic,
        "license_number": license_number,
        "net_salary": net_salary,
        "gender": gender,
        "bank_balance": bank_balance,
        "salary_consistency": salary_consistency,
        "employer_type": employer_type,
        "job_tenure": job_tenure,
        "age": age,
        "dependents": dependents,
        "residence": residence,
        "bike_type": bike_type,
        "bike_price": bike_price,
        "outstanding_loan": outstanding_loan,
    })

# -----------------------------
# Page 2: Evaluation
# -----------------------------
elif page == "Evaluation":
    st.header("Evaluation")

    salary = st.session_state.get("net_salary", 0)
    gender = st.session_state.get("gender", "Male")
    balance = st.session_state.get("bank_balance", 0)
    months = st.session_state.get("salary_consistency", 0)
    employer = st.session_state.get("employer_type", "SME")
    tenure = st.session_state.get("job_tenure", 0)
    age = st.session_state.get("age", 0)
    dependents = st.session_state.get("dependents", 0)
    res = st.session_state.get("residence", "Rented")
    bike_price = st.session_state.get("bike_price", 0)
    outstanding = st.session_state.get("outstanding_loan", 0)

    inc = income_score(salary, gender)
    bal = bank_balance_score(balance)
    sal_c = salary_consistency_score(months)
    emp = employer_type_score(employer)
    job = job_tenure_score(tenure)
    age_s = age_score(age)
    dep = dependents_score(dependents)
    res_s = residence_score(res)
    dti_r = dti_ratio(outstanding, bike_price, salary)
    dti_s = dti_score(dti_r)

    scores = {
        "income": inc,
        "bank_balance": bal,
        "salary_consistency": sal_c,
        "employer_type": emp,
        "job_tenure": job,
        "age": age_s,
        "dependents": dep,
        "residence": res_s,
        "dti": dti_s,
    }

    final = weighted_score(scores)
    dec = decision(final)

    st.session_state.update({
        "scores": scores,
        "final_score": final,
        "decision": dec,
        "dti_ratio": dti_r,
    })

# -----------------------------
# Page 3: Results
# -----------------------------
elif page == "Results":
    st.header("📊 Results")

    scores = st.session_state.get("scores", {})
    final = st.session_state.get("final_score", 0)
    dec = st.session_state.get("decision", "N/A")
    dti_r = st.session_state.get("dti_ratio", 0)

    if not scores:
        st.warning("Please complete Applicant Information and Evaluation first.")
    else:
        st.write("### Scoring Breakdown")
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
                "Decision",
            ],
            "Value": [
                f"{scores['income']:.1f}",
                f"{scores['bank_balance']:.1f}",
                f"{scores['salary_consistency']:.1f}",
                f"{scores['employer_type']:.1f}",
                f"{scores['job_tenure']:.1f}",
                f"{scores['age']:.1f}",
                f"{scores['dependents']:.1f}",
                f"{scores['residence']:.1f}",
                f"{dti_r:.2f}",
                f"{scores['dti']:.1f}",
                f"{final:.1f}",
                dec,
            ]
        })

        st.write("### Decision Reasons")
        for r in decision_reasons(scores, dec):
            st.write(f"- {r}")
