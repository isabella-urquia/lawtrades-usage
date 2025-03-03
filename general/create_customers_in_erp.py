import csv
import time
from uuid import uuid4
import sys
import requests

def csv_to_list_of_dicts(filename):
    with open(filename, mode='r') as file:
        reader = csv.DictReader(file)
        return [row for row in reader]
    
if __name__ == "__main__":
    dicts = csv_to_list_of_dicts(str(sys.argv[1]))
    customers_to_create = set() # To prevent duplicates as can't create customers in ERP with same name

    manufacturer_custom_fields_id_1 = uuid4()
    merchant_id = sys.argv[2]

    throttle = 0
    
    for dict in dicts:
        customer_name = dict["customer_name"]
        if customer_name in customers_to_create:
            continue
        customers_to_create.add(customer_name)

        # OPTIONAL FIELDS
        # first_name = dict["first_name"]
        # last_name = dict["last_name"]
        # email = dict["email"]
        # address_line_1 = dict["billing_address_street_address_line_1"]
        # address_line_2 = dict["billing_address_street_address_line_2"]
        # city = dict["billing_address_street_address_city"]
        # state = dict["billing_address_street_address_state"]
        # zip_code = dict["billing_address_street_address_zip_code"]
        # country = dict["billing_address_street_address_country"]

        # customerAddressPayload = {}
        # customerAddressPayload["addressee"] = customer_name
        # customerAddressPayload["line1"] = address_line_1
        # customerAddressPayload["line2"] = address_line_2
        # customerAddressPayload["city"] = city
        # customerAddressPayload["state"] = state
        # customerAddressPayload["postalCode"] = zip_code
        # customerAddressPayload["country"] = country

        createCustomerPayload = {}
        createCustomerPayload['name'] = customer_name
        createCustomerPayload['companyName'] = customer_name

        # OPTIONAL FIELDS
        # createCustomerPayload["address"] = customerAddressPayload
        # createCustomerPayload['email'] = email

        url = f"http://localhost:3101/v2/integrations/qbo/merchant/{merchant_id}/customer"
        body = {'customer': createCustomerPayload}
        params = {'manufacturer': merchant_id}

        response = requests.post(url, json=body, params=params)
        print(customer_name, response.status_code)
        throttle += 1
        if (throttle > 10):
            time.sleep(20)
            throttle = 0
