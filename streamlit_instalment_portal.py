import streamlit as st
import pandas as pd
import mysql.connector
from mysql.connector import Error
import re

# ============= Wavetec Branding =============
st.set_page_config(page_title="Wavetec EV Installment Portal", layout="centered")
st.title("Wavetec Electric Bike Installment Portal")

# Optional logo (uncomment when you upload logo.png into same folder)
# st.image("logo.png", width=200)

st.markdown("""
This portal helps evaluate applicants for Wavetec's **Electric Bike Installment Program**.  
Applicants are assessed using a transparent scoring system, and approved customers are stored in a secure database.
""")

# ============= Database Connection Function =============
def get_connection():
    try:
        conn = mysql.connector.connect(
            host="3.17.21.91",
            user="ahsan",
            password="ahsan@321",
            database="ev_installment_project"
        )
        return conn
    except Error as e:
        st.error(f"Database connection failed: {e}")
        return None

# ============= Input Validation =============
def validate_cnic(cnic):
    """Check if CNIC matches XXXXX-XXXXXXX-X"""
    pattern = r"^\d{5}-\d{7}-\d{1}$"
    return re.match(pattern, cnic)

# ============= Scoring Functions =============
def income_score(net_salary: float) -> float:
    if net_salary < 50000:
        return 0
    elif net_salary <= 70000:
        return 20 + (net_salary - 50000) * (40 - 20) / (20000)
    elif net_salary <= 90000:
        return 40 + (net_salary - 70000) * (70 - 40) / (20000)
    elif net_salary <= 110000:
        return 70 + (net_salary - 90000) * (90 - 70) / (20000)
    else:
        return 100

def adjusted_income_score(net_salary: float, gender: str) -> float:
    base = income_score(net_salary)
    if gender.upper() == "F":
        return min(base * 1.10, 100)
    return base

def balance_score(avg_balance: float, instalment: float) -> float:
    target = 3 * instalment
    return 100 if avg_balance >= target else (avg_balance / target) * 100

def final_score(net_salary: float, gender: str, avg_balance: float, instalment: float) -> float:
    inc = adjusted_income_score(net_salary, gender)
    bal = balance_score(avg_balance, instalment)
    return 0.60 * inc + 0.40 * bal

def decision(final: float) -> str:
    if final >= 75:
        return "Approve"
    elif final >= 60:
        return "Manual Review"
    else:
        return "Reject"

# ============= Step 1: Applicant Information =============
st.header("Step 1: Applicant Information")

col1, col2 = st.columns(2)
first_name = col1.text_input("First Name")
last_name = col2.text_input("Last Name")

address = st.text_area("Residential Address")

cnic = st.text_input("CNIC (XXXXX-XXXXXXX-X)")
if cnic and not validate_cnic(cnic):
    st.error("Enter valid CNIC in format XXXXX-XXXXXXX-X")

driving_license = st.text_input("Driving License Number (numeric)")
electricity_bills = st.selectbox("Submitted Electricity Bills?", ["Yes", "No"])
gender = st.radio("Gender", ["M", "F"])
guarantors = st.radio("Two Guarantors (at least one female)?", ["Yes", "No"])

if st.button("Confirm Applicant Information"):
    if not first_name or not last_name or not cnic or not driving_license:
        st.error("Please fill in all required fields.")
    elif not validate_cnic(cnic):
        st.error("Invalid CNIC format.")
    elif guarantors == "No":
        st.error("Applicant must have 2 guarantors (including 1 female).")
    else:
        st.success("Applicant information confirmed. Proceed to scoring below.")

# ============= Step 2: Scoring =============
st.header("Step 2: Score Calculator")

salary_input = st.text_input("Net Salary (PKR)", value="0")
balance_input = st.text_input("Average 6 Months Balance (PKR)", value="0")
instalment = st.number_input("Installment Amount (PKR)", value=10000, step=1000)

# Format input with commas
def parse_amount(x):
    return int(x.replace(",", "")) if x else 0

try:
    net_salary = parse_amount(salary_input)
    avg_balance = parse_amount(balance_input)
    salary_display = f"{net_salary:,}"
    balance_display = f"{avg_balance:,}"
    st.write(f"Net Salary Entered: PKR {salary_display}")
    st.write(f"6-Month Avg Balance: PKR {balance_display}")

    if net_salary > 0 and avg_balance > 0:
        inc_score = income_score(net_salary)
        adj_inc_score = adjusted_income_score(net_salary, gender)
        bal_score = balance_score(avg_balance, instalment)
        final = final_score(net_salary, gender, avg_balance, instalment)
        result = decision(final)

        st.subheader("Scoring Results")
        st.write(f"Base Income Score: {inc_score:.2f}")
        st.write(f"Adjusted Income Score: {adj_inc_score:.2f}")
        st.write(f"Balance Score: {bal_score:.2f}")
        st.write(f"Final Score: {final:.2f}")
        st.write(f"Decision: **{result}**")

        # Expert-style reasoning
        st.subheader("Decision Reasoning")
        if result == "Approve":
            st.success("Approved: Applicant has sufficient income and balance stability, reducing risk of default.")
        elif result == "Manual Review":
            st.warning("Manual Review: Applicant’s financials are borderline. Additional verification is recommended.")
        else:
            st.error("Rejected: Insufficient salary or balance history. High risk of default.")

        # ============= Save to Database if Approved =============
        if result == "Approve":
            if st.button("Save Approved Applicant to Database"):
                conn = get_connection()
                if conn:
                    try:
                        cursor = conn.cursor()
                        insert_query = """
                        INSERT INTO data (first_name, last_name, address, cnic, driving_license, electricity_bills, gender, guarantors, net_salary, avg_balance, instalment, final_score, decision)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """
                        values = (first_name, last_name, address, cnic, driving_license, electricity_bills, gender, guarantors,
                                  net_salary, avg_balance, instalment, final, result)
                        cursor.execute(insert_query, values)
                        conn.commit()
                        st.success("Applicant saved successfully to database!")
                    except Error as e:
                        st.error(f"Error saving to database: {e}")
                    finally:
                        conn.close()

except ValueError:
    st.error("Enter numeric values for salary and balance (commas allowed).")


