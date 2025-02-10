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

def csv_to_list_of_dicts(path):
    with open(path, mode='r') as file:
        # DictReader reads each row of the CSV as a dictionary, using the first row as the keys
        reader = csv.DictReader(file)
        return [row for row in reader]
    
def customer_exists(customer_id,):
    cursor.execute("SELECT id FROM customers where id = '{}' AND deleted_at IS NULL limit 1".format(customer_id,))
    row = cursor.fetchone()
    return True if row else False # True if customer exists, False otherwise

def add_cc_email(customer_id, email):
    try:
        new_id = uuid4().hex
        cursor.execute(
            "INSERT INTO contacts_v2 (id, customer_id, email, source, \"isPrimaryContactForSource\", email_sending_type) VALUES (%s, %s, %s, %s, %s, %s)",
            (new_id, customer_id, email, "TABS", "FALSE", "CC")
        )
        
        if cursor.rowcount > 0: # Check if a row was inserted
            return True
        else:
            return False # No rows affected, possibly a failed insertion

    except psycopg2.Error as e: # Catch database-related errors
        print(f"Database error: {e}")
        return False
    
if __name__ == "__main__":
    path = sys.argv[1]
    rows = csv_to_list_of_dicts(path)
    failed_rows = []

    for row in rows:
        customer_id = row['customer_id']
        if customer_exists(customer_id):
            if row['cc_email_1']:
                cc_email = row['cc_email_1']
                if not add_cc_email(customer_id, cc_email): # If an error occurred, add to failed_rows
                    failed_rows.append(row)
            if row['cc_email_2']:
                cc_email = row['cc_email_2']
                if not add_cc_email(customer_id, cc_email): # If an error occurred, add to failed_rows
                    failed_rows.append(row)
            if row['cc_email_3']:
                cc_email = row['cc_email_3']
                if not add_cc_email(customer_id, cc_email): # If an error occurred, add to failed_rows
                    failed_rows.append(row)
    conn.commit()
    cursor.close()
    conn.close()
    
    if failed_rows:
        with open("failed_rows.csv", mode="w", newline="") as file:
            fieldnames = failed_rows[0].keys()
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(failed_rows)
        print("Failed rows were added to failed_rows.csv")




