"""
API GIS Lite - Con datos de ejemplo para demostración
"""

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

app = FastAPI(title="Microsistema GIS API - Demo")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Datos de ejemplo para ciudades chilenas
DATOS_EJEMPLO = {
    "Santiago": {"Hospitales": 45, "Escuelas": 320, "Bancos": 120, "Farmacias": 280, "Comisarías": 25, "total": 790},
    "Concepción": {"Hospitales": 12, "Escuelas": 98, "Bancos": 35, "Farmacias": 72, "Comisarías": 8, "total": 225},
    "Valparaíso": {"Hospitales": 10, "Escuelas": 85, "Bancos": 28, "Farmacias": 60, "Comisarías": 7, "total": 190},
    "Viña del Mar": {"Hospitales": 8, "Escuelas": 72, "Bancos": 25, "Farmacias": 55, "Comisarías": 6, "total": 166},
    "Temuco": {"Hospitales": 7, "Escuelas": 65, "Bancos": 20, "Farmacias": 48, "Comisarías": 5, "total": 145},
    "Antofagasta": {"Hospitales": 9, "Escuelas": 70, "Bancos": 22, "Farmacias": 52, "Comisarías": 6, "total": 159},
}

@app.get("/")
def root():
    return {
        "mensaje": "Microsistema GIS API - Demo funcionando",
        "endpoints": [
            "/reporte_json?ciudad=Santiago, Chile",
            "/mapa?ciudad=Concepción, Chile",
            "/ciudades_sugeridas"
        ]
    }

@app.get("/reporte_json")
def reporte_json(ciudad: str = Query(...)):
    """Retorna estadísticas de infraestructura (demo con datos realistas)"""
    
    ciudad_base = ciudad.split(",")[0].strip()
    
    if ciudad_base in DATOS_EJEMPLO:
        datos = DATOS_EJEMPLO[ciudad_base]
        return {
            "status": "success",
            "ciudad": ciudad,
            "fecha": datetime.now().isoformat(),
            "total_amenidades": datos["total"],
            "desglose": {
                "Hospitales": datos["Hospitales"],
                "Escuelas": datos["Escuelas"],
                "Bancos": datos["Bancos"],
                "Farmacias": datos["Farmacias"],
                "Comisarías": datos["Comisarías"]
            }
        }
    else:
        return {
            "status": "warning",
            "ciudad": ciudad,
            "mensaje": f"Datos no disponibles para {ciudad_base}. Prueba con: Santiago, Concepción, Valparaíso, Viña del Mar, Temuco, Antofagasta",
            "total_amenidades": 0,
            "desglose": {"Hospitales": 0, "Escuelas": 0, "Bancos": 0, "Farmacias": 0, "Comisarías": 0}
        }

@app.get("/mapa", response_class=HTMLResponse)
def generar_mapa(ciudad: str = Query(...)):
    """Genera un mapa interactivo simple"""
    
    ciudad_base = ciudad.split(",")[0].strip()
    
    # Coordenadas de ejemplo
    coords = {
        "Santiago": [-33.4489, -70.6693],
        "Concepción": [-36.827, -73.050],
        "Valparaíso": [-33.0472, -71.6127],
        "Viña del Mar": [-33.0245, -71.5518],
        "Temuco": [-38.7359, -72.5904],
        "Antofagasta": [-23.6500, -70.4000]
    }
    
    coord = coords.get(ciudad_base, [-33.4489, -70.6693])
    
    # Obtener estadísticas para mostrar
    if ciudad_base in DATOS_EJEMPLO:
        datos = DATOS_EJEMPLO[ciudad_base]
        stats_texto = f"Total: {datos['total']} amenidades | 🏥{datos['Hospitales']} 🏫{datos['Escuelas']} 🏦{datos['Bancos']} 💊{datos['Farmacias']}"
    else:
        stats_texto = "Datos de ejemplo no disponibles para esta ciudad"
    
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
        </style>
    </head>
    <body>
        <h2>🗺️ {ciudad}</h2>
        <div class="info">
            📊 <strong>{stats_texto}</strong><br>
            📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </div>
        <div id="map"></div>
        <p>
            <a href="/reporte_json?ciudad={ciudad}">Ver JSON completo</a> | 
            <a href="/ciudades_sugeridas">Ciudades disponibles</a>
        </p>
        <script>
            var map = L.map('map').setView([{coord[0]}, {coord[1]}], 13);
            L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                attribution: '© OpenStreetMap'
            }}).addTo(map);
            L.marker([{coord[0]}, {coord[1]}]).addTo(map)
                .bindPopup('<b>{ciudad}</b><br>{stats_texto}');
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)

@app.get("/ciudades_sugeridas")
def ciudades_sugeridas():
    return {"ciudades_disponibles": list(DATOS_EJEMPLO.keys())}