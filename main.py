from flask import Flask, jsonify
import requests
from datetime import datetime, timedelta
import pytz

app = Flask(__name__)

# --- Parametre du kan ændre ---
SUPPLIER = "dinel_c"
PRICE_AREA = "DK1"
CHEAPEST_HOURS = 20  # Hvor mange timer per døgn du vil have tændt
INVERT_OUTPUT = False  # Sæt til True hvis 1 = sluk og 0 = tænd
# --------------------------------

def get_prices_for_day(date_str):
    url = f"https://stromligning.dk/api/Prices"
    params = {
        "supplier": SUPPLIER,
        "priceArea": PRICE_AREA,
        "date": date_str
    }
    resp = requests.get(url, params=params)
    data = resp.json()
    if isinstance(data, dict) and "prices" in data:
        prices_raw = data["prices"]
    else:
        raise TypeError(f"Expected list, got {type(data)}: {data}")
    
    prices = []
    for item in prices_raw:
        hour = datetime.fromisoformat(item["date"].replace("Z", "+00:00")).hour
        total_price = item["price"]["total"]
        prices.append((hour, total_price))
    
    return prices

def generate_schedule(prices):
    # Find grænsepris for X billigste timer
    sorted_prices = sorted(prices, key=lambda x: x[1])
    threshold_price = sorted_prices[CHEAPEST_HOURS - 1][1]

    selected_hours = [hour for hour, price in prices if price <= threshold_price]

    schedule = [1 if hour in selected_hours else 0 for hour in range(24)]

    if INVERT_OUTPUT:
        schedule = [1 - val for val in schedule]

    return schedule

@app.route("/")
def get_today_schedule():
    # Brug dansk tid
    danish_tz = pytz.timezone("Europe/Copenhagen")
    today = datetime.now(danish_tz).date()
    
    # Hvis klokken er efter 14, brug næste dag
    now = datetime.now(danish_tz)
    if now.hour >= 14:
        target_date = today + timedelta(days=1)
    else:
        target_date = today

    date_str = target_date.strftime("%Y-%m-%d")

    prices = get_prices_for_day(date_str)
    schedule = generate_schedule(prices)

    return jsonify(schedule)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
