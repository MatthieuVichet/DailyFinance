def run_recordings():
    import streamlit as st
    import pandas as pd
    from datetime import datetime, timedelta
    from st_supabase_connection import SupabaseConnection

    st.title("New Expense/Income Recording & Category Management")

    # --- Connect to Supabase ---
    conn = st.connection("supabase", type=SupabaseConnection)

    # --- Load categories ---
    cat_df = pd.DataFrame(conn.table("categories").select("*").execute().data)

    # --- Category Management ---
    st.subheader("Category Management")
    with st.expander("Add/Edit/Delete Categories"):

        # Add new category
        with st.form("add_category_form"):
            new_cat_name = st.text_input("Category Name")
            new_cat_type = st.selectbox("Type", ["Income","Expense"])
            new_cat_color = st.color_picker("Color", value="#FFFFFF")
            new_cat_icon = st.text_input("Icon (emoji or text)")
            submitted = st.form_submit_button("Add Category")
            if submitted and new_cat_name:
                if new_cat_name in cat_df["category"].values:
                    st.warning("Category already exists!")
                else:
                    conn.table("categories").insert({
                        "category": new_cat_name,
                        "type": new_cat_type,
                        "color": new_cat_color,
                        "icon": new_cat_icon
                    }).execute()
                    st.success(f"Category '{new_cat_name}' added!")
                    cat_df = pd.DataFrame(conn.table("categories").select("*").execute().data)

        # Edit category
        edit_cat = st.selectbox("Edit Category", options=[""] + cat_df["category"].tolist())
        if edit_cat:
            row = cat_df[cat_df["category"] == edit_cat].iloc[0]
            new_name = st.text_input("Category Name", value=row["category"])
            new_type = st.selectbox("Type", ["Income","Expense"], index=0 if row["type"]=="Income" else 1)
            new_color = st.color_picker("Color", value=row["color"] if pd.notna(row["color"]) else "#FFFFFF")
            new_icon = st.text_input("Icon", value=row["icon"] if pd.notna(row["icon"]) else "")
            if st.button("Save Changes"):
                conn.table("categories").update({
                    "category": new_name,
                    "type": new_type,
                    "color": new_color,
                    "icon": new_icon
                }).eq("category", edit_cat).execute()
                st.success(f"Category '{edit_cat}' updated!")
                cat_df = pd.DataFrame(conn.table("categories").select("*").execute().data)

        # Delete category
        del_cat = st.selectbox("Delete Category", options=[""] + cat_df["category"].tolist())
        if del_cat and st.button("Delete Category"):
            conn.table("categories").delete().eq("category", del_cat).execute()
            st.success(f"Category '{del_cat}' deleted!")
            cat_df = pd.DataFrame(conn.table("categories").select("*").execute().data)

    # --- Record Transaction ---
    st.subheader("Record Transaction")
    exp_or_inc = st.selectbox("Is it an expense or an income?", options=["Expense","Income"])
    date = st.date_input("Date")

    # Show category names for selection, but get category_id for inserts
    categories_for_type = cat_df[cat_df["type"]==exp_or_inc][["id","category"]]
    category_name = st.selectbox("Category", options=categories_for_type["category"].tolist())
    category_id = categories_for_type[categories_for_type["category"]==category_name]["id"].values[0]

    amount = st.number_input("Amount")
    title = st.text_input("Title")
    comment = st.text_area("Commentary")
    is_recurring = st.checkbox("Recurring Transaction?")

    if is_recurring:
        frequency = st.selectbox("Frequency", options=["Daily","Weekly","Monthly","Yearly"])
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
                day = min(current.day,28)
                current = current.replace(year=year, month=month, day=day)
            elif freq.lower() == "yearly":
                current = current.replace(year=current.year+1)
            else:
                break
        return dates

    # --- Save Transaction ---
    if st.button("Save Transaction"):
        table = "incomes" if exp_or_inc=="Income" else "expenses"

        # Insert main transaction
        conn.table(table).insert({
            "date": date.isoformat(),  # convert to ISO string
            "category_id": int(category_id),
            "amount": float(amount),
            "title": title,
            "comment": "Recurring" if is_recurring else comment
        }).execute()

        # Insert recurring transactions
        if is_recurring:
            future_dates = generate_dates(date, end_date, frequency)
            for d in future_dates[1:]:
                conn.table(table).insert({
                    "date": d.isoformat(),  # convert to ISO string
                    "category_id": int(category_id),
                    "amount": float(amount),
                    "title": title,
                    "comment": "Recurring"
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
                "active": True
            }).execute()

        st.success(f"{exp_or_inc} transaction saved successfully!")
