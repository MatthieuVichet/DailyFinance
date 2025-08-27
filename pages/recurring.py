import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os

st.title("Recurring Transactions")

# --- Paths ---
recurring_file = r"src/data/recurring.xlsx"
income_file = r"src/data/income.xlsx"
expense_file = r"src/data/expenses.xlsx"

# --- Load recurring transactions ---
try:
    recurring_df = pd.read_excel(recurring_file)
except FileNotFoundError:
    st.error("recurring.xlsx not found!")
    st.stop()

recurring_df["StartDate"] = pd.to_datetime(recurring_df["StartDate"])
recurring_df["EndDate"] = pd.to_datetime(recurring_df["EndDate"])

# --- Helper function to generate future dates ---
def generate_dates(row):
    dates = []
    current = max(row["StartDate"], datetime.today())
    end = row["EndDate"]
    freq = row["Frequency"].lower()
    
    while current <= end:
        dates.append(current)
        if freq == "daily":
            current += timedelta(days=1)
        elif freq == "weekly":
            current += timedelta(weeks=1)
        elif freq == "monthly":
            month = current.month + 1 if current.month < 12 else 1
            year = current.year + (current.month // 12)
            day = min(current.day, 28)  # Avoid issues with Feb
            current = current.replace(year=year, month=month, day=day)
        elif freq == "yearly":
            current = current.replace(year=current.year+1)
        else:
            break
    return dates

# --- Generate future entries ---
new_entries = []
for idx, row in recurring_df.iterrows():
    if row["Active"]:
        future_dates = generate_dates(row)
        for date in future_dates:
            new_entries.append({
                "Date": date,
                "Category": row["Category"],
                "Amount": row["Amount"],
                "Title": row["Title"],
                "Comment": "Recurring"
            })

# --- Save to income or expense ---
if new_entries:
    new_df = pd.DataFrame(new_entries)
    income_entries = new_df[new_df["Amount"] > 0]  # Assume positive amounts are income
    expense_entries = new_df[new_df["Amount"] < 0]  # Negative amounts are expenses

    # Load existing files
    if os.path.exists(income_file):
        df_income = pd.read_excel(income_file)
        income_entries = pd.concat([df_income, income_entries], ignore_index=True)
    if os.path.exists(expense_file):
        df_expense = pd.read_excel(expense_file)
        expense_entries = pd.concat([df_expense, expense_entries], ignore_index=True)

    # Save
    income_entries.to_excel(income_file, index=False)
    expense_entries.to_excel(expense_file, index=False)

    st.success(f"{len(new_entries)} recurring entries generated!")

# --- Display recurring transactions ---
st.subheader("Active Recurring Transactions")
st.dataframe(recurring_df[recurring_df["Active"] == True])
