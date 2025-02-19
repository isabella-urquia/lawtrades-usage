import requests
import csv
import os

# Define the API headers
headers = {
    "Authorization": "tabs_sk_V3Ko5AOG095jJsZHuDaYRitgBw6xVT2WvPTH9qUnYeoWEYkFnbNuOwBkpzgnvBvO"
}

# API Endpoint Template
API_URL_TEMPLATE = "https://integrators.prod.api.tabsplatform.com/manufacturers/{}/invoices/{}/attachments/upload"

# Function to send file to API
def send_request(manufacturer_id, invoice_id, filepath):
    if not os.path.exists(filepath):
        print(f"Error: File not found → {filepath}")
        return

    url = API_URL_TEMPLATE.format(manufacturer_id, invoice_id)  # Format URL with dynamic values
    
    with open(filepath, 'rb') as file:
        files = {'file': (os.path.basename(filepath), file, 'application/pdf')}  # Attach file
    
        try:
            response = requests.post(url, headers=headers, files=files, timeout=20)
            response.raise_for_status()  # Raise an error for bad responses (4xx, 5xx)
            print(f"✅ Success: {filepath} → Response: {response.json()}")
        except requests.exceptions.RequestException as e:
            print(f"❌ Error processing {filepath}: {e}")

# Function to process CSV file
def process_csv(file_path):
    with open(file_path, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)  # Read CSV as dictionary
        for row in reader:
            manufacturer_id = row["Manufacturer_id"]
            invoice_id = row["Invoice_id"]
            filepath = row["Filepath"]
            
            send_request(manufacturer_id, invoice_id, filepath)  # Send file to API

# Specify CSV file location
csv_file = "/Users/chiragdas/Downloads/Lawtrades_invoices_feb15th_test.csv"  # Update with actual file path
process_csv(csv_file)
