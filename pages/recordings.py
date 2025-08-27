import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta

st.title("New Expense/Income Recording & Category Management")

# --- Paths ---
income_file = r"C:\Users\matth\OneDrive - Efrei\PersoApp\DailyFinance\src\data\income.xlsx"
expense_file = r"C:\Users\matth\OneDrive - Efrei\PersoApp\DailyFinance\src\data\expenses.xlsx"
categories_file = r"C:\Users\matth\OneDrive - Efrei\PersoApp\DailyFinance\src\data\categories.xlsx"
recurring_file = r"C:\Users\matth\OneDrive - Efrei\PersoApp\DailyFinance\src\data\recurring.xlsx"

# --- Load categories ---
if os.path.exists(categories_file):
    cat_df = pd.read_excel(categories_file)
else:
    cat_df = pd.DataFrame(columns=["Category","Type","Color","Icon"])

# --- Category Management ---
st.subheader("Category Management")

with st.expander("Add/Edit/Delete Categories"):
    # Add new category
    with st.form("add_category_form"):
        new_cat_name = st.text_input("Category Name")
        new_cat_type = st.selectbox("Type", ["Income","Expense"])
        new_cat_color = st.color_picker("Color")
        new_cat_icon = st.text_input("Icon (emoji or text)")
        submitted = st.form_submit_button("Add Category")
        if submitted and new_cat_name:
            if new_cat_name in cat_df["Category"].values:
                st.warning("Category already exists!")
            else:
                cat_df = pd.concat([cat_df, pd.DataFrame([{
                    "Category": new_cat_name,
                    "Type": new_cat_type,
                    "Color": new_cat_color,
                    "Icon": new_cat_icon
                }])], ignore_index=True)
                cat_df.to_excel(categories_file, index=False)
                st.success(f"Category '{new_cat_name}' added!")

    # Edit existing category
    edit_cat = st.selectbox("Edit Category", options=[""] + cat_df["Category"].tolist())
    if edit_cat:
        row = cat_df[cat_df["Category"] == edit_cat].iloc[0]
        new_name = st.text_input("Category Name", value=row["Category"])
        new_type = st.selectbox("Type", ["Income","Expense"], index=0 if row["Type"]=="Income" else 1)
        new_color = st.color_picker("Color", value=row["Color"] if pd.notna(row["Color"]) else "#FFFFFF")
        new_icon = st.text_input("Icon", value=row["Icon"] if pd.notna(row["Icon"]) else "")
        if st.button("Save Changes"):
            cat_df.loc[cat_df["Category"]==edit_cat, ["Category","Type","Color","Icon"]] = [new_name,new_type,new_color,new_icon]
            cat_df.to_excel(categories_file, index=False)
            st.success(f"Category '{edit_cat}' updated!")

    # Delete category
    del_cat = st.selectbox("Delete Category", options=[""] + cat_df["Category"].tolist())
    if del_cat and st.button("Delete Category"):
        cat_df = cat_df[cat_df["Category"] != del_cat]
        cat_df.to_excel(categories_file, index=False)
        st.success(f"Category '{del_cat}' deleted!")

# --- Recording Transactions ---
st.subheader("Record Transaction")

exp_or_inc = st.selectbox("Is it an expense or an income?", options=["Expense","Income"])
date = st.date_input("Date")
# Filter categories by type
categories_for_type = cat_df[cat_df["Type"]==exp_or_inc]["Category"].tolist()
category = st.selectbox("Category", options=categories_for_type)
amount = st.number_input("Amount")
title = st.text_input("Title")
comment = st.text_area("Commentary")
is_recurring = st.checkbox("Recurring Transaction?")

# Recurring options
if is_recurring:
    frequency = st.selectbox("Frequency", options=["Daily","Weekly","Monthly","Yearly"])
    end_date = st.date_input("End Date", min_value=date)

# --- Helper to generate future dates ---
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
    file = income_file if exp_or_inc=="Income" else expense_file
    if os.path.exists(file):
        df = pd.read_excel(file)
    else:
        df = pd.DataFrame(columns=["Date","Category","Amount","Title","Comment"])

    new_entry = {
        "Date": date,
        "Category": category,
        "Amount": amount,
        "Title": title,
        "Comment": comment if not is_recurring else "Recurring"
    }
    df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)

    # Recurring future entries
    if is_recurring:
        future_dates = generate_dates(date,end_date,frequency)
        future_entries = []
        for d in future_dates[1:]:
            future_entries.append({
                "Date": d,
                "Category": category,
                "Amount": amount,
                "Title": title,
                "Comment": "Recurring"
            })
        if future_entries:
            df = pd.concat([df, pd.DataFrame(future_entries)], ignore_index=True)

        # Save to recurring.xlsx
        if os.path.exists(recurring_file):
            recurring_df = pd.read_excel(recurring_file)
        else:
            recurring_df = pd.DataFrame(columns=["Title","Category","Amount","Type","StartDate","Frequency","EndDate","Active"])
        recurring_df = pd.concat([recurring_df, pd.DataFrame([{
            "Title": title,
            "Category": category,
            "Amount": amount,
            "Type": exp_or_inc,
            "StartDate": date,
            "Frequency": frequency,
            "EndDate": end_date,
            "Active": True
        }])], ignore_index=True)
        recurring_df.to_excel(recurring_file,index=False)

    df.to_excel(file,index=False)
    st.success(f"{exp_or_inc} saved successfully!")
