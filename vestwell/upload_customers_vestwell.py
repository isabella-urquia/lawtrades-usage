import csv
import psycopg2
from uuid import uuid4
import os
import sys
import json

conn = psycopg2.connect(
    dbname="core",
    user="rw",
    password=os.getenv('SCRIPT_DB_PASSWORD'),
    port=5432,
    host="core.cluster-cizo3akkr249.us-east-1.rds.amazonaws.com",
    sslmode='require'
)
cursor = conn.cursor()

def csv_to_list_of_dicts(filename):
    with open(filename, mode='r') as file:
        reader = csv.DictReader(file)
        return [row for row in reader]
    
if __name__ == "__main__":
    dicts = {}
    output_csv = []
    print(sys.argv)
    if (len(sys.argv) == 3):
        dicts = csv_to_list_of_dicts(str(sys.argv[1]))
        
    for dict in dicts:
        merchant_id = dict["merchant_id"]
        merchant_name = dict["merchant_name"]
        customer_name_with_prefix = dict["name"]
        name = dict["name"]
        email = dict["email"]
        address_line_1 = dict["billing_address_street_address_line_1"]
        address_line_2 = dict["billing_address_street_address_line_2"]
        city = dict["billing_address_city"]
        state = dict["billing_address_state"]
        zip_code = dict["billing_address_zip_code"]
        country = dict["billing_address_country"]
        plan_id = dict["planid_(externalid)"]
        metadata_fields = ["ordway", "advisor", "statement_advisor", "forfeiture_balance", "prepayment_balance"]

        customer_id = uuid4()
        address_id = uuid4()
        contacts_id = uuid4()

        cursor.execute("INSERT into addresses (id, manufacturer_id, address_line1, address_line2, city, state, country, zip) values (%s, %s, %s, %s, %s, %s, %s, %s) returning id", (address_id.hex, merchant_id, address_line_1, address_line_2, city, state, country, zip_code))
        new_address_id = cursor.fetchone()[0]

        cursor.execute("INSERT into customers (id, manufacturer_id, name, name_with_prefix) values (%s, %s, %s, %s) returning id", (customer_id.hex, merchant_id, name, customer_name_with_prefix))
        new_parent_customer_id = cursor.fetchone()[0]

        cursor.execute("INSERT into customer_address (customer_id, address_id, is_default_billing, is_default_shipping) values (%s, %s, %s, %s)", (new_parent_customer_id, new_address_id, True, True))

        cursor.execute("INSERT into contacts_v2 (id, customer_id, email) values (%s, %s, %s) returning id", (contacts_id.hex, new_parent_customer_id, email))
        new_parent_contact_id = cursor.fetchone()[0]

        metadata = {}
        for field in metadata_fields:
            metadata[field] = dict["metadata:" + field]

        cursor.execute("INSERT into customer_external_ids (customer_id, source_type, external_id, metadata) values (%s, %s, %s, %s)", (new_parent_customer_id, "SALESFORCE", plan_id, json.dumps(metadata)))

        print("New address for parent customer: " + new_address_id)
        print("New parent customer: " + new_parent_customer_id)
        print("New contact for parent customer: " + new_parent_contact_id)

        customer_id_sponsor = uuid4()
        address_id_sponsor = uuid4()
        contacts_id_sponsor = uuid4()
        
        customer_name_sponsor = dict["name"]
        customer_name_with_prefix_sponsor = dict["name"] + ": Sponsor"

        cursor.execute("INSERT into addresses (id, manufacturer_id, address_line1, address_line2, city, state, country, zip) values (%s, %s, %s, %s, %s, %s, %s, %s) returning id", (customer_id_sponsor.hex, merchant_id, address_line_1, address_line_2, city, state, country, zip_code))
        new_address_id_sponsor = cursor.fetchone()[0]

        cursor.execute("INSERT into customers (id, manufacturer_id, name, name_with_prefix, parent_id) values (%s, %s, %s, %s, %s) returning id", (customer_id_sponsor.hex, merchant_id, customer_name_sponsor, customer_name_with_prefix_sponsor, new_parent_customer_id))
        new_customer_id_sponsor = cursor.fetchone()[0]

        cursor.execute("INSERT into customer_address (customer_id, address_id, is_default_billing, is_default_shipping) values (%s, %s, %s, %s)", (new_customer_id_sponsor, new_address_id_sponsor, True, True))

        cursor.execute("INSERT into contacts_v2 (id, customer_id, email) values (%s, %s, %s) returning id", (contacts_id_sponsor.hex, new_customer_id_sponsor, email))
        new_contact_id_sponsor = cursor.fetchone()[0]

        cursor.execute("INSERT into customer_external_ids (customer_id, source_type, external_id, metadata) values (%s, %s, %s, %s)", (new_customer_id_sponsor, "SALESFORCE", plan_id, json.dumps(metadata)))

        print("New address for 'Sponsor' subcustomer: " + new_address_id_sponsor)
        print("New 'Sponsor' subcustomer: " + new_customer_id_sponsor)
        print("New contact for 'Sponsor' subcustomer: " + new_contact_id_sponsor)

        customer_id_participant = uuid4()
        address_id_participant = uuid4()
        contacts_id_participant = uuid4()
        
        customer_name_participant = dict["name"]
        customer_name_with_prefix_participant = dict["name"] + ": Participant"

        cursor.execute("INSERT into addresses (id, manufacturer_id, address_line1, address_line2, city, state, country, zip) values (%s, %s, %s, %s, %s, %s, %s, %s) returning id", (address_id_participant.hex, merchant_id, address_line_1, address_line_2, city, state, country, zip_code))
        new_address_id_participant = cursor.fetchone()[0]

        cursor.execute("INSERT into customers (id, manufacturer_id, name, name_with_prefix, parent_id) values (%s, %s, %s, %s, %s) returning id", (customer_id_participant.hex, merchant_id, customer_name_participant, customer_name_with_prefix_participant, new_parent_customer_id))
        new_customer_id_participant = cursor.fetchone()[0]

        cursor.execute("INSERT into customer_address (customer_id, address_id, is_default_billing, is_default_shipping) values (%s, %s, %s, %s)", (new_customer_id_participant, new_address_id_participant, True, True))

        cursor.execute("INSERT into contacts_v2 (id, customer_id, email) values (%s, %s, %s) returning id", (contacts_id_participant.hex, new_customer_id_participant, email))
        new_contact_id_participant = cursor.fetchone()[0]

        cursor.execute("INSERT into customer_external_ids (customer_id, source_type, external_id, metadata) values (%s, %s, %s, %s)", (new_customer_id_participant, "SALESFORCE", plan_id, json.dumps(metadata)))

        print("New address for 'Participant' subcustomer: " + new_address_id_participant)
        print("New 'Participant' subcustomer: " + new_customer_id_participant)
        print("New 'Participant' subcustomer: " + new_customer_id_participant)

        output_csv.append({"customer_id": new_parent_customer_id, "name": name, "name_with_prefix": customer_name_with_prefix})
        output_csv.append({"customer_id": new_customer_id_sponsor, "name": customer_name_sponsor, "name_with_prefix": customer_name_with_prefix_sponsor})
        output_csv.append({"customer_id": new_customer_id_participant, "name": customer_name_participant, "name_with_prefix": customer_name_with_prefix_participant})
    conn.commit()

    # Output file in CSV format
    filename = str(sys.argv[2])
    # Writing to the CSV file
    with open(filename, mode='w', newline='') as file:
        fields = ["customer_id", "name", "name_with_prefix"]
        writer = csv.DictWriter(file, fieldnames=fields)

        # Write the header
        writer.writeheader()

        # Write the data rows
        writer.writerows(output_csv)

    print(f'Data written to {filename} successfully.')
cursor.close()
conn.close()



