from fastapi import FastAPI
from fastapi.responses import JSONResponse
import requests
from datetime import datetime, timedelta
import os
import uvicorn

app = FastAPI()

# Indstillinger
NUM_HOURS_ON = 6
INVERT_OUTPUT = False  # Hvis True: vælg de DYRESTE timer
LAT = 56.05065
LON = 10.250527
SUPPLIER = "dinel_c"

def get_price_data_for_tomorrow():
    tomorrow = datetime.utcnow().date() + timedelta(days=1)
    date_str = tomorrow.isoformat()

    url = f"https://stromligning.dk/api/Prices?supplier={SUPPLIER}&lat={LAT}&lon={LON}&date={date_str}"
    print("Henter data fra:", url)

    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        if not data.get("prices"):
            return {"error": "Ikke nok prisdata"}

        return data["prices"]

    except requests.RequestException as e:
        return {"error": f"HTTP-fejl: {e}"}
    except Exception as e:
        return {"error": f"Ukendt fejl: {e}"}

def get_cheapest_hours(prices, num_hours, invert=False):
    try:
        hour_prices = []

        for entry in prices:
            hour = datetime.fromisoformat(entry["date"]).hour
            price = entry["price"]["total"]
            hour_prices.append({"hour": hour, "price": price})

        sorted_hours = sorted(hour_prices, key=lambda x: x["price"], reverse=invert)
        selected = sorted_hours[:num_hours]

        selected_hours = [item["hour"] for item in selected]

        result = []
        for hour in range(24):
            result.append({
                "hour": hour,
                "on": hour in selected_hours
            })

        return result

    except Exception as e:
        return {"error": f"Fejl ved sortering: {e}"}

@app.get("/")
def read_root():
    prices = get_price_data_for_tomorrow()
    if isinstance(prices, dict) and "error" in prices:
        print("Fejl under hentning af priser:", prices["error"])
        return JSONResponse(status_code=500, content=prices)

    print("Antal prisintervaller hentet:", len(prices))
    result = get_cheapest_hours(prices, NUM_HOURS_ON, INVERT_OUTPUT)

    if isinstance(result, dict) and "error" in result:
        print("Fejl i prisbehandling:", result["error"])
        return JSONResponse(status_code=500, content=result)

    print("Resultat fra prisdata:", result)
    return result

# Starter server (Render kræver dette)
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
