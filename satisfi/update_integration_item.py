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

def integration_item_id(name):
    cursor.execute("""
        SELECT id FROM items WHERE manufacturer_id = 'd797a8dc-6ad9-49f7-9823-7d43a49ab296' AND name = %s
    """, (name,))
    row = cursor.fetchone()
    return row[0] if row else None

def csv_to_list_of_dicts(path):
    with open(path, mode='r') as file:
        # DictReader reads each row of the CSV as a dictionary, using the first row as the keys
        reader = csv.DictReader(file)
        return [row for row in reader]

def change_integration_item(ii_id, bt_id):
    cursor.execute("""
        UPDATE billing_term_line_items SET \"itemId\" = %s WHERE \"billingTermId\" = %s
    """, (ii_id, bt_id))

def update_invoice_item(ii_id, bt_id):
    cursor.execute("""
        UPDATE invoice_items SET \"itemId\" = %s WHERE \"billingTermId\" = %s
    """, (ii_id, bt_id))


if __name__ == "__main__":
    path = sys.argv[1]
    dicts = csv_to_list_of_dicts(path)
    failed = []
    output_data = []

    for dict in dicts:
        bt_id = dict["bt_id"]
        integration_item_name = dict["integration_item"]
        if not integration_item_name:
            continue
        ii_id = integration_item_id(integration_item_name)

        if ii_id:
            change_integration_item(ii_id, bt_id)
            update_invoice_item(ii_id, bt_id)
            new_row = dict
            new_row["new_ii_id"] = ii_id
            output_data.append(new_row)
        else:
            failed.append(dict)

    conn.commit()
    cursor.close()
    conn.close()

    output_file = path.replace(".csv", "_with_new_ii_ids.csv")

    with open(output_file, mode="w", newline="") as file:
        fieldnames = output_data[0].keys()
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(output_data)

    if failed:
        failed_file = path.replace(".csv", "_failed.csv")
        with open(failed_file, mode="w", newline="") as file:
            fieldnames = failed[0].keys()
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(failed)

    print(f'Data written to files successfully')