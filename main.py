from fastapi import FastAPI
from fastapi.responses import JSONResponse
import requests
from datetime import datetime, timedelta
import os

app = FastAPI()

# KONFIGURATION – juster manuelt
LAT = 56.05065
LON = 10.250527
SUPPLIER_ID = "dinel_c"
NUM_HOURS_ON = 6  # antal billigste timer hvor varmepumpen skal være TÆNDT
INVERT_OUTPUT = False  # hvis True, inverteres så den er SLUKKET de billigste timer

def get_price_data_for_tomorrow():
    # Dato for i morgen
    tomorrow = (datetime.utcnow() + timedelta(days=1)).date()
    url = f"https://stromligning.dk/api/Prices?supplier={SUPPLIER_ID}&lat={LAT}&lon={LON}&date={tomorrow}"

    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return data.get("prices", [])
    except Exception as e:
        return {"error": f"HTTP-fejl: {e}"}

def get_cheapest_hours(prices, num_hours, invert):
    hourly_prices = []

    for entry in prices:
        timestamp = entry["date"]
        hour = datetime.fromisoformat(timestamp.replace("Z", "+00:00")).hour
        total_price = entry["price"]["total"]
        hourly_prices.append((hour, total_price))

    if len(hourly_prices) < 24:
        return {"error": "Ikke nok prisdata"}

    # Sorter timer efter pris
    sorted_by_price = sorted(hourly_prices, key=lambda x: x[1])
    cheapest_hours = set(hour for hour, _ in sorted_by_price[:num_hours])

    result = []
    for hour in range(24):
        is_on = (hour in cheapest_hours)
        result.append({"hour": hour, "on": not is_on if invert else is_on})

    return result

@app.get("/")
def read_root():
    prices = get_price_data_for_tomorrow()
    if isinstance(prices, dict) and "error" in prices:
        return JSONResponse(status_code=500, content=prices)

    result = get_cheapest_hours(prices, NUM_HOURS_ON, INVERT_OUTPUT)
    if isinstance(result, dict) and "error" in result:
        return JSONResponse(status_code=500, content=result)

    return result

# --- Render kræver denne del for at finde porten ---
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
