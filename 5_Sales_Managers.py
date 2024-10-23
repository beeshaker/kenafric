import streamlit as st
import pandas as pd
import plotly.express as px
from conn import MySQLDatabase  # Import the Database class

# Initialize the database connection
db = MySQLDatabase()
db.connect()

# Sidebar: Sales Manager, Product, and Month Selections
st.sidebar.title("Filter Options")

sales_managers = ["All", "George Omondi", "Joshua Ageta", "Kennedy Mutisya", "Jarso Abdi", "Nicholas Dass", "Nicholas Baraka", "Mourice Kevin Barasa"]
selected_sales_manager = st.sidebar.selectbox("Select Sales Manager", sales_managers)

products = db.get_all_products()
products.insert(0, "All")
selected_product = st.sidebar.selectbox("Select Product", products)

months = ['All', 'Jan', 'Feb', 'March', 'April', 'May', 'June', 'July', 'August', 'September']
selected_month = st.sidebar.selectbox("Select Month", months)

# Define the correct month order
month_order = ['Jan', 'Feb', 'March', 'April', 'May', 'June', 'July', 'August', 'September']

# --- Title ---
if selected_sales_manager == "All":
    st.title(f"Cumulative Sales Data for All Sales Managers (Month: {selected_month}, Product: {selected_product})")
else:
    st.title(f"Sales Performance of {selected_sales_manager} (Month: {selected_month}, Product: {selected_product})")

# --- Top 5 Sales Managers and Sales Data ---
if selected_sales_manager == "All":
    st.subheader(f"Top Sales Managers for {selected_product} in {selected_month}")
    top_5_sales_managers_df = db.get_top_5_sales_managers(selected_month, selected_product)
    top_5_sales_managers_df['total_sales'] = top_5_sales_managers_df['total_sales'].round(0).astype(int)
    st.write(top_5_sales_managers_df)
else:
    # --- Sales Manager's Ranking and Performance ---
    st.subheader(f"{selected_sales_manager}'s Performance in {selected_month}")
    
    # Fetch ranking and calculate percentage above/below the median
    sales_manager_ranking_df = db.get_sales_manager_ranking(selected_sales_manager, selected_month, selected_product)
    selected_sales = sales_manager_ranking_df.loc[sales_manager_ranking_df['sales_manager'] == selected_sales_manager, 'total_sales'].values[0]
    
    median_sales = sales_manager_ranking_df['total_sales'].median()
    percentage_diff = ((selected_sales - median_sales) / median_sales) * 100

    # Display ranking and percentage difference
    st.write(f"{selected_sales_manager} is ranked {sales_manager_ranking_df.index[sales_manager_ranking_df['sales_manager'] == selected_sales_manager][0] + 1} out of {len(sales_manager_ranking_df)}.")
    if percentage_diff > 0:
        st.write(f"{selected_sales_manager} is **{percentage_diff:.2f}% above** the median sales for {selected_product} in {selected_month}.")
    else:
        st.write(f"{selected_sales_manager} is **{abs(percentage_diff):.2f}% below** the median sales for {selected_product} in {selected_month}.")

# --- Monthly Sales Line Graph with Median ---
if selected_sales_manager != "All":
    st.subheader(f"Monthly Sales for {selected_sales_manager} ({selected_product})")
    
    # Fetch monthly sales data for the selected manager and product
    monthly_sales_df = db.get_monthly_sales_by_manager(selected_sales_manager, selected_product)
    
    # Fetch median sales for all managers
    median_sales_df = db.get_median_sales_by_month(selected_product)

    # Sort by month order
    monthly_sales_df['month'] = pd.Categorical(monthly_sales_df['month'], categories=month_order, ordered=True)
    median_sales_df['month'] = pd.Categorical(median_sales_df['month'], categories=month_order, ordered=True)

    # Create line chart
    fig = px.line(
        monthly_sales_df,
        x='month',
        y='total_sales',
        title=f"Monthly Sales for {selected_sales_manager}",
        labels={'total_sales': 'Total Sales (Ksh)', 'month': 'Month'}
    )

    # Add a dashed line for median sales
    fig.add_scatter(
        x=median_sales_df['month'],
        y=median_sales_df['median_sales'],
        mode='lines',
        name='Median Sales',
        line=dict(dash='dash')
    )

    st.plotly_chart(fig)

# --- Top 5 Clients for Selected Sales Manager ---
if selected_sales_manager != "All":
    st.subheader(f"Top 5 Clients for {selected_sales_manager} in {selected_month} for {selected_product}")
    
    if selected_product == "All":
        # Fetch cumulative top 5 clients for all products
        top_5_clients_df = db.get_top_5_clients_by_manager_and_product(selected_sales_manager, selected_month, product=None)
    else:
        # Fetch top 5 clients for the selected product
        top_5_clients_df = db.get_top_5_clients_by_manager_and_product(selected_sales_manager, selected_month, product=selected_product)
    
    if not top_5_clients_df.empty:
        top_5_clients_df['total_sales'] = top_5_clients_df['total_sales'].round(0).astype(int)
        st.write(top_5_clients_df)
    else:
        st.write("No data available for the selected filters.")

# --- Cumulative Sales for All Sales Managers ---
if selected_sales_manager == "All":
    st.subheader(f"Cumulative Sales for All Sales Managers ({selected_product})")
    cumulative_sales_df = db.get_cumulative_sales_by_manager('All', selected_month, selected_product)
    
    # Sort by month order
    cumulative_sales_df['month'] = pd.Categorical(cumulative_sales_df['month'], categories=month_order, ordered=True)
    cumulative_sales_df = cumulative_sales_df.sort_values('month')
    
    cumulative_sales_df['total_sales'] = cumulative_sales_df['total_sales'].round(0).astype(int)
    st.write(cumulative_sales_df)
