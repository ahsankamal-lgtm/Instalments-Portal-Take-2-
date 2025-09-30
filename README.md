# ⚡ Electric Bike Loan Scoring Portal

This is a Streamlit-based web application for evaluating applicants for installment-based electric bike loans.  
It calculates a loan eligibility score based on salary, gender, and average 6-month bank balance,  
and stores approved applicants in a Postgres database.

---

## 🚀 Features
- Multi-step form (Applicant Info → Scoring → Results).
- Validates CNIC format, required fields, guarantors, etc.
- Calculates:
  - Base Income Score
  - Adjusted Income Score (gender-adjusted)
  - Balance Score
  - Final Score
  - Decision (Approve / Manual Review / Reject)
- Provides **expert-style reasoning** for decisions.
- Saves approved applicants into a **Postgres database**.
- Displays and allows **CSV export** of all applicants.

---

## 🛠️ Setup Instructions

### 1. Clone or upload to GitHub
Put these files into your GitHub repository:
- `streamlit_instalment_portal.py`
- `requirements.txt`
- `README.md`

### 2. Deploy to Streamlit Cloud
1. Go to [Streamlit Cloud](https://streamlit.io/cloud) and sign in with GitHub.
2. Create a **New App** → select this repo → main file = `streamlit_instalment_portal.py`.
3. Streamlit installs everything from `requirements.txt`.

### 3. Setup Database
The app is ready for **Postgres** (recommended).  
- Create a free Postgres database on [Supabase](https://supabase.com), [Render](https://render.com), or Heroku.  
- Copy the database connection string, it looks like:

  ```
  postgresql://username:password@hostname:5432/databasename
  ```

- On Streamlit Cloud:
  - Open your app → **Manage app** → **Settings → Secrets**.  
  - Add:

    ```toml
    DATABASE_URL="postgresql://username:password@hostname:5432/databasename"
    ```

### 4. Run the App
- After secrets are saved, redeploy the app.  
- Streamlit will now connect to your Postgres DB and persist data.  

---

## ✅ Usage
1. Open your app’s public link.
2. Enter applicant details (validated).
3. Calculate score → see decision + reasoning.
4. Approved applicants are added to the database.
5. Download the approved list as CSV.

---

## 📊 Decision Criteria
- **Final Score ≥ 75** → Approve ✅
- **60 ≤ Final Score < 75** → Manual Review 🟡
- **Final Score < 60** → Reject ❌

Decisions are supported by clear **financial risk-based reasoning**.
