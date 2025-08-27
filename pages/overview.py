import streamlit as st
import pandas as pd
from datetime import datetime

st.title("Overview & Budget Alerts")

# --- File paths ---
income_file = r"src/data/income.xlsx"
expense_file = r"src/data/expenses.xlsx"
budget_file = r"src/data/budgets.xlsx"

# --- Load transactions ---
income_df = pd.read_excel(income_file)
income_df["Date"] = pd.to_datetime(income_df["Date"])
expense_df = pd.read_excel(expense_file)
expense_df["Date"] = pd.to_datetime(expense_df["Date"])

# --- Load budgets ---
try:
    budgets_df = pd.read_excel(budget_file)
except FileNotFoundError:
    budgets_df = pd.DataFrame(columns=["Category","Budget","Type","Month","Year"])

# --- Filter by current month/year ---
today = datetime.today()
current_month = today.month
current_year = today.year

expense_df_month = expense_df[(expense_df["Date"].dt.month==current_month) &
                              (expense_df["Date"].dt.year==current_year)]

budgets_df_month = budgets_df[(budgets_df["Month"]==current_month) & 
                              (budgets_df["Year"]==current_year) & 
                              (budgets_df["Type"]=="Expense")]

# --- Merge actual expenses with budgets ---
actual_per_category = expense_df_month.groupby("Category")["Amount"].sum().reset_index()
merged = pd.merge(budgets_df_month, actual_per_category, on="Category", how="left").fillna(0)

# --- Category-level alerts ---
st.subheader("Category Budget Alerts")
for _, row in merged.iterrows():
    if row["Amount"] > row["Budget"]:
        st.warning(f"⚠️ You exceeded your budget for **{row['Category']}**! "
                   f"Spent: ${row['Amount']:.2f} / Budget: ${row['Budget']:.2f}")
    else:
        st.success(f"✅ Within budget for **{row['Category']}**. "
                   f"Spent: ${row['Amount']:.2f} / Budget: ${row['Budget']:.2f}")

# --- Sidebar summary ---
with st.sidebar:
    st.header("Budget Summary")
    total_spent = expense_df_month["Amount"].sum()
    total_budget = budgets_df_month["Budget"].sum()
    
    st.metric("Total Spent", f"${total_spent:,.2f}")
    st.metric("Total Budget", f"${total_budget:,.2f}")
    
    if total_spent > total_budget:
        st.warning(f"⚠️ Total spending exceeded monthly budget! "
                   f"Spent: ${total_spent:,.2f} / Budget: ${total_budget:,.2f}")
    else:
        st.success(f"✅ You are within budget. Spent: ${total_spent:,.2f} / Budget: ${total_budget:,.2f}")

# --- Optional: show full merged table ---
st.subheader("Detailed Expenses vs Budget")
st.dataframe(merged[["Category","Budget","Amount"]])
