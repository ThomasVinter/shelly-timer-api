from flask import Flask, request, jsonify
import requests
from datetime import datetime
import pytz

app = Flask(__name__)

cached_prices = None
cached_date = None

dk_tz = pytz.timezone("Europe/Copenhagen")

def fetch_prices():
    date_str = datetime.now(dk_tz).strftime("%Y-%m-%d")
    r = requests.get("https://stromligning.dk/api/Prices", params={
        "supplier": "dinel_c",
        "priceArea": "DK1",
        "date": date_str
    })
    r.raise_for_status()
    full_data = r.json()

    # Forventet struktur: {"data": [ ... ]}
    data = full_data["data"]

    # Sorter på time og returnér kun første 24 timer
    prices = sorted((e for e in data if 0 <= e["hour"] < 24), key=lambda x: x["hour"])
    return datetime.now(dk_tz).date(), [p["value"] for p in prices]


@app.route("/")
def cheapest_hours():
    global cached_prices, cached_date
    today = datetime.now(dk_tz).date()

    if cached_prices is None or cached_date != today:
        try:
            cached_date, cached_prices = fetch_prices()
        except Exception as e:
            return jsonify({"error": "Failed to fetch prices", "details": str(e)}), 500

    try:
        hours = int(request.args.get("hours", "8"))
        if not 0 <= hours <= 24:
            raise ValueError()
    except ValueError:
        return jsonify({"error": "Invalid 'hours' parameter"}), 400

    indexed = list(enumerate(cached_prices))
    indexed.sort(key=lambda x: x[1])
    cheapest = set(i for i, _ in indexed[:hours])

    return jsonify([0 if i in cheapest else 1 for i in range(24)])

@app.route("/raw-prices")
def raw_prices():
    global cached_prices, cached_date
    if cached_prices is None or cached_date != datetime.now(dk_tz).date():
        try:
            cached_date, cached_prices = fetch_prices()
        except Exception as e:
            return jsonify({"error": "Failed to fetch prices", "details": str(e)}), 500

    return jsonify({
        "date": cached_date.isoformat(),
        "prices": cached_prices
    })

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
