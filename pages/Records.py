def run_recordings():
    import streamlit as st
    import pandas as pd
    from datetime import datetime, timedelta
    from sqlalchemy import create_engine, text

    st.title("New Expense/Income Recording & Category Management")

    # --- Database connection ---
    DB_URL = st.secrets["postgres"]["url"]
    engine = create_engine(DB_URL, connect_args={"sslmode": "verify-full"})

    # --- Load categories ---
    cat_df = pd.read_sql("SELECT * FROM categories", engine)

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
                    with engine.begin() as conn:
                        conn.execute(text("""
                            INSERT INTO categories (category, type, color, icon)
                            VALUES (:category, :type, :color, :icon)
                        """), {"category": new_cat_name, "type": new_cat_type,
                               "color": new_cat_color, "icon": new_cat_icon})
                    st.success(f"Category '{new_cat_name}' added!")
                    cat_df = pd.read_sql("SELECT * FROM categories", engine)

        # Edit category
        edit_cat = st.selectbox("Edit Category", options=[""] + cat_df["category"].tolist())
        if edit_cat:
            row = cat_df[cat_df["category"] == edit_cat].iloc[0]
            new_name = st.text_input("Category Name", value=row["category"])
            new_type = st.selectbox("Type", ["Income","Expense"], index=0 if row["type"]=="Income" else 1)
            new_color = st.color_picker("Color", value=row["color"] if pd.notna(row["color"]) else "#FFFFFF")
            new_icon = st.text_input("Icon", value=row["icon"] if pd.notna(row["icon"]) else "")
            if st.button("Save Changes"):
                with engine.begin() as conn:
                    conn.execute(text("""
                        UPDATE categories
                        SET category=:new_name, type=:new_type, color=:color, icon=:icon
                        WHERE category=:old_name
                    """), {"new_name": new_name, "new_type": new_type,
                           "color": new_color, "icon": new_icon, "old_name": edit_cat})
                st.success(f"Category '{edit_cat}' updated!")
                cat_df = pd.read_sql("SELECT * FROM categories", engine)

        # Delete category
        del_cat = st.selectbox("Delete Category", options=[""] + cat_df["category"].tolist())
        if del_cat and st.button("Delete Category"):
            with engine.begin() as conn:
                conn.execute(text("DELETE FROM categories WHERE category=:category"), {"category": del_cat})
            st.success(f"Category '{del_cat}' deleted!")
            cat_df = pd.read_sql("SELECT * FROM categories", engine)

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
        
        # Convert to native Python types
        category_id_py = int(category_id)
        amount_py = float(amount)
        
        with engine.begin() as conn:
            # Insert main transaction (date-only)
            conn.execute(text(f"""
                INSERT INTO {table} (date, category_id, amount, title, comment)
                VALUES (:date, :category_id, :amount, :title, :comment)
            """), {
                "date": date,  # already datetime.date from st.date_input
                "category_id": category_id_py,
                "amount": amount_py,
                "title": title,
                "comment": "Recurring" if is_recurring else comment
            })

            # Insert recurring transactions
            if is_recurring:
                future_dates = generate_dates(date, end_date, frequency)
                for d in future_dates[1:]:
                    conn.execute(text(f"""
                        INSERT INTO {table} (date, category_id, amount, title, comment)
                        VALUES (:date, :category_id, :amount, :title, 'Recurring')
                    """), {
                        "date": d,  # each d is a datetime.date
                        "category_id": category_id_py,
                        "amount": amount_py,
                        "title": title
                    })

                # Save to recurrings table
                conn.execute(text("""
                    INSERT INTO recurrings (title, category_id, amount, type, start_date, frequency, end_date, active)
                    VALUES (:title, :category_id, :amount, :type, :start_date, :frequency, :end_date, TRUE)
                """), {
                    "title": title,
                    "category_id": category_id_py,
                    "amount": amount_py,
                    "type": exp_or_inc,
                    "start_date": date,
                    "frequency": frequency,
                    "end_date": end_date
                })

        st.success(f"{exp_or_inc} transaction saved successfully!")
