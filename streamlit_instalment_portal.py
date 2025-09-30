import streamlit as st
import re
import urllib.parse

# -----------------------------
# Utility Functions
# -----------------------------
def validate_cnic(cnic: str) -> bool:
    """Check CNIC format XXXXX-XXXXXXX-X"""
    return bool(re.fullmatch(r"\d{5}-\d{7}-\d", cnic))


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
    if gender == "F":
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
    elif 1 <= years < 3:
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


# -----------------------------
# Streamlit App
# -----------------------------
st.set_page_config(page_title="⚡ Electric Bike Finance Portal", layout="centered")
st.title("⚡ Electric Bike Finance Portal")

tabs = st.tabs(["📋 Applicant Information", "📊 Evaluation", "✅ Results"])

# -----------------------------
# Page 1: Applicant Info
# -----------------------------
with tabs[0]:
    st.subheader("Applicant Information")

    first_name = st.text_input("First Name")
    last_name = st.text_input("Last Name")

    cnic = st.text_input("CNIC Number (Format: XXXXX-XXXXXXX-X)")
    if cnic and not validate_cnic(cnic):
        st.error("❌ Invalid CNIC format. Use XXXXX-XXXXXXX-X")

    license_suffix = st.text_input("Enter last 3 digits for License Number (#XXX)")
    license_number = f"{cnic}#{license_suffix}" if validate_cnic(cnic) and license_suffix else ""

    guarantors = st.radio("Guarantors Available?", ["Yes", "No"])
    female_guarantor = None
    if guarantors == "Yes":
        female_guarantor = st.radio("At least one Female Guarantor?", ["Yes", "No"])

    address = st.text_input("Address")
    area = st.text_input("Area")
    city = st.text_input("City")

    if st.button("📍 View Location on Google Maps"):
        if address and area and city:
            full_address = f"{address}, {area}, {city}"
            encoded = urllib.parse.quote_plus(full_address)
            maps_url = f"https://www.google.com/maps/search/?api=1&query={encoded}"

            js = f"""
            <script>
            window.open("{maps_url}", "_blank").focus();
            </script>
            """
            st.components.v1.html(js, height=0, width=0)
        else:
            st.error("❌ Please complete Address, Area, and City before viewing on Maps.")

    gender = st.radio("Gender", ["M", "F"])

    info_complete = all([
        first_name, last_name, validate_cnic(cnic), license_suffix,
        guarantors, (female_guarantor if guarantors == "Yes" else True),
        address, area, city, gender
    ])
    if info_complete:
        st.success("✅ Applicant Information completed. Proceed to Evaluation tab.")
    else:
        st.warning("⚠️ Please complete all fields.")


# -----------------------------
# Page 2: Evaluation
# -----------------------------
with tabs[1]:
    st.subheader("Evaluation Inputs")

    net_salary = st.number_input("Net Salary", min_value=0, step=1000, format="%i")
    bank_balance = st.number_input("Average 6M Bank Balance", min_value=0, step=1000, format="%i")
    salary_consistency = st.number_input("Months with Salary Credit (0–12)", min_value=0, max_value=12, step=1)
    employer_type = st.selectbox("Employer Type", ["Govt", "MNC", "SME", "Startup"])
    job_years = st.number_input("Job Tenure (Years)", min_value=0, step=1, format="%i")
    age = st.number_input("Age", min_value=18, max_value=70, step=1, format="%i")
    dependents = st.number_input("Number of Dependents", min_value=0, step=1, format="%i")
    residence = st.radio("Residence", ["Owned", "Rented"])
    bike_type = st.selectbox("Bike Type", ["EV-1", "EV-125"])
    bike_price = st.number_input("Bike Price", min_value=0, step=1000, format="%i")
    outstanding = st.number_input("Outstanding Loan", min_value=0, step=1000, format="%i")

    st.info("➡️ Once inputs are completed, check the Results tab for scoring and decision.")


# -----------------------------
# Page 3: Results
# -----------------------------
with tabs[2]:
    st.subheader("📊 Results Summary")

    if info_complete and net_salary > 0:
        inc = income_score(net_salary, gender)
        bal = bank_balance_score(bank_balance)
        sal = salary_consistency_score(salary_consistency)
        emp = employer_type_score(employer_type)
        job = job_tenure_score(job_years)
        ag = age_score(age)
        dep = dependents_score(dependents)
        res = residence_score(residence)

        dti, ratio = dti_score(outstanding, bike_price, net_salary)
        if isinstance(dti, tuple):  # fix for return
            dti, ratio = dti

        # Weighted final score
        final = (
            inc * 0.40 + bal * 0.30 + sal * 0.04 + emp * 0.04 +
            job * 0.04 + ag * 0.04 + dep * 0.04 + res * 0.05 + dti * 0.05
        )

        # Decision
        if final >= 75:
            decision = "✅ Approve"
        elif final >= 60:
            decision = "🟡 Review"
        else:
            decision = "❌ Reject"

        st.markdown("### 🔹 Detailed Scores")
        st.write(f"**Income Score (with gender adj.):** {inc:.1f}")
        st.write(f"**Bank Balance Score:** {bal:.1f}")
        st.write(f"**Salary Consistency Score:** {sal:.1f}")
        st.write(f"**Employer Type Score:** {emp:.1f}")
        st.write(f"**Job Tenure Score:** {job:.1f}")
        st.write(f"**Age Score:** {ag:.1f}")
        st.write(f"**Dependents Score:** {dep:.1f}")
        st.write(f"**Residence Score:** {res:.1f}")
        st.write(f"**Debt-to-Income Ratio:** {ratio:.2f}")
        st.write(f"**Debt-to-Income Score:** {dti:.1f}")
        st.write(f"**Final Score:** {final:.1f}")
        st.subheader(f"🏆 Decision: {decision}")

        # Reasons
        st.markdown("### 📌 Decision Reasons")
        reasons = []
        if inc < 60:
            reasons.append("• Moderate to low income level.")
        if bal >= 100:
            reasons.append("• Bank balance fully meets requirement.")
        else:
            reasons.append("• Bank balance below recommended 3× EMI.")
        if dti < 70:
            reasons.append("• High debt-to-income ratio, risky.")
        if final >= 75:
            reasons.append("• Profile fits approval criteria.")

        for r in reasons:
            st.write(r)
    else:
        st.warning("⚠️ Complete Applicant Information and Evaluation inputs first.")
