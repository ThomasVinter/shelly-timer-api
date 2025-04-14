from fastapi import FastAPI
from fastapi.responses import JSONResponse
import requests
import logging
import os
from datetime import datetime

app = FastAPI()

# Konfiguration
LAT = 56.05065
LON = 10.250527
SUPPLIER_ID = "dinel_c"
CHEAPEST_HOURS = 6
INVERTED = False

logging.basicConfig(level=logging.INFO)

def hent_data_fra_stromligning():
    try:
        lat = 56.05065
        lon = 10.250527

        # 1. Find leverandør
        find_url = f"https://stromligning.dk/api/suppliers/find?lat={lat}&long={lon}"
        headers = {
            "User-Agent": "ShellyController/1.0",
            "Accept": "application/json"
        }
        find_resp = requests.get(find_url, headers=headers, timeout=10)
        find_resp.raise_for_status()
        leverandorer = find_resp.json()
        if not leverandorer:
            return {"error": "Ingen leverandør fundet"}
        supplier_id = leverandorer[0]["id"]

        # 2. Hent priser for den leverandør
        prices_url = f"https://stromligning.dk/api/Prices?supplier={supplier_id}"
        prices_resp = requests.get(prices_url, headers=headers, timeout=10)
        prices_resp.raise_for_status()
        return prices_resp.json()
    
    except Exception as e:
        logging.error("Fejl ved hentning af data: %s", str(e))
        return {"error": f"HTTP-fejl: {str(e)}"}


def beregn_timer(data, antal_timer, inverted):
    try:
        priser = []
        for entry in data.get("Prices", []):
            priser.append({
                "hour": entry["Hour"],
                "total": entry["Total"]
            })

        if not priser or len(priser) < antal_timer:
            return {"error": "Ikke nok prisdata"}

        sorteret = sorted(priser, key=lambda x: x["total"])
        billigste_timer = [entry["hour"] for entry in sorteret[:antal_timer]]

        result = [{"hour": h, "on": not inverted} for h in billigste_timer]
        result += [{"hour": h, "on": inverted} for h in range(24) if h not in billigste_timer]
        return sorted(result, key=lambda x: x["hour"])
    except Exception as e:
        return {"error": str(e)}

@app.get("/tider")
def get_tider():
    try:
        data = hent_data_fra_stromligning()
        if "error" in data:
            return JSONResponse(content=data, status_code=500)
        logging.info("Data modtaget: %s", data)
        result = beregn_timer(data, CHEAPEST_HOURS, INVERTED)
        logging.info("Timer beregnet: %s", result)
        return result
    except Exception as e:
        logging.error("Fejl i get_tider: %s", str(e))
        return JSONResponse(content={"error": str(e)}, status_code=500)

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
