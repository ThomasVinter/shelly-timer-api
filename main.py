from fastapi import FastAPI
from fastapi.responses import JSONResponse
import requests
from datetime import datetime
import logging

app = FastAPI()

# Konfiguration (du kan ændre disse manuelt 2 gange årligt)
CHEAPEST_HOURS = 6
INVERTED = False  # False = tænd de billigste timer, True = sluk de billigste timer

# Fast konfiguration
SUPPLIER = "dinel_c"
PRICE_AREA = "DK1"

logging.basicConfig(level=logging.INFO)

def hent_data_fra_stromligning():
    try:
        dato = datetime.utcnow().date().isoformat()  # F.eks. "2025-04-14"
        url = f"https://stromligning.dk/api/Prices?supplier={SUPPLIER}&priceArea={PRICE_AREA}&date={dato}"
        headers = {
            "User-Agent": "ShellyController/1.0",
            "Accept": "application/json"
        }

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        logging.info("Svar fra stromligning.dk: %s", response.text)
        return response.json()
    except Exception as e:
        logging.error("Fejl ved hentning af data: %s", str(e))
        return {"error": f"HTTP-fejl: {str(e)}"}


def beregn_timer(data, antal_timer, inverted):
    try:
        priser = []

        for entry in data.get("prices", []):
            # Træk timen ud fra tidspunktet
            dt = datetime.fromisoformat(entry["date"].replace("Z", "+00:00"))
            hour = dt.hour
            total = entry["price"]["total"]
            priser.append({
                "hour": hour,
                "total": total
            })

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
        if "error" in result:
            return JSONResponse(content=result, status_code=500)

        return result
    except Exception as e:
        logging.error("Fejl i get_tider: %s", str(e))
        return JSONResponse(content={"error": str(e)}, status_code=500)


if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
