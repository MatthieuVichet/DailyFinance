def run_recurring():
    import streamlit as st
    import pandas as pd
    from datetime import datetime, timedelta
    from sqlalchemy import create_engine, text

    st.title("Recurring Transactions")

    # --- Database connection ---
    DB_URL = st.secrets["postgres"]["url"]
    engine = create_engine(DB_URL)

    # --- Load recurring transactions ---
    recurring_df = pd.read_sql("SELECT * FROM recurrings WHERE active = TRUE", engine)
    if recurring_df.empty:
        st.warning("No active recurring transactions found.")
        st.stop()

    recurring_df["start_date"] = pd.to_datetime(recurring_df["start_date"])
    recurring_df["end_date"] = pd.to_datetime(recurring_df["end_date"])

    # --- Helper: generate future dates ---
    def generate_dates(row):
        dates = []
        current = max(row["start_date"], datetime.today())
        end = row["end_date"]
        freq = row["frequency"].lower()

        while current <= end:
            dates.append(current)
            if freq == "daily":
                current += timedelta(days=1)
            elif freq == "weekly":
                current += timedelta(weeks=1)
            elif freq == "monthly":
                month = current.month + 1 if current.month < 12 else 1
                year = current.year + (current.month // 12)
                day = min(current.day, 28)
                current = current.replace(year=year, month=month, day=day)
            elif freq == "yearly":
                current = current.replace(year=current.year+1)
            else:
                break
        return dates

    # --- Generate and insert future entries ---
    new_entries_count = 0
    for _, row in recurring_df.iterrows():
        future_dates = generate_dates(row)
        table = "incomes" if row["type"] == "Income" else "expenses"

        for date in future_dates:
            engine.execute(text(f"""
                INSERT INTO {table} (date, category, amount, title, comment)
                VALUES (:date, :category, :amount, :title, 'Recurring')
            """), {"date": date, "category": row["category"], "amount": row["amount"], "title": row["title"]})
            new_entries_count += 1

    st.success(f"{new_entries_count} recurring entries generated!")

    # --- Display active recurring transactions ---
    st.subheader("Active Recurring Transactions")
    st.dataframe(recurring_df)
