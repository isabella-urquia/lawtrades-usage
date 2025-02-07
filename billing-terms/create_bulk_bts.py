from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
import json
from datetime import datetime
import os
from dateutil.relativedelta import relativedelta
import sys
import requests
import time
from dateutil import parser
import pandas as pd

# Convert csv to list of dictionaries sorted by contract_id and customer_id
def csv_to_list_of_dicts(path):
    df = pd.read_csv(path)
    df.sort_values(by=['contract_id', 'customer_id'], inplace=True)
    return df, df.to_dict(orient='records')

# Format given date to YYYY-MM-DD
def format_date(date_str):
    if not date_str:
        return None # Return None if the input is None or empty
    
    try:
        parsed_date = parser.parse(date_str)
        return parsed_date.strftime('%Y-%m-%d')
    except (ValueError, TypeError):
        return None # Return None if parsing fails

authorization = '' # Authorization key per merchant
is_remittance = False # Change accordingly

# Process given csv file
def process_file(input_file):
    right_now = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = input_file.replace(".csv", f"_{right_now}.csv")
    df, dicts = csv_to_list_of_dicts(input_file)
    data_list = []
    failed_dicts = []
    customer_id = None
    contract_id = None
    batch_size = 20 # Max is 20 per API call

    try:
        for i, dict in enumerate(dicts):
            if i % 1000 == 0 and i > 0:
                print(f"Processed {i} rows for {input_file}")
            
            # Batches have to be up to 20 BTs at a time, with the same customer and contract
            if i == 0 or (dict["customer_id"] == customer_id and dict["contract_id"] == contract_id and len(data_list) < batch_size):
                customer_id = dict["customer_id"]
                contract_id = dict["contract_id"]
                bt_start_date = format_date(dict["bt_start_date"])
                rs_start_date = format_date(dict.get("revenue_start_date", None))
                rs_end_date = format_date(dict.get("revenue_end_date", None))
                is_recurring = dict["is_recurring"]
                quantity = dict["quantity"]
                due_interval = str(dict["due_interval"])
                due_interval_unit = dict["due_interval_unit"]
                duration = str(dict["duration"])
                net_payment_terms = str(dict["net_payment_terms"])
                billing_type = "FLAT_PRICE"
                is_arrears = "Yes" if dict["is_arrears"] == "True" else "No"
                event_to_track = dict.get("event_to_track", "N/A")
                line_item_name = dict["line_item_name"]
                line_item_note = dict["line_item_note"]
                manuafcturer_id = dict["manufacturer_id"]
                integration_id = dict.get("item_id", "None")
                amount = dict["amount"]
                invoice_type = dict.get("invoice_type", None) # "BILL" if remittance
                
                json_object = {
                    "startDate": bt_start_date,
                    "isRecurring": is_recurring,
                    "quantity": quantity,
                    "dueInterval": due_interval,
                    "dueIntervalUnit": due_interval_unit,
                    "duration": duration,
                    "netPaymentTerms": net_payment_terms,
                    "billingType": billing_type,
                    "isArrears": is_arrears,
                    "eventToTrack": event_to_track,
                    "lineItemName": line_item_name,
                    "lineItemNote": line_item_note,
                    "manufacturerId": manuafcturer_id,
                    "integrationItemName": integration_id,
                    "amount": amount,
                    "revenueStartDate": rs_start_date,
                    "revenueEndDate": rs_end_date,
                    "invoiceType": invoice_type
                }
                
                data_list.append(json_object)

            # New batch so send the data_list with all BTs and reset data_list for thr next batch
            else:
                url = f"http://localhost:3101/billingSchedule/bulk"
                body = {'data': data_list, 'customerId': customer_id, 'contractId': contract_id, 'isRemittance': is_remittance}
                json_string = json.dumps(body, indent=2)
                headers = {'Content-Type': 'application/json', 'Authorization': authorization}
                response = requests.post(url, data=json_string, headers=headers)
                
                if response.status_code != 201:
                    error_message = response.text # Capture API response message
                    for item in data_list:
                        item["error_message"] = error_message # Add error message to each failed row
                    failed_dicts.extend(data_list)

                data_list = []
                customer_id = dict["customer_id"]
                contract_id = dict["contract_id"]
                
                json_object = {
                    "startDate": bt_start_date,
                    "isRecurring": is_recurring,
                    "quantity": quantity,
                    "dueInterval": due_interval,
                    "dueIntervalUnit": due_interval_unit,
                    "duration": duration,
                    "netPaymentTerms": net_payment_terms,
                    "billingType": billing_type,
                    "isArrears": is_arrears,
                    "eventToTrack": event_to_track,
                    "lineItemName": line_item_name,
                    "lineItemNote": line_item_note,
                    "manufacturerId": manuafcturer_id,
                    "integrationItemName": integration_id,
                    "amount": amount,
                    "revenueStartDate": rs_start_date,
                    "revenueEndDate": rs_end_date,
                    "invoiceType": invoice_type
                }
                
                data_list.append(json_object)

        if data_list:
            url = f"http://localhost:3101/billingSchedule/bulk"
            body = {'data': data_list, 'customerId': customer_id, 'contractId': contract_id, 'isRemittance': is_remittance}
            json_string = json.dumps(body, indent=2)
            headers = {'Content-Type': 'application/json', 'Authorization': authorization}
            response = requests.post(url, data=json_string, headers=headers)
            
            if response.status_code != 201:
                error_message = response.text # Capture API response message
                for item in data_list:
                    item["error_message"] = error_message # Add error message to each failed row
                failed_dicts.extend(data_list)

        # If there are failed rows, ensure they're in a format to be re-run and create the file
        # Search the DF for the failed rows that have both note, amount, revenue_schedule matching lineItemNote, amount, revenueStartDate
        if failed_dicts:
            failed_df = df[df.apply(lambda row: any(
                (row["line_item_note"], row["amount"], format_date(row.get("revenue_start_date", None))) == 
                (d["lineItemNote"], d["amount"], d["revenueStartDate"]) for d in failed_dicts), axis=1)].copy()


            # Ensure `error_message` is included
            failed_df["error_message"] = failed_df.apply(lambda row: next(
                (d["error_message"] for d in failed_dicts if 
                (row["line_item_note"], row["amount"], format_date(row.get("revenue_start_date", None))) == 
                (d["lineItemNote"], d["amount"], d["revenueStartDate"])), None), axis=1)

            failed_df.to_csv(output_file, index=False)
    
    except Exception as e:
        print(f"Error processing file {input_file}: {e}")

def main():
    input_files = sys.argv[1:]
    
    with ThreadPoolExecutor(max_workers=len(input_files)) as executor:
        futures = {executor.submit(process_file, file): file for file in input_files}
        
        for future in as_completed(futures):
            file = futures[future]
            try:
                future.result()
                print(f"Processing completed for {file}")
            except Exception as e:
                print(f"Error processing {file}: {e}")

if __name__ == "__main__":
    main()
