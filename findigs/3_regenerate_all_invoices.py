import csv
import psycopg2
import os
import time
import requests

conn = psycopg2.connect(
    dbname="core",
    user="chirag",
    password=os.getenv('SCRIPT_DB_PASSWORD'),
    port=5432,
    host="core-1.c1gkmwasa8f7.us-east-1.rds.amazonaws.com",
    sslmode='require'
)
cursor = conn.cursor()

def csv_to_list_of_dicts():
    with open("Dec_Findigs_Remittance.csv", mode='r') as file:
        # DictReader reads each row of the CSV as a dictionary, using the first row as the keys
        reader = csv.DictReader(file)
        return [row for row in reader]

def find_customer(cid):
    cursor.execute("SELECT customer_id FROM contracts where id = '{}'".format(cid))
    row = cursor.fetchone()
    # Transform the result into a dictionary
    return row[0] if row else None
    
if __name__ == "__main__":
    dicts = csv_to_list_of_dicts()
    contracts = []
    for dict in dicts:
        contracts.append(dict["contract_id"])
    customers = set([])
    for contract in contracts:
        customer = find_customer(contract)
        if (customer):
            customers.add(customer)

    throttle = 0

    print(customers)

    for customer in customers:
        url = "https://admin.prod.api.tabsplatform.com/v2/customers/" + customer + "/invoices"
        headers = {
            "Authorization": "Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6IlAtSHMyRW43OGppakF1NDZBVGxZbyJ9.eyJpc3MiOiJodHRwczovL3Byb2QtYWRtaW4udXMuYXV0aDAuY29tLyIsInN1YiI6Imdvb2dsZS1vYXV0aDJ8MTA5MTA3MTI0NjAwMzIxMzY0ODgxIiwiYXVkIjpbImh0dHBzOi8vYWRtaW4ucHJvZC5hcGkudGFic3BsYXRmb3JtLmNvbSIsImh0dHBzOi8vcHJvZC1hZG1pbi51cy5hdXRoMC5jb20vdXNlcmluZm8iXSwiaWF0IjoxNzM2NzkwNTgxLCJleHAiOjE3MzY4NzY5ODEsInNjb3BlIjoib3BlbmlkIHByb2ZpbGUgZW1haWwiLCJhenAiOiJzYUVlQVlCR2Y5RmZHOE9IZXVrWUhMcVVFT2Q0M3ZzdyIsInBlcm1pc3Npb25zIjpbImNyZWF0ZTpjb250cmFjdHMiLCJkZWxldGU6Y29udHJhY3RzIiwicmVhZDpjb250cmFjdHMiLCJyZWFkOmN1c3RvbWVycyIsInJlYWQ6aW52b2ljZXMiLCJyZWFkOm1lcmNoYW50cyIsInVwZGF0ZTpjb250cmFjdHMiLCJ3cml0ZTpiaWxsaW5nIiwid3JpdGU6Y29udHJhY3RzIiwid3JpdGU6Y3VzdG9tZXJzIiwid3JpdGU6bWVyY2hhbnRzIl19.dh9l8l-aZ7fXTb952bnXsZttOp8wg0x9-NeXXM-ezU0_PcagX9EfCnIPzsSpNjQZtG_WJBYg5wMaOgV8bWPZMRpIo1dsKTn0h4zrs4TL6rDjB6TKogeZfqfwU0NBmEpUQl958ykDhMCPwycnJfQkCuueR2LrMzU1u4DmYIAOgU2IwfHcfz1aV0ytXQrjFpDsKgD726klVYg7Qv-FF2srF6IRE0__tScWsFBvLSC0Kq0lh_KXCVsAOqsNXY9QqVDM9INGi9BRhPkmw6bpusLbqHTBBG6m8eC-KepIPpCL8_CFBKmpY5UUlVJ_y1Vd_jFdQfk5sJnDh0SYwaZCPkeIkQ",
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
    

    