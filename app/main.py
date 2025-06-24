from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from pymongo import MongoClient
from datetime import datetime, timedelta
from app.customer_utils import generate_fake_customer

app = FastAPI()

client = MongoClient("mongodb://mongo:27017/")
db = client["vired"]
collection = db["customer"]

app.mount("/", StaticFiles(directory="app/static", html=True), name="static")

@app.post("/api/generate-customer")
async def generate_customers(request: Request):
    body = await request.json()
    region = body.get("region", "unknown")

    # Get latest customer for region
    latest = collection.find_one(
        {"region": region},
        sort=[("created_at", -1)]
    )

    # Determine starting date
    if latest and latest.get("created_at"):
        start_date = latest["created_at"] + timedelta(days=1)
    else:
        start_date = datetime.utcnow()

    # Generate 30 customers (1 per day for 1 month)
    new_customers = []
    for i in range(30):
        customer = generate_fake_customer(region)
        customer["created_at"] = start_date + timedelta(days=i)
        new_customers.append(customer)

    collection.insert_many(new_customers)
    return {
        "message": f"Inserted 30 customers for region {region} starting from {start_date.date()}",
        "start_date": start_date.isoformat()
    }
