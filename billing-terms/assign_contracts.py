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

def contract_exists(customer_id,):
    cursor.execute("SELECT id FROM contracts where customer_id = '{}' and deleted_at IS NULL limit 1".format(customer_id,))
    row = cursor.fetchone()
    return row[0] if row else None # contract_id if contract exists, None otherwise

def csv_to_list_of_dicts(path):
    with open(path, mode='r') as file:
        # DictReader reads each row of the CSV as a dictionary, using the first row as the keys
        reader = csv.DictReader(file)
        return [row for row in reader]


if __name__ == "__main__":
    path = sys.argv[1]
    dicts = csv_to_list_of_dicts(path)
    output_data = []
    counter = 0

    for dict in dicts:
        counter += 1
        customer_id = dict["customer_id"]
        manufacturer_id = dict["manufacturer_id"]
        contract_id = contract_exists(customer_id)

        output_row = dict
        output_row["contract_id"] = contract_id
        output_data.append(output_row)

        if counter % 100 == 0:
            print(f"Processed {counter} contracts")

    conn.commit()
    cursor.close()
    conn.close()

    output_file = path.replace(".csv", "_with_contracts.csv")

    # Write the list of dictionaries to a CSV file
    with open(output_file, mode="w", newline="") as file:
        fieldnames = output_data[0].keys()
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(output_data)

    print(f'Data written to {output_file} successfully')


