import os
from typing import List, Optional, Tuple

import psycopg2

conn = psycopg2.connect(
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    port=5432,
    host=os.getenv("DB_HOST"),
    sslmode="require",
)
cursor = conn.cursor()

ALKIRA_ID = "dd4337a4-6573-310b-b071-ec8e1b68a193"
ALKIRA_SANDBOX_ID = "3bf1f850-b872-42e2-8285-37ea9f252b11"


def find_event_by_id(event_id: str) -> Optional[Tuple]:
    query = """
        SELECT id, name
        FROM event_types_v2 
        WHERE id = %s 
        AND deleted_at IS NULL 
        ORDER BY created_at DESC 
        LIMIT 1
    """
    cursor.execute(query, (event_id,))
    return cursor.fetchone()


def find_event(manufacturer_id: str, event_name: str) -> Optional[str]:
    query = """
        SELECT id 
        FROM event_types_v2 
        WHERE manufacturer_id = %s 
        AND name = %s 
        AND deleted_at IS NULL 
        ORDER BY created_at DESC 
        LIMIT 1
    """
    cursor.execute(query, (manufacturer_id, event_name))
    row = cursor.fetchone()
    return row[0] if row else None


def find_all_alkira_event_types() -> List[Tuple]:
    query = """
        SELECT field_to_name, name
        FROM event_types_v2 
        WHERE manufacturer_id = %s 
        AND deleted_at IS NULL 
        ORDER BY created_at DESC 
    """
    cursor.execute(query, (ALKIRA_ID,))
    return cursor.fetchall()


def insert_all_alkira_events_into_sandbox() -> None:
    event_types = find_all_alkira_event_types()
    for event_type in event_types:
        cursor.execute(
            """
            INSERT INTO event_types_v2 
            (field_to_sum, display_type, field_to_name, name, manufacturer_id) 
            VALUES (%s, %s, %s, %s, %s)
        """,
            ("value", "GROUPED", event_type[0], event_type[1], ALKIRA_SANDBOX_ID),
        )


def find_all_billing_terms() -> List[Tuple]:
    query = """
        SELECT billing_terms.id,  
        FROM billing_terms 
        JOIN contracts ON contracts.id = billing_terms.contract_id
        WHERE contracts.manufacturer_id = %s 
        AND billing_terms.deleted_at IS NULL 
        AND billing_terms.billing_type NOT IN ('FLAT_PRICE')
        ORDER BY billing_terms.created_at DESC 
    """
    cursor.execute(query, (ALKIRA_SANDBOX_ID,))
    return cursor.fetchall()


def reassign_all_billing_terms() -> None:
    billing_terms = find_all_billing_terms()
    for billing_term in billing_terms:
        event_type = find_event_by_id(billing_term[0])
        if not event_type:
            print(f"No event type found for billing term: {billing_term[0]}")
            continue

        sandbox_type = find_event(ALKIRA_SANDBOX_ID, event_type[1])
        if not sandbox_type:
            print(f"No sandbox event type found for billing term: {billing_term[0]}")
            continue

        cursor.execute(
            """
            UPDATE billing_terms 
            SET event_type_id = %s 
            WHERE id = %s
        """,
            (sandbox_type, billing_term[0]),
        )
        print(f"Reassigned {billing_term[0]}")


if __name__ == "__main__":
    insert_all_alkira_events_into_sandbox()
    reassign_all_billing_terms()
    # conn.commit()

cursor.close()
conn.close()
