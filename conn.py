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
        query = "SELECT DISTINCT bp_name FROM customer_master where group_code = 'DISTRIBUTORS';"
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

    def get_top_clients_for_product(self,product, month):
        if month == 'All':
            query = """
                SELECT 
                    customer_name, 
                    SUM(quantity) AS total_quantity_sold, 
                    SUM(sales_amt) AS total_sales_amount
                FROM 
                    sales_per_client
                WHERE 
                    item_description = %s
                GROUP BY 
                    customer_name
                ORDER BY 
                    total_quantity_sold DESC
                LIMIT 5;
            """
            params = [product]
        else:
            query = """
                SELECT 
                    customer_name, 
                    SUM(quantity) AS total_quantity_sold, 
                    SUM(sales_amt) AS total_sales_amount
                FROM 
                    sales_per_client
                WHERE 
                    item_description = %s AND month = %s
                GROUP BY 
                    customer_name
                ORDER BY 
                    total_quantity_sold DESC
                LIMIT 5;
            """
            params = [product, month]

        df = pd.read_sql(query, self.conn, params=params)
        return df
    
    


    def get_all_products(self):
        query = """
            SELECT DISTINCT item_description
            FROM sales_per_client
            ORDER BY item_description;
        """
        df = pd.read_sql(query, self.conn)
        return df['item_description'].tolist()  # Return as a list of product names.
    
    
    # Fetch sales distribution by route for the selected product and month
    def get_sales_distribution_by_route(self,product, month):
        if month == 'All':
            query = """
                SELECT 
                    customer_master.route, 
                    SUM(sales_per_client.quantity) AS total_quantity_sold 
                FROM 
                    sales_per_client
                JOIN 
                    customer_master 
                ON 
                    sales_per_client.customer_code = customer_master.bp_code
                WHERE 
                    sales_per_client.item_description = %s
                GROUP BY 
                    customer_master.route
                ORDER BY 
                    total_quantity_sold DESC;
            """
            params = [product]
        else:
            query = """
                SELECT 
                    customer_master.route, 
                    SUM(sales_per_client.quantity) AS total_quantity_sold 
                FROM 
                    sales_per_client
                JOIN 
                    customer_master 
                ON 
                    sales_per_client.customer_code = customer_master.bp_code
                WHERE 
                    sales_per_client.item_description = %s AND sales_per_client.month = %s
                GROUP BY 
                    customer_master.route
                ORDER BY 
                    total_quantity_sold DESC;
            """
            params = [product, month]

        df = pd.read_sql(query, self.conn, params=params)
        return df
    
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
    
    def get_all_clients_product_sales(self,selected_month):
        if selected_month == 'All':
            query = """
                SELECT item_description, SUM(quantity) AS total_quantity_sold
                FROM sales_per_client
                WHERE customer_code IN (
                    SELECT bp_code FROM customer_master WHERE group_code = 'DISTRIBUTORS'
                )
                GROUP BY item_description
                ORDER BY total_quantity_sold DESC;
            """
            df = pd.read_sql(query, self.conn)
        else:
            query = """
                SELECT item_description, SUM(quantity) AS total_quantity_sold 
                FROM sales_per_client
                WHERE month = %s AND customer_code IN (
                    SELECT bp_code FROM customer_master WHERE group_code = 'DISTRIBUTORS'
                )
                GROUP BY item_description
                ORDER BY total_quantity_sold DESC;
            """
            df = pd.read_sql(query, self.conn, params=[selected_month])
        return df
    
    def get_client_product_sales_detailed(self, client_name):
        query = """
            SELECT 
                sales_per_client.month,
                sales_per_client.item_description,
                SUM(sales_per_client.quantity) AS total_quantity_sold,
                SUM(sales_per_client.sales_amt) AS sales_amt
            FROM 
                sales_per_client
            JOIN 
                customer_master ON sales_per_client.customer_code = customer_master.bp_code
            WHERE 
                customer_master.bp_name = %s
            GROUP BY 
                sales_per_client.month, sales_per_client.item_description;
        """
        df = pd.read_sql(query, self.conn, params=[client_name])
        return df
    
    
    ###### Distributors Page
    # Function to get the top 20 distributors by total sales
    def get_top_20_distributors(self):
        query = """
            SELECT customer_master.bp_name AS distributor_name, 
                SUM(customer_wise_sales.total_ar_invoice) AS total_sales
            FROM customer_wise_sales
            JOIN customer_master ON customer_wise_sales.customer_code = customer_master.bp_code
            WHERE customer_master.group_code = 'DISTRIBUTORS'
            GROUP BY customer_master.bp_name
            ORDER BY total_sales DESC
            LIMIT 20;
        """
        df = pd.read_sql(query, self.conn)
        return df
    
    

    # Function to get total sales by product for top 20 distributors
    def get_top_clients_product_sales(self, client_type, percentage):
    # Step 1: Retrieve all distributors' sales data
        group_code_condition = "group_code IS NOT NULL" if client_type == "All" else "group_code = %s"

        query_top_clients = f"""
            SELECT 
                customer_master.bp_name, 
                SUM(cws.total_ar_invoice) AS total_sales
            FROM 
                customer_wise_sales cws
            JOIN 
                customer_master ON cws.customer_code = customer_master.bp_code
            WHERE 
                {group_code_condition}
            GROUP BY 
                customer_master.bp_name
            ORDER BY 
                total_sales DESC
        """

        # Fetch the top clients
        if client_type == "All":
            df_clients = pd.read_sql(query_top_clients, self.conn)
        else:
            df_clients = pd.read_sql(query_top_clients, self.conn, params=[client_type])

        # Step 2: Calculate how many clients to include based on the selected percentage
        top_clients_limit = int(len(df_clients) * (percentage / 100))
        top_clients_df = df_clients.head(top_clients_limit)  # Select the top clients

        # Step 3: Use the top clients' data to fetch their product sales
        top_client_names = top_clients_df['bp_name'].tolist()  # List of top client names

        # If there are no clients in the result, return an empty DataFrame
        if not top_client_names:
            return pd.DataFrame()

        # Step 4: Dynamically construct the query with placeholders for the `IN` clause
        placeholders = ', '.join(['%s'] * len(top_client_names))
        query_product_sales = f"""
            SELECT 
                spc.month, 
                spc.item_description, 
                SUM(spc.sales_amt) AS total_sales_amt, 
                SUM(spc.quantity) AS total_quantity_sold
            FROM 
                sales_per_client spc
            JOIN 
                customer_master cm ON spc.customer_code = cm.bp_code
            WHERE 
                cm.bp_name IN ({placeholders})
            GROUP BY 
                spc.month, spc.item_description
            ORDER BY 
                spc.month ASC, total_sales_amt DESC;
        """

        # Execute the query and pass the list of top client names as parameters
        df_product_sales = pd.read_sql(query_product_sales, self.conn, params=top_client_names)

        return df_product_sales




    
    
    def get_monthly_clients_product_sales(self, client_type, percentage):
    # Step 1: Get the top clients based on the percentage
        client_condition = ""
        params = []

        # If the client type is not 'All', add the filtering condition for group_code
        if client_type != 'All':
            client_condition = "WHERE customer_master.group_code = %s"
            params.append(client_type)

        # Step 2: Retrieve all relevant clients
        query_top_clients = f"""
            SELECT customer_master.bp_name, 
                SUM(cws.total_ar_invoice) AS total_sales
            FROM customer_wise_sales cws
            JOIN customer_master ON cws.customer_code = customer_master.bp_code
            {client_condition}
            GROUP BY customer_master.bp_name
            ORDER BY total_sales DESC
        """
        
        # Fetch the clients
        df_clients = pd.read_sql(query_top_clients, self.conn, params=params)

        # Step 3: Calculate the limit based on the selected percentage
        top_clients_limit = int(len(df_clients) * (percentage / 100))
        top_clients_df = df_clients.head(top_clients_limit)

        # Step 4: If no clients are found, return an empty DataFrame
        if top_clients_df.empty:
            return pd.DataFrame()

        # Step 5: Extract the list of client names
        top_client_names = top_clients_df['bp_name'].tolist()

        # Step 6: Use the client names in the second query to fetch monthly product sales
        placeholders = ', '.join(['%s'] * len(top_client_names))

        query_product_sales = f"""
            SELECT spc.month, 
                spc.item_description, 
                SUM(spc.sales_amt) AS total_sales_amt, 
                SUM(spc.quantity) AS total_quantity_sold
            FROM sales_per_client spc
            JOIN customer_master cm ON spc.customer_code = cm.bp_code
            WHERE cm.bp_name IN ({placeholders})
            GROUP BY spc.month, spc.item_description
            ORDER BY spc.month ASC, total_sales_amt DESC;
        """

        # Step 7: Execute the query with the top client names as parameters
        df_product_sales = pd.read_sql(query_product_sales, self.conn, params=top_client_names)

        return df_product_sales
    
    
    
    def get_total_sales_by_client_type(self, client_type):
        client_condition = ""
        if client_type != 'All':
            client_condition = "WHERE customer_master.group_code = %s"

        query = f"""
            SELECT SUM(cws.total_ar_invoice) AS total_sales
            FROM customer_wise_sales cws
            JOIN customer_master ON cws.customer_code = customer_master.bp_code
            {client_condition};
        """
        
        if client_type == 'All':
            result = pd.read_sql(query, self.conn)
        else:
            result = pd.read_sql(query, self.conn, params=[client_type])
        
        return result['total_sales'].iloc[0]
    
    
    def get_total_overall_sales(self):
        query = """
            SELECT SUM(total_ar_invoice) AS total_sales
            FROM customer_wise_sales;
        """
        result = pd.read_sql(query, self.conn)
        return result['total_sales'].iloc[0]
    
    
    def get_top_clients(self, client_type, percentage):
    # If client type is 'All', no need to filter by group_code
        client_condition = ""
        params = []

        if client_type != 'All':
            client_condition = "WHERE customer_master.group_code = %s"
            params.append(client_type)

        # Query to get the total sales for each client based on the selected client type
        query_top_clients = f"""
            SELECT customer_master.bp_name AS client_name, 
                SUM(cws.total_ar_invoice) AS total_sales
            FROM customer_wise_sales cws
            JOIN customer_master ON cws.customer_code = customer_master.bp_code
            {client_condition}
            GROUP BY customer_master.bp_name
            ORDER BY total_sales DESC
        """

        # Fetch the top clients
        df_clients = pd.read_sql(query_top_clients, self.conn, params=params)

        # Calculate the number of top clients to select based on the percentage
        top_clients_limit = int(len(df_clients) * (percentage / 100))
        
        # Return the top percentage of clients
        return df_clients.head(top_clients_limit)


