import csv
import psycopg2
from uuid import uuid4
from datetime import datetime
import sys
from dateutil.relativedelta import relativedelta
from dateutil.parser import parse
import json
import os

conn = psycopg2.connect(
    dbname="core",
    user="read",
    password=os.getenv('SCRIPT_DB_PASSWORD'),
    port=5432,
    host="core-1.c1gkmwasa8f7.us-east-1.rds.amazonaws.com",
    sslmode='require'
)
cursor = conn.cursor()

first_day_of_month = datetime.now().replace(day=1)
first_day_of_next_month = (first_day_of_month + relativedelta(months=1)).replace(day=1)
last_day_of_current_month = first_day_of_next_month - relativedelta(days=1)

first_day_this_month_str = first_day_of_month.strftime('%Y-%m-%d')
first_day_next_month_str = first_day_of_next_month.strftime('%Y-%m-%d')
last_day_this_month_str = last_day_of_current_month.strftime('%Y-%m-%d')

start_date = first_day_this_month_str
end_date = last_day_this_month_str

# start_date = '2024-12-01'
# end_date = '2024-12-31'

def existsBT(cid):
    cursor.execute("SELECT b.id FROM billing_terms b JOIN contracts c ON b.contract_id = c.id WHERE c.id = %s AND b.start_date = %s AND c.deleted_at is null AND b.deleted_at is null limit 1", (cid, start_date))

    row = cursor.fetchone()
    # Transform the result into a dictionary
    return row[0] if row else None

def contract_id(vid):
    cursor.execute("SELECT c.id FROM contracts c join customers cu on c.customer_id = cu.id join customer_external_ids cei on cei.customer_id = cu.id where cu.manufacturer_id = '76310fa7-758a-4062-307e-a9e75497b770' and cei.source_type = 'QUICKBOOKS' and cei.customer_external_type='VENDOR' and c.deleted_at is NULL and cei.external_id = '{}' limit 1".format(vid))
    row = cursor.fetchone()
    # Transform the result into a dictionary
    return row[0] if row else None

def csv_to_list_of_dicts(filename):
    with open(filename, mode='r') as file:
        # DictReader reads each row of the CSV as a dictionary, using the first row as the keys
        reader = csv.DictReader(file)
        return [row for row in reader]

import pandas


