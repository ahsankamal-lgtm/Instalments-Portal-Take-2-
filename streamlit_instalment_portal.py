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

    query = """
    INSERT INTO data (
        first_name, last_name, cnic, license_no,
        guarantors, female_guarantor, address, area, city, gender,
        net_salary, emi, bike_type, bike_price
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    values = (
        data["first_name"], data["last_name"], data["cnic"], data["license_no"],
        data["guarantors"], data["female_guarantor"], data["address"], data["area"], data["city"], data["gender"],
        data["net_salary"], data["emi"], data["bike_type"], data["bike_price"]
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

    address = st.text_input("Address")
    area = st.text_input("Area")
    city = st.text_input("City")

    if st.button("📍 View Location"):
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

    guarantor_valid = (guarantors == "Yes")
    female_guarantor_valid = (female_guarantor == "Yes") if guarantors == "Yes" else True

    if not guarantor_valid:
        st.error("🚫 Application Rejected: No guarantor available.")
    elif guarantors == "Yes" and not female_guarantor_valid:
        st.error("🚫 Application Rejected: At least one female guarantor is required.")

    info_complete = all([
        first_name, last_name, validate_cnic(cnic), license_suffix,
        guarantor_valid, female_guarantor_valid,
        address, area, city, gender
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
                            "address": address,
                            "area": area,
                            "city": city,
                            "gender": gender,
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
            # Show dataframe with checkboxes
            df_display = df.copy()
            df_display["Select"] = False  # add column for selection

            # Selection UI
            selected_rows = st.multiselect(
                "✅ Select Applicants to Delete",
                options=df["id"].tolist(),
                format_func=lambda x: f"ID {x} - {df.loc[df['id']==x, 'first_name'].values[0]} {df.loc[df['id']==x, 'last_name'].values[0]}"
            )

            st.dataframe(df, use_container_width=True, hide_index=True)

            # Delete button
            if selected_rows:
                if st.button("🗑️ Delete Selected Applicants"):
                    try:
                        conn = get_db_connection()
                        cur = conn.cursor()

                        # Delete selected applicants
                        format_strings = ",".join(["%s"] * len(selected_rows))
                        cur.execute(f"DELETE FROM data WHERE id IN ({format_strings})", tuple(selected_rows))
                        conn.commit()

                        # Re-sequence IDs
                        cur.execute("SET @count = 0")
                        cur.execute("UPDATE data SET id = @count:=@count+1")
                        conn.commit()

                        cur.close()
                        conn.close()
                        st.success(f"✅ Deleted applicants {selected_rows} and re-sequenced IDs.")
                        st.experimental_rerun()
                    except Exception as e:
                        st.error(f"❌ Failed to delete: {e}")

            # 📥 Download Excel Button
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
