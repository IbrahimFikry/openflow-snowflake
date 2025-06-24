from faker import Faker
import random
from datetime import datetime
import uuid

fake = Faker()

# Capital city mapping by country
CAPITALS = {
    "USA": "Washington, D.C.",
    "Malaysia": "Kuala Lumpur",
    "Brunei": "Bandar Seri Begawan",
    "Indonesia": "Jakarta",
    "Philippines": "Manila",
    "Thailand": "Bangkok",
    "Ukraine": "Kyiv",
    "Spain": "Madrid",
    "Turkey": "Ankara",
    "Germany": "Berlin",
    "France": "Paris",
    "Nigeria": "Abuja",
    "Kenya": "Nairobi",
    "South Africa": "Pretoria",
    "Ghana": "Accra",
    "Egypt": "Cairo",
    "Japan": "Tokyo",
    "Australia": "Canberra",
    "New Zealand": "Wellington",
    "Taiwan": "Taipei"
}

def generate_fake_customer(region: str):
    now = datetime.utcnow()
    account_created = fake.date_time_between(start_date='-5y', end_date='-2y')
    last_login = fake.date_time_between(start_date='-30d', end_date='now')
    last_used_mt5 = fake.date_time_between(start_date='-60d', end_date='now')

    # Region-based country selection
    region = region.lower()
    if region == "north america":
        country = "USA"
    elif region == "southeast asia":
        country = random.choice(["Malaysia", "Brunei", "Indonesia", "Philippines", "Thailand"])
    elif region == "europe":
        country = random.choice(["Ukraine", "Spain", "Turkey", "Germany", "France"])
    elif region == "africa":
        country = random.choice(["Nigeria", "Kenya", "South Africa", "Ghana", "Egypt"])
    elif region == "oceania":
        country = random.choice(["Japan", "Australia", "New Zealand", "Taiwan"])
    else:
        country = fake.country()

    # Use the capital city from the mapping
    city = CAPITALS.get(country, fake.city())
    lat = float(fake.latitude())
    lon = float(fake.longitude())
    platforms = random.choice(['mt5', 'web', 'mobile', 'web,mobile', 'mt5,web', 'mt5,mobile'])
    watchlist = random.sample(['ETHUSD', 'USDJPY', 'BTCUSD', 'EURUSD', 'XAUUSD'], k=2)

    return {
        "customer_id": f"CUST{str(uuid.uuid4().int)[:7]}",
        "ip_address": fake.ipv4(),
        "country": country,
        "city": city,
        "latitude": lat,
        "longitude": lon,
        "watchlist": ",".join(watchlist),
        "last_login": last_login,
        "account_created": account_created,
        "platforms": platforms,
        "last_used_web": None if "web" not in platforms else fake.date_time_between(start_date='-60d', end_date='now'),
        "last_used_mobile": None if "mobile" not in platforms else fake.date_time_between(start_date='-60d', end_date='now'),
        "last_used_mt5": last_used_mt5 if "mt5" in platforms else None,
        "region": region,
        "created_at": now,
        "added_from_dashboard": True
    }
