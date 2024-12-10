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
import time
import requests

conn = psycopg2.connect(
    dbname="core",
    user="rw",
    password=os.getenv('SCRIPT_DB_PASSWORD'),
    port=5432,
    host="core.cluster-c1gkmwasa8f7.us-east-1.rds.amazonaws.com",
    sslmode='require'
)
cursor = conn.cursor()

def csv_to_list_of_dicts():
    with open("output26.csv", mode='r') as file:
        # DictReader reads each row of the CSV as a dictionary, using the first row as the keys
        reader = csv.DictReader(file)
        return [row for row in reader]

def contract(cid):
    cursor.execute("SELECT customer_id FROM contracts where id = '{}'".format(cid))
    row = cursor.fetchone()
    # Transform the result into a dictionary
    return row[0] if row else None
    
g = []
if __name__ == "__main__":
    customers = set([])
    for a in g:
        customer = contract(a)
        # print(customer)

        customers.add(customer)

    throttle = 0

    print(customers)

    for customer in customers:
        url = "https://admin.prod.api.tabsplatform.com/v2/customers/" + customer + "/invoices"
        headers = {
            "Authorization": "Bearer eyJhbGciOiJSUzI1NiIsImNhdCI6ImNsX0I3ZDRQRDExMUFBQSIsImtpZCI6Imluc18yY2UzRTBXSTVWUmdzNnpCbElKQ3Nad1hHZk8iLCJ0eXAiOiJKV1QifQ.eyJhenAiOiJodHRwczovL2dhcmFnZS50YWJzcGxhdGZvcm0uY29tIiwiZXhwIjoxNzI4NDA4NDM3LCJpYXQiOjE3Mjg0MDgzNzcsImlzcyI6Imh0dHBzOi8vY2xlcmsudGFic3BsYXRmb3JtLmNvbSIsIm5iZiI6MTcyODQwODM2Nywib3JnX2lkIjoib3JnXzJjZTZ2OUtoTDlvZklWdzd3V21vS2N4T2lRWiIsIm9yZ19wZXJtaXNzaW9ucyI6WyJvcmc6Y29udHJhY3RzOmRlbGV0ZSIsIm9yZzppbnZvaWNlczpkZWxldGUiLCJvcmc6ZXZlbnRzOmNyZWF0ZSIsIm9yZzpzdXBlcl9wb3dlcjpjcmVhdGUiLCJvcmc6dXNlcnM6dXBkYXRlIiwib3JnOnVzZXJzOmNyZWF0ZSIsIm9yZzpyZW1pdHRhbmNlczp1cGRhdGUiLCJvcmc6cmVtaXR0YW5jZXM6cmVhZCIsIm9yZzp1c2VyczpyZWFkIiwib3JnOmN1c3RvbWVyczpyZWFkIiwib3JnOmN1c3RvbWVyczpjcmVhdGUiLCJvcmc6Y29udHJhY3RzOnJlYWQiLCJvcmc6Y29udHJhY3RzOnVwZGF0ZSIsIm9yZzppbnZvaWNlczpyZWFkIiwib3JnOmludm9pY2VzOnVwZGF0ZSIsIm9yZzpjb250cmFjdHM6Y3JlYXRlIiwib3JnOmludm9pY2VzOmNyZWF0ZSIsIm9yZzpldmVudHM6cmVhZCIsIm9yZzptZXJjaGFudHM6dXBkYXRlIiwib3JnOm1lcmNoYW50czpyZWFkIiwib3JnOm1heF9hZG1pbjphbGwiXSwib3JnX3JvbGUiOiJvcmc6YWRtaW4iLCJvcmdfc2x1ZyI6InByb2QiLCJzaWQiOiJzZXNzXzJuQTBQeWFCMGpveU1TajVBdDFCWlZORmhEeiIsInN1YiI6InVzZXJfMmNlSEJYdEQzaUY3NHoyN0wwREJ6TEpiZndRIn0.04Rkqw9U5GYbiv8wQexlE0nhce2uWzDuKcbWtiIHuVp7MB6P1GTo-w9XIwCm27pV5gYjSYZeb3dv3F6SStZUropFdfkeLR5qMg8uPLI7NdDjeQXxL48AIE12-FLcjHBcwLrh23G7hT1Z2vDkjXAKOboB3TQhUmtYi5xk08BncFr8XAh55vCVpr4F5csuGfwZgdGUCLcT2dvkhuc-TelZqr4D3rfqRckcr8UkWGe50q-umi75xt29eMXAVUxtP3NRmOCitpfiVRjHGpzcNcfnm_uN1jHGow_Csf95SS9-czNPruvOWp8NJ8huDOBcaCK9K5mtl9aH5bOZsyK_5UUI_w",
        }
        body = {
            "invoiceType": "BILL"
        }

        response = requests.post(url, headers=headers, data=body)
        print(customer, response.status_code)
        throttle += 1
        if (throttle > 10):
            time.sleep(20)
            throttle = 0
    

    