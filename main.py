from fastapi import FastAPI
from fastapi.responses import JSONResponse
import requests
from datetime import datetime
import logging
import os

app = FastAPI()

# Konfiguration
LAT = 56.05065
LON = 10.250527
CHEAPEST_HOURS = 6
INVERTED = False

logging.basicConfig(level=logging.INFO)

def hent_data_fra_stromligning():
    try:
        url = f"https://www.stromligning.dk/api/Prices?lat={LAT}&lon={LON}"
        headers = {
            "User-Agent": "ShellyController/1.0",
            "Accept": "application/json"
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        logging.info("Svar fra stromligning.dk (statuskode %s): %s", response.status_code, response.text)

        data = response.json()

        if "Prices" not in data or not isinstance(data["Prices"], list):
            logging.error("Ugyldigt svarformat fra API: %s", data)
            return {"error": "Ugyldigt svar fra stromligning.dk"}

        return data

    except requests.exceptions.HTTPError as e:
        logging.error("HTTP-fejl: %s", str(e))
        return {"error": f"HTTP-fejl: {str(e)}"}
    except Exception as e:
        logging.error("Anden fejl ved hentning: %s", str(e))
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
    port = int(os.environ.get("PORT", 8000))
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=port)