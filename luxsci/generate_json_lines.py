import csv
import json
from datetime import datetime
from dateutil.relativedelta import relativedelta
import requests
import time


manufacturer_id = "<ID HERE>"

def csv_to_list_of_dicts(path):
    with open(path, mode='r') as file:
        # DictReader reads each row of the CSV as a dictionary, using the first row as the keys
        reader = csv.DictReader(file)
        return [row for row in reader]


if __name__ == "__main__":
    path = "<PATH HERE>"
    dicts = csv_to_list_of_dicts(path)
    throttle = 0
    
    for dict in dicts:
        # Input file date format
        input_rev_start_date = dict["revenue_start_date"]

        # Parse the string into a datetime object using the correct input format
        rev_start_date = datetime.strptime(input_rev_start_date, "%m/%d/%y")

        # Add 1 month to the date
        rev_end_date = rev_start_date + relativedelta(months=1)

        # Format the start and end dates to the desired output format
        service_start_date = rev_start_date.strftime("%Y-%m-%d")
        service_end_date = rev_end_date.strftime("%Y-%m-%d")

        service_term = "1"
        item_name = dict["type_description"]
        item_description = dict["description"]
        integration_item = "7f99a0e0-8c21-41cf-b498-1c9ce3b71deb" # Hard-code for ID "2024 Historicals"
        billing_type = "FLAT_PRICE"
        total_price = dict["amount"]
        quantity = "1"

        start_date = datetime.strptime(dict["invoice_date"], "%m/%d/%y").strftime("%Y-%m-%d")
        end_date = start_date
        
        period = "1"
        num_periods = "1"
        frequency_unit = "NONE"
        net_terms = "30"
        arrears = "No"
        event_to_track = "N/A"

        customer_name = dict["customer_name"]
        contract_id = dict["contract_id"]

        revenue_schedule_data = [
            {
                "service_start_date":{
                    "source": "",
                    "value": service_start_date,
                    "type": "date"
                },
                "service_term":{
                    "value": service_term,
                    "type": "string"
                },
                "service_end_date":{
                    "type": "string",
                    "value": service_end_date
                },
                "item_name":{
                    "value": item_name,
                    "type": "string"
                },
                "item_description":{
                    "value": item_description,
                    "type": "string"
                },
                "integration_item":{
                    "value": integration_item,
                    "type": "string"
                },
                "billing_type":{
                    "value": billing_type,
                    "type": "string"
                },
                "total_price":{
                    "source": "",
                    "value": total_price,
                    "unit": "$",
                    "type": "accountingCurrency"
                },
                "quantity":{
                    "value": quantity,
                    "type": "string"
                },
                "start_date":{
                    "source": "",
                    "value": start_date,
                    "type": "date"
                },
                "period":{
                    "value": period,
                    "type": "string"
                },
                "#_of_periods":{
                    "value": num_periods,
                    "type": "string"
                },
                "frequency_unit":{
                    "value": frequency_unit,
                    "type": "string"
                },
                "end_date":{
                    "type": "string",
                    "value": end_date
                },
                "net_terms":{
                    "value": net_terms,
                    "type": "string"
                },
                "arrears":{
                    "value": arrears,
                    "type": "string"
                },
                "event_to_track":{
                    "value": event_to_track,
                    "type": "string"
                }
            }]
        
        json_file = {
            "webhook":{
                "payload": contract_id,
                "url": ""
            },
            "parsed_document": {
                "name": {
                    "value": customer_name,
                    "type": "string"
                },
                "customer_email": None,
                "street_address_line_1": None,
                "street_address_line_2": None,
                "city": None,
                "state": None,
                "zip_code": None,
                "country": None,
                "total_price.unit": {
                    "value": "USD",
                    "type": "string"
                },
                "revenue_schedule": revenue_schedule_data
            }
        }

        json_string = json.dumps(json_file)

        # If run locally in dev
        url = f"http://localhost:3101/migrations/createBillingTermsAndRevenueSchedulesFromSensible"

        # If run in prod
        # url = f"https://admin.dev.api.tabsplatform.com/migrations/createBillingTermsAndRevenueSchedulesFromSensible"
        # headers = {
        #     "Authorization": "",
        # }
        body = {'req': json_string}

        response = requests.post(url, data=body)
        print(contract_id, response.status_code)
        throttle += 1
        if (throttle > 10):
            time.sleep(20)
            throttle = 0
