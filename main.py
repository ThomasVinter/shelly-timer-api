from flask import Flask, jsonify
import requests
from datetime import datetime
import pytz

app = Flask(__name__)

# Dansk tidszone
DK_TIMEZONE = pytz.timezone("Europe/Copenhagen")

SUPPLIER = "dinel_c"
PRICE_AREA = "DK1"

def get_prices_for_day(date_str):
    url = f"https://stromligning.dk/api/Prices?supplier={SUPPLIER}&priceArea={PRICE_AREA}&date={date_str}"
    response = requests.get(url)
    data = response.json()

    prices = []
    for entry in data:
        # Konverter UTC til dansk tid
        timestamp_utc = datetime.fromisoformat(entry["date"].replace("Z", "+00:00"))
        timestamp_dk = timestamp_utc.astimezone(DK_TIMEZONE)

        total_price = entry["price"]["total"]  # kr/kWh inkl. moms og afgifter
        prices.append((timestamp_dk, total_price))

    return prices

@app.route("/")
def get_today_schedule():
    now_dk = datetime.now(DK_TIMEZONE)
    today = now_dk.date()
    
    # Hvis klokken er efter 14 dansk tid, brug næste dags data
    if now_dk.hour >= 14:
        target_date = today + timedelta(days=1)
    else:
        target_date = today

    date_str = target_date.strftime("%Y-%m-%d")
    prices = get_prices_for_day(date_str)

    # Find de 6 billigste timer
    sorted_prices = sorted(prices, key=lambda x: x[1])
    cheapest_hours = sorted([dt.hour for dt, _ in sorted_prices[:6]])

    return jsonify({
        "date": date_str,
        "cheapest_hours": cheapest_hours
    })

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
