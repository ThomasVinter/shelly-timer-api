
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import requests
from datetime import datetime

app = FastAPI()

# Konfiguration (du kan ændre disse direkte i koden)
LAT = 56.05065
LON = 10.250527
CHEAPEST_HOURS = 6
INVERTED = False

def hent_data_fra_stromligning(lat, lon):
    try:
        url = f"https://www.stromligning.dk/api/Prices?lat={lat}&lon={lon}"
        headers = {"User-Agent": "ShellyController/1.0"}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}

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
    data = hent_data_fra_stromligning(LAT, LON)
    if "error" in data:
        return JSONResponse(content=data, status_code=500)
    result = beregn_timer(data, CHEAPEST_HOURS, INVERTED)
    return result
    if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)

