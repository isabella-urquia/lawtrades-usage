from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
import pandas as pd
import os
from typing import List, Dict, Any
import uvicorn

app = FastAPI(title="Step-Up Pricing API", description="API for fetching step-up pricing data")

# Enable CORS for all origins (adjust as needed for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_stepup_pricing_data():
    """Fetch step-up pricing data from database"""
    try:
        # Hardcoded database connection
        conn = psycopg2.connect(
            dbname="core",
            user="read",
            password="k9gxPS0UoqEbIhx0QhZEp1UeJi5F",
            port=5432,
            host="core-1.c1gkmwasa8f7.us-east-1.rds.amazonaws.com",
            sslmode='require'
        )
        
        # SQL query to get step-up pricing for Lawtrades manufacturer
        sql_query = """
        SELECT DISTINCT 
            et.name AS event_type_name,
            c.customer_id,
            (CAST(p.mantissa AS numeric) * POWER(10.0, p.exponent::int))::numeric(38,6) AS unit_price
        FROM event_types_v2 et
        JOIN billing_terms bt
            ON bt.event_type_id = et.id
        JOIN contracts c
            ON bt.contract_id = c.id
        LEFT JOIN pricings p 
            ON p."billingTermId" = bt.id
        WHERE c.manufacturer_id = '7af68809-96ba-4de9-a1a0-4be7b103a491'
          AND et.deleted_at IS NULL
          AND bt.deleted_at IS NULL
          AND c.deleted_at IS NULL
          AND et.name LIKE '%% - %%'
        ORDER BY et.name;
        """
        
        # Execute query
        df = pd.read_sql_query(sql_query, conn)
        conn.close()
        
        if len(df) == 0:
            return []
        
        # Transform data into the format expected by the app
        stepup_data = []
        for _, row in df.iterrows():
            event_type_name = row['event_type_name']
            customer_id = row['customer_id']
            unit_price = float(row['unit_price'])
            
            # Extract lawyer name and suffix
            if ' - ' in event_type_name:
                lawyer_name = event_type_name.split(' - ')[0]
                suffix = ' - ' + event_type_name.split(' - ')[1]
                
                stepup_data.append({
                    "lawyer_name": lawyer_name,
                    "customer_id": customer_id,
                    "suffix": suffix,
                    "unit_price": unit_price
                })
        
        return stepup_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/")
async def root():
    return {"message": "Step-Up Pricing API", "version": "1.0.0"}

@app.get("/api/stepup-pricing")
async def get_stepup_pricing():
    """Get step-up pricing data for Lawtrades"""
    try:
        data = get_stepup_pricing_data()
        return {
            "success": True,
            "data": data,
            "count": len(data)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stepup-pricing/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "message": "API is running"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

