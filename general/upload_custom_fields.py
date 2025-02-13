import csv
import psycopg2
from uuid import uuid4
import os
import sys
import json
import sys

conn = psycopg2.connect(
    dbname="core",
    user="rw",
    password=os.getenv('SCRIPT_DB_PASSWORD'),
    port=5432,
    host=os.getenv('DATABASE_URL'),
    sslmode='require'
)
cursor = conn.cursor()

def csv_to_list_of_dicts(filename):
    with open(filename, mode='r') as file:
        reader = csv.DictReader(file)
        return [row for row in reader]
    
if __name__ == "__main__":
    dicts = csv_to_list_of_dicts(str(sys.argv[1]))

    manufacturer_custom_fields_id_1 = uuid4()
    merchant_id = sys.argv[2]
    cursor.execute("INSERT into manufacturer_custom_fields (id, manufacturer_id, name, send_to_customer, send_to_erp) values (%s, %s, %s, %s, %s) returning id", (manufacturer_custom_fields_id_1.hex, merchant_id, 'Segment', True, False))
    new_manufacturer_custom_field = cursor.fetchone()[0]
    
    for dict in dicts:
        customer_id = dict["customer_id"]
        segment = dict["segment"]
        customer_custom_field_default_id_1 = uuid4()
        cursor.execute("INSERT into customer_custom_field_defaults (id, manufacturer_field_id, default_value, customer_id) values (%s, %s, %s, %s) returning id", (customer_custom_field_default_id_1.hex,new_manufacturer_custom_field, segment, customer_id))
    conn.commit()

cursor.close()
conn.close()
