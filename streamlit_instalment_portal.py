import streamlit as st
import re
import urllib.parse
import mysql.connector
import pandas as pd
from io import BytesIO


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

    # --- Check if CNIC already exists ---
    cursor.execute("SELECT COUNT(*) FROM data WHERE cnic = %s", (data["cnic"],))
    (exists,) = cursor.fetchone()
    if exists > 0:
        cursor.close()
        conn.close()
        raise ValueError("❌ CNIC already exists in the database. Please enter a unique CNIC.")

    # Columns in the exact order we will pass values
    columns = [
        "applicant_type", "name", "cnic", "license_no",
        "phone_number", "gender",
        "guarantors", "female_guarantor", "electricity_bill", "pdc_option",  
        "education", "occupation", "designation",
        "employer_name", "employer_contact",
        "address", "city", "state_province", "postal_code", "country",
        "net_salary", "applicant_bank_balance", "guarantor_bank_balance",
        "employer_type", "age", "residence",
        "bike_type", "bike_price", "down_payment", "tenure", "emi",
        "outstanding",
        "decision"
    ]

    full_name = f"{data['first_name']} {data['last_name']}".strip()
    full_address = f"{data['street_address']}, {data['area_address']}"

    # Values in the same order as `columns`
    values = (
        data["applicant_type"],
        full_name, data["cnic"], data["license_no"],
        data["phone_number"], data["gender"],
        data["guarantors"], data["female_guarantor"], data["electricity_bill"], data["pdc_option"],
        data.get("education"), data.get("occupation"), data.get("designation"),
        data.get("employer_name"), data.get("employer_contact"),
        full_address, data["city"], data["state_province"], data["postal_code"], data["country"],
        data["net_salary"], data["applicant_bank_balance"], data.get("guarantor_bank_balance"),
        data["employer_type"], data["age"], data["residence"],
        data["bike_type"], data["bike_price"], data["down_payment"], data["tenure"], data["emi"],data["outstanding"],
        data["decision"]
    )


    # Build placeholders dynamically so counts always match
    placeholders = ", ".join(["%s"] * len(values))
    cols_sql = ", ".join(columns)
    query = f"INSERT INTO data ({cols_sql}) VALUES ({placeholders})"

    cursor.execute(query, values)
    conn.commit()
    cursor.close()
    conn.close()


def fetch_all_applicants():
    conn = get_db_connection()
    query = """
    SELECT 
        id, 
        applicant_type,
        name, 
        cnic, 
        license_no,
        phone_number, 
        gender,
        guarantors, 
        female_guarantor, 
        electricity_bill,
        pdc_option,
        education, 
        occupation, 
        designation,
        employer_name,
        employer_contact,
        address, 
        city, 
        state_province, 
        postal_code, 
        country,
        net_salary, 
        applicant_bank_balance, 
        guarantor_bank_balance,
        employer_type, 
        age, 
        residence,
        bike_type, 
        bike_price, 
        down_payment,
        tenure,
        emi, 
        outstanding,
        decision
    FROM data
    ORDER BY id ASC;
    """
    df = pd.read_sql(query, conn)
    conn.close()
    return df


def resequence_ids():
    """ Re-sequence IDs after deletion and reset AUTO_INCREMENT """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SET @count = 0;")
        cursor.execute("UPDATE data SET id = (@count := @count + 1)")
        cursor.execute("ALTER TABLE data AUTO_INCREMENT = 1")
        conn.commit()
        cursor.close()
        conn.close()
        st.success("✅ IDs resequenced successfully!")
    except Exception as e:
        st.error(f"❌ Failed to resequence IDs: {e}")

import math
import re

# -----------------------------
# Validation Functions
# -----------------------------
def validate_cnic(cnic: str) -> bool:
    return bool(re.fullmatch(r"\d{5}-?\d{7}-?\d", cnic))


def validate_phone(phone: str) -> bool:
    return phone.isdigit() and len(phone) == 11

# -----------------------------
# Scoring Functions
# -----------------------------
def income_score(net_salary, gender):
    if net_salary < 50000:
        base = 0
    elif net_salary < 70000:
        base = 20
    elif net_salary < 90000:
        base = 35
    elif net_salary < 100000:
        base = 50
    elif net_salary < 120000:
        base = 60
    elif net_salary < 150000:
        base = 80
    else:
        base = 100
    if gender == "F":
        base *= 1.1
    return min(base, 100)
    