if __name__ == "__main__":

    df = pandas.read_csv("/Users/chiragdas/Downloads/findigs_monthly_activity_2024_12_01 (1).csv")
    print('dfff', df)
    dicts = csv_to_list_of_dicts("/Users/chiragdas/Downloads/findigs_monthly_activity_2024_12_01 (1).csv")
    vendor_dict = {}

    for dict in dicts:
        total_remit = 0
        lines = []

        # has_pet_ver_pm_share = float(dict["pet_verification_pm_share"])
        application_remit = float(dict["total_application_pm_share"])
        pet_remit = float(dict['total_pet_verification_pm_share'])
        decision_assist_fees = float(dict['total_decision_assist_fees_collected'])
        subscription_fees = float(dict['total_subscription_fees_collected'])
        total_remit = application_remit + pet_remit - decision_assist_fees - subscription_fees
        total_apps_submitted = int(dict['total_apps_submitted'])
        total_pet_verifications = int(dict['total_pets_charged'])
        total_decision_assists = int(0 if dict['total_decision_assist_apps'] == '' else dict['total_decision_assist_apps'])
        total_apps_run = int(dict['total_apps_run'])

        manual = float(dict['manual_adjustments'] if dict['manual_adjustments'] != '' else 0)
        total_processing_fees = float(0 if dict['total_payment_processing_fees'] == '' else dict['total_payment_processing_fees'])


        flexible = dict['pricing_model_type'] == 'per_application_flexi'

        if (application_remit != 0):
            lines.append(
                {
                    "name": "Application Remittance", 
                    "companyname": dict['portfolio_name'],
                    "amount": -1.0*application_remit,
                    "qty": total_apps_submitted if not flexible else 1, 
                    "note": "" if not flexible else str(total_apps_submitted) + " applications submitted, " + str(total_apps_run) + " applications run",
                    "item_id": 'aa3afdd1-5c61-4772-a91a-f7c5eee536bd'
                }
            )
        if (pet_remit != 0):
            lines.append(
                {
                    "name": "Pet Verification Remittance", 
                    "companyname": dict['portfolio_name'],
                    "amount": -1.0*pet_remit,
                    "qty": total_pet_verifications,
                    "note": "",
                    "item_id": "edaf45fd-527c-4879-8fc7-f42355a8d5fd"
                }
            )
        if (decision_assist_fees != 0):
            lines.append(
                {
                    "name": "Decision Assist Fees", 
                    "companyname": dict['portfolio_name'],
                    "amount": decision_assist_fees,
                    "qty": total_decision_assists,
                    "note": "",
                    "item_id": '06e39cc3-f6b0-41ee-81ab-610120fd3514'
                }
            )
        if (manual != 0):
            lines.append({
                    "name": "Manual Adjustment", 
                    "companyname": dict['portfolio_name'],
                    "amount": manual,
                    "qty": 1,
                    "note": dict['notes'],
                    "item_id": 'aa3afdd1-5c61-4772-a91a-f7c5eee536bd'
                })
        if (total_processing_fees != 0):
            lines.append(
                {
                    "name": "Payment Processing Fees", 
                    "companyname": dict['portfolio_name'],
                    "amount": total_processing_fees,
                    "qty": 1, 
                    "note": "" if not flexible else str(total_apps_submitted) + " applications submitted, " + str(total_apps_run) + " applications run",
                    "item_id": 'aa3afdd1-5c61-4772-a91a-f7c5eee536bd'
                }
            )

        if dict['quickbooks_vendor_id'] in vendor_dict:
            vals = vendor_dict[dict['quickbooks_vendor_id']]
            vals.extend(lines)
            vendor_dict[dict['quickbooks_vendor_id']] = vals
        else:
            vendor_dict[dict['quickbooks_vendor_id']] = lines
    
    dict_csvs = []

    for multiple_lines in vendor_dict:
        total = 0.0
        for line in vendor_dict[multiple_lines]:
            total = total + line['amount']
        
        if (total < 0):
            print(multiple_lines + " has negative amount")
            continue
           
        for line in vendor_dict[multiple_lines]:
            note = ""
            if (len(vendor_dict[multiple_lines]) > 1):
                note = line['companyname']
            if (line['note'] != ''):
                if note != '':
                    note = note + " - " + line['note']
                else:
                    note = line['note']
            contract = contract_id(multiple_lines)
            if contract == None:
                print("no contract for " + multiple_lines)
                continue

            bt_exists = existsBT(contract)
            if (bt_exists):
                print("bt_exists for " + contract)
                continue
            csv_dict = {
                "contract_id": contract,
                "start_date": start_date,
                "end_date": end_date,
                "billing_type": 'FLAT_PRICE',
                "is_recurring": True,
                "due_interval": 1,
                "due_interval_unit": 'NONE',
                "net_payment_terms": 30,
                "is_arrears": True,
                "billing_line_item_name": line['name'],
                "billing_line_item_note": note,
                "billing_term_line_item_id": uuid4(),
                "quantity": line['qty'],
                "price": line['amount'],
                "condition_operator": "NOT_OPERATOR",
                "condition_value": 0,
                "item_id": line['item_id']
            }
            dict_csvs.append(csv_dict)
    
    filename = 'Dec_Invoices_Findigs_4.csv'
    # Writing to the CSV file
    with open(filename, mode='w', newline='') as file:
        # Assuming all dictionaries have the same keys, use the keys from the first dictionary
        print(dict_csvs)
        fields = dict_csvs[0].keys()
        writer = csv.DictWriter(file, fieldnames=fields)

        # Write the header
        writer.writeheader()

        # Write the data rows
        writer.writerows(dict_csvs)

    print(f'Data written to {filename} successfully.')


