def run_dashboard():
    import streamlit as st
    import pandas as pd
    from datetime import datetime, timedelta
    import plotly.graph_objects as go
    from st_supabase_connection import SupabaseConnection

    from src.features.charts import (
        category_pie, category_bar, category_line_with_trend,
        forecast_category, budget_bar_chart
    )

    st.title("📊 Dashboard & Budget Overview")

    # --- Connect to Supabase ---
    conn = st.connection("supabase", type=SupabaseConnection)

    # --- Sidebar Filters ---
    st.sidebar.header("Filters")
    view_type = st.sidebar.radio("Choose view", ["Single Type", "Income vs Expense"])
    show_recurring = st.sidebar.checkbox("Show recurring transactions only")
    show_non_recurring = st.sidebar.checkbox("Show non-recurring transactions only")
    forecast_days = st.sidebar.slider("Days to Forecast", 7, 90, 30)
    period_options = ["Week-to-Date", "Month-to-Date", "Year-to-Date",
                      "Last 7 Days", "Last 30 Days", "Last 365 Days"]
    today = pd.Timestamp.today().date()
    month = st.sidebar.selectbox("Select Month", list(range(1, 13)), index=today.month - 1)
    year = st.sidebar.selectbox("Select Year", list(range(today.year - 5, today.year + 2)), index=5)

    # --- Helper: filter by period ---
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
        else:
            start_date = datetime.min
        return df[df["Date"] >= pd.to_datetime(start_date)]

    # --- Load table helper ---
    def load_table(table):
        rows = conn.table(table).select("*").execute()
        df = pd.DataFrame(rows.data)

        if df.empty:
            return df

        # Rename for dashboard consistency, but KEEP category_id for merges
        rename_map = {}
        if table in ["incomes", "expenses"]:
            rename_map = {
                "date": "Date",
                "amount": "Amount",
                "comment": "Comment",
                "title": "Title"
                # DON'T rename category_id here
            }
        elif table == "budgets":
            rename_map = {
                "budget": "Budget",
                "amount": "Amount",
                "month": "Month",
                "year": "Year",
                "type": "Type"
                # DON'T rename category_id here
            }
        elif table == "categories":
            rename_map = {
                "category": "Category",
                "type": "Type",
                "color": "Color",
                "icon": "Icon"
                # Keep id as-is for merge
            }
        elif table == "recurrings":
            rename_map = {
                "title": "Title",
                "amount": "Amount",
                "type": "Type",
                "start_date": "Date",
                "frequency": "Frequency",
                "end_date": "EndDate",
                "active": "Active"
                # Keep category_id
            }

        df = df.rename(columns=rename_map)

        # Ensure Date columns are datetime
        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"])

        return df



    # --- Load data from Supabase ---
    incomes_df = load_table("incomes")
    expenses_df = load_table("expenses")
    budgets_df = load_table("budgets")
    categories_df = load_table("categories")

    # Join categories info
    if not categories_df.empty:
        for name, df in zip(["incomes_df", "expenses_df", "budgets_df"],
                            [incomes_df, expenses_df, budgets_df]):
            if not df.empty:
                df_merged = df.merge(
                    categories_df,
                    left_on="category_id",  # keep category_id for merge
                    right_on="id",
                    how="left",
                    suffixes=("", "_cat")
                )
                # Overwrite df variable in global scope
                if name == "incomes_df":
                    incomes_df = df_merged
                elif name == "expenses_df":
                    expenses_df = df_merged
                elif name == "budgets_df":
                    budgets_df = df_merged

    # --- Views ---
    if view_type == "Single Type":
        exp_or_inc = st.selectbox("Choose data type", ["Income", "Expense"])
        df = incomes_df if exp_or_inc == "Income" else expenses_df
        if df.empty:
            st.info("No data found.")
            return

        period = st.selectbox("Select period", period_options)
        filtered_df = filter_period(df, period)

        if show_recurring:
            filtered_df = filtered_df[filtered_df["Comment"].str.lower() == "recurring"]
        elif show_non_recurring:
            filtered_df = filtered_df[filtered_df["Comment"].str.lower() != "recurring"]

        if filtered_df.empty:
            st.info("No records for the selected filters.")
        else:
            col1, col2 = st.columns(2)
            col1.metric("Number of Records", len(filtered_df))
            col2.metric("Total Amount", f"${filtered_df['Amount'].sum():,.2f}")

            with st.expander("Category Charts"):
                st.plotly_chart(category_pie(filtered_df), use_container_width=True)
                st.plotly_chart(category_bar(filtered_df), use_container_width=True)
                st.plotly_chart(category_line_with_trend(filtered_df), use_container_width=True)

            with st.expander("Predictive Analytics / Linear Forecast"):
                # --- Remove rows with missing Date or Amount ---
                clean_df = filtered_df.dropna(subset=["Date", "Amount"])
                
                # --- Ensure there are enough points to fit a linear model ---
                if len(clean_df) < 2:
                    st.warning("Not enough data for forecasting.")
                else:
                    try:
                        st.plotly_chart(forecast_category(clean_df, periods=forecast_days),
                                        use_container_width=True)
                    except np.linalg.LinAlgError:
                        st.warning("Forecasting failed: data is insufficient or degenerate.")


    else:  # --- Income vs Expense ---
        if incomes_df.empty and expenses_df.empty:
            st.info("No income or expense data found.")
            return

        incomes_df["Type"] = "Income"
        expenses_df["Type"] = "Expense"
        df = pd.concat([incomes_df, expenses_df], ignore_index=True)

        period = st.selectbox("Select period", period_options)
        filtered_df = filter_period(df, period)

        if show_recurring:
            filtered_df = filtered_df[filtered_df["Comment"].str.lower() == "recurring"]
        elif show_non_recurring:
            filtered_df = filtered_df[filtered_df["Comment"].str.lower() != "recurring"]

        if filtered_df.empty:
            st.info("No records for the selected filters.")
        else:
            total_income = filtered_df.loc[filtered_df["Type"] == "Income", "Amount"].sum()
            total_expense = filtered_df.loc[filtered_df["Type"] == "Expense", "Amount"].sum()
            net = total_income - total_expense
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Income", f"${total_income:,.2f}")
            col2.metric("Total Expense", f"${total_expense:,.2f}")
            col3.metric("Net", f"${net:,.2f}")

            with st.expander("Category Comparison"):
                cat_data = filtered_df.groupby(["Category", "Type"])["Amount"].sum().reset_index()
                fig_cat = go.Figure()
                for t in ["Income", "Expense"]:
                    temp = cat_data[cat_data["Type"] == t]
                    fig_cat.add_trace(go.Bar(x=temp["Category"], y=temp["Amount"], name=t))
                fig_cat.update_layout(title="Income vs Expense per Category", barmode="group",
                                      xaxis_title="Category", yaxis_title="Amount")
                st.plotly_chart(fig_cat, use_container_width=True)

            with st.expander("Historical Income vs Expense"):
                hist_data = filtered_df.groupby(["Date", "Type"])["Amount"].sum().reset_index()
                fig_hist = go.Figure()
                for t in ["Income", "Expense"]:
                    temp = hist_data[hist_data["Type"] == t]
                    fig_hist.add_trace(go.Scatter(x=temp["Date"], y=temp["Amount"],
                                                  mode="lines+markers", name=t))
                net_data = hist_data.pivot(index="Date", columns="Type", values="Amount").fillna(0)
                net_data["Net"] = net_data.get("Income", 0) - net_data.get("Expense", 0)
                fig_hist.add_trace(go.Scatter(x=net_data.index, y=net_data["Net"],
                                              mode="lines+markers", name="Net",
                                              line=dict(color="black", dash="dash")))
                fig_hist.update_layout(title="Historical Income vs Expense",
                                       xaxis_title="Date", yaxis_title="Amount")
                st.plotly_chart(fig_hist, use_container_width=True)

            with st.expander("Income vs Expense Ratio"):
                total_income = max(total_income, 1)
                fig_ratio = go.Figure(go.Indicator(
                    mode="gauge+number+delta",
                    value=total_expense,
                    delta={'reference': total_income, 'relative': True, 'position': 'top'},
                    gauge={
                        'axis': {'range': [0, total_income]},
                        'bar': {'color': "red"},
                        'steps': [
                            {'range': [0, total_income * 0.5], 'color': "lightgreen"},
                            {'range': [total_income * 0.5, total_income], 'color': "orange"}
                        ],
                        'threshold': {'line': {'color': "black", 'width': 4},
                                      'thickness': 0.75, 'value': total_expense}
                    }
                ))
                st.plotly_chart(fig_ratio, use_container_width=True)

    # --- Budget vs Actual ---
    if not budgets_df.empty:
        st.subheader("Budget vs Actual per Category")
        actual_income = filtered_df[filtered_df["Type"] == "Income"] \
            .groupby(["Category", "Type"])["Amount"].sum().reset_index()
        actual_expense = filtered_df[filtered_df["Type"] == "Expense"] \
            .groupby(["Category", "Type"])["Amount"].sum().reset_index()

        actual_df = pd.concat([actual_income, actual_expense], ignore_index=True)
        merged_budget = pd.merge(budgets_df, actual_df, on=["Category", "Type"], how="left").fillna(0)

        merged_budget.rename(columns={"Amount_y": "Amount", "Amount_x": "Budget"}, inplace=True)

        st.dataframe(merged_budget[["Category", "Type", "Amount", "Budget", "Color", "Icon"]])

        st.subheader("Budget Alerts")
        for _, row in merged_budget.iterrows():
            if row["Amount"] > row["Budget"]:
                st.warning(f"⚠️ Exceeded budget for **{row['Category']}**: "
                           f"Spent ${row['Amount']:.2f} / Budget ${row['Budget']:.2f}")
            else:
                st.success(f"✅ Within budget for **{row['Category']}**: "
                           f"Spent ${row['Amount']:.2f} / Budget ${row['Budget']:.2f}")

        st.plotly_chart(budget_bar_chart(merged_budget), use_container_width=True)
