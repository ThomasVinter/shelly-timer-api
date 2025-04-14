# Shelly Timer API

Dette er en FastAPI-baseret webservice der returnerer de X billigste timer på døgnet, inkl. tariftakster fra DinEl via stromligning.dk.

## Installation (Render.com)

1. Gå til https://render.com
2. Opret en gratis konto
3. Vælg "New Web Service" -> "Deploy from GitHub" eller "Manual Deploy"
4. Upload denne mappe som ZIP eller læg på GitHub
5. Sæt Build Command: `pip install -r requirements.txt`
6. Sæt Start Command: `uvicorn app.main:app --host 0.0.0.0 --port 10000`
7. Vælg "Free Instance"

Du får en URL som fx:
https://dinvarmepumpe.onrender.com/tider

Din Shelly-enhed skal lave HTTP GET mod denne URL hvert 30. minut.