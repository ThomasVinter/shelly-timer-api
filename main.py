from fastapi import FastAPI
from fastapi.responses import JSONResponse
from datetime import datetime, timedelta
import requests
import logging

app = FastAPI()

# Konfiguration
LAT = 56.05065
LON = 10.250527
SUPPLIER = "dinel_c"
ANTAL_TIMER = 6              # Antal billigste timer hvor varmepumpen skal være tændt
INVERTER = False             # False = tænd i billige timer, True = sluk i billige timer

# Cache
sidst_hentet_dato = None
sidst_genereret_resultat = None

# Logging
logging.basicConfig(level=logging.INFO)

@app.get("/tider")
def get_tider():
    global sidst_hentet_dato, sidst_genereret_resultat

    now = datetime.now()

    # Brug i morgen efter kl. 14, ellers i dag
    if now.hour >= 14:
        dato = (now + timedelta(days=1)).strftime("%Y-%m-%d")
    else:
        dato = now.strftime("%Y-%m-%d")

    if sidst_hentet_dato == dato and sidst_genereret_resultat:
        return JSONResponse(content=sidst_genereret_resultat)

    priser = hent_data_fra_stromligning(dato)
    if "error" in priser:
        return JSONResponse(content=priser)

    try:
        liste = lav_timer_liste(priser)
        sidst_hentet_dato = dato
        sidst_genereret_resultat = liste
        return JSONResponse(content=liste)
    except Exception as e:
        logging.error("Fejl ved behandling: %s", str(e))
        return JSONResponse(content={"error": str(e)})

def hent_data_fra_stromligning(dato):
    try:
        url = (
            f"https://stromligning.dk/api/Prices"
            f"?supplier={SUPPLIER}"
            f"&lat={LAT}&lon={LON}"
            f"&date={dato}"
        )
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

def lav_timer_liste(data):
    if "prices" not in data:
        raise ValueError("Ingen prisdata tilgængelig")

    priser = data["prices"]
    if len(priser) < 24:
        raise ValueError("Ikke nok prisdata")

    # Udtræk time og totalpris
    timepriser = []
    for entry in priser:
        dt = datetime.fromisoformat(entry["date"].replace("Z", "+00:00"))
        pris = entry["price"]["total"]
        timepriser.append({"hour": dt.hour, "pris": pris})

    # Sortér og vælg de billigste timer
    sorterede = sorted(timepriser, key=lambda x: x["pris"])
    billigste_timer = set(entry["hour"] for entry in sorterede[:ANTAL_TIMER])

    # Generér 24 elementer
    resultat = []
    for hour in range(24):
        on = hour in billigste_timer
        if INVERTER:
            on = not on
        resultat.append({"hour": hour, "on": on})

    return resultat
