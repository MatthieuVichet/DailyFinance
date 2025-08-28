def run_dashboard():
    import streamlit as st
    import pandas as pd
    from datetime import datetime, timedelta
    from sqlalchemy import create_engine
    import plotly.graph_objects as go
    from src.features.charts import (
        category_pie, category_bar, category_line_with_trend,
        forecast_category, budget_bar_chart
    )

    st.title("Dashboard & Budget Overview")

    # --- Connect to DB ---
    DB_URL = st.secrets["postgres"]["url"]
    engine = create_engine(DB_URL)

    # --- Sidebar Filters ---
    st.sidebar.header("Filters")
    view_type = st.sidebar.radio("Choose view", options=["Single Type", "Income vs Expense"])
    show_recurring = st.sidebar.checkbox("Show recurring transactions only")
    show_non_recurring = st.sidebar.checkbox("Show non-recurring transactions only")
    forecast_days = st.sidebar.slider("Days to Forecast", min_value=7, max_value=90, value=30)
    period_options = ["Week-to-Date", "Month-to-Date", "Year-to-Date",
                      "Last 7 Days", "Last 30 Days", "Last 365 Days"]
    today = datetime.today()

    # --- Select month/year for budgets ---
    month = st.sidebar.selectbox("Select Month", list(range(1,13)), index=today.month-1)
    year = st.sidebar.selectbox("Select Year", list(range(today.year-5, today.year+2)), index=5)

    # --- Helper: filter period ---
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
        return df[df["date"] >= start_date]

    # --- Load data from DB ---
    incomes_df = pd.read_sql("SELECT * FROM incomes", engine)
    expenses_df = pd.read_sql("SELECT * FROM expenses", engine)
    budgets_df = pd.read_sql("SELECT * FROM budgets", engine)
    categories_df = pd.read_sql("SELECT category, type, color, icon FROM categories", engine)

    # --- Merge categories for colors/icons ---
    for df in [incomes_df, expenses_df]:
        df["date"] = pd.to_datetime(df["date"])
        df["month"] = df["date"].dt.month
        df["year"] = df["date"].dt.year
        df = df.merge(categories_df, on=["category", "type"], how="left")
        df["color"].fillna("#808080", inplace=True)
        df["icon"].fillna("❓", inplace=True)

    budgets_df = budgets_df[(budgets_df["month"] == month) & (budgets_df["year"] == year)]
    budgets_df = budgets_df.merge(categories_df, on=["category", "type"], how="left")
    budgets_df["color"].fillna("#808080", inplace=True)
    budgets_df["icon"].fillna("❓", inplace=True)

    # --- Single Type View ---
    if view_type == "Single Type":
        exp_or_inc = st.selectbox("Choose data type", options=["Income","Expense"])
        df = incomes_df if exp_or_inc=="Income" else expenses_df
        period = st.selectbox("Select period", period_options)
        filtered_df = filter_period(df, period)

        if show_recurring:
            filtered_df = filtered_df[filtered_df["comment"].str.lower() == "recurring"]
        elif show_non_recurring:
            filtered_df = filtered_df[filtered_df["comment"].str.lower() != "recurring"]

        # --- Metrics ---
        col1, col2 = st.columns(2)
        col1.metric("Number of Records", len(filtered_df))
        col2.metric("Total Amount", f"${filtered_df['amount'].sum():,.2f}")

        # --- Charts ---
        with st.expander("Category Charts"):
            st.plotly_chart(category_pie(filtered_df), use_container_width=True)
            st.plotly_chart(category_bar(filtered_df), use_container_width=True)
            st.plotly_chart(category_line_with_trend(filtered_df), use_container_width=True)

        # --- Predictive Analytics ---
        with st.expander("Predictive Analytics / Linear Forecast"):
            fig_forecast = forecast_category(filtered_df, periods=forecast_days)
            st.plotly_chart(fig_forecast, use_container_width=True)

    # --- Income vs Expense Comparison ---
    else:
        incomes_df["type"] = "Income"
        expenses_df["type"] = "Expense"
        df = pd.concat([incomes_df, expenses_df], ignore_index=True)
        period = st.selectbox("Select period", period_options)
        filtered_df = filter_period(df, period)

        if show_recurring:
            filtered_df = filtered_df[filtered_df["comment"].str.lower() == "recurring"]
        elif show_non_recurring:
            filtered_df = filtered_df[filtered_df["comment"].str.lower() != "recurring"]

        # --- Metrics ---
        total_income = filtered_df.loc[filtered_df["type"]=="Income","amount"].sum()
        total_expense = filtered_df.loc[filtered_df["type"]=="Expense","amount"].sum()
        net = total_income - total_expense
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Income", f"${total_income:,.2f}")
        col2.metric("Total Expense", f"${total_expense:,.2f}")
        col3.metric("Net", f"${net:,.2f}")

        # --- Category Comparison ---
        with st.expander("Category Comparison"):
            cat_data = filtered_df.groupby(["category","type"])["amount"].sum().reset_index()
            fig_cat = go.Figure()
            for t in ["Income","Expense"]:
                temp = cat_data[cat_data["type"]==t]
                fig_cat.add_trace(go.Bar(x=temp["category"], y=temp["amount"], name=t))
            fig_cat.update_layout(title="Income vs Expense per Category", barmode="group",
                                  xaxis_title="Category", yaxis_title="Amount")
            st.plotly_chart(fig_cat, use_container_width=True)

        # --- Historical Line Chart ---
        with st.expander("Historical Income vs Expense"):
            hist_data = filtered_df.groupby(["date","type"])["amount"].sum().reset_index()
            fig_hist = go.Figure()
            for t in ["Income","Expense"]:
                temp = hist_data[hist_data["type"]==t]
                fig_hist.add_trace(go.Scatter(x=temp["date"], y=temp["amount"], mode="lines+markers", name=t))
            net_data = hist_data.pivot(index="date", columns="type", values="amount").fillna(0)
            net_data["Net"] = net_data.get("Income",0)-net_data.get("Expense",0)
            fig_hist.add_trace(go.Scatter(x=net_data.index, y=net_data["Net"], mode="lines+markers",
                                          name="Net", line=dict(color="black", dash="dash")))
            fig_hist.update_layout(title="Historical Income vs Expense", xaxis_title="Date", yaxis_title="Amount")
            st.plotly_chart(fig_hist, use_container_width=True)

        # --- Income vs Expense Ratio ---
        if total_income == 0: total_income = 1
        with st.expander("Income vs Expense Ratio"):
            fig_ratio = go.Figure(go.Indicator(
                mode="gauge+number+delta",
                value=total_expense,
                domain={'x':[0,1],'y':[0,1]},
                title={'text':"Expenses vs Income"},
                delta={'reference':total_income,'relative':True,'position':'top'},
                gauge={
                    'axis':{'range':[0,total_income]},
                    'bar':{'color':"red"},
                    'steps':[{'range':[0,total_income*0.5],'color':"lightgreen"},
                             {'range':[total_income*0.5,total_income],'color':"orange"}],
                    'threshold':{'line':{'color':"black",'width':4},'thickness':0.75,'value':total_expense}
                }
            ))
            st.plotly_chart(fig_ratio, use_container_width=True)

    # --- Budget vs Actual Table ---
    st.subheader("Budget vs Actual per Category")
    actual_income = filtered_df[filtered_df["type"]=="Income"].groupby("category")["amount"].sum().reset_index()
    actual_expense = filtered_df[filtered_df["type"]=="Expense"].groupby("category")["amount"].sum().reset_index()
    actual_df = pd.concat([actual_income, actual_expense], ignore_index=True)
    merged_budget = pd.merge(budgets_df, actual_df, on=["category","type"], how="left").fillna(0)
    st.dataframe(merged_budget[["category","type","budget","amount","color","icon"]])

    # --- Alerts ---
    st.subheader("Budget Alerts")
    for _, row in merged_budget.iterrows():
        if row["amount"] > row["budget"]:
            st.warning(f"⚠️ You exceeded your budget for **{row['category']}**! "
                       f"Spent: ${row['amount']:.2f} / Budget: ${row['budget']:.2f}")
        else:
            st.success(f"✅ Within budget for **{row['category']}**. "
                       f"Spent: ${row['amount']:.2f} / Budget: ${row['budget']:.2f}")

    # --- Plot Budget Chart ---
    fig_budget = budget_bar_chart(merged_budget)
    st.plotly_chart(fig_budget, use_container_width=True)
