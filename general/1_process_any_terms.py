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

def event_exists(storeid):
    query = """
        SELECT id 
        FROM event_types_v2 
        WHERE manufacturer_id = %s 
        AND name = %s 
        AND deleted_at IS NULL 
        ORDER BY created_at DESC 
        LIMIT 1
    """
    cursor.execute(query, ('dd4337a4-6573-310b-b071-ec8e1b68a193', storeid))
    row = cursor.fetchone()
    # Transform the result into a dictionary
    return row[0] if row else None

def convert_date(dts):
    return datetime.datetime.strptime(dts, "%m/%d/%Y")

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

cs = set()
if __name__ == "__main__":
    # Add filenames here for each csv file
    file_names = []
    for file_name in file_names:
        print("Processing " + file_name)
        path = "<ADD PATH TO FOLDER HERE>" + file_name + ".csv"
        dicts = csv_to_list_of_dicts(path)
        
        for dict in dicts:
            billing_term_id = uuid4()
            contract_id = dict["contract_id"]
            if dict["start_date"] == '' or dict["start_date"] == None:
                continue
            cs.add(contract_id)
            start_date = convert_date(dict["start_date"])
            end_date = convert_date(dict["end_date"])
        
            # Use other columns if they exist, fallback to start_date/end_date
            rev_sched_start_date = (
                convert_date(dict["revenue_schedule_start_date"])
                if "revenue_schedule_start_date" in dict.keys() and dict["revenue_schedule_start_date"] else start_date
            )
            rev_sched_end_date = (
                convert_date(dict["revenue_schedule_end_date"])
                if "revenue_schedule_end_date" in dict.keys() and dict["revenue_schedule_end_date"] else end_date
            )

            # Extract revenue recognition column; use None if empty
            revenue_recognition = (
                dict["revenue_recognition"].strip() 
                if "revenue_recognition" in dict.keys() and dict["revenue_recognition"] else None
            )

            billing_type = dict["billing_type"]
            is_recurring = dict['is_recurring'] == 'TRUE'
            due_interval = int(dict["due_interval"] if dict["due_interval"] != '' else 1)
            net_payment_terms = int(dict["net_payment_terms"])
            due_interval_unit = dict["due_interval_unit"].upper() if dict["due_interval_unit"] != '' else "NONE"

            duration = int(dict["duration"])

            is_arrears = dict["is_arrears"] == 'TRUE'

            customer_id = dict['customer_id']

            # billing_line_item_note = dict["billing_line_item_note"]

            billing_term_line_item_id = uuid4()
            name = dict["billing_line_item_name"]
            description = dict["billing_line_item_note"]

            event_id = event_exists(dict['event_to_track'])
            if (billing_type != 'FLAT_PRICE' and event_id == None):
                print("No event")
                continue
            # event_name = event_exists(dict['event_to_track'])

            quantity = dict["Quantity"].replace("$", "").replace(",", "").strip() if dict["Quantity"] != '' else 0

            item_id = dict['integration_item_id'] if 'integration_item_id' in dict and dict['integration_item_id'] != '' else None

            # item_id = None
            pricing_id = uuid4()
            tier = 0
            currency = "usd"
            mantissa = float(dict['discounted pricing'].replace("$", "").replace(",", "").strip())
            exponent = 0

            # event_type_id = None

            condition_operator = "NOT_OPERATOR" if "conditionOperator" not in dict or dict["conditionOperator"] == '' else dict["conditionOperator"]
            condition_value = 0 if "conditionValue" not in dict or dict["conditionValue"] == '' else int(dict["conditionValue"])

            rp_id = uuid4()
            rs_id = uuid4()

            print(billing_term_id.hex, contract_id, billing_type, start_date, end_date, is_recurring, due_interval, net_payment_terms, due_interval_unit, is_arrears)
            print(billing_term_line_item_id.hex, billing_term_id.hex, name, "", quantity)
            print(pricing_id.hex, billing_term_id.hex, "", tier, "usd", str(mantissa), str(exponent), condition_value, condition_operator)
            cursor.execute("INSERT into revenue_product (id, customer_id) values (%s, %s)", (rp_id.hex, customer_id))
            cursor.execute("INSERT into revenue_schedule (id, revenue_product_id, service_start_date, service_end_date) values (%s, %s, %s, %s, %s)", (rs_id.hex, rp_id.hex, rev_sched_start_date, rev_sched_end_date, revenue_recognition))
            cursor.execute("INSERT INTO billing_terms (id, contract_id, billing_type, start_date, end_date, is_recurring, due_interval, net_payment_terms, due_interval_unit, is_arrears, event_type_id, duration, revenue_schedule_id) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", (billing_term_id.hex, contract_id, billing_type, start_date, end_date, is_recurring, due_interval, net_payment_terms, due_interval_unit, is_arrears, event_id, duration, rs_id.hex))
            cursor.execute("INSERT into billing_term_line_items (id, \"billingTermId\", name, note, quantity, \"itemId\") values (%s, %s, %s, %s, %s, %s)", (billing_term_line_item_id.hex, billing_term_id.hex, name, description, quantity, item_id))
            cursor.execute("INSERT into pricings (id, \"billingTermId\", name, tier, currency, mantissa, exponent, condition_value, condition_operator) values (%s, %s, %s, %s, %s, %s, %s, %s, %s)", (pricing_id.hex, billing_term_id.hex, "", tier, "usd", str(mantissa), str(exponent), condition_value, condition_operator))

        # if (billing_type.lower()) == "unit_price":
        #     event_type = snake_case(name)
        #     event_type_id = uuid4()
        #     cursor.execute("INSERT INTO event_types (id, name, display_name, unit_type_id) values (%s, %s, %s, %s)", (event_type_id.hex, event_type, name, '03c5a9a1-8933-4227-8087-6ad2d936ffa3'))
        #     cursor.execute("INSERT into billing_term_event_types (id, billing_term_id, event_type_id, field_to_sum) values (%s,%s,%s,%s)", (uuid4().hex, billing_term_id.hex,event_type_id.hex, ""))
        #     current_date = start_date + relativedelta(days=1)

        #     while current_date <= end_date:
        #         cursor.execute("INSERT INTO events (id, time, event_type_id, unit_id, metadata) values (%s, %s, %s, %s, %s::jsonb)", (uuid4().hex, current_date, event_type_id.hex, "9df5bb64-c374-4a9e-bd90-c99680cb8f9a", json.dumps({})))
        #         current_date += relativedelta(months=1)
    conn.commit()
cursor.close()
conn.close()

print(cs)

# Alkira files path

