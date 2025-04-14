from flask import Flask, jsonify
import requests
from datetime import datetime, timedelta
import pytz

app = Flask(__name__)

# Tidszoner
utc = pytz.utc
dk_tz = pytz.timezone("Europe/Copenhagen")

# Antal ønskede billigste timer pr. dag
CHEAPEST_HOURS = 6
INVERT_SELECTION = False  # Sæt til True hvis du vil vælge de dyreste i stedet

def get_prices_for_day(date_str):
    url = f"https://stromligning.dk/api/Prices?priceArea=DK1&supplier=dinel_c&date={date_str}"
    response = requests.get(url)
    data = response.json()

    prices = []
    for entry in data:
        # Konverter UTC ISO-timestamp til lokal dansk tid (automatisk med sommer/vintertid)
        timestamp_utc = datetime.fromisoformat(entry["date"].replace("Z", "+00:00"))
        timestamp_local = timestamp_utc.astimezone(dk_tz)

        prices.append({
            "timestamp_utc": timestamp_utc,
            "timestamp_local": timestamp_local,
            "total_price": entry["price"]["total"]
        })

    return prices

def get_cheapest_hours(prices, hours=6, invert=False):
    sorted_prices = sorted(prices, key=lambda p: p["total_price"], reverse=invert)
    selected = sorted(sorted_prices[:hours], key=lambda p: p["timestamp_local"].hour)
    return selected

@app.route("/")
def get_today_schedule():
    now = datetime.now(dk_tz)
    
    # Brug morgendagens dato, hvis klokken er efter 14:00 (priser for i morgen er først tilgængelige derefter)
    if now.hour >= 14:
        target_date = now + timedelta(days=1)
    else:
        target_date = now

    date_str = target_date.strftime("%Y-%m-%d")
    prices = get_prices_for_day(date_str)
    cheapest = get_cheapest_hours(prices, hours=CHEAPEST_HOURS, invert=INVERT_SELECTION)

    result = []
    for entry in cheapest:
        hour = entry["timestamp_local"].hour
        result.append(hour)

    return jsonify({
        "date": date_str,
        "selected_hours": result
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
