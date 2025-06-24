from faker import Faker
from datetime import datetime
import random

fake = Faker()

def generate_fake_customer(region: str):
    return {
        "name": fake.name(),
        "email": fake.email(),
        "region": region,
        "signup_channel": random.choice(["ads", "referral", "organic"]),
        "created_at": datetime.utcnow()
    }