"""
API GIS Lite - Versión optimizada para Render free tier
"""

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import requests
import json
from datetime import datetime
import urllib.parse

app = FastAPI(title="Microsistema GIS API Lite")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Overpass API de OpenStreetMap (más liviano que OSMnx)
OVERPASS_URL = "https://overpass-api.de/api/interpreter"

def query_overpass(ciudad, amenity_type):
    """Consulta Overpass API para un tipo de amenidad"""
    # Escapar nombre de ciudad
    ciudad_encoded = urllib.parse.quote(ciudad)
    
    query = f"""
    [out:json];
    area["name"="{ciudad}"]->.searchArea;
    node["amenity"="{amenity_type}"](area.searchArea);
    out center;
    """
    
    try:
        response = requests.post(OVERPASS_URL, data=query, timeout=25)
        if response.status_code == 200:
            data = response.json()
            return len(data.get("elements", []))
        return 0
    except:
        return 0

@app.get("/")
def root():
    return {
        "mensaje": "Microsistema GIS API Lite funcionando",
        "version": "1.0",
        "endpoints": [
            "/reporte_json?ciudad=Santiago, Chile",
            "/mapa?ciudad=Concepción, Chile"
        ]
    }

@app.get("/reporte_json")
def reporte_json(ciudad: str = Query(..., description="Ciudad, País")):
    """Retorna estadísticas de infraestructura"""
    
    amenidades = ["hospital", "school", "bank", "pharmacy", "police"]
    nombres = {
        "hospital": "Hospitales",
        "school": "Escuelas",
        "bank": "Bancos", 
        "pharmacy": "Farmacias",
        "police": "Comisarías"
    }
    
    resultados = {}
    total = 0
    
    for amenity in amenidades:
        cantidad = query_overpass(ciudad, amenity)
        resultados[nombres[amenity]] = cantidad
        total += cantidad
    
    return {
        "status": "success",
        "ciudad": ciudad,
        "fecha": datetime.now().isoformat(),
        "total_amenidades": total,
        "desglose": resultados
    }

@app.get("/mapa", response_class=HTMLResponse)
def generar_mapa(ciudad: str = Query(...)):
    """Genera un mapa simple con Folium"""
    
    # Usar coordenadas aproximadas por nombre (simplificado)
    coords_ciudades = {
        "Santiago": [-33.4489, -70.6693],
        "Concepción": [-36.827, -73.050],
        "Valparaíso": [-33.0472, -71.6127],
        "Viña del Mar": [-33.0245, -71.5518],
        "Temuco": [-38.7359, -72.5904],
        "Antofagasta": [-23.6500, -70.4000]
    }
    
    # Extraer nombre base
    nombre_base = ciudad.split(",")[0].strip()
    coords = coords_ciudades.get(nombre_base, [-33.4489, -70.6693])
    
    html_content = f"""
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
            📊 <strong>Reporte generado:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br>
            ℹ️ Mapa base de ubicación. Los datos detallados están en el endpoint /reporte_json
        </div>
        <div id="map"></div>
        <p><a href="/reporte_json?ciudad={ciudad}">Ver estadísticas JSON</a></p>
        <script>
            var map = L.map('map').setView([{coords[0]}, {coords[1]}], 13);
            L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                attribution: '© OpenStreetMap'
            }}).addTo(map);
            L.marker([{coords[0]}, {coords[1]}]).addTo(map)
                .bindPopup('<b>{ciudad}</b>');
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/ciudades_sugeridas")
def ciudades_sugeridas():
    return {
        "chile": [
            "Santiago, Chile",
            "Concepción, Chile",
            "Valparaíso, Chile",
            "Viña del Mar, Chile",
            "Temuco, Chile",
            "Antofagasta, Chile"
        ]
    }