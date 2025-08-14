import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from conn1 import MySQLDatabase
import pandas as pd
import numpy as np

# =========================
# App + DB init
# =========================
st.set_page_config(page_title="Sales Dashboard + Forecast", layout="wide")
st.title("📊 Sales Dashboard")

db = MySQLDatabase()
db.connect()

# =========================
# Sidebar controls
# =========================
st.sidebar.header("Forecast Settings")
forecast_horizon = st.sidebar.slider("Forecast horizon (months)", 3, 12, 6)

# Month helpers
month_order = ['Jan', 'Feb', 'March', 'April', 'May', 'June',
               'July', 'August', 'September', 'October', 'November', 'December']
month_map = {m: i+1 for i, m in enumerate(month_order)}

# =========================
# Overall Trend (clean)
# =========================


# Pull overall monthly sales (expects columns: month, total_sales)
overall_sales_df = db.get_overall_sales_per_month()

# Ensure month ordering, numeric types
overall_sales_df['month'] = pd.Categorical(overall_sales_df['month'], categories=month_order, ordered=True)
overall_sales_df['month_num'] = overall_sales_df['month'].map(month_map)
overall_sales_df['total_sales'] = pd.to_numeric(overall_sales_df['total_sales'], errors='coerce')

overall_sales_df = overall_sales_df.dropna(subset=['month', 'month_num', 'total_sales']).sort_values('month_num')

fig_trend = px.line(
    overall_sales_df,
    x="month",
    y="total_sales",
    title="Overall Sales",
    markers=True
)
fig_trend.update_layout(
    xaxis_title="Month",
    yaxis_title="Total Sales",
    hovermode="x unified"
)
st.plotly_chart(fig_trend, use_container_width=True)

# =========================
# Prophet Forecast (month-only labels, actuals as 2024)
# =========================
st.subheader("🔮 Forecast (Prophet)")

# Prepare Prophet-friendly data using fixed year 2024 for actuals
df_prophet = overall_sales_df[['month_num', 'total_sales']].copy()
df_prophet['ds'] = pd.to_datetime(df_prophet['month_num'].apply(lambda m: f"2024-{int(m):02d}-01"))
df_prophet['y'] = df_prophet['total_sales'].astype(float)
df_prophet = df_prophet[['ds', 'y']].dropna().sort_values('ds')

if df_prophet.empty or len(df_prophet) < 3:
    st.info("Not enough data points to fit a forecast. Need at least 3 months of data.")
else:
    try:
        from prophet import Prophet

        # Model with yearly seasonality over months
        model = Prophet(yearly_seasonality=False, weekly_seasonality=False, daily_seasonality=False)
        model.add_seasonality(name='yearly', period=12, fourier_order=3)
        model.fit(df_prophet)

        # Forecast N months ahead (month start freq)
        future = model.make_future_dataframe(periods=forecast_horizon, freq='MS')
        forecast = model.predict(future)

        # Split actual vs forecast by last actual ds
        last_actual_ds = df_prophet['ds'].max()
        actual_fc = forecast[forecast['ds'] <= last_actual_ds].copy()
        future_fc = forecast[forecast['ds'] > last_actual_ds].copy()

        # Plot
        fig_fc = go.Figure()

        # Actuals (blue solid)
        fig_fc.add_trace(go.Scatter(
            x=actual_fc['ds'],
            y=actual_fc['yhat'],
            mode='lines+markers',
            name='Actuals (2024)',
            line=dict(width=2)
        ))

        # Forecast (orange dashed)
        fig_fc.add_trace(go.Scatter(
            x=future_fc['ds'],
            y=future_fc['yhat'],
            mode='lines+markers',
            name='Forecast (2025+)',
            line=dict(width=2, dash='dash')
        ))

        # Confidence interval band (over entire forecast frame for clarity)
        fig_fc.add_trace(go.Scatter(
            x=pd.concat([forecast['ds'], forecast['ds'][::-1]]),
            y=pd.concat([forecast['yhat_upper'], forecast['yhat_lower'][::-1]]),
            fill='toself',
            fillcolor='rgba(0, 150, 200, 0.15)',
            line=dict(color='rgba(255,255,255,0)'),
            name='Confidence Interval'
        ))

        # Month-only x-axis labels
        fig_fc.update_xaxes(
            tickformat="%b",  # Jan, Feb, ...
            dtick="M1"
        )

        fig_fc.update_layout(
            title=f"Monthly Sales Forecast (next {forecast_horizon} months)",
            xaxis_title="Month",
            yaxis_title="Total Sales",
            hovermode="x unified"
        )

        st.plotly_chart(fig_fc, use_container_width=True)

        # Insight blurb
        last_forecast_row = future_fc.tail(1).iloc[0] if not future_fc.empty else forecast.tail(1).iloc[0]
        last_actual_val = df_prophet['y'].iloc[-1]
        change = last_forecast_row['yhat'] - last_actual_val
        pct = (change / last_actual_val * 100) if last_actual_val else np.nan
        trend = "growth" if change > 0 else "decline" if change < 0 else "flat"

        st.markdown(
            f"**Insight:** Expected sales in **{last_forecast_row['ds'].strftime('%B %Y')}**: "
            f"**{last_forecast_row['yhat']:.0f}** "
            f"(range **{last_forecast_row['yhat_lower']:.0f}–{last_forecast_row['yhat_upper']:.0f}**). "
            + (f"Compared to the last actual month (**{last_actual_val:,.0f}**), this implies **{trend}** of **{abs(pct):.1f}%**."
               if not np.isnan(pct) else "")
        )

    except Exception as e:
        st.warning(f"Prophet is not available or failed to run: {e}\nInstall with: pip install prophet")

