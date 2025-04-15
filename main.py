from flask import Flask, jsonify
from datetime import datetime
from zoneinfo import ZoneInfo
import requests

app = Flask(__name__)

SUPPLIER = "dinel_c"
PRICE_AREA = "DK1"
NUMBER_OF_CHEAPEST_HOURS = 6
INVERT_SELECTION = False

def get_prices_for_day(date_str):
    url = f"https://stromligning.dk/api/Prices?priceArea={PRICE_AREA}&supplier={SUPPLIER}&date={date_str}"
    response = requests.get(url)
    data = response.json()

    if not isinstance(data, dict) or "prices" not in data:
        raise TypeError(f"Expected dict with 'prices' key, got: {data}")

    prices_raw = data["prices"]
    prices = []
    for entry in prices_raw:
        timestamp_utc = datetime.fromisoformat(entry["date"].replace("Z", "+00:00"))
        timestamp_local = timestamp_utc.astimezone(ZoneInfo("Europe/Copenhagen"))
        prices.append({
            "hour": timestamp_local.hour,
            "price": entry["price"]["total"]
        })

    return prices

def get_schedule(prices, num_hours=NUMBER_OF_CHEAPEST_HOURS, invert=INVERT_SELECTION):
    sorted_prices = sorted(prices, key=lambda x: x["price"])
    cheapest_hours = sorted([p["hour"] for p in sorted_prices[:num_hours]])

    schedule = [1 if hour in cheapest_hours else 0 for hour in range(24)]
    if invert:
        schedule = [0 if bit else 1 for bit in schedule]
    return schedule

@app.route("/")
def get_today_schedule():
    today = datetime.now(ZoneInfo("Europe/Copenhagen"))
    date_str = today.strftime("%Y-%m-%d")
    prices = get_prices_for_day(date_str)
    schedule = get_schedule(prices)
    return jsonify(schedule)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
