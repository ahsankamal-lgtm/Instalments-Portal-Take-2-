import re
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, Float, String, Boolean, DateTime, MetaData, Table
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

# ===============================
# Database Setup
# ===============================
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///customers.db")
engine = create_engine(DATABASE_URL)
metadata = MetaData()

customers_table = Table(
    "customers", metadata,
    Column("id", Integer, primary_key=True),
    Column("first_name", String),
    Column("last_name", String),
    Column("address", String),
    Column("cnic", String, unique=True),
    Column("license", String),
    Column("electricity_bills", Boolean),
    Column("guarantors_available", Boolean),
    Column("gender", String),
    Column("net_salary", Integer),
    Column("avg_balance", Integer),
    Column("instalment", Integer),
    Column("income_score", Float),
    Column("adjusted_income_score", Float),
    Column("balance_score", Float),
    Column("final_score", Float),
    Column("decision", String),
    Column("reason", String),
    Column("created_at", DateTime, default=datetime.utcnow),
)

metadata.create_all(engine)
Session = sessionmaker(bind=engine)

# ===============================
# Scoring Functions
# ===============================
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

def balance_score(avg_balance: float, instalment: float = 10000) -> float:
    target = 3 * instalment
    if avg_balance >= target:
        return 100
    return (avg_balance / target) * 100

def final_score(net_salary: float, gender: str, avg_balance: float, instalment: float = 10000) -> float:
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

def reasoning(net_salary, gender, avg_balance, instalment, final):
    reasons = []
    if net_salary < 50000:
        reasons.append("Net salary below safe lending threshold (PKR 50,000).")
    if avg_balance < 3 * instalment:
        reasons.append("Bank balance insufficient to cover 3× instalment amount.")
    if gender.upper() == "F":
        reasons.append("Female applicant – positive adjustment applied for income stability.")
    if final >= 75:
        reasons.append("Strong financial standing: meets salary and balance criteria.")
    elif 60 <= final < 75:
        reasons.append("Moderate financial standing: requires manual review to mitigate risk.")
    else:
        reasons.append("High risk: insufficient salary or bank balance for repayment capacity.")
    return " ".join(reasons)

# ===============================
# Streamlit App
# ===============================
st.set_page_config(page_title="Electric Bike Loan Scoring Portal", layout="wide")

if "page" not in st.session_state:
    st.session_state.page = "form"

st.title("⚡ Electric Bike Loan Scoring Portal")

# -------------------------------
# PAGE 1: Applicant Information
# -------------------------------
if st.session_state.page == "form":
    st.header("Step 1: Applicant Information")

    first_name = st.text_input("First Name")
    last_name = st.text_input("Last Name")
    address = st.text_area("Residential Address")
    cnic = st.text_input("CNIC Number (XXXXX-XXXXXXX-X)")
    license_num = st.text_input("Driving License Number")
    electricity_bills = st.radio("Electricity Bills Submitted?", ["Yes", "No"])
    guarantors = st.radio("Two guarantors available (at least one female)?", ["Yes", "No"])
    gender = st.radio("Gender", ["M", "F"])

    # Validation
    errors = []
    if cnic and not re.match(r"^\d{5}-\d{7}-\d{1}$", cnic):
        errors.append("CNIC format is invalid. Use XXXXX-XXXXXXX-X")

    if st.button("Next"):
        if errors:
            for e in errors:
                st.error(e)
        elif not all([first_name, last_name, address, cnic, license_num]):
            st.error("All fields are required.")
        else:
            st.session_state.applicant = {
                "first_name": first_name,
                "last_name": last_name,
                "address": address,
                "cnic": cnic,
                "license": license_num,
                "electricity_bills": electricity_bills == "Yes",
                "guarantors": guarantors == "Yes",
                "gender": gender,
            }
            st.session_state.page = "scoring"
            st.experimental_rerun()

# -------------------------------
# PAGE 2: Scoring Calculator
# -------------------------------
elif st.session_state.page == "scoring":
    st.header("Step 2: Scoring Calculator")

    salary_input = st.text_input("Net Salary (PKR)", value="0")
    balance_input = st.text_input("6-month Avg Bank Balance (PKR)", value="0")
    instalment = st.number_input("Installment Amount (PKR)", min_value=5000, step=1000, value=10000)

    def parse_amount(text):
        try:
            return int(text.replace(",", "").strip())
        except:
            return 0

    net_salary = parse_amount(salary_input)
    avg_balance = parse_amount(balance_input)
    gender = st.session_state.applicant["gender"]

    if st.button("Calculate Score"):
        inc_score = income_score(net_salary)
        adj_inc_score = adjusted_income_score(net_salary, gender)
        bal_score = balance_score(avg_balance, instalment)
        final = final_score(net_salary, gender, avg_balance, instalment)
        result = decision(final)
        reason = reasoning(net_salary, gender, avg_balance, instalment, final)

        st.subheader("📊 Results")
        st.write(f"**Base Income Score:** {inc_score:.2f}")
        st.write(f"**Adjusted Income Score:** {adj_inc_score:.2f}")
        st.write(f"**Balance Score:** {bal_score:.2f}")
        st.write(f"**Final Score:** {final:.2f}")
        st.write(f"**Decision:** {result}")
        st.info(f"**Reasoning:** {reason}")

        # Save to DB
        session = Session()
        new_customer = {
            "first_name": st.session_state.applicant["first_name"],
            "last_name": st.session_state.applicant["last_name"],
            "address": st.session_state.applicant["address"],
            "cnic": st.session_state.applicant["cnic"],
            "license": st.session_state.applicant["license"],
            "electricity_bills": st.session_state.applicant["electricity_bills"],
            "guarantors_available": st.session_state.applicant["guarantors"],
            "gender": gender,
            "net_salary": net_salary,
            "avg_balance": avg_balance,
            "instalment": instalment,
            "income_score": inc_score,
            "adjusted_income_score": adj_inc_score,
            "balance_score": bal_score,
            "final_score": final,
            "decision": result,
            "reason": reason,
            "created_at": datetime.utcnow()
        }
        session.execute(customers_table.insert().values(new_customer))
        session.commit()
        session.close()

        st.success("✅ Applicant added to database")

        st.session_state.page = "results"
        st.experimental_rerun()

# -------------------------------
# PAGE 3: Results & Database
# -------------------------------
elif st.session_state.page == "results":
    st.header("Step 3: Approved Customers Database")

    session = Session()
    rows = session.execute(customers_table.select()).fetchall()
    session.close()

    if rows:
        df = pd.DataFrame(rows, columns=rows[0].keys())
        st.dataframe(df)
        st.download_button("Download CSV", df.to_csv(index=False), "approved_customers.csv")
    else:
        st.info("No customers in database yet.")