st.markdown("---")

# =========================
# Top 5 Customers by Month
# =========================
st.header("Top 5 Customers' Monthly Sales")

top_customers_sales_df = db.get_top_customers_sales_per_month()  # expects: customer_name, month, total_sales
top_customers_sales_df['month'] = pd.Categorical(top_customers_sales_df['month'], categories=month_order, ordered=True)
top_customers_sales_df = top_customers_sales_df.sort_values('month')

def plot_customers_sales_per_month(df: pd.DataFrame):
    fig = go.Figure()
    for customer in df['customer_name'].unique():
        sub = df[df['customer_name'] == customer]
        fig.add_trace(go.Scatter(
            x=sub['month'],
            y=sub['total_sales'],
            mode='lines+markers',
            name=customer,
            hovertemplate='Customer: %{text}<br>Month: %{x}<br>Sales: %{y}',
            text=sub['customer_name']
        ))
    fig.update_layout(
        title='Top 5 Customers Sales by Month',
        xaxis_title='Month',
        yaxis_title='Total Sales',
        legend_title='Customer',
        hovermode='x unified',
        margin=dict(l=0, r=0, t=30, b=30),
        legend=dict(x=1, y=1, traceorder='normal')
    )
    fig.update_xaxes(tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)

plot_customers_sales_per_month(top_customers_sales_df)



# =========================
# (Optional) Customer Impact on Route Sales
# =========================
# If you want this back, uncomment the lines below and ensure your DB method returns:
# customer_name, route, month, total_sales
#
# st.header("Customer Impact on Route Sales by Month")
# customer_route_sales_df = db.get_customer_sales_per_route()
# customer_route_sales_df['month'] = pd.Categorical(customer_route_sales_df['month'], categories=month_order, ordered=True)
# customer_route_sales_df = customer_route_sales_df.sort_values('month')
#
# def plot_customer_impact_on_route_sales(df: pd.DataFrame):
#     fig = go.Figure()
#     for route in df['route'].unique():
#         route_data = df[df['route'] == route]
#         for customer in route_data['customer_name'].unique():
#             sub = route_data[route_data['customer_name'] == customer]
#             fig.add_trace(go.Scatter(
#                 x=sub['month'],
#                 y=sub['total_sales'],
#                 mode='lines+markers',
#                 name=f"{customer} ({route})",
#                 hovertemplate='Customer: %{text}<br>Route: {route}<br>Month: %{x}<br>Sales: %{y}',
#                 text=sub['customer_name']
#             ))
#     fig.update_layout(
#         title='Customer Impact on Route Sales by Month',
#         xaxis_title='Month',
#         yaxis_title='Total Sales',
#         legend_title='Customer (Route)',
#         hovermode='x unified',
#         margin=dict(l=0, r=0, t=30, b=30),
#         legend=dict(x=1, y=1, traceorder='normal')
#     )
#     fig.update_xaxes(tickangle=-45)
#     st.plotly_chart(fig, use_container_width=True)
#
# plot_customer_impact_on_route_sales(customer_route_sales_df)

# =========================
# Cleanup
# =========================
db.close()
