import csv
import sys
import psycopg2
from uuid import uuid4
import os

conn = psycopg2.connect(
    dbname="core",
    user="rw",
    password=os.getenv('SCRIPT_DB_PASSWORD'),
    port=5432,
    host="core.cluster-c1gkmwasa8f7.us-east-1.rds.amazonaws.com",
    sslmode='require'
)
cursor = conn.cursor()

def get_bts(manufacturer_id):
    cursor.execute("""
        SELECT 
            customers.id AS customer_id, 
            customers.name AS customer_name, 
            billing_terms.id AS billing_term_id, 
            billing_term_line_items.name AS item_name, 
            billing_term_line_items."itemId" AS integration_id, 
            items.name AS integration_name
        FROM billing_terms 
        JOIN contracts ON billing_terms.contract_id = contracts.id
        JOIN customers ON contracts.customer_id = customers.id
        JOIN billing_term_line_items ON billing_term_line_items.\"billingTermId\" = billing_terms.id
        JOIN items ON items.id = billing_term_line_items.\"itemId\"
        WHERE customers.manufacturer_id = %s 
        AND billing_terms.deleted_at IS NULL
    """, (manufacturer_id,))
    
    rows = cursor.fetchall()
    return rows if rows else []


if __name__ == "__main__":
    manufacturer_id = sys.argv[1]
    output_file = f"bts_for_{manufacturer_id}.csv"
    output_data = get_bts(manufacturer_id)
    headers = ["customer_id", "customer_name", "billing_term_id", "item_name", "integration_id", "integration_name"]
    
    with open(output_file, mode="w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(headers)  # Write column headers
        writer.writerows(output_data)  # Write the data rows
    
    print(f"Data written to {output_file} successfully.")