def bank_balance_score_custom(applicant_balance, guarantor_balance, emi):
    """
    Binary scoring logic:
    - Applicant >= 3x EMI → 100
    - Guarantor >= 6x EMI → 100
    - If both provided:
        → Applicant takes priority if both qualify
    """
    score = 0
    source = "None"

    applicant_ok = applicant_balance is not None and applicant_balance >= 3 * emi
    guarantor_ok = guarantor_balance is not None and guarantor_balance >= 6 * emi

    if applicant_ok and guarantor_ok:
        score, source = 100, "Applicant (Priority)"
    elif applicant_ok:
        score, source = 100, "Applicant"
    elif guarantor_ok:
        score, source = 100, "Guarantor"
    else:
        score, source = 0, "None"

    return score, source


def salary_consistency_score(months):
    return min((months / 6) * 100, 100)

def employer_type_score(emp_type):
    mapping = {"Govt": 100, "MNC": 80, "Private Limited": 70, "SME": 60, "Startup": 40, "Self-employed": 20}
    return mapping.get(emp_type, 0)

def job_tenure_score(years):
    if years >= 10:
        return 100
    elif years >= 5:
        return 70
    elif years >= 3:
        return 50
    elif years >= 1:
        return 20
    else:
        return 0

def age_score(age):
    if age < 18:
        return -1  # reject
    elif age <= 25:
        return 80
    elif age <= 30:
        return 100
    elif age <= 40:
        return 60
    else:
        return 30

def dependents_score(dep):
    if dep == 0:
        return 100
    elif dep <= 2:
        return 80
    elif dep <= 4:
        return 60
    else:
        return 40

def residence_score(res):
    mapping = {"Owned": 100, "Family": 80, "Rented": 60, "Temporary": 40}
    return mapping.get(res, 0)

def dti_score(outstanding, emi, net_salary, tenure):
    """
    Debt-to-Income (DTI) Score:
    ratio = (Outstanding / tenure + EMI) / Net Salary
    """
    if net_salary <= 0 or tenure <= 0:
        return 0, 0

    monthly_obligation = (outstanding / tenure) + emi
    ratio = monthly_obligation / net_salary

    if ratio <= 0.1:
        score = 100
    elif ratio <= 0.2:
        score = 80
    elif ratio <= 0.3:
        score = 60
    elif ratio <= 0.5:
        score = 40
    else:
        score = 20

    return score, ratio

def calculate_min_emi(bike_price, down_payment, tenure):
    """Minimum EMI needed to cover bike price"""
    if tenure <= 0:
        return 0
    return math.ceil((bike_price - down_payment) / tenure)



import streamlit as st

# --- PAGE CONFIG ---
st.set_page_config(page_title="EV Bike Finance Portal", layout="centered")

# --- SESSION STATE INIT ---
if 'app_started' not in st.session_state:
    st.session_state['app_started'] = False

# --- LANDING PAGE ---
if not st.session_state['app_started']:
    # Custom styling (gradient background + blue button)
    page_bg = """
    <style>
    [data-testid="stAppViewContainer"] {
        background: linear-gradient(135deg, #001F3F 0%, #0074D9 50%, #7FDBFF 100%);
        color: white;
        padding-top: 6rem;
    }
    [data-testid="stHeader"] {background: rgba(0,0,0,0);}
    .title {
        font-size: 2.8rem;
        font-weight: 800;
        margin-bottom: 1rem;
        text-align: center;
        background: linear-gradient(to right, #7FDBFF, #39CCCC, #01FF70);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .subtitle {
        font-size: 1.1rem;
        color: #E0E0E0;
        text-align: center;
        margin-bottom: 2.5rem;
    }
    .divider {
        border: none;
        height: 1px;
        background-color: rgba(255, 255, 255, 0.3);
        margin: 2rem 0;
    }
    /* --- Custom blue button --- */
    div.stButton > button:first-child {
        background-color: #0074D9;
        color: white;
        border: none;
        padding: 0.75rem 1.5rem;
        border-radius: 10px;
        font-size: 1.1rem;
        font-weight: 600;
        transition: 0.3s ease-in-out;
    }
    div.stButton > button:first-child:hover {
        background-color: #005fa3;
        transform: translateY(-2px);
        box-shadow: 0 4px 10px rgba(0,0,0,0.3);
    }
    </style>
    """
    st.markdown(page_bg, unsafe_allow_html=True)

    # Main content block
    st.markdown('<h1 class="title">⚡ EV Bike Finance Portal</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="subtitle">A unified digital platform to evaluate, approve, and manage electric bike financing — faster, smarter, and sustainable.</p>',
        unsafe_allow_html=True
    )

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # CTA button (blue now!)
    if st.button("🚀 Start New Application", use_container_width=True):
        st.session_state['app_started'] = True
        st.rerun()

    st.stop()
