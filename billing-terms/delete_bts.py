import psycopg2
import pandas as pd
import sys
from datetime import datetime
import os
import ast

conn = psycopg2.connect(
    dbname="core",
    user="rw",
    password=os.getenv('SCRIPT_DB_PASSWORD'),
    port=5432,
    host="core.cluster-c1gkmwasa8f7.us-east-1.rds.amazonaws.com",
    sslmode='require'
)
cursor = conn.cursor()

def delete_billing_terms(csv_file):
    # Load CSV into DataFrame
    df = pd.read_csv(csv_file)
    
    if 'bt_ids' not in df.columns:
        print("Error: 'bt_ids' column not found in CSV.")
        return
    
    billing_term_ids = []
    for bt_list in df['bt_ids']:
        try:
            ids = ast.literal_eval(bt_list) if isinstance(bt_list, str) else bt_list
            if isinstance(ids, list):
                billing_term_ids.extend(ids)
        except (ValueError, SyntaxError):
            print(f"Skipping invalid bt_ids entry: {bt_list}")
    
    if not billing_term_ids:
        print("No valid billing term IDs found in the CSV.")
        return
    
    # Ensure UUID type for PostgreSQL query
    billing_term_ids = [str(bt_id) for bt_id in billing_term_ids]
    
    cursor = conn.cursor()
    
    try:
        # Update billing_terms table
        cursor.execute("UPDATE billing_terms SET deleted_at = NOW() WHERE id = ANY(%s::uuid[]) RETURNING revenue_schedule_id;", (billing_term_ids,))
        
        revenue_schedule_results = cursor.fetchall()
        revenue_schedule_ids = [row[0] for row in revenue_schedule_results if row[0] is not None]
        
        if revenue_schedule_ids:
            # Ensure UUID type
            revenue_schedule_ids = [str(rs_id) for rs_id in revenue_schedule_ids]
            
            # Update revenue_schedule table
            cursor.execute("UPDATE revenue_schedule SET deleted_at = NOW() WHERE id = ANY(%s::uuid[]) RETURNING revenue_product_id;", (revenue_schedule_ids,))
            
            revenue_product_results = cursor.fetchall()
            revenue_product_ids = [row[0] for row in revenue_product_results if row[0] is not None]
            
            if revenue_product_ids:
                # Ensure UUID type
                revenue_product_ids = [str(rp_id) for rp_id in revenue_product_ids]
                
                # Update revenue_products table
                cursor.execute("UPDATE revenue_product SET deleted_at = NOW() WHERE id = ANY(%s::uuid[]);", (revenue_product_ids,))
        
        # Commit the transaction
        conn.commit()
        print(f"Deleted {len(billing_term_ids)} billing terms, {len(revenue_schedule_ids)} revenue schedules, and {len(revenue_product_ids)} revenue products.")
    
    except Exception as e:
        conn.rollback()
        print(f"Error: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python delete_billing_terms.py <csv_file>")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    delete_billing_terms(csv_file)