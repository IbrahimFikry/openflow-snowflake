from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from pymongo import MongoClient
from datetime import datetime
from app.customer_utils import generate_fake_customer
from fastapi.responses import JSONResponse
from bson import ObjectId

app = FastAPI()

# MongoDB client
client = MongoClient("mongodb://mongo:27017/")
db = client["vired"]
collection = db["customer"]

@app.post("/api/generate-customer")
async def generate_customer(request: Request):
    try:
        body = await request.json()
        region = body.get("region", "unknown")

        customer = generate_fake_customer(region)
        result = collection.insert_one(customer)

        customer["_id"] = str(result.inserted_id)
        customer["created_at"] = customer["created_at"].isoformat()

        return JSONResponse(content={
            "message": f"Customer added to region {region}",
            "customer": customer
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})

# Bulk insertion endpoint generator
def create_bulk_endpoint(path: str, count: int):
    @app.post(path)
    async def bulk_insert(request: Request):
        try:
            body = await request.json()
            region = body.get("region", "unknown")

            customers = [generate_fake_customer(region) for _ in range(count)]
            collection.insert_many(customers)

            return {"message": f"{count} customers added to region {region}"}
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JSONResponse(status_code=500, content={"error": str(e)})

# Define multiple endpoints
create_bulk_endpoint("/api/generate-customer-50", 50)
create_bulk_endpoint("/api/generate-customer-250", 250)
create_bulk_endpoint("/api/generate-customer-500", 500)
create_bulk_endpoint("/api/generate-customer-1000", 1000)

# Serve static frontend
app.mount("/", StaticFiles(directory="app/static", html=True), name="static")