st.markdown(
    """
    <style>
    /* 🔵 Global Blue Gradient Background */
    [data-testid="stAppViewContainer"] {
        background: linear-gradient(to bottom right, #004aad, #5de0e6);
        background-attachment: fixed;
    }

    /* 📄 Solid White Form Container */
    .block-container {
        background-color: #ffffff;  /* Fully opaque white */
        padding: 2rem 3rem;
        border-radius: 20px;
        box-shadow: 0px 3px 10px rgba(0,0,0,0.2);
        margin-top: 2rem;
        margin-bottom: 2rem;
    }

    /* 🌈 Headings on Blue Background (Landing Page Titles) */
    h1, h2, h3, h4 {
        color: #ffffff;
        font-weight: 700;
    }

    /* 🧾 Form and Body Text (on white areas) */
    .stTextInput label,
    .stSelectbox label,
    .stNumberInput label,
    .stRadio label,
    .stCheckbox label,
    p, span, div, label {
        color: #002b80 !important;  /* Dark blue text for readability */
    }

    /* 💾 Primary Buttons */
    button[kind="primary"] {
        background-color: #004aad !important;
        color: white !important;
        font-weight: 600 !important;
        border-radius: 10px !important;
        border: none !important;
    }

    button[kind="primary"]:hover {
        background-color: #0059d6 !important;
        color: white !important;
    }

    /* 🎯 Input Styling */
    .stTextInput > div > div > input,
    .stNumberInput input,
    .stSelectbox select {
        border-radius: 10px !important;
        border: 1px solid #004aad !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)


# -----------------------------
# Streamlit App
# -----------------------------
st.title("⚡ Electric Bike Finance Portal")

tabs = st.tabs(["📋 Applicant Information", "📊 Evaluation", "🎯 Results", "📂 Applicants", "👾 Agent"])

# -----------------------------
# Page 1: Applicant Info
# -----------------------------
with tabs[0]:
    st.subheader("Applicant Information")

    applicant_type = st.selectbox(
        "Applicant Type",
        ["Employee", "Businessman"],
        key="applicant_type"
    )

    first_name = st.text_input("First Name")
    last_name = st.text_input("Last Name")

    cnic = st.text_input("CNIC Number (Format: XXXXX-XXXXXXX-X)")
    if cnic and not validate_cnic(cnic):
        st.error("❌ Invalid CNIC format. Use XXXXX-XXXXXXX-X")

    license_suffix = st.number_input(
        "Enter last 3 digits for License Number (#XXX)",
        min_value=0, max_value=999, step=1, format="%03d"
    )
    license_number = f"{cnic}#{license_suffix}" if validate_cnic(cnic) else ""

    phone_number = st.text_input("Phone Number (11 digits only)")
    if phone_number and not validate_phone(phone_number):
        st.error("❌ Invalid Phone Number - Please enter exactly 11 digits")

    gender = st.radio("Gender", ["M", "F"])

    guarantors = st.radio("Guarantors Available?", ["Yes", "No"])
    female_guarantor = None
    if guarantors == "Yes":
        female_guarantor = st.radio("At least one Female Guarantor?", ["Yes", "No"])

    electricity_bill = st.radio("Is Electricity Bill Available?", ["Yes", "No"])
    if electricity_bill == "No":
        st.error("🚫 Application Rejected: Electricity bill not available.")

    pdc_option = st.radio("Is the candidate willing to provide post-dated cheques (PDCs)?", ["Yes", "No"])
    if pdc_option == "No":
        st.error("🚫 Application Rejected: PDCs not available")

    with st.expander("🎓 Qualifications (Optional)"):
        education = st.selectbox(
            "Education",
            ["", "No Formal Education", "Primary", "Secondary", "Intermediate", "Bachelor's", "Master's", "PhD"]
        )
        occupation = st.text_input("Occupation")
        designation = st.text_input("Designation")
        employer_name = st.text_input("Employer Name")
        employer_contact = st.text_input("Employer Contact (11 digits)")

        # Validate employer contact only if entered
        if employer_contact and not validate_phone(employer_contact):
            st.error("❌ Invalid Employer Contact - Please enter exactly 11 digits")


    street_address = st.text_input("Street Address")
    area_address = st.text_input("Area Address")
    city = st.text_input("City")
    state_province = st.text_input("State/Province")
    postal_code = st.text_input("Postal Code (Optional)")
    country = st.text_input("Country")

    if st.button("📍 View Location"):
        if street_address and area_address and city and state_province and country:
            full_address = f"{street_address}, {area_address}, {city}, {state_province}, {country} {postal_code or ''}"
            encoded = urllib.parse.quote_plus(full_address)
            maps_url = f"https://www.google.com/maps/search/?api=1&query={encoded}"

            js = f"""
            <script>
            window.open("{maps_url}", "_blank").focus();
            </script>
            """
            st.components.v1.html(js, height=0, width=0)
        else:
            st.error("❌ Please complete all mandatory address fields before viewing on Maps.")

    guarantor_valid = (guarantors == "Yes")
    female_guarantor_valid = (female_guarantor == "Yes") if guarantors == "Yes" else True

    if not guarantor_valid:
        st.error("🚫 Application Rejected: No guarantor available.")
    elif guarantors == "Yes" and not female_guarantor_valid:
        st.error("🚫 Application Rejected: At least one female guarantor is required.")

    info_complete = all([
        first_name, last_name, validate_cnic(cnic),
        guarantor_valid, female_guarantor_valid,
        phone_number and validate_phone(phone_number),
        street_address, area_address, city, state_province, country,
        gender, electricity_bill == "Yes"
    ])

    st.session_state.applicant_valid = info_complete

    if info_complete:
        st.success("✅ Applicant Information completed. Proceed to Evaluation tab.")
    else:
        st.warning("⚠️ Please complete all required fields before proceeding.")


# -------------------
# EVALUATION 
# -------------------
with tabs[1]:
    if not st.session_state.get("applicant_valid", False):
        st.error("🚫 Please complete Applicant Information first.")
    else:
        st.subheader("Evaluation Inputs")

        # Get applicant type from previous tab (default to employee if not set)
        applicant_type = st.session_state.get("applicant_type", "Employee")

        # Dynamic labels based on applicant type
        if applicant_type == "Businessman":
            salary_label = "Net Profit (PKR)"
            consistency_label = "Months with Revenue Generated (0–6)"
            tenure_label = "Business Years"

    # 🔹 Show Evidence of Tax Return question
            tax_return = st.radio("Evidence of Tax Return?", ["Yes", "No"], key="tax_return")
        else:
            salary_label = "Net Salary (PKR)"
            consistency_label = "Months with Salary Credit (0–6)"
            tenure_label = "Job Tenure (Years)"


        # ✅ Smooth, lag-free number input (shows formatted value below)
        def formatted_number_input(label, key, optional=False):
            raw_key = f"{key}_raw"
            raw_val = st.session_state.get(raw_key, "")

            # Basic input (no commas while typing)
            input_val = st.text_input(label, value=raw_val, key=raw_key)

            # Keep only digits
            clean_val = re.sub(r"[^\d]", "", input_val)

            # Convert to number
            num = int(clean_val) if clean_val else (0 if not optional else None)

            # Display formatted version below
            if clean_val:
                st.caption(f"💰 **Formatted:** {num:,}")

            return num

        # 💰 Financial Inputs
        net_salary = formatted_number_input(salary_label, key="net_salary")
        applicant_bank_balance = formatted_number_input(
            "Applicant's Average 6M Bank Balance (PKR)", key="applicant_bank_balance"
        )
        guarantor_bank_balance = formatted_number_input(
            "Guarantor's Average 6M Bank Balance (Optional, PKR)", key="guarantor_bank_balance", optional=True
        )

        # 📅 Other Inputs
        salary_consistency = st.number_input(consistency_label, min_value=0, max_value=6, step=1)
        employer_type = st.selectbox("Employer Type", ["Govt", "MNC", "Private Limited", "SME", "Startup", "Self-employed"])
        age = st.number_input("Age", min_value=18, max_value=70, step=1)
        job_years = st.number_input(tenure_label, min_value=0, step=1)
        if job_years > age:
            st.error("❌ Job tenure cannot exceed age. Please correct the values.")
        dependents = st.number_input("Number of Dependents", min_value=0, step=1)
        residence = st.radio("Residence", ["Owned", "Family", "Rented", "Temporary"])

        # 🚲 Bike Type
        bike_type = st.selectbox("Bike Type", ["EV-1", "EV-125"])

        # 🏦 Financing Plan Dropdown (Dynamic)
        # 🔁 CHANGED: plans now depend on bike_type
        if bike_type == "EV-1":
            # EV-1 has only one 2-Year plan
            financing_plans = {
                "2 Year Plan": {"upfront": 30000, "installment": 10000, "tenure": 24},
            }
        else:
            # EV-125 keeps the original three plans
            financing_plans = {
                "1 Year Plan": {"upfront": 60000, "installment": 25500, "tenure": 12},
                "2 Year Plan": {"upfront": 40000, "installment": 14900, "tenure": 24},
                "3 Year Plan": {"upfront": 40000, "installment": 9900, "tenure": 36},
            }

        selected_plan = st.selectbox("Financing Plan", list(financing_plans.keys()))

        # ✅ Calculate plan values
        plan = financing_plans[selected_plan]
        bike_price = plan["upfront"] + plan["installment"] * plan["tenure"]
        emi = plan["installment"]
        tenure = plan["tenure"]
        down_payment = plan["upfront"]

        # 🏦 Display Plan Details (read-only)
        with st.container():
            st.markdown("💳 Financing Plan Details")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Down Payment / Upfront", f"Rs. {down_payment:,}")
                st.metric("Installment Amount", f"Rs. {emi:,}")
            with col2:
                st.metric("Tenure (Months)", f"{tenure}")
                st.metric("Total Bike Price", f"Rs. {bike_price:,}")

        # 🚫 Outstanding Obligation input remains editable
        outstanding = st.number_input("Outstanding Obligation", min_value=0, step=1000)

        # 💡 Minimum EMI info
        st.info(f"💡 EMI to be used for scoring: {emi:,}")



# -------------------
# RESULTS (Reactive)
# -------------------
with tabs[2]:
    if not st.session_state.get("applicant_valid", False):
        st.error("🚫 Please complete Applicant Information first.")
    else:
        st.subheader("🎯 Results Summary")

        if net_salary > 0 and tenure > 0:
            # --- Calculate Scores ---
            inc = income_score(net_salary, gender)
            bal, bal_source = bank_balance_score_custom(applicant_bank_balance, guarantor_bank_balance, emi)
            sal = salary_consistency_score(salary_consistency)
            emp = employer_type_score(employer_type)
            job = job_tenure_score(job_years)
            ag = age_score(age)
            dep = dependents_score(dependents)
            res = residence_score(residence)
            dti, ratio = dti_score(outstanding, emi, net_salary, tenure)

            # --- Final Decision ---
            final_score = 0  # ✅ Prevent NameError if rejected early

            applicant_type = st.session_state.get("applicant_type", "")
            tax_return = st.session_state.get("tax_return", "Yes")

            if applicant_type == "Businessman" and tax_return == "No":
                decision = "Rejected"
                decision_display = "❌ Rejected (No Tax Return)"
                st.error("❌ Rejected: No evidence of tax return provided.")
            elif ag == -1:
                decision = "Reject"
                decision_display = "❌ Reject (Underage)"
            elif bal == 0:
                decision = "Reject"
                decision_display = "❌ Reject (Insufficient Bank Balance)"
            else:
                final_score = (
                    inc * 0.40 + bal * 0.30 + sal * 0.04 + emp * 0.04 +
                    job * 0.04 + ag * 0.04 + dep * 0.04 + res * 0.05 +
                    dti * 0.05
                )
                if final_score >= 75:
                    decision = "Approved"
                    decision_display = "✅ Approve"
                elif final_score >= 60:
                    decision = "Review"
                    decision_display = "🟡 Review"
                else:
                    decision = "Reject"
                    decision_display = "❌ Reject"

            # --- Display Scores ---
            st.markdown("### 🔹 Detailed Scores")
            st.write(f"Income Score: {inc:.1f}")
            st.write(f"Bank Balance Score ({bal_source}): {bal:.1f}")
            st.write(f"Salary Consistency: {sal:.1f}")
            st.write(f"Employer Type Score: {emp:.1f}")
            st.write(f"Job Tenure Score: {job:.1f}")
            st.write(f"Age Score: {ag:.1f}")
            st.write(f"Dependents Score: {dep:.1f}")
            st.write(f"Residence Score: {res:.1f}")
            st.write(f"Debt-to-Income Ratio: {ratio:.2f}")
            st.write(f"Debt-to-Income Score: {dti:.1f}")
            st.write(f"EMI used for scoring: {emi}")

            # ✅ Show N/A for Final Score if rejected early
            if decision == "Reject" and final_score == 0:
                st.write("Final Score: N/A")
            else:
                st.write(f"Final Score: {final_score:.1f}")

            st.subheader(f"🏆 Decision: {decision_display}")

            # -------------------------------
            # ⚠️ Bank Balance Rejection Message
            # -------------------------------
            if bal == 0:
                messages = []

                # Applicant condition
                if applicant_bank_balance is not None and applicant_bank_balance < 3 * emi:
                    messages.append(
                        f"Applicant bank balance Rs. {applicant_bank_balance:,.0f} "
                        f"< required bank balance Rs. {3 * emi:,.0f} (3×EMI)"
                    )

                # Guarantor condition
                if guarantor_bank_balance is not None and guarantor_bank_balance < 6 * emi:
                    messages.append(
                        f" Guarantor bank balance Rs. {guarantor_bank_balance:,.0f} "
                        f"< required guarantor bank balance Rs. {6 * emi:,.0f} (6×EMI)"
                    )

                # Display messages
                if messages:
                    st.markdown("Bank Balance Criteria Not Met")
                    for msg in messages:
                        st.markdown(
                            f'<div style="background-color: #fff3cd; border-left: 6px solid #ffeb3b; '
                            f'padding: 10px; border-radius: 8px; margin-bottom: 8px;">'
                            f'⚠️ <b>{msg}</b></div>',
                            unsafe_allow_html=True
                        )

            # --- Financial Plan ---
            if decision in ["Approved", "Review", "Reject"]:
                st.markdown("### 💰 Applicant Financial Plan")
                remaining_price = bike_price - down_payment
                total_payment = emi * tenure
                break_even = down_payment + total_payment
                st.write(f"**Bike Price:** {bike_price:,.0f}")
                st.write(f"**Down Payment:** {down_payment:,.0f}")
                st.write(f"**Remaining Bike Price after Down Payment:** {remaining_price:,.0f}")
                st.write(f"**Installment Tenure (Months):** {tenure}")
                st.write(f"**Monthly EMI:** {emi:,.0f}")
                st.write(f"**Total EMI over Tenure:** {total_payment:,.0f}")
                st.write(f"**Total Paid Towards Bike (Down Payment + EMIs):** {break_even:,.0f}")

                # --- Save Applicant Button ONLY if Approved ---
                if st.button("💾 Save Applicant to Database"):
                    try:
                        applicant_data = {
                            "first_name": first_name,
                            "last_name": last_name,
                            "cnic": cnic,
                            "license_no": license_number,
                            "phone_number": phone_number,
                            "gender": gender,
                            "guarantors": guarantors,
                            "female_guarantor": female_guarantor,
                            "electricity_bill": electricity_bill,
                            "pdc_option": pdc_option,
                            "education": education,
                            "occupation": occupation,
                            "designation": designation,
                            "employer_name": employer_name,
                            "employer_contact": employer_contact,
                            "street_address": street_address,
                            "area_address": area_address,
                            "city": city,
                            "state_province": state_province,
                            "postal_code": postal_code,
                            "country": country,
                            "net_salary": net_salary,
                            "applicant_bank_balance": applicant_bank_balance,
                            "guarantor_bank_balance": guarantor_bank_balance,
                            "employer_type": employer_type,
                            "age": age,
                            "residence": residence,
                            "bike_type": bike_type,
                            "bike_price": bike_price,
                            "down_payment": down_payment,
                            "tenure": tenure,
                            "emi": emi,
                            "outstanding": outstanding,
                            "decision": decision,
                            "applicant_type": st.session_state.get("applicant_type", "Employee"),

                        }

                        save_to_db(applicant_data)
                        st.success("✅ Applicant saved successfully!")
                    except Exception as e:
                        st.error(f"❌ Failed to save applicant: {e}")




# -----------------------------
# Page 4: Applicants
# -----------------------------
with tabs[3]:
    st.subheader("📂 Applicants Database")

    if st.button("🔄 Refresh Data"):
        resequence_ids()
        st.session_state.refresh = True

    def delete_applicant(applicant_id: int):
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM data WHERE id = %s", (applicant_id,))
            conn.commit()
            cursor.close()
            conn.close()
            st.success(f"✅ Applicant with ID {applicant_id} deleted successfully!")
        except Exception as e:
            st.error(f"❌ Failed to delete applicant: {e}")

    try:
        df = fetch_all_applicants()
        if not df.empty:
            st.dataframe(df, use_container_width=True)

            delete_id = st.number_input("Enter Applicant ID to Delete", min_value=1, step=1)

            # 🔹 NEW: Two-step confirmation logic
            if "confirm_delete" not in st.session_state:
                st.session_state.confirm_delete = None

            if st.button("🗑️ Delete Applicant"):
                if delete_id in df["id"].values:
                    # Store selected ID + Name for confirmation
                    applicant_name = df.loc[df["id"] == delete_id, "name"].values[0]
                    st.session_state.confirm_delete = {"id": delete_id, "name": applicant_name}
                else:
                    st.error("❌ Invalid ID. Please enter a valid Applicant ID from the table.")

            # Show confirmation prompt if a delete is triggered
            if st.session_state.confirm_delete:
                c_id = st.session_state.confirm_delete["id"]
                c_name = st.session_state.confirm_delete["name"]
                st.warning(f"⚠️ Are you sure you want to delete the data for ID: {c_id} and Name: {c_name}?")

                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✅ Yes, Delete"):
                        delete_applicant(c_id)
                        st.session_state.confirm_delete = None  # reset confirmation
                with col2:
                    if st.button("❌ No, Cancel"):
                        st.info("Deletion cancelled.")
                        st.session_state.confirm_delete = None  # reset confirmation

            # Excel download remains the same
            df = df.sort_values(by="id", ascending=True)
            output = BytesIO()
            with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                df.to_excel(writer, index=False, sheet_name="Applicants")
            excel_data = output.getvalue()

            st.download_button(
                label="📥 Download Excel",
                data=excel_data,
                file_name="applicants.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.info("ℹ️ No applicants found in the database yet.")
    except Exception as e:
        st.error(f"❌ Failed to load applicants: {e}")


# -----------------------------
# Page 5: Agent (Direct Scoring)
# -----------------------------
with tabs[4]:
    st.subheader("👾 Scoring Agent")

    # Applicant type & gender
    agent_applicant_type = st.selectbox(
        "Applicant Type",
        ["Employee", "Businessman"],
        key="agent_applicant_type"
    )
    agent_gender = st.radio("Gender", ["M", "F"], key="agent_gender")

    # Dynamic labels (same logic as Evaluation tab)
    if agent_applicant_type == "Businessman":
        agent_salary_label = "Net Profit (PKR)"
        agent_consistency_label = "Months with Revenue Generated (0–6)"
        agent_tenure_label = "Business Years"
        agent_tax_return = st.radio("Evidence of Tax Return?", ["Yes", "No"], key="agent_tax_return")
    else:
        agent_salary_label = "Net Salary (PKR)"
        agent_consistency_label = "Months with Salary Credit (0–6)"
        agent_tenure_label = "Job Tenure (Years)"
        agent_tax_return = "Yes"  # implicitly yes for employees

    # Reuse formatted input helper with separate keys
    def agent_formatted_number_input(label, key, optional=False):
        raw_key = f"{key}_raw"
        raw_val = st.session_state.get(raw_key, "")

        input_val = st.text_input(label, value=raw_val, key=raw_key)
        clean_val = re.sub(r"[^\d]", "", input_val)
        num = int(clean_val) if clean_val else (0 if not optional else None)

        if clean_val:
            st.caption(f"💰 **Formatted:** {num:,}")

        return num

    # Core financial inputs
    agent_net_salary = agent_formatted_number_input(agent_salary_label, key="agent_net_salary")
    agent_applicant_bank_balance = agent_formatted_number_input(
        "Applicant's Average 6M Bank Balance (PKR)", key="agent_applicant_bank_balance"
    )
    agent_guarantor_bank_balance = agent_formatted_number_input(
        "Guarantor's Average 6M Bank Balance (Optional, PKR)", key="agent_guarantor_bank_balance", optional=True
    )

    agent_salary_consistency = st.number_input(agent_consistency_label, min_value=0, max_value=6, step=1, key="agent_salary_consistency")
    agent_employer_type = st.selectbox(
        "Employer Type",
        ["Govt", "MNC", "Private Limited", "SME", "Startup", "Self-employed"],
        key="agent_employer_type"
    )
    agent_age = st.number_input("Age", min_value=18, max_value=70, step=1, key="agent_age")
    agent_job_years = st.number_input(agent_tenure_label, min_value=0, step=1, key="agent_job_years")
    if agent_job_years > agent_age:
        st.error("❌ Job tenure cannot exceed age. Please correct the values.")
    agent_dependents = st.number_input("Number of Dependents", min_value=0, step=1, key="agent_dependents")
    agent_residence = st.radio("Residence", ["Owned", "Family", "Rented", "Temporary"], key="agent_residence")

    # EMI / Debt inputs
    agent_emi = st.number_input("Proposed EMI (Monthly Installment)", min_value=0, step=1000, key="agent_emi")
    agent_tenure = st.number_input("Tenure (Months)", min_value=1, step=1, key="agent_tenure")
    agent_outstanding = st.number_input("Existing Outstanding Obligation", min_value=0, step=1000, key="agent_outstanding")

    if st.button("🧮 Calculate Agent Score", key="agent_calculate_btn"):
        if agent_net_salary <= 0 or agent_emi <= 0 or agent_tenure <= 0:
            st.error("❌ Please enter valid Net Salary/Profit, EMI, and Tenure values.")
        else:
            # Individual scores using same logic as main engine
            a_inc = income_score(agent_net_salary, agent_gender)
            a_bal, a_bal_source = bank_balance_score_custom(
                agent_applicant_bank_balance, agent_guarantor_bank_balance, agent_emi
            )
            a_sal = salary_consistency_score(agent_salary_consistency)
            a_emp = employer_type_score(agent_employer_type)
            a_job = job_tenure_score(agent_job_years)
            a_ag = age_score(agent_age)
            a_dep = dependents_score(agent_dependents)
            a_res = residence_score(agent_residence)
            a_dti, a_ratio = dti_score(agent_outstanding, agent_emi, agent_net_salary, agent_tenure)

            a_final_score = 0
            # Decision logic mirrors Results tab
            if agent_applicant_type == "Businessman" and agent_tax_return == "No":
                a_decision = "Rejected"
                a_decision_display = "❌ Rejected (No Tax Return)"
                st.error("❌ Rejected: No evidence of tax return provided.")
            elif a_ag == -1:
                a_decision = "Reject"
                a_decision_display = "❌ Reject (Underage)"
            elif a_bal == 0:
                a_decision = "Reject"
                a_decision_display = "❌ Reject (Insufficient Bank Balance)"
            else:
                a_final_score = (
                    a_inc * 0.40 + a_bal * 0.30 + a_sal * 0.04 + a_emp * 0.04 +
                    a_job * 0.04 + a_ag * 0.04 + a_dep * 0.04 + a_res * 0.05 +
                    a_dti * 0.05
                )
                if a_final_score >= 75:
                    a_decision = "Approved"
                    a_decision_display = "✅ Approve"
                elif a_final_score >= 60:
                    a_decision = "Review"
                    a_decision_display = "🟡 Review"
                else:
                    a_decision = "Reject"
                    a_decision_display = "❌ Reject"

            # Show detailed scores
            st.markdown("### 🔹 Agent — Detailed Scores")
            st.write(f"Income Score: {a_inc:.1f}")
            st.write(f"Bank Balance Score ({a_bal_source}): {a_bal:.1f}")
            st.write(f"Salary Consistency: {a_sal:.1f}")
            st.write(f"Employer Type Score: {a_emp:.1f}")
            st.write(f"Job Tenure Score: {a_job:.1f}")
            st.write(f"Age Score: {a_ag:.1f}")
            st.write(f"Dependents Score: {a_dep:.1f}")
            st.write(f"Residence Score: {a_res:.1f}")
            st.write(f"Debt-to-Income Ratio: {a_ratio:.2f}")
            st.write(f"Debt-to-Income Score: {a_dti:.1f}")
            st.write(f"EMI used for scoring: {agent_emi}")

            if a_decision == "Reject" and a_final_score == 0:
                st.write("Final Score: N/A")
            else:
                st.write(f"Final Score: {a_final_score:.1f}")

            st.subheader(f"🏆 Agent Decision: {a_decision_display}")

            # Bank balance criteria explanation
            if a_bal == 0:
                a_messages = []
                if agent_applicant_bank_balance is not None and agent_applicant_bank_balance < 3 * agent_emi:
                    a_messages.append(
                        f"Applicant bank balance Rs. {agent_applicant_bank_balance:,.0f} "
                        f"< required bank balance Rs. {3 * agent_emi:,.0f} (3×EMI)"
                    )
                if agent_guarantor_bank_balance is not None and agent_guarantor_bank_balance < 6 * agent_emi:
                    a_messages.append(
                        f" Guarantor bank balance Rs. {agent_guarantor_bank_balance:,.0f} "
                        f"< required guarantor bank balance Rs. {6 * agent_emi:,.0f} (6×EMI)"
                    )
                if a_messages:
                    st.markdown("Bank Balance Criteria Not Met (Agent View)")
                    for msg in a_messages:
                        st.markdown(
                            f'<div style="background-color: #fff3cd; border-left: 6px solid #ffeb3b; '
                            f'padding: 10px; border-radius: 8px; margin-bottom: 8px;">'
                            f'⚠️ <b>{msg}</b></div>',
                            unsafe_allow_html=True
                        )
