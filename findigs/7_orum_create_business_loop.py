import requests

def create_businesses(merchant_id, businesses, token):
    url = f"http://your-api-url/{merchant_id}/createBusiness"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    for business in businesses:
        try:
            response = requests.post(
                url,
                json={
                    "refId": business["refId"],
                    "refIdType": "CUSTOMER",  # Hardcoded value
                },
                headers=headers,
            )
            response.raise_for_status()
            print(f"Business created successfully: {response.json()}")
        except requests.exceptions.RequestException as e:
            print(f"Error creating business for {business['refId']}: {e}")

merchant_id = "76310fa7-758a-4062-307e-a9e75497b770"  
businesses = [
    {"refId": "business-1"},
    {"refId": "business-2"},
    # Add all 50 businesses here...
]
token = "YOUR_ACCESS_TOKEN"  # Replace with your API token
create_businesses(merchant_id, businesses, token)
