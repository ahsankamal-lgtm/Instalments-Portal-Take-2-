import streamlit as st
import re
import webbrowser
import mysql.connector
import pandas as pd

# ---------------- DATABASE FUNCTIONS ----------------
def save_applicant_to_db(applicant_data):
    try:
        conn = mysql.connector.connect(
            host="3.17.21.91",
            user="ahsan",
            password="ahsan@321",
            database="ev_installment_project"
        )
        cursor = conn.cursor()

        insert_query = """
        INSERT INTO data (
            first_name, last_name, cnic, license_no,
            guarantors, female_guarantor, address, area, city,
            gender, net_salary, monthly_instalment, bike_type, bike_price, emi
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        cursor.execute(insert_query, (
            applicant_data["first_name"],
            applicant_data["last_name"],
            applicant_data["cnic"],
            applicant_data["license_no"],
            applicant_data["guarantors"],
            applicant_data["female_guarantor"],
            applicant_data["address"],
            applicant_data["area"],
            applicant_data["city"],
            applicant_data["gender"],
            applicant_data["net_salary"],
            applicant_data["monthly_instalment"],
            applicant_data["bike_type"],
            applicant_data["bike_price"],
            applicant_data["emi"],
        ))

        conn.commit()
        conn.close()
        return True, "✅ Applicant information saved to database successfully."

    except Exception as e:
        return False, f"❌ Failed to save applicant: {str(e)}"

def fetch_all_data():
    try:
        conn = mysql.connector.connect(
            host="3.17.21.91",
            user="ahsan",
            password="ahsan@321",
            database="ev_installment_project"
        )
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM data")
        rows = cursor.fetchall()
        conn.close()
        return pd.DataFrame(rows)
    except Exception as e:
        return pd.DataFrame(), f"❌ Failed to fetch data: {str(e)}"


# ---------------- STREAMLIT APP ----------------
st.set_page_config(page_title="Electric Bike Finance Portal", layout="wide")

st.title("⚡ Electric Bike Finance Portal")

tabs = st.tabs(["📝 Applicant Info", "📊 Evaluation", "📋 Results", "📋 Applicants"])

# ---------------- APPLICANT INFO TAB ----------------
with tabs[0]:
    st.header("Applicant Information")

    with st.form("applicant_form"):
        first_name = st.text_input("First Name")
        last_name = st.text_input("Last Name")
        cnic = st.text_input("CNIC Number (Format: XXXXX-XXXXXXX-X)")
        license_suffix = st.text_input("Enter last 3 digits for License Number")
        guarantors = st.number_input("Number of Guarantors", min_value=0, step=1)
        female_guarantor = st.checkbox("At least 1 Female Guarantor Present")
        address = st.text_input("Address")
        area = st.text_input("Area")
        city = st.text_input("City")
        gender = st.selectbox("Gender", ["Male", "Female", "Other"])

        # Google Maps button
        if st.form_submit_button("📍 View Location on Google Maps"):
            if address and area and city:
                maps_url = f"https://www.google.com/maps/search/{address}, {area}, {city}"
                webbrowser.open_new_tab(maps_url)

        submitted = st.form_submit_button("✅ Save Applicant Info")

    if submitted:
        # Validation
        if not re.match(r"^\d{5}-\d{7}-\d{1}$", cnic):
            st.error("❌ Invalid CNIC format. Use XXXXX-XXXXXXX-X")
        elif len(license_suffix) != 3 or not license_suffix.isdigit():
            st.error("❌ License suffix must be exactly 3 digits.")
        elif not female_guarantor:
            st.error("❌ At least one female guarantor is required.")
        else:
            license_no = f"{cnic}#{license_suffix}"
            st.session_state["applicant_info"] = {
                "first_name": first_name,
                "last_name": last_name,
                "cnic": cnic,
                "license_no": license_no,
                "guarantors": guarantors,
                "female_guarantor": "Yes" if female_guarantor else "No",
                "address": address,
                "area": area,
                "city": city,
                "gender": gender,
            }
            st.success("✅ Applicant information saved! Please proceed to Evaluation.")


# ---------------- EVALUATION TAB ----------------
with tabs[1]:
    st.header("Evaluation")
    if "applicant_info" not in st.session_state:
        st.warning("⚠️ Please complete Applicant Information first.")
    else:
        net_salary = st.number_input("Net Monthly Salary", min_value=0)
        monthly_instalment = st.number_input("Monthly Instalment", min_value=0)
        bike_type = st.selectbox("Bike Type", ["Electric Bike A", "Electric Bike B"])
        bike_price = st.number_input("Bike Price", min_value=0)

        # EMI calculation
        emi = monthly_instalment

        if st.button("Run Evaluation"):
            if net_salary >= emi * 3:
                st.session_state["evaluation"] = {
                    "net_salary": net_salary,
                    "monthly_instalment": monthly_instalment,
                    "bike_type": bike_type,
                    "bike_price": bike_price,
                    "emi": emi,
                    "decision": "Approved ✅",
                }
            else:
                st.session_state["evaluation"] = {
                    "net_salary": net_salary,
                    "monthly_instalment": monthly_instalment,
                    "bike_type": bike_type,
                    "bike_price": bike_price,
                    "emi": emi,
                    "decision": "Rejected ❌",
                }
            st.success("✅ Evaluation complete! Check the Results tab.")


# ---------------- RESULTS TAB ----------------
with tabs[2]:
    st.header("Results")
    if "evaluation" not in st.session_state:
        st.warning("⚠️ Run evaluation first.")
    else:
        result = st.session_state["evaluation"]
        st.subheader("📊 Decision Result")
        st.write(f"**Decision:** {result['decision']}")
        st.write(f"**Net Salary:** {result['net_salary']}")
        st.write(f"**Monthly Instalment (EMI):** {result['monthly_instalment']}")
        st.write(f"**Bike Type:** {result['bike_type']}")
        st.write(f"**Bike Price:** {result['bike_price']}")

        if result["decision"] == "Approved ✅":
            if st.button("💾 Save to Database"):
                applicant_data = {
                    **st.session_state["applicant_info"],
                    **result,
                }
                success, msg = save_applicant_to_db(applicant_data)
                if success:
                    st.success(msg)
                else:
                    st.error(msg)


# ---------------- APPLICANTS TAB ----------------
with tabs[3]:
    st.header("📋 Saved Applicants")
    if st.button("🔄 Load Applicants"):
        df = fetch_all_data()
        if not df.empty:
            st.dataframe(df)
        else:
            st.warning("⚠️ No applicants found in database.")
