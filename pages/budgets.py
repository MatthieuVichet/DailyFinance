import streamlit as st
import pandas as pd
from datetime import datetime
from src.features.charts import budget_bar_chart  # import the chart function

st.title("Savings & Budget Tracking")

# --- File paths ---
budget_file = r"src\data\budget.xlsx"
income_file = r"src\data\income.xlsx"
expense_file = r"src\data\expenses.xlsx"

# --- Select month & year ---
today = datetime.today()
month = st.selectbox("Select Month", list(range(1,13)), index=today.month-1)
year = st.selectbox("Select Year", list(range(today.year-5, today.year+2)), index=5)

# --- Load budgets ---
try:
    budgets_df = pd.read_excel(budget_file)
except FileNotFoundError:
    st.warning("Budget file not found!")
    budgets_df = pd.DataFrame(columns=["Category","Budget","Type","Month","Year"])

# Filter by selected month/year, handle missing columns
for col in ["Month","Year"]:
    if col not in budgets_df.columns:
        budgets_df[col] = today.month if col=="Month" else today.year

budgets_df = budgets_df[(budgets_df["Month"]==month) & (budgets_df["Year"]==year)]

# --- Load transactions ---
def load_transactions(file):
    if not pd.io.common.file_exists(file):
        return pd.DataFrame(columns=["Date","Category","Amount"])
    df = pd.read_excel(file)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Month"] = df["Date"].dt.month
    df["Year"] = df["Date"].dt.year
    return df

income_df = load_transactions(income_file)
expense_df = load_transactions(expense_file)

# Filter by month/year
income_df = income_df[(income_df["Month"]==month) & (income_df["Year"]==year)]
expense_df = expense_df[(expense_df["Month"]==month) & (expense_df["Year"]==year)]

# --- Aggregate actuals ---
def calculate_actual(df, df_type):
    if df.empty or "Amount" not in df.columns:
        return pd.DataFrame(columns=["Category","Amount","Type"])
    actual = df.groupby("Category")["Amount"].sum().reset_index()
    actual["Type"] = df_type
    return actual

income_actual = calculate_actual(income_df, "Income")
expense_actual = calculate_actual(expense_df, "Expense")
actual_df = pd.concat([income_actual, expense_actual], ignore_index=True)

# Ensure 'Amount' exists
if "Amount" not in actual_df.columns:
    actual_df["Amount"] = 0

# Merge with budgets
merged_df = pd.merge(budgets_df, actual_df, on=["Category","Type"], how="left")
merged_df["Amount"] = merged_df.get("Amount", 0)  # default to 0 if missing
merged_df.fillna(0, inplace=True)

st.subheader("Budget vs Actual")
st.dataframe(merged_df[["Category","Type","Budget","Amount"]])

# --- Plot chart using charts.py ---
fig = budget_bar_chart(merged_df)
st.plotly_chart(fig, use_container_width=True)
