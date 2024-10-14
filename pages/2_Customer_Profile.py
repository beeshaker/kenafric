import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from conn import MySQLDatabase  # Import the Database class
import numpy as np
import plotly.express as px

# Initialize the database connection
db = MySQLDatabase()
db.connect()


# Sidebar: Client Selection
st.sidebar.title("Client Selection")
clients = db.get_all_clients()
selected_client = st.sidebar.selectbox("Select a Client", clients)

# Define the correct order of months
month_order = ['All', 'Jan', 'Feb', 'March', 'April', 'May', 'June', 'July', 'August', 'September']
selected_month = st.selectbox("Select a Month for Product Breakdown", month_order)



# --- Treemap for all ---
if selected_client:
    # --- Treemap for all clients to show the "average customer basket" ---
    st.title("Average Customer Basket Breakdown (Top Products by Percentage)")

    # Fetch product sales for all clients based on selected month
    all_clients_product_sales_df = db.get_all_clients_product_sales(selected_month)

    # Calculate the total quantity sold for all products
    total_quantity_sold = all_clients_product_sales_df['total_quantity_sold'].sum()

    # Calculate the percentage for each product
    all_clients_product_sales_df['percentage'] = (all_clients_product_sales_df['total_quantity_sold'] / total_quantity_sold) * 100

    # Generate the treemap to show the product breakdown for all clients
    fig_treemap_all = px.treemap(all_clients_product_sales_df,
                                 path=['item_description'],
                                 values='total_quantity_sold',
                                 title="Average Customer Basket: Product Distribution",
                                 labels={'total_quantity_sold': 'Quantity Sold'},
                                 custom_data=['percentage'])

    # Customize the hover template to include the percentage
    fig_treemap_all.update_traces(
        hovertemplate='<b>%{label}</b><br>Quantity Sold: %{value}<br>Percentage: %{customdata[0]:.2f}%'
    )

    # Display the treemap for all clients
    st.plotly_chart(fig_treemap_all)


    
    
     # --- Treemap: Client's Basket Breakdown ---
    st.title(f"{selected_client}'s Basket Breakdown")

    # Fetch product sales for the selected client based on the selected month
    client_product_sales_df = db.get_client_product_sales(selected_client, selected_month)

    # Calculate the total quantity sold for the client
    total_quantity_sold_client = client_product_sales_df['total_quantity_sold'].sum()

    # Calculate the percentage for each product in the client's basket
    client_product_sales_df['percentage'] = (client_product_sales_df['total_quantity_sold'] / total_quantity_sold_client) * 100

    # Generate the treemap to show the product breakdown for the selected client
    fig_treemap_client = px.treemap(client_product_sales_df,
                                    path=['item_description'],
                                    values='total_quantity_sold',
                                    title=f"{selected_client}'s Basket: Product Distribution",
                                    labels={'total_quantity_sold': 'Quantity Sold'},
                                    custom_data=['percentage'])

    # Customize the hover template to include the percentage for the client
    fig_treemap_client.update_traces(
        hovertemplate='<b>%{label}</b><br>Quantity Sold: %{value}<br>Percentage: %{customdata[0]:.2f}%'
    )

    # Display the treemap for the selected client
    st.plotly_chart(fig_treemap_client)
    
    
    
    
    # --- Title ---
    st.title(f"Change in Quantity Bought by {selected_client} for Each Product")

    # Fetch sales data for the selected client
    client_sales_df = db.get_client_product_sales_detailed(selected_client)


    # Convert 'month' column to categorical with the correct order and sort the dataframe
    client_sales_df['month'] = pd.Categorical(client_sales_df['month'], categories=month_order, ordered=True)
    client_sales_df = client_sales_df.sort_values(['item_description', 'month'])

    # Calculate the month-to-month change in quantity for each product
    client_sales_df['qty_change'] = client_sales_df.groupby('item_description')['total_quantity_sold'].diff()

    # Calculate the percentage change in quantity bought for each product
    client_sales_df['pct_change'] = client_sales_df.groupby('item_description')['total_quantity_sold'].pct_change() * 100

    # Fill NaN values in 'qty_change' and 'pct_change' with 0 for the first month of each product
    client_sales_df[['qty_change', 'pct_change']] = client_sales_df[['qty_change', 'pct_change']].fillna(0)

    # --- Line Graph: Percentage Change in Quantity for Each Product ---
    st.subheader("Percentage Change in Quantity for Each Product (Line Graph)")

    fig = go.Figure()

    # Loop through each product and plot the line graph for percentage change
    for product in client_sales_df['item_description'].unique():
        product_data = client_sales_df[client_sales_df['item_description'] == product]
        
        fig.add_trace(go.Scatter(
            x=product_data['month'],
            y=product_data['pct_change'],
            mode='lines+markers',
            name=product,
            hoverinfo='text',
            text=[f"{product}: {pct_change:.2f}%" for pct_change in product_data['pct_change']]
        ))

    # Update layout for better readability
    fig.update_layout(
        title="Percentage Change in Quantity for Each Product",
        xaxis_title="Month",
        yaxis_title="Percentage Change (%)",
        hovermode="x unified"
    )

    # Rotate x-axis labels for better readability
    fig.update_xaxes(tickangle=-45)

    # Display the line graph
    st.plotly_chart(fig)

    # --- Title ---
    st.title(f"Unit Price for Each Product Bought by {selected_client}")

    # Fetch sales data for the selected client
    client_sales_df = db.get_client_product_sales_detailed(selected_client)

    # Convert 'month' column to categorical with the correct order and sort the dataframe
    client_sales_df['month'] = pd.Categorical(client_sales_df['month'], categories=month_order, ordered=True)
    client_sales_df = client_sales_df.sort_values(['item_description', 'month'])

    # Calculate the month-to-month change in quantity for each product
    client_sales_df['qty_change'] = client_sales_df.groupby('item_description')['total_quantity_sold'].diff()

    # Calculate the percentage change in quantity bought for each product
    client_sales_df['pct_change'] = client_sales_df.groupby('item_description')['total_quantity_sold'].pct_change() * 100

    # Fill NaN values in 'qty_change' and 'pct_change' with 0 for the first month of each product
    client_sales_df[['qty_change', 'pct_change']] = client_sales_df[['qty_change', 'pct_change']].fillna(0)

    # --- Calculate the Unit Price (sales_amt / total_quantity_sold) ---
    client_sales_df['unit_price'] = client_sales_df['sales_amt'] / client_sales_df['total_quantity_sold']

    # --- Line Graph: Unit Price for Each Product ---
    st.subheader("Unit Price for Each Product (Line Graph)")

    fig_unit_price = go.Figure()

    # Loop through each product and plot the line graph for unit price
    for product in client_sales_df['item_description'].unique():
        product_data = client_sales_df[client_sales_df['item_description'] == product]
        
        fig_unit_price.add_trace(go.Scatter(
            x=product_data['month'],
            y=product_data['unit_price'],
            mode='lines+markers',
            name=product,
            hoverinfo='text',
            text=[f"{product}: ${unit_price:.2f}" for unit_price in product_data['unit_price']]
        ))

    # Update layout for better readability
    fig_unit_price.update_layout(
        title="Unit Price for Each Product",
        xaxis_title="Month",
        yaxis_title="Unit Price (Ksh)",
        hovermode="x unified"
    )

    # Rotate x-axis labels for better readability
    fig_unit_price.update_xaxes(tickangle=-45)

    # Display the unit price line graph
    st.plotly_chart(fig_unit_price)

    # --- Dropdown to select a product ---
    st.subheader("Select a Product to View Details")
    selected_product = st.selectbox("Choose a Product", client_sales_df['item_description'].unique())

    # Filter the data for the selected product
    filtered_df = client_sales_df[client_sales_df['item_description'] == selected_product]

    # --- Display Detailed Table for the Selected Product ---
    st.subheader(f"Details for {selected_product}")

    # Ensure that 'unit_price' and 'sales_amt' are included in the filtered data
    # Reorder the columns to have 'unit_price' before 'sales_amt'
    detailed_table = filtered_df[['month', 'total_quantity_sold', 'qty_change', 'pct_change', 'unit_price', 'sales_amt']].copy()

    # Rename columns for better readability
    detailed_table = detailed_table.rename(columns={
        'total_quantity_sold': 'Quantity Sold',
        'qty_change': 'Quantity Change',
        'pct_change': 'Percentage Change (%)',
        'unit_price': 'Unit Price (Ksh)',
        'sales_amt': 'Sales Value'
    })

    # Display the detailed table for the selected product with unit price and sales value
    st.write(detailed_table)

    


# --- Existing logic for sales data and route sales breakdown ---

# Fetch sales data for the selected client
if selected_client:
    client_sales_df = db.get_client_sales(selected_client)

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
            total_route_sales.append(np.nan)
            percentages.append(0)
            continue
        
        # Fetch total route sales for the given route and month
        route_sales = db.get_route_sales_for_client(route, month)
        
        # Add route sales to the total_route_sales list
        total_route_sales.append(route_sales)

        # Calculate the percentage of total route sales attributed to the client
        if route_sales > 0:
            percentage = (row['total_sold_to_client'] / route_sales) * 100
        else:
            percentage = 0  # If no route sales, percentage is 0

        percentages.append(percentage)

    # Add the total route sales and percentage to the DataFrame
    client_sales_df['total_route_sales'] = total_route_sales
    client_sales_df['percentage_of_route'] = percentages

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
