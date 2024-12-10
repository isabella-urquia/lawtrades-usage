import csv
import psycopg2
from uuid import uuid4
from datetime import datetime
import sys
import datetime
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

def existsBT(cid):
    cursor.execute("SELECT b.id FROM billing_terms b join contracts c on b.contract_id = c.id where c.id = '{}' and b.start_date = '2024-11-01' and b.created_at < '2024-12-01' limit 1".format(cid))
    row = cursor.fetchone()
    # Transform the result into a dictionary
    return row[0] if row else None

def convert_date(dts):
    return datetime.datetime.strptime(dts, "%Y-%m-%d")

def csv_to_list_of_dicts():
    with open("output27.csv", mode='r') as file:
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

cs = set()
if __name__ == "__main__":
    dicts = csv_to_list_of_dicts()
    
    for dict in dicts:
        billing_term_id = uuid4()
        contract_id = dict["contract_id"]
        if dict["start_date"] == '' or dict["start_date"] == None:
            continue

        if existsBT(contract_id) != None:
            print("billing term exists for " + contract_id)
            continue

        cs.add(contract_id)
        start_date = convert_date(dict["start_date"])
        end_date = convert_date(dict["end_date"])
        billing_type = dict["billing_type"]
        is_recurring = False
        due_interval = int(dict["due_interval"])
        net_payment_terms = int(dict["net_payment_terms"])
        due_interval_unit = dict["due_interval_unit"]
        is_arrears = True

        billing_line_item_note = dict['billing_line_item_note']

        billing_term_line_item_id = uuid4()
        name = dict["billing_line_item_name"]
        quantity = 0 if dict["quantity"] == '' else float(dict["quantity"])

        item_id = dict['item_id']
        pricing_id = uuid4()
        tier = 0
        currency = "usd"
        mantissa = int(float(dict["price"].replace("$", "").replace(",", "").strip()) * 100)
        exponent = -2

        condition_operator = "NOT_OPERATOR" if "conditionOperator" not in dict or dict["conditionOperator"] == '' else dict["conditionOperator"]
        condition_value = 0 if "conditionValue" not in dict or dict["conditionValue"] == '' else int(dict["conditionValue"])

        print(billing_term_id.hex, contract_id, billing_type, start_date, end_date, is_recurring, due_interval, net_payment_terms, due_interval_unit, True)
        print(billing_term_line_item_id.hex, billing_term_id.hex, name, "", quantity)
        print (pricing_id.hex, billing_term_id.hex, "", tier, "usd", str(mantissa), str(exponent), condition_value, condition_operator)
        cursor.execute("INSERT INTO billing_terms (id, contract_id, billing_type, start_date, end_date, is_recurring, due_interval, net_payment_terms, due_interval_unit, is_arrears, duration, date_offset, invoice_type) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", (billing_term_id.hex, contract_id, billing_type, start_date, end_date, is_recurring, due_interval, net_payment_terms, due_interval_unit, True, 1, -1, "INVOICE"))
        cursor.execute("INSERT into billing_term_line_items (id, \"billingTermId\", name, note, quantity, \"itemId\") values (%s, %s, %s, %s, %s, %s)", (billing_term_line_item_id.hex, billing_term_id.hex, name, billing_line_item_note, quantity, item_id))
        cursor.execute("INSERT into pricings (id, \"billingTermId\", name, tier, currency, mantissa, exponent, condition_value, condition_operator) values (%s, %s, %s, %s, %s, %s, %s, %s, %s)", (pricing_id.hex, billing_term_id.hex, "", tier, "usd", str(mantissa), str(exponent), condition_value, condition_operator))

        if (billing_type.lower()) == "unit_price":
            raise Exception("not implemented")

    conn.commit()
cursor.close()
conn.close()

print(cs)