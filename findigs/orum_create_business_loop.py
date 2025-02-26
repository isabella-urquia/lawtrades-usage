import requests
import csv
import os
import sys
import json


def csv_to_list_of_dicts(filename):
    with open(filename, mode='r') as file:
        # DictReader reads each row of the CSV as a dictionary, using the first row as the keys
        reader = csv.DictReader(file)
        return [row for row in reader]



def create_businesses(merchant_id, businesses, token):
    url = f"http://your-api-url/v2/integrations/orum/{merchant_id}/createBusiness" #Ask Eng
    headers = {
        "Authorization": f"Bearer {token}", ##Ask Eng
        "Content-Type": "application/json"
    }

    for business in businesses:
        ref_id = business.get("refId")  # Use `.get()` to avoid KeyErrors
        if not ref_id:
            print("Skipping entry due to missing refId:", business)
            continue  # Skip the business entry if "refId" is missing

        try:
            response = requests.post(
                url,
                json={
                    "refId": ref_id,
                    "refIdType": "CUSTOMER",  # Hardcoded value
                },
                headers=headers,
            )
            response.raise_for_status()
            print(f"Business created successfully: {response.json()}")
        except requests.exceptions.RequestException as e:
            print(f"Error creating business for {business['refId']}: {e}")

if __name__ == "__main__":
    businesses = csv_to_list_of_dicts("/Users/chiragdas/Downloads/Findigs_Jan_original.csv")
    merchant_id = "76310fa7-758a-4062-307e-a9e75497b770"  
# if using JSON instead of CSV
# businesses = [
#     {"refId": "business-1"},
#     {"refId": "business-2"},
#     # Add all 50 businesses here...
# ]
token = "YOUR_ACCESS_TOKEN"  # Replace with your API token
create_businesses(merchant_id, businesses, token)
