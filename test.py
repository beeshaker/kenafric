import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from conn import MySQLDatabase  # Import the Database class
import numpy as np

# Initialize the database connection
db = MySQLDatabase()
db.connect()

# Sidebar: Client Selection
st.sidebar.title("Client Selection")
clients = db.get_all_clients()
selected_client = st.sidebar.selectbox("Select a Client", clients)

# Fetch sales data for the selected client
if selected_client:
    client_sales_df = db.get_client_sales(selected_client)

    # Define the correct order of months
    month_order = ['Jan','Feb', 'March', 'April', 'May', 'June', 'July', 'August', 'September']

    # Convert 'month' column to categorical with the correct order and sort the dataframe
    client_sales_df['month'] = pd.Categorical(client_sales_df['month'], categories=month_order, ordered=True)
    client_sales_df = client_sales_df.sort_values('month')

    # Calculate the percentage of route sales attributed to the client
    st.header(f"Percentage of Route Sales Attributed to {selected_client}")

    total_route_sales = []
    percentages = []

    # Extract the route name from the first row (assuming the route is the same across months for the client)
    route_name = client_sales_df['route'].iloc[0] if not client_sales_df.empty else "Unknown Route"

    for _, row in client_sales_df.iterrows():
        route = row['route']
        month = row['month']
        
        # Check if route or month is NaN, if so, skip that iteration
        if pd.isna(route) or pd.isna(month):
            total_route_sales.append(np.nan)  # Append NaN if data is invalid
            percentages.append(0)  # Set percentage to 0 in case of invalid data
            continue
        
        # Fetch total route sales for the given route and month
        route_sales = db.get_route_sales_for_client(route, month)
        
        # Add route sales to the total_route_sales list
        total_route_sales.append(route_sales)

        # Calculate the percentage of total route sales attributed to the client
        if route_sales > 0:
            percentage = (row['total_sales'] / route_sales) * 100
        else:
            percentage = 0  # If no route sales, percentage is 0

        percentages.append(percentage)

    # Add the total route sales and percentage to the DataFrame
    client_sales_df['total_route_sales'] = total_route_sales
    client_sales_df['percentage_of_route'] = percentages

    # Rename the total_sales column to total_sold_to_client
    client_sales_df.rename(columns={'total_sales': 'total_sold_to_client'}, inplace=True)

    # Reorder the columns as desired: month, total_sold_to_client, total_route_sales, percentage_of_route
    client_sales_df = client_sales_df[['month', 'total_sold_to_client', 'total_route_sales', 'percentage_of_route']]

    # Display the main DataFrame without the index column
    st.write(client_sales_df.reset_index(drop=True))

    # --- New Table: Change in Sales per Month for Client and Route ---

    # Calculate the change in sales for the client between months using the diff() function
    client_sales_df['client_sales_change'] = client_sales_df['total_sold_to_client'].diff()

    # Calculate the change in route sales between months using the diff() function
    client_sales_df['route_sales_change'] = client_sales_df['total_route_sales'].diff()

    # Calculate the percentage change for client sales between months
    client_sales_df['client_sales_percentage_change'] = client_sales_df['total_sold_to_client'].pct_change() * 100

    # Calculate the percentage change for route sales between months
    client_sales_df['route_sales_percentage_change'] = client_sales_df['total_route_sales'].pct_change() * 100

    # Display the new table showing the change in sales for the client and the route
    st.header(f"Monthly Sales Change for {selected_client} and Their Route: {route_name}")

    # Show the table with absolute changes and percentage changes
    sales_change_df = client_sales_df[['month', 'total_sold_to_client', 'client_sales_change', 
                                    'client_sales_percentage_change', 'total_route_sales', 
                                    'route_sales_change', 'route_sales_percentage_change']]

    # Display the sales change table without the index column
    st.write(sales_change_df.reset_index(drop=True))
    
    # Plot Percentage Change Graph
    client_sales_df['client_sales_percentage_change'] = client_sales_df['client_sales_percentage_change'].fillna(0)
    client_sales_df['route_sales_percentage_change'] = client_sales_df['route_sales_percentage_change'].fillna(0)

    # Create a line graph for percentage changes in client sales and route sales
    st.header(f"Percentage Change in Sales for {selected_client} and Their Route: {route_name}")

    fig = go.Figure()

    # Line for client's percentage change
    fig.add_trace(go.Scatter(
        x=client_sales_df['month'],
        y=client_sales_df['client_sales_percentage_change'],
        mode='lines+markers',
        name=f"{selected_client} Sales Change (%)"
    ))

    # Line for route's percentage change
    fig.add_trace(go.Scatter(
        x=client_sales_df['month'],
        y=client_sales_df['route_sales_percentage_change'],
        mode='lines+markers',
        name=f"{route_name} Route Sales Change (%)"
    ))

    # Update layout for better readability
    fig.update_layout(
        title=f"Percentage Change in Sales for {selected_client} and Their Route",
        xaxis_title="Month",
        yaxis_title="Percentage Change (%)",
        legend_title="Legend",
        hovermode="x unified"
    )

    # Rotate x-axis labels for better readability
    fig.update_xaxes(tickangle=-45)

    # Display the graph
    st.plotly_chart(fig)

    # Plot the client's sales per month    
    st.header(f"Sales per Month for {selected_client}")
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=client_sales_df['month'],
        y=client_sales_df['total_sold_to_client'],
        mode='lines+markers',
        name=selected_client
    ))
    fig.update_layout(
        title=f'Sales Trend for {selected_client}',
        xaxis_title='Month',
        yaxis_title='Total Sales',
        hovermode='x unified'
    )
    fig.update_xaxes(tickangle=-45)
    st.plotly_chart(fig)
