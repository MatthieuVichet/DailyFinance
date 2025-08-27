import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from src.features.charts import (
    category_pie, category_bar, category_line_with_trend,
    forecast_category, budget_bar_chart
)
import plotly.graph_objects as go

# --- Sidebar Filters ---
st.sidebar.header("Filters")
view_type = st.sidebar.radio("Choose view", options=["Single Type", "Income vs Expense"])
show_recurring = st.sidebar.checkbox("Show recurring transactions only")
show_non_recurring = st.sidebar.checkbox("Show non-recurring transactions only")
forecast_days = st.sidebar.slider("Days to Forecast", min_value=7, max_value=90, value=30)
period_options = ["Week-to-Date", "Month-to-Date", "Year-to-Date",
                  "Last 7 Days", "Last 30 Days", "Last 365 Days"]

# --- Load data ---
income_file = r"src\data\income.xlsx"
expense_file = r"src\data\expenses.xlsx"
today = datetime.today()

def filter_period(df, period):
    if period == "Week-to-Date":
        start_date = today - pd.to_timedelta(today.weekday(), unit="d")
    elif period == "Month-to-Date":
        start_date = today.replace(day=1)
    elif period == "Year-to-Date":
        start_date = today.replace(month=1, day=1)
    elif period == "Last 7 Days":
        start_date = today - timedelta(days=7)
    elif period == "Last 30 Days":
        start_date = today - timedelta(days=30)
    elif period == "Last 365 Days":
        start_date = today - timedelta(days=365)
    return df[df["Date"] >= start_date]

# --- Single Type View ---
if view_type == "Single Type":
    exp_or_inc = st.selectbox("Choose data type", options=["Income", "Expense"])
    file = income_file if exp_or_inc=="Income" else expense_file
    df = pd.read_excel(file)
    df["Date"] = pd.to_datetime(df["Date"])
    
    period = st.selectbox("Select period", period_options)
    filtered_df = filter_period(df, period)

    if show_recurring:
        filtered_df = filtered_df[filtered_df["Comment"] == "Recurring"]
    elif show_non_recurring:
        filtered_df = filtered_df[filtered_df["Comment"] != "Recurring"]

    # --- Metrics ---
    col1, col2 = st.columns(2)
    col1.metric("Number of Records", len(filtered_df))
    col2.metric("Total Amount", f"${filtered_df['Amount'].sum():,.2f}")

    # --- Collapsible Charts ---
    with st.expander("Category Charts"):
        st.plotly_chart(category_pie(filtered_df), use_container_width=True, key="pie_chart")
        st.plotly_chart(category_bar(filtered_df), use_container_width=True, key="bar_chart")
        st.plotly_chart(category_line_with_trend(filtered_df), use_container_width=True, key="trend_chart")

    # --- Predictive Analytics ---
    with st.expander("Predictive Analytics / Linear Forecast"):
        fig_forecast = forecast_category(filtered_df, periods=forecast_days)
        st.plotly_chart(fig_forecast, use_container_width=True, key="forecast_chart")

# --- Income vs Expense Comparison ---
else:
    # Load both datasets
    income_df = pd.read_excel(income_file)
    income_df["Type"] = "Income"
    expense_df = pd.read_excel(expense_file)
    expense_df["Type"] = "Expense"
    df = pd.concat([income_df, expense_df], ignore_index=True)
    df["Date"] = pd.to_datetime(df["Date"])
    
    period = st.selectbox("Select period", period_options)
    filtered_df = filter_period(df, period)

    if show_recurring:
        filtered_df = filtered_df[filtered_df["Comment"] == "Recurring"]
    elif show_non_recurring:
        filtered_df = filtered_df[filtered_df["Comment"] != "Recurring"]

    # --- Metrics ---
    total_income = filtered_df.loc[filtered_df["Type"]=="Income","Amount"].sum()
    total_expense = filtered_df.loc[filtered_df["Type"]=="Expense","Amount"].sum()
    net = total_income - total_expense
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Income", f"${total_income:,.2f}")
    col2.metric("Total Expense", f"${total_expense:,.2f}")
    col3.metric("Net", f"${net:,.2f}")

    # --- Category Bar Chart ---
    with st.expander("Category Comparison"):
        cat_data = filtered_df.groupby(["Category","Type"])["Amount"].sum().reset_index()
        fig_cat = go.Figure()
        for t in ["Income","Expense"]:
            temp = cat_data[cat_data["Type"]==t]
            fig_cat.add_trace(go.Bar(x=temp["Category"], y=temp["Amount"], name=t))
        fig_cat.update_layout(title="Income vs Expense per Category", barmode="group",
                              xaxis_title="Category", yaxis_title="Amount")
        st.plotly_chart(fig_cat, use_container_width=True, key="inc_exp_cat_chart")

    # --- Historical Line Chart ---
    with st.expander("Historical Income vs Expense"):
        hist_data = filtered_df.groupby(["Date","Type"])["Amount"].sum().reset_index()
        fig_hist = go.Figure()
        for t in ["Income","Expense"]:
            temp = hist_data[hist_data["Type"]==t]
            fig_hist.add_trace(go.Scatter(x=temp["Date"], y=temp["Amount"], mode="lines+markers", name=t))
        # Net line
        net_data = hist_data.pivot(index="Date", columns="Type", values="Amount").fillna(0)
        net_data["Net"] = net_data.get("Income",0) - net_data.get("Expense",0)
        fig_hist.add_trace(go.Scatter(x=net_data.index, y=net_data["Net"], mode="lines+markers",
                                      name="Net", line=dict(color="black", dash="dash")))
        fig_hist.update_layout(title="Historical Income vs Expense", xaxis_title="Date", yaxis_title="Amount")
        st.plotly_chart(fig_hist, use_container_width=True, key="inc_exp_hist_chart")

    # --- Income vs Expense Ratio ---
    if total_income == 0:
        total_income = 1
    with st.expander("Income vs Expense Ratio"):
        fig_ratio = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=total_expense,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': "Expenses vs Income"},
            delta={'reference': total_income, 'relative': True, 'position':'top'},
            gauge={
                'axis': {'range': [0, total_income]},
                'bar': {'color': "red"},
                'steps': [
                    {'range': [0, total_income*0.5], 'color': "lightgreen"},
                    {'range': [total_income*0.5, total_income], 'color': "orange"}
                ],
                'threshold': {
                    'line': {'color': "black", 'width': 4},
                    'thickness': 0.75,
                    'value': total_expense
                }
            }
        ))
        st.plotly_chart(fig_ratio, use_container_width=True, key="inc_exp_ratio")
