def run_recurring():
    import streamlit as st
    import pandas as pd
    from datetime import datetime, timedelta
    from st_supabase_connection import SupabaseConnection

    if "user_id" not in st.session_state or st.session_state.user_id is None:
        from pages.Login import run_login
        run_login()
        return

    st.title("Recurring Transactions")

    # --- Connect to Supabase ---
    conn = st.connection("supabase", type=SupabaseConnection)

    # --- Load active recurring transactions for this user only ---
    recurring_df = pd.DataFrame(
        conn.table("recurrings")
            .select("*")
            .eq("user_id", st.session_state.user_id)
            .execute().data
    )

    if recurring_df.empty:
        st.warning("No active recurring transactions found.")
        st.stop()

    # Ensure datetime columns
    recurring_df["start_date"] = pd.to_datetime(recurring_df["start_date"])
    recurring_df["end_date"] = pd.to_datetime(recurring_df["end_date"])

    # --- Load categories for display purposes (user-specific) ---
    categories_df = pd.DataFrame(
        conn.table("categories")
            .select("id", "category")
            .eq("user_id", st.session_state.user_id)
            .execute().data
    )

    # --- Helper: generate future dates ---
    def generate_dates(row):
        dates = []
        current = max(row["start_date"].date(), datetime.today().date())
        end = row["end_date"].date() if pd.notna(row["end_date"]) else current
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
                current = current.replace(year=current.year + 1)
            else:
                break
        return dates

    # --- Generate and insert future entries (user-specific) ---
    new_entries_count = 0
    for _, row in recurring_df.iterrows():
        future_dates = generate_dates(row)
        table = "incomes" if row["type"] == "Income" else "expenses"

        for date in future_dates:
            conn.table(table).insert({
                "date": date,
                "category_id": int(row["category_id"]),
                "amount": float(row["amount"]),
                "title": row["title"],
                "comment": "Recurring",
                "user_id": st.session_state.user_id
            }).execute()
            new_entries_count += 1

    st.success(f"{new_entries_count} recurring entries generated!")

    # --- Display active recurring transactions ---
    if not categories_df.empty:
        recurring_display_df = recurring_df.merge(
            categories_df.rename(columns={"category": "Category"}),
            left_on="category_id", right_on="id", how="left"
        )
    else:
        recurring_display_df = recurring_df.copy()
        recurring_display_df["Category"] = None

    st.subheader("Active Recurring Transactions")
    st.dataframe(recurring_display_df[[
        "title", "Category", "amount", "type", "start_date", "frequency", "end_date"
    ]])
