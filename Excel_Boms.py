import streamlit as st
import pandas as pd

# Streamlit app to upload and split Excel data
st.title("BOM Excel Processor")

# Step 1: Upload the Excel file
uploaded_file = st.file_uploader("Upload your BOM Excel file", type=["xlsx"])

if uploaded_file is not None:
    # Step 2: Read the Excel file into a pandas DataFrame
    df = pd.read_excel(uploaded_file)

    # Show the uploaded data
    st.subheader("Uploaded Data")
    st.write(df)

    # Step 3: Split data into products, bom_components, and bill_of_materials tables
    # Filter rows where the 'Depth' is 1 (Finished Goods) for the products table
    products_df = df[df['Depth'] == 1][['Item', 'Item Description', 'UoM']].copy()
    products_df.columns = ['item_code', 'description', 'uom']  # Rename columns to match the products table

    # For BOM components, take all unique 'Item' and 'Item Description' regardless of depth
    bom_components_df = df[['Item', 'Item Description', 'UoM']].drop_duplicates().copy()
    bom_components_df.columns = ['item_code', 'description', 'uom']  # Rename columns to match the bom_components table

    # Create bill_of_materials table from relevant columns
    bill_of_materials_df = df[['Item', 'Quantity', 'Whse', 'Price', 'Depth', 'BOM Type']].copy()
    bill_of_materials_df.columns = ['component_code', 'quantity', 'warehouse', 'price', 'depth', 'bom_type']
    # Add a column for the finished good (first item in each group with Depth == 1)
    bill_of_materials_df['finished_good_code'] = df['Item'].where(df['Depth'] == 1).ffill()  # Forward fill finished goods

    # Show split DataFrames
    st.subheader("Products Table")
    st.write(products_df)

    st.subheader("BOM Components Table")
    st.write(bom_components_df)

    st.subheader("Bill of Materials Table")
    st.write(bill_of_materials_df)


