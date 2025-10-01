import streamlit as st
import pandas as pd
import mysql.connector
from mysql.connector import Error
import io

# ---------------- DATABASE CONNECTION ----------------
def create_connection():
    try:
        connection = mysql.connector.connect(
            host="3.17.21.91",
            database="ev_installment_project",
            user="ahsan",
            password="ahsan@321"
        )
        return connection
    except Error as e:
        st.error(f"❌ Database connection failed: {e}")
        return None

# ---------------- FETCH APPLICANTS ----------------
def fetch_applicants():
    connection = create_connection()
    if connection:
        try:
            query = "SELECT * FROM data"
            df = pd.read_sql(query, connection)
            connection.close()
            return df
        except Error as e:
            st.error(f"❌ Failed to fetch applicants: {e}")
            return pd.DataFrame()
    return pd.DataFrame()

# ---------------- DELETE FUNCTIONS ----------------
def delete_applicant(applicant_id):
    connection = create_connection()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("DELETE FROM data WHERE id = %s", (applicant_id,))
            connection.commit()
            connection.close()
            return True
        except Error as e:
            st.error(f"❌ Failed to delete applicant: {e}")
            return False
    return False

def bulk_delete(applicant_ids):
    connection = create_connection()
    if connection:
        try:
            cursor = connection.cursor()
            format_strings = ','.join(['%s'] * len(applicant_ids))
            cursor.execute(f"DELETE FROM data WHERE id IN ({format_strings})", tuple(applicant_ids))
            connection.commit()
            connection.close()
            return True
        except Error as e:
            st.error(f"❌ Failed bulk delete: {e}")
            return False
    return False

# ---------------- DOWNLOAD HELPERS ----------------
def convert_df_to_csv(df):
    return df.to_csv(index=False).encode("utf-8")

def convert_df_to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Applicants")
    processed_data = output.getvalue()
    return processed_data

# ---------------- STREAMLIT APP ----------------
st.set_page_config(page_title="Electric Bike Finance Portal", layout="wide")

tabs = ["Applicant Information", "Evaluation", "Results", "Applicants"]
current_tab = st.sidebar.radio("Navigation", tabs)

if current_tab == "Applicants":
    st.header("📋 Applicants Database")

    # Button to reload applicants after changes
    if st.button("🔄 Refresh Applicants"):
        st.experimental_rerun()

    df = fetch_applicants()

    if df.empty:
        st.info("No applicants found in the database.")
    else:
        # Show applicants table with index
        st.dataframe(df)

        # Download options
        csv = convert_df_to_csv(df)
        st.download_button(
            "⬇️ Download CSV",
            data=csv,
            file_name="applicants.csv",
            mime="text/csv",
        )

        excel = convert_df_to_excel(df)
        st.download_button(
            "⬇️ Download Excel",
            data=excel,
            file_name="applicants.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        st.subheader("🗑 Manage Applicants")

        # Individual delete
        selected_id = st.number_input("Enter Applicant ID to delete", min_value=1, step=1)
        if st.button("Delete Selected Applicant"):
            if st.checkbox("Confirm deletion of selected applicant"):
                if delete_applicant(selected_id):
                    st.success(f"✅ Applicant ID {selected_id} deleted successfully.")
                    st.experimental_rerun()
            else:
                st.warning("⚠️ Please confirm deletion by ticking the checkbox.")

        # Bulk delete
        bulk_ids = st.text_input("Enter Applicant IDs to delete (comma separated)")
        if st.button("Bulk Delete"):
            if st.checkbox("Confirm bulk deletion"):
                try:
                    ids = [int(x.strip()) for x in bulk_ids.split(",") if x.strip().isdigit()]
                    if ids and bulk_delete(ids):
                        st.success(f"✅ Applicants {ids} deleted successfully.")
                        st.experimental_rerun()
                except ValueError:
                    st.error("❌ Invalid IDs. Please enter comma-separated numeric IDs.")
            else:
                st.warning("⚠️ Please confirm bulk deletion by ticking the checkbox.")
