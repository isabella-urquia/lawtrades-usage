import csv
import psycopg2
from uuid import uuid4
from datetime import datetime
from dateutil.relativedelta import relativedelta
from dateutil.parser import parse
import json
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

def csv_to_list_of_dicts(path):
    with open(path, mode='r') as file:
        # DictReader reads each row of the CSV as a dictionary, using the first row as the keys
        reader = csv.DictReader(file)
        return [row for row in reader]
    
def snake_case(s):
    # Replace / and - with _
    s = s.replace("/", "").replace("-", "")
    
    # Split the string by spaces and make it lowercase
    words = s.split()
    words = [word.lower() for word in words]
    
    # Join the words with underscores
    return "_".join(words)

if __name__ == "__main__":
    # Given filke with customer names, map all to their ids in our database (output file has customer_id, vendor_id, customer_name)
    path = "<PATH TO CUSOTMERS NAMES FILE>"
    dicts = csv_to_list_of_dicts(path)
    new_list_of_dicts = []
    
    for dict in dicts:
        customer_name = dict["customer_name"]

        cursor.execute("SELECT id FROM customers WHERE name = %s AND manufacturer_id='76310fa7-758a-4062-307e-a9e75497b770'", (customer_name,))
        customer_id = cursor.fetchone()
        customer_id = customer_id[0] if customer_id else None
        new_list_of_dicts.append({
            "customer_id": customer_id,
            "vendor_id": dict["vendor_id"],
            "customer_name": customer_name
        })
    
    filename = 'output_findigs_customers.csv'
    # Writing to the CSV file
    with open(filename, mode='w', newline='') as file:
        # Assuming all dictionaries have the same keys, use the keys from the first dictionary
        fields = new_list_of_dicts[0].keys()
        writer = csv.DictWriter(file, fieldnames=fields)

        # Write the header
        writer.writeheader()

        # Write the data rows
        writer.writerows(new_list_of_dicts)

    print(f'Data written to {filename} successfully.')

    # After all customer ids where found, add them to customers_external_ids table with their external ids
    path = "customers_with_external_ids.csv"
    dicts = csv_to_list_of_dicts(path)

    for dict in dicts:
        customer_id = dict["customer_id"]
        external_id = dict["vendor_id"]
        cursor.execute("SELECT customer_id FROM customer_external_ids WHERE customer_id = %s AND external_id = %s", (customer_id, external_id))
        if cursor.fetchone():
            continue
        cursor.execute("INSERT into customer_external_ids (customer_id, external_id,source_type,customer_external_type) values (%s, %s, %s, %s)", (customer_id, external_id, 'QUICKBOOKS', 'VENDOR'))
    conn.commit()
    print("Done inserting data to customer_external_ids table")
cursor.close()
conn.close()
