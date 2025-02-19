import requests

def create_external_accounts(merchant_id, accounts, token):
    # Define the API endpoint URL
    url = f"http://your-api-url/{merchant_id}/createExternalAccount"
    
    # Set the authorization headers
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # Loop through the accounts and make API calls
    for account in accounts:
        try:
            response = requests.post(
                url,
                json={
                    "refId": account["refId"],
                    "refIdType": "CUSTOMER",  # Hardcoded value
                    "accountConfig": {
                        "accountNumber": account["accountNumber"],
                        "routingNumber": account["routingNumber"],
                        "accountHolderName": account.get("accountHolderName", ""),  # Default to blank if not provided
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

# Define the merchant ID and API token
merchant_id = "76310fa7-758a-4062-307e-a9e75497b770"  # Replace with your merchant ID
token = "YOUR_ACCESS_TOKEN"  # Replace with your API token

# List of accounts to be created
accounts = [
    {"refId": "account-1", "accountNumber": "1234567890", "routingNumber": "987654321"},
    {"refId": "account-2", "accountNumber": "2345678901", "routingNumber": "876543210"},
    {"refId": "account-3", "accountNumber": "3456789012", "routingNumber": "765432109"},
    # Add all 50 accounts here...
]

# Call the function to create external accounts
create_external_accounts(merchant_id, accounts, token)
