from flask import Flask, request, jsonify
import requests
from datetime import datetime, timedelta
import pytz

app = Flask(__name__)

# Fast opsætning
SUPPLIER = "dinel_c"
PRICE_AREA = "DK1"
API_URL = "https://stromligning.dk/api/Prices"
TIMEZONE = pytz.timezone("Europe/Copenhagen")

# Cache
cached_prices = []
cached_date = None

def fetch_prices_for_today():
    global cached_prices, cached_date

    now = datetime.now(TIMEZONE)
    today = now.date()

    if cached_date == today and cached_prices:
        return cached_prices

    # Hent data fra API
    response = requests.get(API_URL, params={
        "supplier": SUPPLIER,
        "priceArea": PRICE_AREA,
        "date": today.isoformat()
    })

    if response.status_code != 200:
        raise Exception("API request failed")

    try:
        all_data = response.json()
    except Exception:
        raise Exception("Invalid JSON")

    # Filtrer præcis de 24 timer for dags dato (kl. 00:00–23:00 dansk tid)
    today_prices = []
    for entry in all_data:
        try:
            timestamp = datetime.fromisoformat(entry["date"].replace("Z", "+00:00")).astimezone(TIMEZONE)
            if timestamp.date() == today:
                total_price = entry["price"]["total"]
                hour = timestamp.hour
                today_prices.append((hour, total_price))
        except Exception:
            continue

    if len(today_prices) != 24:
        raise Exception("Did not find 24 hourly prices for today")

    # Sorter efter time (sikkerhed)
    today_prices.sort(key=lambda x: x[0])

    # Cache
    cached_prices = today_prices
    cached_date = today
    return today_prices

@app.route("/")
def cheapest_hours():
    try:
        num_hours = int(request.args.get("hours", 6))
        prices = fetch_prices_for_today()

        # Sorter efter pris og vælg de billigste N timer
        sorted_prices = sorted(prices, key=lambda x: x[1])
        cheapest_hours_set = set([hour for hour, _ in sorted_prices[:num_hours]])

        # Lav en liste med 0 for billig time, 1 for dyr
        result = [0 if hour in cheapest_hours_set else 1 for hour, _ in prices]

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": "Failed to fetch prices", "details": str(e)}), 500
