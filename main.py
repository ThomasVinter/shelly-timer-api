from fastapi import FastAPI
from fastapi.responses import JSONResponse
import requests
from datetime import datetime, timedelta
import logging

app = FastAPI()

# Konfiguration
LAT = 56.05065
LON = 10.250527
CHEAPEST_HOURS = 6
INVERTED = False

logging.basicConfig(level=logging.INFO)

def hent_data_fra_stromligning():
    try:
        supplier = "dinel_c"
        today = datetime.now().strftime("%Y-%m-%d")
        url = f"https://stromligning.dk/api/Prices?supplier={supplier}&lat={LAT}&lon={LON}&date={today}"
        headers = {
            "User-Agent": "ShellyController/1.0",
            "Accept": "application/json"
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        logging.info("Svar fra stromligning.dk OK")
        return response.json()
    except Exception as e:
        logging.error("Fejl ved hentning af data: %s", str(e))
        return {"error": f"HTTP-fejl: {str(e)}"}

def beregn_timer(data, antal_timer, inverted):
    try:
        priser = []
        for entry in data.get("prices", []):
            dt_utc = datetime.fromisoformat(entry["date"].replace("Z", "+00:00"))
            dt_local = dt_utc + timedelta(hours=2)  # Dansk sommertid (UTC+2)
            hour = dt_local.hour
            total = entry["price"]["total"]
            priser.append({"hour": hour, "total": total})

            # DEBUG: Udskriv tidspunkt og pris
            logging.info(f"Time (lokal): {dt_local.strftime('%Y-%m-%d %H:%M')} - Totalpris: {total:.3f} kr")

        if len(priser) < antal_timer:
            return {"error": "Ikke nok prisdata"}

        sorteret = sorted(priser, key=lambda x: x["total"])
        billigste_timer = [entry["hour"] for entry in sorteret[:antal_timer]]

        result = [{"hour": h, "on": not inverted} for h in billigste_timer]
        result += [{"hour": h, "on": inverted} for h in range(24) if h not in billigste_timer]
        return sorted(result, key=lambda x: x["hour"])

    except Exception as e:
        logging.error("Fejl i beregn_timer: %s", str(e))
        return {"error": str(e)}

@app.get("/tider")
def get_tider():
    try:
        data = hent_data_fra_stromligning()
        if "error" in data:
            return JSONResponse(content=data, status_code=500)
        result = beregn_timer(data, CHEAPEST_HOURS, INVERTED)
        return result
    except Exception as e:
        logging.error("Fejl i get_tider: %s", str(e))
        return JSONResponse(content={"error": str(e)}, status_code=500)

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
