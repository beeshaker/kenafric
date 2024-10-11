import streamlit as st
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from conn import MySQLDatabase  # Import the Database class
import pandas as pd


# Initialize the database connection
db = MySQLDatabase()
db.connect()

# Streamlit Dashboard Layout
st.title("Sales Dashboard")

# --- Top 5 Customers Sales per Month ---
st.header("Top 5 Customers' Monthly Sales")
top_customers_sales_df = db.get_top_customers_sales_per_month()

# Define the correct order of months
month_order = ['Jan', 'Feb', 'March', 'April', 'May', 'June', 'July', 'August', 'September']

# Convert 'month' column to categorical with the correct order
top_customers_sales_df['month'] = pd.Categorical(
    top_customers_sales_df['month'], 
    categories=month_order, 
    ordered=True
)

# Sort the dataframe by the 'month' column
top_customers_sales_df = top_customers_sales_df.sort_values('month')

def plot_customers_sales_per_month(df):
    fig = go.Figure()

    # Group data by customer_name
    for customer in df['customer_name'].unique():
        customer_data = df[df['customer_name'] == customer]
        fig.add_trace(go.Scatter(
            x=customer_data['month'],
            y=customer_data['total_sales'],
            mode='lines+markers',
            name=customer,
            hovertemplate='Customer: %{text}<br>Month: %{x}<br>Sales: %{y}',
            text=customer_data['customer_name']
        ))

    fig.update_layout(
        title='Top 5 Customers Sales by Month',
        xaxis_title='Month',
        yaxis_title='Total Sales',
        legend_title='Customer',
        hovermode='x unified',  # This will show hover info for all lines on the same x-axis
        margin=dict(l=0, r=0, t=30, b=30),  # Adjust margins to fit the legend
        legend=dict(x=1, y=1, traceorder='normal')  # Position the legend outside
    )

    fig.update_xaxes(tickangle=-45)  # Rotate x-axis labels for better readability

    st.plotly_chart(fig)

plot_customers_sales_per_month(top_customers_sales_df)

# --- Route Sales per Month ---
st.header("Route Sales per Month")
route_sales_df = db.get_route_sales_per_month()

# Define the correct order of months
month_order = ['Jan', 'Feb', 'March', 'April', 'May', 'June', 'July', 'August', 'September']

# Convert 'month' column to categorical with the correct order
route_sales_df['month'] = pd.Categorical(
    route_sales_df['month'], 
    categories=month_order, 
    ordered=True
)

# Sort the dataframe by the 'month' column to ensure the correct order
route_sales_df = route_sales_df.sort_values('month')

def plot_route_sales_per_month(df):
    fig = go.Figure()

    # Group data by route
    for route in df['route'].unique():
        route_data = df[df['route'] == route]
        fig.add_trace(go.Scatter(
            x=route_data['month'],
            y=route_data['total_sales'],
            mode='lines+markers',
            name=route,
            hovertemplate='Route: %{text}<br>Month: %{x}<br>Sales: %{y}',
            text=route_data['route']
        ))

    fig.update_layout(
        title='Route Sales by Month',
        xaxis_title='Month',
        yaxis_title='Total Sales',
        legend_title='Route',
        hovermode='x unified',
        margin=dict(l=0, r=0, t=30, b=30),
        legend=dict(x=1, y=1, traceorder='normal')
    )

    # Rotate x-axis labels for better readability
    fig.update_xaxes(tickangle=-45, categoryorder='array', categoryarray=month_order)

    st.plotly_chart(fig)

plot_route_sales_per_month(route_sales_df)


# --- Customer Impact on Route Sales ---
st.header("Customer Impact on Route Sales")
customer_route_sales_df = db.get_customer_sales_per_route()

# Convert 'month' column to categorical with the correct order
customer_route_sales_df['month'] = pd.Categorical(
    customer_route_sales_df['month'], 
    categories=month_order, 
    ordered=True
)

# Sort the dataframe by the 'month' column
customer_route_sales_df = customer_route_sales_df.sort_values('month')

def plot_customer_impact_on_route_sales(df):
    fig = go.Figure()

    # Group data by route and customer_name
    for route in df['route'].unique():
        route_data = df[df['route'] == route]
        for customer in route_data['customer_name'].unique():
            customer_data = route_data[route_data['customer_name'] == customer]
            fig.add_trace(go.Scatter(
                x=customer_data['month'],
                y=customer_data['total_sales'],
                mode='lines+markers',
                name=f"{customer} ({route})",
                hovertemplate='Customer: %{text}<br>Route: %{route}<br>Month: %{x}<br>Sales: %{y}',
                text=customer_data['customer_name']
            ))

    fig.update_layout(
        title='Customer Impact on Route Sales by Month',
        xaxis_title='Month',
        yaxis_title='Total Sales',
        legend_title='Customer (Route)',
        hovermode='x unified',
        margin=dict(l=0, r=0, t=30, b=30),
        legend=dict(x=1, y=1, traceorder='normal')
    )

    fig.update_xaxes(tickangle=-45)  # Rotate x-axis labels for better readability

    st.plotly_chart(fig)

plot_customer_impact_on_route_sales(customer_route_sales_df)
# Close the database connection at the end
db.close()