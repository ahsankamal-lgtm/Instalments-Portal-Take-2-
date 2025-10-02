import streamlit as st
import pandas as pd
import mysql.connector
from mysql.connector import Error
from io import BytesIO

# -----------------------------
# DB Connection
# -----------------------------
def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host="3.17.21.91",    # update if needed
            user="ahsan",
            password="ahsan@321",
            database="ev_installment_project"
        )
        return conn
    except Error as e:
        st.error(f"❌ Database connection failed: {e}")
        return None

# -----------------------------
# Save applicant info
# -----------------------------
def save_to_db(applicant):
    try:
        conn = get_db_connection()
        if conn is None:
            return
        cur = conn.cursor()

        query = """
            INSERT INTO data (
                first_name, last_name, cnic, license_no, guarantors, female_guarantor,
                street_address, area_address, city, state_province, postal_code, country,
                phone_number, gender, electricity_bill, net_salary, emi, bike_type, bike_price
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        values = (
            applicant["first_name"], applicant["last_name"], applicant["cnic"],
            applicant["license_no"], applicant["guarantors"], applicant["female_guarantor"],
            applicant["street_address"], applicant["area_address"], applicant["city"],
            applicant["state_province"], applicant["postal_code"], applicant["country"],
            applicant["phone_number"], applicant["gender"], applicant["electricity_bill"],
            applicant["net_salary"], applicant["emi"], applicant["bike_type"], applicant["bike_price"]
        )

        cur.execute(query, values)
        conn.commit()
        cur.close()
        conn.close()
        st.success("✅ Applicant saved successfully!")
    except Error as e:
        st.error(f"❌ Failed to save applicant: {e}")

# -----------------------------
# Fetch all applicants
# -----------------------------
def fetch_all_applicants():
    try:
        conn = get_db_connection()
        if conn is None:
            return pd.DataFrame()
        query = "SELECT * FROM data ORDER BY created_at DESC"
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except Error as e:
        st.error(f"❌ Failed to load applicants: {e}")
        return pd.DataFrame()

# -----------------------------
# Delete applicant
# -----------------------------
def delete_applicant(applicant_id):
    try:
        conn = get_db_connection()
        if conn is None:
            return
        cur = conn.cursor()
        cur.execute("DELETE FROM data WHERE id = %s", (applicant_id,))
        conn.commit()
        cur.close()
        conn.close()
        st.success(f"✅ Applicant with ID {applicant_id} deleted.")
    except Error as e:
        st.error(f"❌ Failed to delete applicant: {e}")

# -----------------------------
# File export helpers
# -----------------------------
def df_to_csv_bytes(df):
    return df.to_csv(index=False).encode("utf-8")

def df_to_excel_bytes(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Applicants")
    return output.getvalue()

# -----------------------------
# Streamlit App
# -----------------------------
st.set_page_config(page_title="Applicant Portal", layout="wide")
st.title("📋 Instalment Applicant Portal")

tabs = st.tabs(["Applicant Info", "Evaluation", "Results", "Applicants Database"])

# -----------------------------
# Page 1: Applicant Info
# -----------------------------
with tabs[0]:
    st.subheader("📝 Applicant Information")

    first_name = st.text_input("First Name")
    last_name = st.text_input("Last Name")
    cnic = st.text_input("CNIC")
    license_no = st.text_input("License Number")
    guarantors = st.text_input("Number of Guarantors")
    female_guarantor = st.text_input("Female Guarantor (Yes/No)")

    # Address fields
    street_address = st.text_input("Street Address")
    area_address = st.text_input("Area Address")
    city = st.text_input("City")
    state_province = st.text_input("State/Province")
    postal_code = st.text_input("Postal Code (Optional)")
    country = st.text_input("Country")

    # Phone with validation
    phone_number = st.text_input("Phone Number (11-12 digits)")
    if phone_number and (len(phone_number) < 11 or len(phone_number) > 12):
        st.error("❌ Invalid Phone Number - Please enter a valid phone number")

    gender = st.selectbox("Gender", ["M", "F"])

    # Electricity bill check
    electricity_bill = st.radio("Is electricity bill available?", ["Yes", "No"])
    if electricity_bill == "No":
        st.error("⚠️ Applicant rejected: Electricity bill required to continue.")
        st.stop()

    net_salary = st.number_input("Net Salary", min_value=0)
    emi = st.number_input("Expected EMI", min_value=0)
    bike_type = st.text_input("Bike Type")
    bike_price = st.number_input("Bike Price", min_value=0)

    # Save applicant button
    if st.button("💾 Save Applicant"):
        if not phone_number or len(phone_number) not in [11, 12]:
            st.error("❌ Invalid Phone Number - Please enter a valid phone number")
        else:
            applicant = {
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
                "bike_price": bike_price,
            }
            save_to_db(applicant)

    # View Location button
    if st.button("📍 View Location on Map"):
        full_address = f"{street_address}, {area_address}, {city}, {state_province}, {country}"
        st.map(pd.DataFrame({"lat": [24.8607], "lon": [67.0011]}))  # Placeholder map (Karachi)
        st.info(f"Showing location for: {full_address}")

# -----------------------------
# Page 4: Applicants Database
# -----------------------------
with tabs[3]:
    st.subheader("👥 Applicants Database")

    df = fetch_all_applicants()
    if df.empty:
        st.info("No applicants found.")
    else:
        st.dataframe(df, use_container_width=True)

        # Download buttons
        csv_bytes = df_to_csv_bytes(df)
        st.download_button("📥 Download CSV", data=csv_bytes,
                           file_name="applicants.csv", mime="text/csv")

        excel_bytes = df_to_excel_bytes(df)
        st.download_button("📥 Download Excel", data=excel_bytes,
                           file_name="applicants.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        # Delete applicant dropdown
        st.subheader("🗑️ Delete Applicant")
        applicant_options = [f"{row['id']} - {row['first_name']} {row['last_name']}" for _, row in df.iterrows()]
        selected = st.selectbox("Select applicant to delete", ["--Select--"] + applicant_options)

        if selected != "--Select--":
            selected_id = int(selected.split(" - ")[0])
            if st.button("Confirm Delete"):
                delete_applicant(selected_id)
