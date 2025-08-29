def run_recordings():
    import streamlit as st
    import pandas as pd
    from datetime import datetime, timedelta
    from st_supabase_connection import SupabaseConnection

    # --- Require login ---
    if "user_id" not in st.session_state or st.session_state.user_id is None:
        from pages.Login import run_login
        run_login()
        return

    st.title("New Expense/Income Recording & Category Management")

    # --- Connect to Supabase ---
    conn = st.connection("supabase", type=SupabaseConnection)

    # --- Load categories safely ---
    cat_data = conn.table("categories") \
        .select("*") \
        .eq("user_id", st.session_state.user_id) \
        .execute().data
    cat_df = pd.DataFrame(cat_data)

    # --- CATEGORY MANAGEMENT ---
    st.subheader("Category Management")
    with st.expander("Add/Edit/Delete Categories"):

        # Add new category
        with st.form("add_category_form"):
            new_cat_name = st.text_input("Category Name")
            new_cat_type = st.selectbox("Type", ["Income", "Expense"])
            new_cat_color = st.color_picker("Color", value="#FFFFFF")
            new_cat_icon = st.text_input("Icon (emoji or text)")
            submitted = st.form_submit_button("Add Category")

            if submitted and new_cat_name:
                if (
                    not cat_df.empty
                    and "category" in cat_df.columns
                    and new_cat_name in cat_df["category"].values
                ):
                    st.warning("Category already exists!")
                else:
                    conn.table("categories").insert({
                        "category": new_cat_name,
                        "type": new_cat_type,
                        "color": new_cat_color,
                        "icon": new_cat_icon,
                        "user_id": st.session_state.user_id,
                    }).execute()
                    st.success(f"Category '{new_cat_name}' added!")
                    st.rerun()

        if not cat_df.empty and {"id", "category", "type"}.issubset(cat_df.columns):
            # --- Edit category ---
            edit_cat = st.selectbox("Edit Category", options=[""] + cat_df["category"].tolist())
            if edit_cat:
                row = cat_df[cat_df["category"] == edit_cat].iloc[0]
                new_name = st.text_input("Category Name", value=row["category"])
                new_type = st.selectbox("Type", ["Income", "Expense"], index=0 if row["type"] == "Income" else 1)
                new_color = st.color_picker("Color", value=row.get("color", "#FFFFFF"))
                new_icon = st.text_input("Icon", value=row.get("icon", ""))
                if st.button("Save Changes", type='primary'):
                    conn.table("categories").update({
                        "category": new_name,
                        "type": new_type,
                        "color": new_color,
                        "icon": new_icon,
                    }).eq("id", row["id"]) \
                     .eq("user_id", st.session_state.user_id) \
                     .execute()
                    st.success(f"Category '{edit_cat}' updated!")
                    st.rerun()

            # --- Delete category ---
            del_cat = st.selectbox("Delete Category", options=[""] + cat_df["category"].tolist())
            if del_cat and st.button("Delete Category", type="secondary"):
                conn.table("categories").delete() \
                    .eq("category", del_cat) \
                    .eq("user_id", st.session_state.user_id) \
                    .execute()
                st.success(f"Category '{del_cat}' deleted!")
                st.rerun()
        else:
            st.info("No categories available yet. Add one first.")

    # --- RECORD TRANSACTION ---
    st.subheader("Record Transaction")
    exp_or_inc = st.selectbox("Is it an expense or an income?", options=["Expense", "Income"])
    date = st.date_input("Date")

    if cat_df.empty or not {"id", "category", "type"}.issubset(cat_df.columns):
        st.warning("⚠️ No categories found. Please add categories first.")
        return

    categories_for_type = cat_df[cat_df["type"] == exp_or_inc][["id", "category"]]
    if categories_for_type.empty:
        st.warning(f"No categories found for {exp_or_inc}. Please add one first.")
        return

    category_name = st.selectbox("Category", options=categories_for_type["category"].tolist())
    category_id = categories_for_type[categories_for_type["category"] == category_name]["id"].values[0]

    amount = st.number_input("Amount")
    title = st.text_input("Title")
    comment = st.text_area("Commentary")
    is_recurring = st.checkbox("Recurring Transaction?")

    if is_recurring:
        frequency = st.selectbox("Frequency", options=["Daily", "Weekly", "Monthly", "Yearly"])
        end_date = st.date_input("End Date", min_value=date)

    # --- Helper: generate future dates ---
    def generate_dates(start_date, end_date, freq):
        dates = []
        current = start_date
        while current <= end_date:
            dates.append(current)
            if freq.lower() == "daily":
                current += timedelta(days=1)
            elif freq.lower() == "weekly":
                current += timedelta(weeks=1)
            elif freq.lower() == "monthly":
                month = current.month + 1 if current.month < 12 else 1
                year = current.year + (current.month // 12)
                day = min(current.day, 28)
                current = current.replace(year=year, month=month, day=day)
            elif freq.lower() == "yearly":
                current = current.replace(year=current.year + 1)
            else:
                break
        return dates

    # --- Save Transaction ---
    if st.button("Save Transaction", type="primary"):
        table = "incomes" if exp_or_inc == "Income" else "expenses"

        # Insert main transaction
        conn.table(table).insert({
            "date": date.isoformat(),
            "category_id": int(category_id),
            "amount": float(amount),
            "title": title,
            "user_id": st.session_state.user_id,
            "comment": "Recurring" if is_recurring else comment
        }).execute()

        # Insert recurring transactions
        if is_recurring:
            future_dates = generate_dates(date, end_date, frequency)
            for d in future_dates[1:]:
                conn.table(table).insert({
                    "date": d.isoformat(),
                    "category_id": int(category_id),
                    "amount": float(amount),
                    "title": title,
                    "comment": "Recurring",
                    "user_id": st.session_state.user_id
                }).execute()

            # Save to recurrings table
            conn.table("recurrings").insert({
                "title": title,
                "category_id": int(category_id),
                "amount": float(amount),
                "type": exp_or_inc,
                "start_date": date.isoformat(),
                "frequency": frequency,
                "end_date": end_date.isoformat(),
                "active": True,
                "user_id": st.session_state.user_id
            }).execute()

        st.success(f"{exp_or_inc} transaction saved successfully!")
            
    # --- Edit/Delete Existing Transactions ---
    st.subheader("Manage Existing Transactions")

    # Load user's transactions
    transactions_data = conn.table("incomes").select("*").eq("user_id", st.session_state.user_id).execute().data
    expenses_data = conn.table("expenses").select("*").eq("user_id", st.session_state.user_id).execute().data

    incomes_df = pd.DataFrame(transactions_data)
    expenses_df = pd.DataFrame(expenses_data)

    if not incomes_df.empty:
        incomes_df["Type"] = "Income"
    if not expenses_df.empty:
        expenses_df["Type"] = "Expense"

    df_all = pd.concat([incomes_df, expenses_df], ignore_index=True)
    if df_all.empty:
        st.info("No transactions recorded yet.")
    else:
        # Let user select a record to edit/delete
        record_options = [f"{row['Type']} - {row.get('title', '')} - ${row.get('amount', 0)} ({row.get('date','')})" 
                        for idx, row in df_all.iterrows()]
        selected_record = st.selectbox("Select a transaction to edit/delete", options=[""] + record_options)

        if selected_record:
            # Get the selected row
            idx = record_options.index(selected_record)
            record = df_all.iloc[idx]

            # Edit fields
            new_date = st.date_input("Date", value=pd.to_datetime(record["date"]))
            new_type = st.selectbox("Type", ["Income", "Expense"], index=0 if record["Type"]=="Income" else 1)
            new_amount = st.number_input("Amount", value=float(record["amount"]))
            new_title = st.text_input("Title", value=record.get("title",""))
            new_comment = st.text_area("Comment", value=record.get("comment",""))

            # Save changes
            if st.button("Save Changes", type="primary"):
                table_name = "incomes" if record["Type"]=="Income" else "expenses"
                conn.table(table_name).update({
                    "date": new_date.isoformat(),
                    "amount": new_amount,
                    "title": new_title,
                    "comment": new_comment
                }).eq("id", int(record["id"])).eq("user_id", st.session_state.user_id).execute()
                st.success("Transaction updated successfully!")
                st.rerun()

            # Delete record
            if st.button("Delete Transaction", type="secondary"):
                table_name = "incomes" if record["Type"]=="Income" else "expenses"
                conn.table(table_name).delete().eq("id", int(record["id"])).eq("user_id", st.session_state.user_id).execute()
                st.success("Transaction deleted successfully!")
                st.rerun()
