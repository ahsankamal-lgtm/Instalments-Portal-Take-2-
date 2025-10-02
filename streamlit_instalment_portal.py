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
            st.dataframe(df, use_container_width=True, hide_index=True)

            # Dropdown for Delete Row
            df["full_label"] = df.apply(lambda row: f"{row['id']} - {row['first_name']} {row['last_name']}", axis=1)
            selected_applicant = st.selectbox("Select Applicant to Delete", options=df["full_label"].tolist())

            if st.button("🗑️ Delete Selected Applicant"):
                try:
                    # Extract ID from selection
                    delete_id = int(selected_applicant.split(" - ")[0])

                    conn = get_db_connection()
                    cur = conn.cursor()
                    cur.execute("DELETE FROM data WHERE id = %s", (delete_id,))
                    conn.commit()

                    # Re-sequence IDs
                    cur.execute("SET @count = 0")
                    cur.execute("UPDATE data SET id = @count:=@count+1")
                    conn.commit()

                    cur.close()
                    conn.close()
                    st.success(f"✅ Applicant {selected_applicant} deleted successfully and IDs resequenced.")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Failed to delete applicant: {e}")

            # 📥 Download Excel Button
            from io import BytesIO
            output = BytesIO()
            with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                df.drop(columns=["full_label"]).to_excel(writer, index=False, sheet_name="Applicants")
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
