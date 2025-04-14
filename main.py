from fastapi import FastAPI
from fastapi.responses import JSONResponse
import requests
from datetime import datetime, timedelta
import logging

app = FastAPI()

# Konfiguration
LAT = 56.05065
LON = 10.250527
SUPPLIER = "dinel_c"
CHEAPEST_HOURS = 6
INVERTED = False

logging.basicConfig(level=logging.INFO)

# Cache til at huske dagsdata
cached_date = None
cached_result = None

def hent_priser_fra_stromligning(dato: str):
    try:
        url = f"https://stromligning.dk/api/Prices?supplier={SUPPLIER}&lat={LAT}&lon={LON}&date={dato}"
        headers = {"User-Agent": "ShellyController/1.0"}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logging.error("HTTP-fejl: %s", str(e))
        return {"error": f"HTTP-fejl: {str(e)}"}

def beregn_timer(data, antal_timer, inverted):
    try:
        priser = []
        for entry in data.get("prices", []):
            dt = datetime.fromisoformat(entry["date"].replace("Z", "+00:00"))
            hour = dt.hour
            priser.append({
                "hour": hour,
                "total": entry["price"]["total"]
            })

        if len(priser) < 24:
            return {"error": "Ikke nok prisdata"}

        sorteret = sorted(priser, key=lambda x: x["total"])
        billigste_timer = [entry["hour"] for entry in sorteret[:antal_timer]]

        result = [{"hour": h, "on": not inverted} for h in billigste_timer]
        result += [{"hour": h, "on": inverted} for h in range(24) if h not in billigste_timer]
        return sorted(result, key=lambda x: x["hour"])
    except Exception as e:
        logging.error("Fejl i beregning: %s", str(e))
        return {"error": str(e)}

@app.get("/tider")
def get_tider():
    global cached_date, cached_result
    try:
        nu = datetime.utcnow()
        dato = nu.strftime("%Y-%m-%d")

        if cached_date == dato and cached_result:
            return cached_result

        data = hent_priser_fra_stromligning(dato)
        if "error" in data:
            return JSONResponse(content=data, status_code=500)

        result = beregn_timer(data, CHEAPEST_HOURS, INVERTED)
        if "error" in result:
            return JSONResponse(content=result, status_code=500)

        cached_date = dato
        cached_result = result
        return result
    except Exception as e:
        logging.error("Fejl i get_tider: %s", str(e))
        return JSONResponse(content={"error": str(e)}, status_code=500)

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
