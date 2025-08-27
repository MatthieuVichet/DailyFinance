import plotly.graph_objects as go
import pandas as pd
import numpy as np


def category_pie(df):
    """Donut chart of total amounts per category"""
    data = df.groupby("Category")["Amount"].sum().reset_index()

    fig = go.Figure(
        go.Pie(
            labels=data["Category"],
            values=data["Amount"],
            hole=0.3
        )
    )
    fig.update_layout(title="Percentage of Amount per Category")
    return fig


def category_bar(df):
    """Bar chart of amounts per category"""
    data = df.groupby("Category")["Amount"].sum().reset_index()

    fig = go.Figure(
        go.Bar(
            x=data["Category"],
            y=data["Amount"],
            text=data["Amount"],
            textposition="auto",
            marker_color='indianred'
        )
    )
    fig.update_layout(
        title="Total Amount per Category",
        xaxis_title="Category",
        yaxis_title="Amount"
    )
    return fig


def category_line(df):
    """Line chart per category with total overlay"""
    fig = go.Figure()
    df["Date"] = pd.to_datetime(df["Date"])

    for cat, group in df.groupby("Category"):
        group = group.sort_values("Date")
        fig.add_trace(go.Scatter(
            x=group["Date"],
            y=group["Amount"],
            mode="lines+markers",
            name=cat
        ))

    total_df = df.groupby("Date")["Amount"].sum().reset_index()
    fig.add_trace(go.Scatter(
        x=total_df["Date"],
        y=total_df["Amount"],
        mode="lines+markers",
        name="Total",
        line=dict(color="black", width=4, dash="dash")
    ))

    fig.update_layout(
        title="Historical Amount per Category (with Total)",
        xaxis_title="Date",
        yaxis_title="Amount"
    )
    return fig


def budget_bar_chart(df):
    """Compare Actual vs Budget per category"""
    fig = go.Figure()

    for _, row in df.iterrows():
        color = "green" if row["Amount"] <= row["Budget"] else "red"
        fig.add_trace(go.Bar(
            x=[row["Category"]],
            y=[row["Amount"]],
            marker_color=color,
            text=f"${row['Amount']:,.2f} / ${row['Budget']:,.2f}",
            textposition="auto"
        ))

    fig.update_layout(
        title="Actual vs Budget",
        xaxis_title="Category",
        yaxis_title="Amount",
        showlegend=False
    )
    return fig


def category_line_with_trend(df, window=3):
    """Line chart with moving average and anomaly detection"""
    fig = go.Figure()
    df["Date"] = pd.to_datetime(df["Date"])

    for cat, group in df.groupby("Category"):
        group = group.sort_values("Date")

        group["SMA"] = group["Amount"].rolling(window=window, min_periods=1).mean()
        z_scores = (group["Amount"] - group["Amount"].mean()) / group["Amount"].std()
        group["Anomaly"] = z_scores.abs() > 2

        fig.add_trace(go.Scatter(
            x=group["Date"], y=group["Amount"],
            mode="lines+markers", name=cat
        ))

        fig.add_trace(go.Scatter(
            x=group["Date"], y=group["SMA"],
            mode="lines",
            name=f"{cat} SMA",
            line=dict(dash="dash", width=2)
        ))

        anomalies = group[group["Anomaly"]]
        if not anomalies.empty:
            fig.add_trace(go.Scatter(
                x=anomalies["Date"], y=anomalies["Amount"],
                mode="markers",
                name=f"{cat} Anomaly",
                marker=dict(color="red", size=10, symbol="x")
            ))

    total_df = df.groupby("Date")["Amount"].sum().reset_index()
    fig.add_trace(go.Scatter(
        x=total_df["Date"], y=total_df["Amount"],
        mode="lines+markers", name="Total",
        line=dict(color="black", width=4, dash="dot")
    ))

    fig.update_layout(
        title="Historical Amount per Category with Trend & Anomalies",
        xaxis_title="Date",
        yaxis_title="Amount"
    )
    return fig


def forecast_category(df, periods=30):
    """
    Lightweight 'forecast' using linear extrapolation instead of Prophet.
    For each category:
      - Plot historical data
      - Extend line using a simple trend
    """
    fig = go.Figure()
    df["Date"] = pd.to_datetime(df["Date"])

    for cat, group in df.groupby("Category"):
        group = group.sort_values("Date")

        if len(group) < 2:
            fig.add_trace(go.Scatter(
                x=group["Date"], y=group["Amount"],
                mode="lines+markers", name=f"{cat} (insufficient data)",
                line=dict(color="gray", dash="dot")
            ))
            continue

        # Actual
        fig.add_trace(go.Scatter(
            x=group["Date"], y=group["Amount"],
            mode="lines+markers", name=f"{cat} Actual"
        ))

        # Simple forecast: linear regression (date as numeric)
        x = (group["Date"] - group["Date"].min()).dt.days.values.reshape(-1, 1)
        y = group["Amount"].values
        if len(np.unique(y)) > 1:  # avoid constant series
            coef = np.polyfit(x.flatten(), y, 1)
            slope, intercept = coef

            future_days = np.arange(x.max() + 1, x.max() + periods + 1)
            future_dates = pd.date_range(start=group["Date"].max() + pd.Timedelta(days=1), periods=periods)
            forecast_values = intercept + slope * future_days

            fig.add_trace(go.Scatter(
                x=future_dates, y=forecast_values,
                mode="lines", name=f"{cat} Forecast",
                line=dict(dash="dot")
            ))

    fig.update_layout(
        title=f"Actual vs Linear Forecast per Category ({periods} days ahead)",
        xaxis_title="Date",
        yaxis_title="Amount"
    )
    return fig
