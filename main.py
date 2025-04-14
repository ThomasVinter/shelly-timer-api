import os
import requests
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from datetime import datetime
import pytz

app = FastAPI()

# ==== KONFIGURATION: ændr disse som ønsket ====
ANTAL_TIMER_ON = 6
INVERTER = False  # True = relæet er TÆNDT i dyre timer
LAT = 56.05065
LON = 10.250527
# =============================================

@app.get("/tider")
def get_tider():
    try:
        # Hent priser fra stromligning.dk
        nu = datetime.now(pytz.timezone("Europe/Copenhagen"))
        dato = nu.strftime("%Y-%m-%d")
        url = f"https://www.stromligning.dk/api/historik?lat={LAT}&lon={LON}&dato={dato}"
        response = requests.get(url)
        data = response.json()

        priser = data.get("priser", [])
        if len(priser) != 24:
            raise Exception("Mangler timepriser")

        # Udvælg X billigste timer
        timepriser = [(i, priser[i]["pris"]) for i in range(24)]
        sorterede = sorted(timepriser, key=lambda x: x[1])
        billigste_timer = set(i for i, _ in sorterede[:ANTAL_TIMER_ON])

        timerliste = []
        for i in range(24):
            skal_taendes = i in billigste_timer
            if INVERTER:
                skal_taendes = not skal_taendes
            timerliste.append(1 if skal_taendes else 0)

        return JSONResponse(content={"tider": timerliste})
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

# Render kræver vi bruger port fra miljøvariabel
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
