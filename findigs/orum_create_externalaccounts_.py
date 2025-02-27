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


def create_external_accounts(merchant_id, accounts, token):
    # Define the API endpoint URL
    url = f"http://your-api-url/v2/integrations/orum/merchant/{merchant_id}/createExternalAccount"
    
    # Set the authorization headers
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # Loop through the accounts and make API calls
    for account in accounts:
        ref_id = account.get("refId")
        account_number = account.get("accountNumber")
        routing_number = account.get("routingNumber")
        account_holder_name = account.get("accountHolderName", "")

        if not ref_id or not account_number or not routing_number:
            print(f"Skipping account due to missing data: {account}")
            continue

        try:
            response = requests.post(
                url,
                json={
                    "refId": ref_id,
                    "refIdType": "CUSTOMER",  # Hardcoded value
                    "accountConfig": {
                        "accountNumber": account_number,
                        "routingNumber": routing_number,
                        "accountHolderName": account_holder_name,  # Default to blank if not provided
                    },
                },
                headers=headers,
            )
            
            # Raise exception for HTTP errors
            response.raise_for_status()

            # Print success message
            print(f"External account created successfully: {response.json()}")
        
        except requests.exceptions.RequestException as e:
            # Print error message if the request fails
            print(f"Error creating external account for {account['refId']}: {e}")


if __name__ == "__main__":
    accounts = csv_to_list_of_dicts("/Users/chiragdas/Downloads/Findigs_Jan_original.csv")
    merchant_id = "76310fa7-758a-4062-307e-a9e75497b770"  
# if using JSON instead of CSV
# businesses = [
#     {"refId": "business-1"},
#     {"refId": "business-2"},
#     # Add all 50 businesses here...
# ]
token = "YOUR_ACCESS_TOKEN"  # Replace with your API token

# List of accounts to be created: JSON
# accounts = [
#     {"refId": "account-1", "accountNumber": "1234567890", "routingNumber": "987654321"},
#     {"refId": "account-2", "accountNumber": "2345678901", "routingNumber": "876543210"},
#     {"refId": "account-3", "accountNumber": "3456789012", "routingNumber": "765432109"},
#     # Add all 50 accounts here...
# ]

# Call the function to create external accounts
create_external_accounts(merchant_id, accounts, token)
