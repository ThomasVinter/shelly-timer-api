from flask import Flask, jsonify
import requests
from datetime import datetime, timedelta
import pytz

app = Flask(__name__)

# --- Parametre du kan ændre ---
SUPPLIER = "dinel_c"
PRICE_AREA = "DK1"
CHEAPEST_HOURS = 20  # Antal ønskede "1" i resultatet
INVERT_OUTPUT = False  # Sæt til True hvis 1 = sluk og 0 = tænd
# --------------------------------

def get_prices_for_day(date_str):
    url = "https://stromligning.dk/api/Prices"
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
        raise TypeError(f"Expected dict with 'prices', got {data}")

    prices = []
    for item in prices_raw:
        dt = datetime.fromisoformat(item["date"].replace("Z", "+00:00"))
        hour = dt.hour
        price = item["price"]["total"]
        prices.append((hour, price))

    return prices

def generate_schedule(prices):
    # Sortér på pris og tag præcis X timer
    sorted_prices = sorted(prices, key=lambda x: x[1])
    selected_hours = set()

    for hour, price in sorted_prices:
        selected_hours.add(hour)
        if len(selected_hours) == CHEAPEST_HOURS:
            break

    schedule = [1 if hour in selected_hours else 0 for hour in range(24)]

    if INVERT_OUTPUT:
        schedule = [1 - val for val in schedule]

    return schedule

@app.route("/")
def get_schedule():
    danish_tz = pytz.timezone("Europe/Copenhagen")
    now = datetime.now(danish_tz)

    # Brug næste dag hvis klokken er efter 14
    target_date = now.date()
    if now.hour >= 14:
        target_date += timedelta(days=1)

    date_str = target_date.strftime("%Y-%m-%d")
    prices = get_prices_for_day(date_str)
    schedule = generate_schedule(prices)
    return jsonify(schedule)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
