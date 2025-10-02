import streamlit as st
import re
import urllib.parse
import mysql.connector
import pandas as pd

# -----------------------------
# Database Connection
# -----------------------------
def get_db_connection():
    return mysql.connector.connect(
        host="3.17.21.91",
        user="ahsan",
        password="ahsan@321",
        database="ev_installment_project"
    )

def save_to_db(data: dict):
    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
    INSERT INTO data (
        first_name, last_name, cnic, license_no,
        guarantors, female_guarantor, street_address, area_address, city, 
        state_province, postal_code, country, phone_number, gender,
        electricity_bill, net_salary, emi, bike_type, bike_price
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    values = (
        data["first_name"], data["last_name"], data["cnic"], data["license_no"],
        data["guarantors"], data["female_guarantor"], data["street_address"], data["area_address"], data["city"],
        data["state_province"], data["postal_code"], data["country"], data["phone_number"], data["gender"],
        data["electricity_bill"], data["net_salary"], data["emi"], data["bike_type"], data["bike_price"]
    )

    cursor.execute(query, values)
    conn.commit()
    cursor.close()
    conn.close()

def fetch_all_applicants():
    conn = get_db_connection()
    query = "SELECT * FROM data"
    df = pd.read_sql(query, conn)
    conn.close()
    return df

# -----------------------------
# Utility Functions
# -----------------------------
def validate_cnic(cnic: str) -> bool:
    """Check CNIC format XXXXX-XXXXXXX-X"""
    return bool(re.fullmatch(r"\d{5}-\d{7}-\d", cnic))

def validate_phone(phone: str) -> bool:
    """Check phone number length 11–12 characters"""
    return phone.isdigit() and 11 <= len(phone) <= 12

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

def bank_balance_score(balance, emi):
    if emi <= 0:
        return 0
    threshold = emi * 3
    score = (balance / threshold) * 100
    return min(score, 100)

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
        return 0, 0
    ratio = (outstanding + bike_price) / net_salary
    if ratio <= 0.5:
        return 100, ratio
    elif ratio <= 1:
        return 70, ratio
    else:
        return 40, ratio

# -----------------------------
# Streamlit App
# -----------------------------
st.set_page_config(page_title="⚡ Electric Bike Finance Portal", layout="centered")
st.title("⚡ Electric Bike Finance Portal")

tabs = st.tabs(["📋 Applicant Information", "📊 Evaluation", "✅ Results", "📂 Applicants"])

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

    # Address fields
    street_address = st.text_input("Street Address")
    area_address = st.text_input("Area Address")
    city = st.text_input("City")
    state_province = st.text_input("State/Province")
    postal_code = st.text_input("Postal Code (Optional)")
    country = st.text_input("Country")

    if st.button("📍 View Location"):
        if street_address and area_address and city and state_province and country:
            full_address = f"{street_address}, {area_address}, {city}, {state_province}, {country}"
            if postal_code:
                full_address += f", {postal_code}"
            encoded = urllib.parse.quote_plus(full_address)
            maps_url = f"https://www.google.com/maps/search/?api=1&query={encoded}"

            js = f"""
            <script>
            window.open("{maps_url}", "_blank").focus();
            </script>
            """
            st.components.v1.html(js, height=0, width=0)
        else:
            st.error("❌ Please complete Street, Area, City, State/Province, and Country before viewing on Maps.")

    phone_number = st.text_input("Phone Number")
    if phone_number and not validate_phone(phone_number):
        st.error("❌ Invalid Phone Number - Please enter a valid phone number")

    gender = st.radio("Gender", ["M", "F"])

    electricity_bill = st.radio("Is electricity bill available?", ["Yes", "No"])

    guarantor_valid = (guarantors == "Yes")
    female_guarantor_valid = (female_guarantor == "Yes") if guarantors == "Yes" else True
    phone_valid = validate_phone(phone_number) if phone_number else False
    electricity_valid = (electricity_bill == "Yes")

    if not guarantor_valid:
        st.error("🚫 Application Rejected: No guarantor available.")
    elif guarantors == "Yes" and not female_guarantor_valid:
        st.error("🚫 Application Rejected: At least one female guarantor is required.")
    elif not electricity_valid:
        st.error("🚫 Application Rejected: Electricity bill not available.")

    info_complete = all([
        first_name, last_name, validate_cnic(cnic), license_suffix,
        guarantor_valid, female_guarantor_valid,
        street_address, area_address, city, state_province, country,
        phone_valid, gender, electricity_valid
    ])

    st.session_state.applicant_valid = info_complete

    if info_complete:
        st.success("✅ Applicant Information completed. Proceed to Evaluation tab.")
    else:
        st.warning("⚠️ Please complete all fields before proceeding.")

# -----------------------------
# Page 2: Evaluation
# -----------------------------
with tabs[1]:
    if not st.session_state.get("applicant_valid", False):
        st.error("🚫 Please complete Applicant Information first.")
    else:
        st.subheader("Evaluation Inputs")

        net_salary = st.number_input("Net Salary", min_value=0, step=1000, format="%i")
        emi = st.number_input("Monthly Installment (EMI)", min_value=0, step=500, format="%i")
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
    if not st.session_state.get("applicant_valid", False):
        st.error("🚫 Please complete Applicant Information first.")
    else:
        st.subheader("📊 Results Summary")

        if st.session_state.get("applicant_valid") and 'net_salary' in locals() and net_salary > 0 and 'emi' in locals() and emi > 0:
            inc = income_score(net_salary, gender)
            bal = bank_balance_score(bank_balance, emi)
            sal = salary_consistency_score(salary_consistency)
            emp = employer_type_score(employer_type)
            job = job_tenure_score(job_years)
            ag = age_score(age)
            dep = dependents_score(dependents)
            res = residence_score(residence)
            dti, ratio = dti_score(outstanding, bike_price, net_salary)

            final = (
                inc * 0.40 + bal * 0.30 + sal * 0.04 + emp * 0.04 +
                job * 0.04 + ag * 0.04 + dep * 0.04 + res * 0.05 + dti * 0.05
            )

            if final >= 75:
                decision = "✅ Approve"
            elif final >= 60:
                decision = "🟡 Review"
            else:
                decision = "❌ Reject"

            st.markdown("### 🔹 Detailed Scores")
            st.write(f"**Income Score (with gender adj.):** {inc:.1f}")
            st.write(f"**Bank Balance Score (vs. 3× EMI):** {bal:.1f}")
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

            st.markdown("### 📌 Decision Reasons")
            reasons = []
            if inc < 60:
                reasons.append("• Moderate to low income level.")
            if bal >= 100:
                reasons.append("• Bank balance fully meets requirement (≥ 3× EMI).")
            else:
                reasons.append("• Bank balance below recommended 3× EMI.")
            if dti < 70:
                reasons.append("• High debt-to-income ratio, risky.")
            if final >= 75:
                reasons.append("• Profile fits approval criteria.")
            for r in reasons:
                st.write(r)

            if decision == "✅ Approve":
                if st.button("💾 Save Applicant to Database"):
                    try:
                        save_to_db({
                            "first_name": first_name,
                            "last_name": last_name,
                            "cnic": cnic,
                            "license_no": license_number,
                            "guarantors": guarantors,
                            "female_guarantor": female_guarantor if female_guarantor else "No",
                            "street_address": street_address,
                            "area_address": area_address,
                            "city": city,
                            "state_province": state_province,
                            "postal_code": postal_code,
                            "country": country,
                            "phone_number": phone_number,
                            "gender": gender,
                            "electricity_bill": electricity_bill,
                            "net_salary": net_salary,
                            "emi": emi,
                            "bike_type": bike_type,
                            "bike_price": bike_price,
                        })
                        st.success("✅ Applicant information saved to database successfully!")
                    except Exception as e:
                        st.error(f"❌ Failed to save applicant: {e}")
        else:
            st.warning("⚠️ Complete Evaluation inputs first")

# -----------------------------
# Page 4: Applicants
# -----------------------------
with tabs[3]:
    st.subheader("📂 Applicants Database")

    if st.button("🔄 Refresh Data"):
        st.session_state.refresh = True

    try:
        df = fetch_all_applicants()
        if not df.empty:
            # Search and filter options
            search_cnic = st.text_input("🔎 Search by CNIC")
            filter_city = st.selectbox("🏙️ Filter by City", ["All"] + sorted(df["city"].unique().tolist()))
            filter_gender = st.selectbox("⚧ Filter by Gender", ["All"] + sorted(df["gender"].unique().tolist()))

            # Apply filters
            if search_cnic:
                df = df[df["cnic"].str.contains(search_cnic, case=False, na=False)]
            if filter_city != "All":
                df = df[df["city"] == filter_city]
            if filter_gender != "All":
                df = df[df["gender"] == filter_gender]

            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("ℹ️ No applicants found in the database yet.")
    except Exception as e:
        st.error(f"❌ Failed to load applicants: {e}")

