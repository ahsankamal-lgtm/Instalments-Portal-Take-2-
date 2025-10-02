import streamlit as st
import pandas as pd
import mysql.connector
from io import BytesIO
import base64
from geopy.geocoders import Nominatim

# -----------------------------
# DB CONNECTION
# -----------------------------
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="yourpassword",
        database="instalments_db"
    )

# -----------------------------
# SAVE TO DB
# -----------------------------
def save_to_db(data):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        insert_query = """
        INSERT INTO data 
        (first_name, last_name, cnic, license_no, guarantors, female_guarantor,
        street_address, area_address, city, state_province, postal_code, country, phone_number,
        gender, electricity_bill, net_salary, emi, bike_type, bike_price)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """

        cursor.execute(insert_query, (
            data["first_name"], data["last_name"], data["cnic"], data["license_no"],
            data["guarantors"], data["female_guarantor"], data["street_address"],
            data["area_address"], data["city"], data["state_province"],
            data.get("postal_code"), data["country"], data["phone_number"],
            data["gender"], data["electricity_bill"], data["net_salary"],
            data["emi"], data["bike_type"], data["bike_price"]
        ))

        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        st.error(f"❌ Failed to save applicant: {e}")
        return False

# -----------------------------
# FETCH FROM DB
# -----------------------------
def fetch_all_applicants():
    try:
        conn = get_db_connection()
        query = "SELECT * FROM data"
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"❌ Failed to load applicants: {e}")
        return pd.DataFrame()

# -----------------------------
# EXPORT TO EXCEL
# -----------------------------
def df_to_excel_bytes(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Applicants")
    return output.getvalue()

# -----------------------------
# SCORING FUNCTIONS (from Excel rules)
# -----------------------------
def score_net_salary(net_salary, gender):
    if net_salary < 50000:
        score = 0
    elif 50000 <= net_salary < 70000:
        score = 20
    elif 70000 <= net_salary < 90000:
        score = 35
    elif 90000 <= net_salary < 100000:
        score = 50
    elif 100000 <= net_salary < 120000:
        score = 60
    elif 120000 <= net_salary < 150000:
        score = 80
    else:
        score = 100

    if gender == "F":
        score = min(score * 1.1, 100)  # 10% bonus for females
    return score

def score_bank_balance(avg_balance, emi):
    required = emi * 3
    score = (avg_balance / required) * 100 if required > 0 else 0
    return min(score, 100)

def score_salary_consistency(months_credited):
    return (months_credited / 6) * 100

def score_employer_type(employer_type):
    mapping = {
        "Govt": 100,
        "Semi-Govt": 80,
        "Private": 70,
        "Self-Employed": 40
    }
    return mapping.get(employer_type, 0)

def score_job_tenure(years):
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

def score_age(age):
    if age < 18:
        return -999  # auto reject
    elif 18 <= age <= 24:
        return 80
    elif 25 <= age <= 30:
        return 100
    elif 31 <= age <= 40:
        return 60
    else:
        return 30

def score_dependents(dep):
    if dep <= 1:
        return 100
    elif dep == 2:
        return 70
    else:
        return 40

def score_residence(residence):
    return 100 if residence == "Owned" else 60

def score_dti(loans, bike_price, salary):
    ratio = (loans + bike_price) / salary if salary > 0 else 999
    if ratio <= 2:
        return 100
    elif ratio <= 4:
        return 70
    else:
        return 40

# -----------------------------
# STREAMLIT UI
# -----------------------------
st.set_page_config(page_title="Instalment Scoring Portal", layout="wide")
tabs = st.tabs(["Applicant Info", "Evaluation", "Results", "Applicants Database"])

# -----------------------------
# Page 1: Applicant Info
# -----------------------------
with tabs[0]:
    st.header("📋 Applicant Information")

    first_name = st.text_input("First Name")
    last_name = st.text_input("Last Name")
    cnic = st.text_input("CNIC")
    license_no = st.text_input("License No")
    guarantors = st.selectbox("Guarantors Provided?", ["Yes", "No"])
    female_guarantor = st.selectbox("Female Guarantor?", ["Yes", "No"])

    # Address fields
    street_address = st.text_input("Street Address")
    area_address = st.text_input("Area Address")
    city = st.text_input("City")
    state_province = st.text_input("State/Province")
    postal_code = st.text_input("Postal Code (Optional)")
    country = st.text_input("Country")

    # Phone validation
    phone_number = st.text_input("Phone Number")
    if phone_number and (len(phone_number) < 11 or len(phone_number) > 12):
        st.error("Invalid Phone Number - Please enter a valid phone number")

    gender = st.selectbox("Gender", ["M", "F"])
    electricity_bill = st.radio("Is electricity bill available?", ["Yes", "No"])

    net_salary = st.number_input("Net Salary", min_value=0)
    emi = st.number_input("EMI", min_value=0)
    bike_type = st.text_input("Bike Type")
    bike_price = st.number_input("Bike Price", min_value=0)

    if electricity_bill == "No":
        st.error("❌ Applicant Rejected - Electricity bill not available")
    else:
        if st.button("Save Applicant"):
            data = {
                "first_name": first_name,
                "last_name": last_name,
                "cnic": cnic,
                "license_no": license_no,
                "guarantors": guarantors,
                "female_guarantor": female_guarantor,
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
                "bike_price": bike_price
            }
            if save_to_db(data):
                st.success("✅ Applicant saved successfully!")

# -----------------------------
# Page 4: Applicants Database
# -----------------------------
with tabs[3]:
    st.header("👥 Applicants Database")

    df = fetch_all_applicants()
    if df.empty:
        st.info("No applicants found.")
    else:
        st.dataframe(df, use_container_width=True)

        # Download Excel
        excel_bytes = df_to_excel_bytes(df)
        st.download_button("📥 Download Excel", data=excel_bytes,
                           file_name="applicants.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        # Safe delete dropdown
        st.subheader("🗑️ Delete Applicant")
        options = [f"{row['id']} - {row['first_name']} {row['last_name']}" for _, row in df.iterrows()]
        selected = st.selectbox("Select Applicant to Delete", options)

        if st.button("Delete Selected Applicant"):
            if selected:
                selected_id = int(selected.split(" - ")[0])
                try:
                    conn = get_db_connection()
                    cur = conn.cursor()
                    cur.execute("DELETE FROM data WHERE id = %s", (selected_id,))
                    conn.commit()
                    cur.close()
                    conn.close()
                    st.success(f"✅ Applicant {selected_id} deleted successfully.")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Failed to delete applicant: {e}")
