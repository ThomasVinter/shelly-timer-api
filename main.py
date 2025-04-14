from fastapi import FastAPI
from fastapi.responses import JSONResponse
import requests
from datetime import datetime, timedelta
import uvicorn

app = FastAPI()

LAT = 56.05065
LON = 10.250527
ANTAL_TIMER_TAENDT = 6
INVERTERET = False  # False = tænd de billigste timer, True = sluk de dyreste

def hent_leverandoer():
    try:
        url = f"https://stromligning.dk/api/suppliers/find?lat={LAT}&long={LON}"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return data[0]["id"]
    except Exception as e:
        raise RuntimeError(f"Kunne ikke finde leverandør: {e}")

def hent_priser(supplier_id):
    try:
        i_dag = datetime.now()
        hvis_klokken_efter_14 = i_dag.hour >= 14
        dato = (i_dag + timedelta(days=1)) if hvis_klokken_efter_14 else i_dag
        dato_str = dato.strftime("%Y-%m-%d")

        url = f"https://stromligning.dk/api/Prices?supplier={supplier_id}&date={dato_str}"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        priser = data.get("prices", [])
        if len(priser) < 24:
            raise ValueError("Ikke nok prisdata")

        return priser
    except Exception as e:
        raise RuntimeError(f"HTTP-fejl: {e}")

def beregn_timer(priser):
    # Lav en liste med (hour, total_price)
    timesliste = []
    for entry in priser:
        dt = datetime.fromisoformat(entry["date"].replace("Z", "+00:00"))
        hour = dt.hour
        total = entry["price"]["total"]
        timesliste.append((hour, total))

    # Sortér efter pris (lav til høj eller høj til lav afhængigt af INVERTERET)
    sorteret = sorted(timesliste, key=lambda x: x[1], reverse=INVERTERET)

    valgte_timer = set(hour for hour, _ in sorteret[:ANTAL_TIMER_TAENDT])

    resultat = [{"hour": hour, "on": hour in valgte_timer} for hour in range(24)]
    return resultat

@app.get("/")
def get_timer():
    try:
        supplier_id = hent_leverandoer()
        priser = hent_priser(supplier_id)
        timer = beregn_timer(priser)
        return JSONResponse(content=timer)
    except Exception as e:
        return JSONResponse(content={"error": str(e)})

import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
