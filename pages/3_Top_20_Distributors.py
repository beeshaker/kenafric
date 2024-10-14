import streamlit as st
import pandas as pd
import plotly.express as px
from conn import MySQLDatabase  # Import the Database class

# Initialize the database connection
db = MySQLDatabase()
db.connect()


# --- New Page for Top 20 Distributors ---
st.title("Top 20 Distributors by Sales")


# Fetch product sales for top 20 distributors
top_20_product_sales_df = db.get_top_20_product_sales()

# Fetch monthly product sales for top 20 distributors
monthly_product_sales_df = db.get_monthly_product_sales()
# Fetch top 20 distributors
top_distributors_df = db.get_top_20_distributors()

# Fetch total sales for all distributors and all customers
total_distributor_sales = db.get_total_distributor_sales()
total_sales = db.get_total_overall_sales()

# Calculate the total sales of the top 20 distributors
top_20_total_sales = top_distributors_df['total_sales'].sum()

# Calculate the percentage of top 20 sales out of all distributor sales and total sales
percentage_of_distributor_sales = (top_20_total_sales / total_distributor_sales) * 100
percentage_of_total_sales = (top_20_total_sales / total_sales) * 100

# Display the top 20 distributors and their sales amounts
st.subheader("Top 20 Distributors")


# --- Display the Percentage of Sales ---
st.subheader("Percentage of Sales from Top 20 Distributors")
st.write(f"Total sales from the top 20 distributors: **Ksh{top_20_total_sales:,.2f}**")

st.write(f"Percentage of all distributor sales: **{percentage_of_distributor_sales:.2f}%**")
st.write(f"Percentage of total sales (all customers): **{percentage_of_total_sales:.2f}%**")

# --- Bar Chart for Top 20 Distributors by Sales ---
st.subheader("Sales Distribution of Top 20 Distributors")



# Create a bar chart for the top distributors
fig_bar = px.bar(
    top_distributors_df, 
    x='distributor_name', 
    y='total_sales', 
    title="Top 20 Distributors by Total Sales", 
    labels={'distributor_name': 'Distributor Name', 'total_sales': 'Total Sales'},
    text='total_sales'
)

# Update the layout for better readability
fig_bar.update_layout(
    xaxis_title="Distributor Name",
    yaxis_title="Total Sales",
    xaxis_tickangle=-45,
    hovermode="x unified"
)

# Display the bar chart
st.plotly_chart(fig_bar)

st.write(top_distributors_df)


st.subheader("Cumulative Product Sales for Top 20 Distributors")

# Fetch cumulative product sales for top 20 distributors
top_20_product_sales_df = db.get_top_20_product_sales()

# Create the treemap
fig_treemap = px.treemap(
    top_20_product_sales_df,
    path=['item_description'],
    values='total_sales_amt',
    title="Cumulative Product Sales for Top 20 Distributors",
    labels={'total_sales_amt': 'Total Sales Amount (Ksh)'}
)

# Display the treemap
st.plotly_chart(fig_treemap)

# --- Monthly Product Sales for Top 20 Distributors (Line Chart) ---
st.subheader("Monthly Product Sales for Top 20 Distributors")

# Fetch monthly product sales for top 20 distributors
monthly_product_sales_df = db.get_monthly_product_sales()

# Create the line chart
fig_line = px.line(
    monthly_product_sales_df,
    x='month',
    y='total_sales_amt',
    color='item_description',
    title="Monthly Product Sales for Top 20 Distributors",
    labels={'total_sales_amt': 'Total Sales Amount ($)', 'month': 'Month', 'item_description': 'Product'}
)

# Display the line chart
st.plotly_chart(fig_line)