#### Distributors ####

    def get_top_20_product_sales(self):
            query = """
                SELECT 
                    spc.item_description, 
                    SUM(spc.sales_amt) AS total_sales_amt,
                    SUM(spc.quantity) AS total_quantity_sold
                FROM 
                    (SELECT customer_master.bp_name, SUM(cws.total_ar_invoice) AS total_sales
                    FROM customer_wise_sales cws
                    JOIN customer_master ON cws.customer_code = customer_master.bp_code
                    WHERE customer_master.group_code = 'DISTRIBUTORS'
                    GROUP BY customer_master.bp_name
                    ORDER BY total_sales DESC
                    LIMIT 20) AS top_20_distributors
                JOIN sales_per_client spc ON spc.customer_code = (SELECT bp_code FROM customer_master WHERE bp_name = top_20_distributors.bp_name)
                GROUP BY spc.item_description
                ORDER BY total_sales_amt DESC;
            """
            df = pd.read_sql(query, self.conn)
            return df

    # Function to get monthly product sales for top 20 distributors
    def get_monthly_product_sales(self):
        query = """
            SELECT 
                spc.month,
                spc.item_description, 
                SUM(spc.sales_amt) AS total_sales_amt,
                SUM(spc.quantity) AS total_quantity_sold
            FROM 
                (SELECT customer_master.bp_name, SUM(cws.total_ar_invoice) AS total_sales
                FROM customer_wise_sales cws
                JOIN customer_master ON cws.customer_code = customer_master.bp_code
                WHERE customer_master.group_code = 'DISTRIBUTORS'
                GROUP BY customer_master.bp_name
                ORDER BY total_sales DESC
                LIMIT 20) AS top_20_distributors
            JOIN sales_per_client spc ON spc.customer_code = (SELECT bp_code FROM customer_master WHERE bp_name = top_20_distributors.bp_name)
            GROUP BY spc.month, spc.item_description
            ORDER BY spc.month ASC, total_sales_amt DESC;
        """
        df = pd.read_sql(query, self.conn)
        return df


    def get_total_distributor_sales(self):
        query = """
            SELECT SUM(customer_wise_sales.total_ar_invoice) AS total_distributor_sales
            FROM customer_wise_sales
            JOIN customer_master ON customer_wise_sales.customer_code = customer_master.bp_code
            WHERE customer_master.group_code = 'DISTRIBUTORS';
        """
        result = pd.read_sql(query, self.conn)
        return result['total_distributor_sales'].iloc[0]

    def get_total_overall_sales(self):
        query = """
            SELECT SUM(total_ar_invoice) AS total_sales
            FROM customer_wise_sales;
        """
        result = pd.read_sql(query, self.conn)
        return result['total_sales'].iloc[0]