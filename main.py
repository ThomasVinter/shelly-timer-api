from fastapi import FastAPI
from fastapi.responses import JSONResponse
import requests
from datetime import datetime, timedelta
import logging
import os

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
        i_dag = datetime.now()
        i_morgen = i_dag + timedelta(days=1)
        dato = i_morgen.strftime("%Y-%m-%d")

        url = (
            f"https://stromligning.dk/api/Prices"
            f"?supplier={SUPPLIER_ID}&lat={LAT}&lon={LON}&date={dato}"
        )
        headers = {
            "User-Agent": "ShellyController/1.0",
            "Accept": "application/json"
        }

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        logging.info("Svar fra API: %s", response.text)
        return response.json()
    except Exception as e:
        logging.error("Fejl i hent_data_fra_stromligning: %s", str(e))
        return {"error": f"HTTP-fejl: {str(e)}"}

def beregn_timer(data, antal_timer, inverted):
    try:
        priser = []
        for entry in data.get("prices", []):
            hour = datetime.fromisoformat(entry["date"]).hour
            priser.append({
                "hour": hour,
                "total": entry["price"]["total"]
            })

        if not priser or len(priser) < 24:
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

# Start server når du kører lokalt eller hos Render
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
