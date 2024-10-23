import streamlit as st
import pandas as pd
import plotly.express as px
from conn1 import MySQLDatabase  # Import the Database class

# Initialize the database connection
db = MySQLDatabase()
db.connect()

st.sidebar.title("Product Profile")
products = db.get_all_products()  # Assuming this function returns a list of all available products
selected_product = st.sidebar.selectbox("Select a Product", products)

# Sidebar: Month Selection with 'All' option
month_order = ['All', 'Jan', 'Feb', 'March', 'April', 'May', 'June', 'July', 'August', 'September']
selected_month = st.sidebar.selectbox("Select a Month", month_order)


# Display the top 5 clients and sales distribution by route
if selected_product:
    # Fetch the top 5 clients for the selected product and month
    top_clients_df = db.get_top_clients_for_product(selected_product, selected_month)

    # Check if data is available for the product
    if not top_clients_df.empty:
        st.subheader(f"Top 5 Clients for {selected_product} in {selected_month}")

        # Display the top 5 clients as a table
        st.write(top_clients_df)

        # Bar chart to visualize the top 5 clients by quantity sold
        fig_clients = px.bar(top_clients_df, x='customer_name', y='total_quantity_sold', 
                             title=f"Top 5 Clients by Quantity Sold for {selected_product}",
                             labels={'total_quantity_sold': 'Quantity Sold', 'customer_name': 'Client Name'},
                             text='total_quantity_sold')

        # Display the bar chart for clients
        st.plotly_chart(fig_clients)

        
        
    # Function to group smaller routes into "Other"
def group_small_routes(dataframe, value_column, label_column, threshold):
    total_value = dataframe[value_column].sum()
    
    # Calculate the percentage contribution of each route
    dataframe['percentage'] = (dataframe[value_column] / total_value) * 100
    
    # Separate out the routes with contributions below the threshold
    small_routes = dataframe[dataframe['percentage'] < threshold]
    large_routes = dataframe[dataframe['percentage'] >= threshold]
    
    # Sum up the small routes and create an "Other" row
    if not small_routes.empty:
        other_value = small_routes[value_column].sum()
        other_row = pd.DataFrame({label_column: ['Other'], value_column: [other_value], 'percentage': [other_value / total_value * 100]})
        # Append the "Other" row to the large routes
        grouped_data = pd.concat([large_routes, other_row], ignore_index=True)
    else:
        grouped_data = large_routes
    
    return grouped_data


# Get route distribution data (modify as needed to get your data)
route_distribution_df = db.get_sales_distribution_by_route(selected_product, selected_month)  # Example function call

# Group small routes (optional)
threshold = 2  # Routes contributing less than 2% will be grouped into 'Other'
grouped_route_df = group_small_routes(route_distribution_df, 'total_quantity_sold', 'route', threshold)

# Generate a simplified pie chart with grouped data
fig_route = px.pie(grouped_route_df, values='total_quantity_sold', names='route',
                   title=f"Sales Distribution by Route for {selected_product} in {selected_month}",
                   labels={'total_quantity_sold': 'Quantity Sold', 'route': 'Route'})

# Display the pie chart
st.plotly_chart(fig_route)

# Generate a treemap with grouped data
fig_treemap = px.treemap(grouped_route_df, 
                         path=['route'], 
                         values='total_quantity_sold', 
                         title=f"Sales Distribution by Route for {selected_product} in {selected_month}",
                         labels={'total_quantity_sold': 'Quantity Sold'})

# Display the treemap
st.plotly_chart(fig_treemap)