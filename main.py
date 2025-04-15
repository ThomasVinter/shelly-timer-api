from flask import Flask, request, jsonify
import requests
from datetime import datetime, timedelta
import pytz

app = Flask(__name__)

# Fast opsætning
API_URL = "https://stromligning.dk/api/Prices"
SUPPLIER = "dinel_c"
PRICE_AREA = "DK1"

# Intern cache
cached_prices = None
cached_date = None

# Hjælpefunktion til at hente priser for i dag i lokal tid (Danmark)
def fetch_today_prices():
    global cached_prices, cached_date

    # Dansk tid
    danish_tz = pytz.timezone("Europe/Copenhagen")
    now = datetime.now(danish_tz)
    today_date = now.strftime("%Y-%m-%d")

    # Hvis vi allerede har hentet for i dag, genbrug data
    if cached_date == today_date and cached_prices:
        return cached_prices

    # Kald API
    response = requests.get(API_URL, params={
        "supplier": SUPPLIER,
        "priceArea": PRICE_AREA,
        "date": today_date
    })

    if response.status_code != 200:
        raise Exception("Failed to fetch data")

    data = response.json()
    if not isinstance(data, list):
        raise Exception("Unexpected response format")

    # Filtrér kun de 24 timer for i dag
    prices = []
    for entry in data:
        timestamp = datetime.fromisoformat(entry['date'].replace("Z", "+00:00")).astimezone(danish_tz)
        if timestamp.date() == now.date():
            prices.append((timestamp.hour, entry['price']['total']))

    # Gem til cache
    cached_prices = prices
    cached_date = today_date

    return prices

# Webroute: /?hours=4
@app.route("/")
def get_cheapest_hours():
    try:
        hours = int(request.args.get("hours", 4))
        prices = fetch_today_prices()

        # Sortér priser og tag de X billigste
        sorted_prices = sorted(prices, key=lambda x: x[1])
        cheapest_hours = set([hour for hour, _ in sorted_prices[:hours]])

        # Lav output-array: 0 hvis billig, ellers 1
        output = [0 if hour in cheapest_hours else 1 for hour in range(24)]
        return jsonify(output)

    except Exception as e:
        return jsonify({"error": "Failed to fetch prices", "details": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
