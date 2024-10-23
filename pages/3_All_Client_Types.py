import streamlit as st
import pandas as pd
import plotly.express as px
from conn1 import MySQLDatabase  # Import the Database class

# Initialize the database connection
db = MySQLDatabase()
db.connect()

# Sidebar: Client Type and Percentage Selection
st.sidebar.title("Filter Options")
client_types = ['All','DISTRIBUTORS', 'SPECIAL DISTRIBUTOR', 'MINIMART', 'KABL OFFICE', 'M/BIKE','SUPERMARKET', 'KABL STAFF','SCHOOLS','LOCAL CUSTOMERS','CORPORATES']
selected_client_type = st.sidebar.selectbox("Select Client Type", client_types)

selected_percentage = st.sidebar.slider("Select Percentage", 0, 100, 1)

# --- New Page for Top Clients Based on Selection ---
st.title(f"Top {selected_percentage}% {selected_client_type} by Sales")

# Fetch product sales for the top clients based on selected client type and percentage
top_clients_product_sales_df = db.get_top_clients_product_sales(selected_client_type, selected_percentage)

# Fetch monthly product sales for the top clients
monthly_product_sales_df = db.get_monthly_clients_product_sales(selected_client_type, selected_percentage)

# Fetch top clients based on selected client type and percentage
top_clients_df = db.get_top_clients(selected_client_type, selected_percentage)

# Fetch total sales for the selected client type and all customers
total_client_type_sales = db.get_total_sales_by_client_type(selected_client_type)
total_sales = db.get_total_overall_sales()

# Calculate the total sales of the top clients
top_clients_total_sales = top_clients_df['total_sales'].sum()

# Calculate the percentage of top clients' sales out of all client type sales and total sales
percentage_of_client_type_sales = (top_clients_total_sales / total_client_type_sales) * 100
percentage_of_total_sales = (top_clients_total_sales / total_sales) * 100

# Round sales figures to integers
top_clients_total_sales = round(top_clients_total_sales)
percentage_of_client_type_sales = round(percentage_of_client_type_sales)
percentage_of_total_sales = round(percentage_of_total_sales)

# Round all columns in the DataFrame to integers
top_clients_df['total_sales'] = top_clients_df['total_sales'].round(0)
top_clients_product_sales_df['total_sales_amt'] = top_clients_product_sales_df['total_sales_amt'].round(0)
monthly_product_sales_df['total_sales_amt'] = monthly_product_sales_df['total_sales_amt'].round(0)

# Display the top clients and their sales amounts
st.subheader(f"Top {selected_percentage}% {selected_client_type} by Sales")

# --- Display the Percentage of Sales ---
st.subheader(f"Percentage of Sales from Top {selected_percentage}% {selected_client_type}")
st.write(f"Total sales from the top {selected_percentage}% {selected_client_type}: **Ksh{top_clients_total_sales:,.0f}**")
st.write(f"Percentage of all {selected_client_type} sales: **{percentage_of_client_type_sales:.0f}%**")
st.write(f"Percentage of total sales (all customers): **{percentage_of_total_sales:.0f}%**")

# --- Bar Chart for Top Clients by Sales ---
st.subheader(f"Sales Distribution of Top {selected_percentage}% {selected_client_type}")

# Create a bar chart for the top clients
fig_bar = px.bar(
    top_clients_df, 
    x='client_name', 
    y='total_sales', 
    title=f"Top {selected_percentage}% {selected_client_type} by Total Sales", 
    labels={'client_name': f"{selected_client_type} Name", 'total_sales': 'Total Sales'},
    text='total_sales'
)

# Update the layout for better readability
fig_bar.update_layout(
    xaxis_title=f"{selected_client_type} Name",
    yaxis_title="Total Sales",
    xaxis_tickangle=-45,
    hovermode="x unified"
)

# Display the bar chart
st.plotly_chart(fig_bar)
top_clients_df[['total_sales', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep']] = top_clients_df[['total_sales', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep']].round(0)
# Display the top clients DataFrame
st.write(top_clients_df)

# --- Cumulative Product Sales for Top Clients ---
st.subheader(f"Cumulative Product Sales for Top {selected_percentage}% {selected_client_type}")

# Create the treemap for cumulative product sales for the top clients
fig_treemap = px.treemap(
    top_clients_product_sales_df,
    path=['item_description'],
    values='total_sales_amt',
    title=f"Cumulative Product Sales for Top {selected_percentage}% {selected_client_type}",
    labels={'total_sales_amt': 'Total Sales Amount (Ksh)'}
)

# Display the treemap
st.plotly_chart(fig_treemap)

# --- Monthly Product Sales for Top Clients (Line Chart) ---
st.subheader(f"Monthly Product Sales for Top {selected_percentage}% {selected_client_type}")

# Create the line chart for monthly product sales for the top clients
fig_line = px.line(
    monthly_product_sales_df,
    x='month',
    y='total_sales_amt',
    color='item_description',
    title=f"Monthly Product Sales for Top {selected_percentage}% {selected_client_type}",
    labels={'total_sales_amt': 'Total Sales Amount (Ksh)', 'month': 'Month', 'item_description': 'Product'}
)

# Display the line chart
st.plotly_chart(fig_line)
