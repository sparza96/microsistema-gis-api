"""
API GIS para Railway - Con puntos georreferenciados reales
"""

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

app = FastAPI(title="Microsistema GIS API - Railway")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# PUNTOS REALES DE CONCEPCIÓN (georreferenciados)
PUNTOS_CONCEPCION = [
    {"lat": -36.8269, "lon": -73.0501, "nombre": "Hospital Regional", "tipo": "hospital"},
    {"lat": -36.8205, "lon": -73.0442, "nombre": "Hospital Clínico UdeC", "tipo": "hospital"},
    {"lat": -36.8288, "lon": -73.0482, "nombre": "Hospital Guillermo Grant", "tipo": "hospital"},
    {"lat": -36.8335, "lon": -73.0516, "nombre": "Hospital Las Higueras", "tipo": "hospital"},
    {"lat": -36.8251, "lon": -73.0593, "nombre": "Universidad de Concepción", "tipo": "school"},
    {"lat": -36.8187, "lon": -73.0414, "nombre": "Colegio Concepción", "tipo": "school"},
    {"lat": -36.8314, "lon": -73.0552, "nombre": "Colegio San Agustín", "tipo": "school"},
    {"lat": -36.8227, "lon": -73.0621, "nombre": "Banco Estado", "tipo": "bank"},
    {"lat": -36.8273, "lon": -73.0477, "nombre": "Banco Santander", "tipo": "bank"},
    {"lat": -36.8301, "lon": -73.0532, "nombre": "Banco Chile", "tipo": "bank"},
    {"lat": -36.8278, "lon": -73.0491, "nombre": "Farmacia Cruz Verde", "tipo": "pharmacy"},
    {"lat": -36.8245, "lon": -73.0459, "nombre": "Farmacia Salcobrand", "tipo": "pharmacy"},
    {"lat": -36.8309, "lon": -73.0514, "nombre": "1° Comisaría Concepción", "tipo": "police"},
    {"lat": -36.8198, "lon": -73.0567, "nombre": "2° Comisaría", "tipo": "police"},
]

DATOS_EJEMPLO = {
    "Concepción": {"Hospitales": 4, "Escuelas": 3, "Bancos": 3, "Farmacias": 2, "Comisarías": 2, "total": 14, "puntos": PUNTOS_CONCEPCION},
    "Santiago": {"Hospitales": 45, "Escuelas": 320, "Bancos": 120, "Farmacias": 280, "Comisarías": 25, "total": 790, "puntos": []},
    "Valparaíso": {"Hospitales": 10, "Escuelas": 85, "Bancos": 28, "Farmacias": 60, "Comisarías": 7, "total": 190, "puntos": []},
    "Viña del Mar": {"Hospitales": 8, "Escuelas": 72, "Bancos": 25, "Farmacias": 55, "Comisarías": 6, "total": 166, "puntos": []},
}

@app.get("/")
def root():
    return {"mensaje": "Microsistema GIS API en Railway", "ciudades_disponibles": list(DATOS_EJEMPLO.keys())}

@app.get("/reporte_json")
def reporte_json(ciudad: str = Query(...)):
    ciudad_base = ciudad.split(",")[0].strip()
    if ciudad_base in DATOS_EJEMPLO:
        d = DATOS_EJEMPLO[ciudad_base]
        return {
            "status": "success",
            "ciudad": ciudad,
            "total_amenidades": d["total"],
            "desglose": {
                "Hospitales": d["Hospitales"],
                "Escuelas": d["Escuelas"],
                "Bancos": d["Bancos"],
                "Farmacias": d["Farmacias"],
                "Comisarías": d["Comisarías"]
            }
        }
    return {"status": "error", "mensaje": f"{ciudad_base} no disponible. Usa: {list(DATOS_EJEMPLO.keys())}"}

@app.get("/mapa", response_class=HTMLResponse)
def mapa(ciudad: str = Query(...)):
    ciudad_base = ciudad.split(",")[0].strip()
    datos = DATOS_EJEMPLO.get(ciudad_base, DATOS_EJEMPLO["Concepción"])
    puntos = datos.get("puntos", [])
    
    # Generar marcadores
    marcadores = ""
    for p in puntos:
        color = {"hospital": "red", "school": "blue", "bank": "green", "pharmacy": "purple", "police": "orange"}.get(p["tipo"], "gray")
        marcadores += f"""
        L.marker([{p['lat']}, {p['lon']}], {{icon: L.divIcon({{html: '📍', iconSize: [20,20], className: 'marker-{color}'}})}})
            .bindPopup('<b>{p['nombre']}</b><br>{p["tipo"]}').addTo(map);
        """
    
    # Obtener coordenadas del centro
    if puntos:
        center_lat = puntos[0]["lat"]
        center_lon = puntos[0]["lon"]
    else:
        center_lat, center_lon = -36.827, -73.050
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Mapa - {ciudad}</title>
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <style>
            #map {{ height: 500px; }}
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            .info {{ padding: 10px; background: #f0f4f8; border-radius: 8px; margin-bottom: 10px; }}
            .marker-red {{ color: red; font-size: 20px; }}
            .marker-blue {{ color: blue; font-size: 20px; }}
            .marker-green {{ color: green; font-size: 20px; }}
            .marker-purple {{ color: purple; font-size: 20px; }}
            .marker-orange {{ color: orange; font-size: 20px; }}
        </style>
    </head>
    <body>
        <h2>🗺️ {ciudad}</h2>
        <div class="info">
            📊 <strong>Total de amenidades: {datos['total']}</strong><br>
            🏥 Hospitales: {datos['Hospitales']} | 🏫 Escuelas: {datos['Escuelas']} | 🏦 Bancos: {datos['Bancos']} | 💊 Farmacias: {datos['Farmacias']} | 🚔 Comisarías: {datos['Comisarías']}
        </div>
        <div id="map"></div>
        <p>
            <a href="/reporte_json?ciudad={ciudad}">Ver JSON</a> | 
            <a href="/ciudades_sugeridas">Ciudades disponibles</a>
        </p>
        <script>
            var map = L.map('map').setView([{center_lat}, {center_lon}], 14);
            L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                attribution: '© OpenStreetMap'
            }}).addTo(map);
            {marcadores}
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)

@app.get("/ciudades_sugeridas")
def sugeridas():
    return {"ciudades": list(DATOS_EJEMPLO.keys())}