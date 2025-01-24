import os
import psycopg2
from psycopg2 import sql

# Database connection
conn = psycopg2.connect(
    dbname="core",
    user="rw",
    password=os.getenv('SCRIPT_DB_PASSWORD'),
    port=5432,
    host="core.cluster-c1gkmwasa8f7.us-east-1.rds.amazonaws.com",
    sslmode='require'
)

# Data to update
updates = [
    {"invoice_id": "10194ff4-c89e-490c-ac39-14fcb11d8cee", "amount": 84.45},
    {"invoice_id": "0710c5e3-a335-4230-bd35-404c19b6413e", "amount": 65.10},
    {"invoice_id": "8afa9ca2-d159-4ab4-8264-6b5fa7db77ce", "amount": 48.83},
    {"invoice_id": "8dc6520b-07d5-4b5c-992b-85142cdf65cf", "amount": 81.37},
    {"invoice_id": "5df15d9f-6329-41db-b3ee-95f4dcbacbf7", "amount": 205.87},
    {"invoice_id": "0485b468-2451-46e9-802e-b05ac6836121", "amount": 62.79},
    {"invoice_id": "5884e327-446f-46ad-b4f7-433c89be6733", "amount": 62.79},
    {"invoice_id": "21791ab5-a411-4339-abd9-bb7cf28a7705", "amount": 32.51},
    {"invoice_id": "8ac612a0-7e76-47b0-8e3e-13a642b9e181", "amount": 17.04},
    {"invoice_id": "e71f7a06-4ea5-48fa-a97c-bb54c92dcd7c", "amount": 110.08}
]

# Update the amounts
try:
    with conn.cursor() as cursor:
        for update_data in updates:
            query = sql.SQL("""
                UPDATE invoices
                SET amount = %s,
                    balance_remaining = %s,
                    mantissa = %s,
                    exp = %s
                WHERE id = %s
            """).format()
            cursor.execute(query, (update_data["amount"], update_data["amount"], update_data["amount"], 0, update_data["invoice_id"]))
        conn.commit()
        print("Invoices updated successfully!")
except Exception as e:
    print(f"An error occurred: {e}")
    conn.rollback()
finally:
    conn.close()
