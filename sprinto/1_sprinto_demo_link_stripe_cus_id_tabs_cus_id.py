import datetime
import os
from typing import List, Optional, Tuple
from uuid import uuid4
import csv
import psycopg2

# configs from .env
conn = psycopg2.connect(
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    port=5432,
    host=os.getenv("DB_HOST"),
    sslmode="require",
)

cursor = conn.cursor()

#expects a csv with the following columns: Customer ID, Stripe Customer ID, Stripe Payment Method ID in the same repo
data = []
with open('stripe_customer_upload.csv', 'r') as file:
    reader = csv.DictReader(file)

    cnt = 0
    for row in reader:
        data.append((row['Customer ID'], row['Stripe Customer ID'], row['Stripe Payment Method ID']))

if __name__ == "__main__":

    count = 0
    for row in data:
        customerId = row[0]
        stripeId = row[1]
        paymentMethodId = row[2]

        findIdQuery = """
            SELECT id
            FROM stripe_accounts
            WHERE stripe_account_id = %s
        """
        cursor.execute(findIdQuery, (stripeId,))

        detailsId = None

        x = cursor.fetchone()
        if x:
            detailsId = x[0]

        if not detailsId:   
            detailsId = uuid4()
            insertDetailsQuery = """
                INSERT INTO stripe_accounts (id, created_at, ready_for_payments, stripe_account_id)
                VALUES (%s, %s, %s, %s)
            """
            print(insertDetailsQuery, (str(detailsId), datetime.datetime.now(), True, stripeId))
            cursor.execute(insertDetailsQuery, (str(detailsId), datetime.datetime.now(), True, stripeId))


        customerLinkId = uuid4()
        insertLinkQuery = """
            INSERT INTO customer_stripe_accounts (id, customer_id, "detailsId", default_payment_method, default_payment_method_type)
            VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(insertLinkQuery, (str(customerLinkId), customerId, str(detailsId), paymentMethodId, None))
        conn.commit()
        print(count)
        count += 1


cursor.close()
conn.close()
