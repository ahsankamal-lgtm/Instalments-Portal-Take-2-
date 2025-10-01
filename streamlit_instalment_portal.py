import streamlit as st
import re
import urllib.parse
import mysql.connector
import pandas as pd
import io

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

# -----------------------------
# Helper: Fetch / Delete / Export
# -----------------------------
def fetch_all_applicants():
    """Return a pandas DataFrame with all rows from data table."""
    conn = None
    try:
        conn = get_db_connection()
        df = pd.read_sql("SELECT * FROM data", conn)
        return df
    except Exception as e:
        st.error(f"❌ Failed to fetch applicants: {e}")
        return pd.DataFrame()
    finally:
        if conn:
            conn.close()

def delete_applicant_by_id(applicant_id):
    """Delete a single applicant by id. Returns True on success."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM data WHERE id = %s", (int(applicant_id),))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        st.error(f"❌ Failed to delete applicant: {e}")
        return False

def delete_multiple_applicants(ids):
    """Delete multiple applicants by id list. Returns True on success."""
    if not ids:
        return False
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        format_strings = ','.join(['%s'] * len(ids))
        cur.execute(f"DELETE FROM data WHERE id IN ({format_strings})", tuple(ids))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        st.error(f"❌ Failed bulk delete: {e}")
        return False

def df_to_csv_bytes(df: pd.DataFrame):
    return df.to_csv(index=False).encode("utf-8")

def df_to_excel_bytes(df: pd.DataFrame):
    output = io.BytesIO()
    # Use xlsxwriter (or openpyxl) as engine — xlsxwriter recommended for speed
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Applicants")
        # writer.save() <-- removed (handled automatically by context manager)
    processed_data = output.getvalue()
    return processed_data

# -----------------------------
# Utility Functions & Scoring
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

def bank_balance_score(balance, emi):
    """Score bank balance: 100 if ≥ 3 × EMI, proportional otherwise"""
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

# --- add the Applicants tab as the 4th tab; first three tabs unchanged ---
tabs = st.tabs(["📋 Applicant Information", "📊 Evaluation", "✅ Results", "👥 Applicants Database"])

# -----------------------------
# Page 1: Applicant Info (unchanged)
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

    # Validation rules
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
# Page 2: Evaluation (unchanged)
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
# Page 3: Results (unchanged)
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

            # Reasons
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

            # Save to DB only if approved
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
# Page 4: Applicants Database (ENHANCED WITH SOFT DELETE)
# -----------------------------
with tabs[3]:
    st.subheader("👥 Applicants Database")

    # Refresh button
    refresh = st.button("🔄 Refresh Applicants")

    # Show deleted toggle
    show_deleted = st.checkbox("Show Deleted Applicants", value=False)

    # Fetch data (active or deleted depending on toggle)
    df = fetch_all_applicants()
    if not df.empty and "is_deleted" in df.columns:
        if show_deleted:
            filtered_db = df[df["is_deleted"] == 1]
        else:
            filtered_db = df[df["is_deleted"] == 0]
    else:
        filtered_db = df.copy()

    if filtered_db.empty:
        st.info("No applicants found.")
    else:
        # Filters
        col1, col2, col3 = st.columns([2, 2, 2])
        search_cnic = col1.text_input("🔎 Search CNIC")
        search_name = col2.text_input("🔎 Search Name")
        filter_city = col3.selectbox("🏙 Filter by City", ["All"] + sorted(df['city'].dropna().unique().tolist()))

        filtered = filtered_db.copy()
        if search_cnic:
            filtered = filtered[filtered['cnic'].astype(str).str.contains(search_cnic, na=False)]
        if search_name:
            filtered = filtered[
                filtered['first_name'].astype(str).str.contains(search_name, case=False, na=False) |
                filtered['last_name'].astype(str).str.contains(search_name, case=False, na=False)
            ]
        if filter_city and filter_city != "All":
            filtered = filtered[filtered['city'] == filter_city]

        st.dataframe(filtered, use_container_width=True)

        # Download buttons
        csv_bytes = df_to_csv_bytes(filtered)
        st.download_button("📥 Download CSV", data=csv_bytes, file_name="applicants_filtered.csv", mime="text/csv")

        excel_bytes = df_to_excel_bytes(filtered)
        st.download_button("📥 Download Excel", data=excel_bytes, file_name="applicants_filtered.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        st.markdown("---")
        st.subheader("🗑️ Manage Applicants")

        # Single soft delete / restore
        single_id = st.number_input("Enter Applicant ID", min_value=1, step=1, key="single_id_action")

        if st.button("🗑️ Soft Delete Applicant"):
            if not df[df["id"] == single_id].empty:
                try:
                    conn = get_db_connection()
                    cur = conn.cursor()
                    cur.execute("UPDATE data SET is_deleted = 1 WHERE id = %s", (int(single_id),))
                    conn.commit()
                    cur.close()
                    conn.close()
                    st.success(f"✅ Applicant {single_id} marked as deleted.")
                    st.experimental_rerun()
                except Exception as e:
                    st.error(f"❌ Failed to soft delete: {e}")
            else:
                st.warning("⚠️ Applicant ID not found.")

        if st.button("♻️ Restore Applicant"):
            if not df[df["id"] == single_id].empty:
                try:
                    conn = get_db_connection()
                    cur = conn.cursor()
                    cur.execute("UPDATE data SET is_deleted = 0 WHERE id = %s", (int(single_id),))
                    conn.commit()
                    cur.close()
                    conn.close()
                    st.success(f"✅ Applicant {single_id} restored successfully.")
                    st.experimental_rerun()
                except Exception as e:
                    st.error(f"❌ Failed to restore: {e}")
            else:
                st.warning("⚠️ Applicant ID not found.")

        # Bulk delete / restore
        st.write("Select multiple applicants to manage:")
        id_list = filtered['id'].tolist()
        selected_ids = st.multiselect("Select Applicant IDs", options=id_list, key="bulk_ids")

        colA, colB = st.columns([1, 1])
        if colA.button("🗑️ Bulk Soft Delete"):
            try:
                conn = get_db_connection()
                cur = conn.cursor()
                format_strings = ','.join(['%s'] * len(selected_ids))
                cur.execute(f"UPDATE data SET is_deleted = 1 WHERE id IN ({format_strings})", tuple(selected_ids))
                conn.commit()
                cur.close()
                conn.close()
                st.success(f"✅ Applicants {selected_ids} marked as deleted.")
                st.experimental_rerun()
            except Exception as e:
                st.error(f"❌ Bulk soft delete failed: {e}")

        if colB.button("♻️ Bulk Restore"):
            try:
                conn = get_db_connection()
                cur = conn.cursor()
                format_strings = ','.join(['%s'] * len(selected_ids))
                cur.execute(f"UPDATE data SET is_deleted = 0 WHERE id IN ({format_strings})", tuple(selected_ids))
                conn.commit()
                cur.close()
                conn.close()
                st.success(f"✅ Applicants {selected_ids} restored successfully.")
                st.experimental_rerun()
            except Exception as e:
                st.error(f"❌ Bulk restore failed: {e}")

    # Refresh
    if refresh:
        st.experimental_rerun()
