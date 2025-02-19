import csv
import psycopg2
from uuid import uuid4
import os
import sys
import json

conn = psycopg2.connect(
    dbname="core",
    user="rw",
    password=os.getenv('SCRIPT_DB_PASSWORD'),
    port=5432,
    host="core.cluster-cizo3akkr249.us-east-1.rds.amazonaws.com",
    sslmode='require'
)
cursor = conn.cursor()

def csv_to_list_of_dicts(filename):
    with open(filename, mode='r') as file:
        reader = csv.DictReader(file)
        return [row for row in reader]
    
if __name__ == "__main__":
    dicts = {}
    output_csv = []

    merchant_name = "Findigs"
    merchant_id = "2972d5be-f370-acc6-978f-8d4ec4eb5f24"

    dicts = csv_to_list_of_dicts(("/Users/chiragdas/Downloads/Create Findigs Customers bulk - 2.18.24 - Create Customers.csv"))
        
    for dict in dicts:
        customer_name = dict["customer_name"]
        first_name = dict.get("first_name", "None")
        last_name = dict.get("last_name", "None")
        email = dict["email"]
        address_line_1 = dict["billing_address_street_address_line_1"]
        address_line_2 = dict.get("Street address line 2", "None")
        city = dict["billing_address_street_address_city"]
        state = dict["billing_address_street_address_state"]
        zip_code = dict["billing_address_street_address_zip_code"]
        country = dict["billing_address_street_address_country"]
        external_id = dict["external_id"]

        customer_id = uuid4()
        address_id = uuid4()
        contacts_id = uuid4()

        cursor.execute("INSERT into addresses (id, manufacturer_id, address_line1, address_line2, city, state, country, zip) values (%s, %s, %s, %s, %s, %s, %s, %s) returning id", (address_id.hex, merchant_id, address_line_1, address_line_2, city, state, country, zip_code))
        new_address_id = cursor.fetchone()[0]

        cursor.execute("INSERT into customers (id, manufacturer_id, name, name_with_prefix) values (%s, %s, %s, %s) returning id", (customer_id.hex, merchant_id, customer_name, customer_name))
        new_parent_customer_id = cursor.fetchone()[0]

        cursor.execute("INSERT into customer_address (customer_id, address_id, is_default_billing, is_default_shipping) values (%s, %s, %s, %s)", (new_parent_customer_id, new_address_id, True, True))

        cursor.execute("INSERT into customer_external_ids (customer_id, external_id,source_type,customer_external_type) values (%s, %s, %s, %s)", (customer_id.hex, external_id, 'QUICKBOOKS', 'VENDOR'))


        cursor.execute("INSERT into contacts_v2 (id, first_name, last_name, customer_id, email) values (%s, %s, %s, %s, %s) returning id", (contacts_id.hex, first_name, last_name, new_parent_customer_id, email))
        new_parent_contact_id = cursor.fetchone()[0]

        cursor.execute("UPDATE customers set primary_billing_contact_id = %s where id = %s and deleted_at is NULL", (new_parent_contact_id, new_parent_customer_id))

        print("New address for parent customer: " + new_address_id)
        print("New parent customer: " + new_parent_customer_id)
        print("New contact for parent customer: " + new_parent_contact_id)

        output_csv.append({"customer_id": new_parent_customer_id, "name": customer_name})
    conn.commit()

    # Output file in CSV format
    filename = 'Feb_Customers_created.csv'
    # Writing to the CSV file
    with open(filename, mode='w', newline='') as file:
        fields = ["customer_id", "name", "contact_id"]
        writer = csv.DictWriter(file, fieldnames=fields)

        # Write the header
        writer.writeheader()

        # Write the data rows
        writer.writerows(output_csv)

    print(f'Data written to {filename} successfully.')
cursor.close()
conn.close()



