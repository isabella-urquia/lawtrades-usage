import csv
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

manufacturer_id = "006531c4-3718-4b25-9136-00bb8534cd31" # LuxSci

def customer_exists(customer_id):
    if not customer_id:
        return None
    cursor.execute("SELECT id FROM customers where id = '{}' and manufacturer_id = '{}' limit 1".format(customer_id, manufacturer_id))
    row = cursor.fetchone()
    return row[0] if row else None # id if customer exists, None otherwise

def csv_to_list_of_dicts(path):
    with open(path, mode='r') as file:
        # DictReader reads each row of the CSV as a dictionary, using the first row as the keys
        reader = csv.DictReader(file)
        return [row for row in reader]


if __name__ == "__main__":
    path = "/Users/mzisbrod/Documents/GitHub/tabs-fde/luxsci/luxsci_dec_2023.csv"
    dicts = csv_to_list_of_dicts(path)
    output_data = []

    contracts = [] # List of dictionaries of all added contracts
    customer_contracts = {} # Dict of {customer_id: contract_id} mapping
    customers_to_create = []
    aws_s3_key = "3446ddcc-2679-4f17-a71b-38458ea67961/Tabs_blank_contract.pdf" # Blank contract
    
    for dict in dicts:
        input_customer_id = dict["customer_id"]
        customer_id = customer_exists(input_customer_id)

        # If customer exists, create contract for it
        if customer_id:
            if customer_id not in customer_contracts:
                # Customer exists and contract wasn't created for this customer yet
                contract_id = uuid4()
                cursor.execute("INSERT INTO contracts (id, customer_id, uploader_id, aws_s3_key, manufacturer_id, name, file_name, last_modified_by, last_modified_by_type, deleted_at, bulk_upload_id, contract_summary) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", 
                        (contract_id.hex, customer_id, None, aws_s3_key, manufacturer_id, None, None, None, None, None, None, None))
                customer_contracts[customer_id] = contract_id

                output_data.append({
                    "contract_id": contract_id.hex,
                    "customer_id": customer_id,
                    "customer_name": dict["customer_name"],
                    "invoice_date": dict["invoice_date"],
                    "invoice_id": dict["invoice_id"],
                    "type_description": dict["type_description"],
                    "description": dict["description"],
                    "amount": dict["amount"],
                    "revenue_start_date": dict["revenue_start_date"]
                })

        else:
            if input_customer_id and input_customer_id not in customers_to_create:
                customers_to_create.append(input_customer_id)

    conn.commit()
cursor.close()
conn.close()

output_file = "luxsci_dec_2023_contracts.csv"

# Write the list of dictionaries to a CSV file
with open(output_file, mode="w", newline="") as file:
    # Get the column headers from the keys of the first dictionary
    fieldnames = output_data[0].keys()
    
    # Create a DictWriter object
    writer = csv.DictWriter(file, fieldnames=fieldnames)
    
    # Write the header row
    writer.writeheader()
    
    # Write the data rows
    writer.writerows(output_data)

print(f'Data written to {output_file} successfully')

print(f'Customers to create: {customers_to_create}')

