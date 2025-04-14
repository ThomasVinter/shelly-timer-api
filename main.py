from fastapi import FastAPI
from fastapi.responses import JSONResponse
import requests
from datetime import datetime
import pytz

app = FastAPI()

# === KONFIGURATION ===
LAT = "56.05065"
LONG = "10.250527"
SUPPLIER_INDEX = 0  # 0 = nærmeste supplier
ADDITIONAL_COST = 0.04  # DinEl tariftakst pr. kWh
HOURS_TO_KEEP_ON = 8  # Antal timer varmepumpen skal køre
INVERTED = False  # True = varmepumpen kører i dyre timer

@app.get("/tider")
def get_on_hours():
    # 1. Find supplier
    supplier_url = f"https://stromligning.dk/api/suppliers/find?lat={LAT}&long={LONG}"
    supplier_res = requests.get(supplier_url)
    suppliers = supplier_res.json()
    if not suppliers:
        return JSONResponse(content={"error": "Ingen suppliers fundet"}, status_code=500)

    supplier = suppliers[SUPPLIER_INDEX]
    supplier_id = supplier["id"]
    price_area = supplier["priceArea"]

    # 2. Hent priser for i dag
    now = datetime.now(pytz.timezone("Europe/Copenhagen"))
    date_str = now.strftime("%Y-%m-%d")
    from_time = f"{date_str}T00:00:00"
    to_time = f"{date_str}T23:00:00"

    price_url = (
        f"https://stromligning.dk/api/prices?from={from_time}&to={to_time}"
        f"&supplierId={supplier_id}&priceArea={price_area}"
    )
    price_res = requests.get(price_url)
    data = price_res.json()

    # 3. Beregn totalpris per time
    prices = []
    for hour_data in data:
        hour = datetime.fromisoformat(hour_data["date"]).hour
        total = hour_data["total"] + ADDITIONAL_COST
        prices.append({"hour": hour, "price": total})

    # 4. Sorter og udvælg billigste timer
    prices.sort(key=lambda x: x["price"])
    keep_on_hours = [p["hour"] for p in prices[:HOURS_TO_KEEP_ON]]

    # 5. Returnér tænd/sluk-timer baseret på inverteret logik
    if INVERTED:
        all_hours = set(range(24))
        result = sorted(list(all_hours - set(keep_on_hours)))
    else:
        result = sorted(keep_on_hours)

    return {"on_hours": result}