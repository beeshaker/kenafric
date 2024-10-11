import mysql.connector
from mysql.connector import Error
import pandas as pd



class MySQLDatabase():
    def __init__(self):
        self.host = "digiage.co.ke"
        self.user = "digiagec_vscu"
        self.password = "NN9RqO0JsU~w"
        self.database = "digiagec_kenafric"
        self.conn = None
        self.cursor = None
        
        

    def connect(self):
        """Establish a connection to the database."""
        try:
            self.conn = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database
            )
            if self.conn.is_connected():
                self.cursor = self.conn.cursor(buffered=True)
                print("Connection to MySQL database successful")
        except Error as e:
            print(f"Error: {e}")
            self.conn = None

    def close(self):
        """Close the connection to the database."""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
            print("Connection closed")
            
    def get_top_customers(self):
        query = """
        SELECT customer_name, SUM(total_ar_invoice) as total_sales 
        FROM customer_wise_sales 
        GROUP BY customer_name 
        ORDER BY total_sales DESC 
        LIMIT 5
        """
        df = pd.read_sql(query, self.conn)
        return df

    # Query top 5 routes by total sales
    def get_top_routes(self):
        query = """
        SELECT route, SUM(amount) as total_sales 
        FROM route_wise_sales 
        GROUP BY route 
        ORDER BY total_sales DESC 
        LIMIT 5
        """
        df = pd.read_sql(query, self.conn)
        return df

    # Query top 5 items by total sales
    def get_top_items(self):
        query = """
        SELECT item_description, SUM(sales_amt) as total_sales 
        FROM item_wise_sales 
        GROUP BY item_description 
        ORDER BY total_sales DESC 
        LIMIT 5
        """
        df = pd.read_sql(query, self.conn)
        return df
            
    
    def get_top_customers_sales_per_month(self):
        # Step 1: Get top 5 customers based on total sales
        top_customers_query = """
        SELECT customer_name 
        FROM customer_wise_sales
        GROUP BY customer_name
        ORDER BY SUM(total_ar_invoice) DESC
        LIMIT 5
        """
        top_customers_df = pd.read_sql(top_customers_query, self.conn)
        top_customers_list = top_customers_df['customer_name'].tolist()

        # Step 2: Dynamically build SQL query to get monthly sales for those top 5 customers
        placeholders = ', '.join(['%s'] * len(top_customers_list))  # Create placeholders for IN clause
        query = f"""
        SELECT customer_name, month, SUM(total_ar_invoice) as total_sales
        FROM customer_wise_sales
        WHERE customer_name IN ({placeholders})
        GROUP BY customer_name, month
        ORDER BY customer_name, month;
        """
        
        # Execute query with top customer names as parameters
        df = pd.read_sql(query, self.conn, params=top_customers_list)
        return df

    def get_route_sales_per_month(self):
        query = """
        SELECT route, month, SUM(amount) as total_sales
        FROM route_wise_sales
        GROUP BY route, month
        ORDER BY route, month;
        """
        df = pd.read_sql(query, self.conn)
        return df
    
    # New method to get customer sales per route
    def get_customer_sales_per_route(self):
        query = """
        SELECT * FROM (
            SELECT 
                route_wise_sales.route, 
                customer_master.bp_name AS customer_name, 
                customer_wise_sales.month, 
                SUM(customer_wise_sales.total_ar_invoice) AS total_sales,
                ROW_NUMBER() OVER (PARTITION BY route_wise_sales.route ORDER BY SUM(customer_wise_sales.total_ar_invoice) DESC) AS rank
            FROM 
                customer_wise_sales
            JOIN 
                customer_master ON customer_wise_sales.customer_code = customer_master.bp_code
            JOIN 
                route_wise_sales ON customer_master.route = route_wise_sales.route
            GROUP BY 
                route_wise_sales.route, customer_master.bp_name, customer_wise_sales.month
        ) AS ranked_customers
        WHERE rank <= 5
        ORDER BY route, month;
        """
        df = pd.read_sql(query, self.conn)
        return df
    
    
    def get_all_clients(self):
        query = "SELECT DISTINCT bp_name FROM customer_master;"
        df = pd.read_sql(query, self.conn)
        return df['bp_name'].tolist()

    def get_client_sales(self, client_name):
        query = """
        SELECT 
            customer_wise_sales.month, 
            SUM(customer_wise_sales.total_ar_invoice) AS total_sold_to_client, 
            customer_master.route
        FROM 
            customer_wise_sales
        JOIN 
            customer_master ON customer_wise_sales.customer_code = customer_master.bp_code
        WHERE 
            customer_master.bp_name = %s
        GROUP BY 
            customer_wise_sales.month, customer_master.route;
        """
        df = pd.read_sql(query, self.conn, params=[client_name])
        return df

    def get_route_sales_for_client(self, route, month):
        query = """
        SELECT SUM(amount) AS total_route_sales
        FROM route_wise_sales
        WHERE route = %s AND month = %s;
        """
        df = pd.read_sql(query, self.conn, params=[route, month])

        # If the result is None or empty, return 0, otherwise return the total sales
        return df['total_route_sales'].values[0] if not df.empty and pd.notna(df['total_route_sales'].values[0]) else 0

    def get_client_product_sales(self, client_name, selected_month=None):
        query = """
            SELECT 
                customer_name, 
                item_description, 
                SUM(quantity) AS total_quantity_sold 
            FROM 
                sales_per_client
            WHERE 
                customer_name = %s
        """
        # If a specific month is selected, filter by that month
        if selected_month and selected_month != 'All':
            query += " AND month = %s GROUP BY customer_name, item_description"
            df = pd.read_sql(query, self.conn, params=[client_name, selected_month])
        else:
            query += " GROUP BY customer_name, item_description"
            df = pd.read_sql(query, self.conn, params=[client_name])
        
        return df
