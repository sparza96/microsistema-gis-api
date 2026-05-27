"""
DÍA 2 - API GIS con FastAPI
Endpoints para obtener reportes de infraestructura de cualquier ciudad
"""

import osmnx as ox
import folium
from folium import plugins
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import json
from datetime import datetime
import uuid
import os

app = FastAPI(title="Microsistema GIS API", description="API para análisis de infraestructura urbana", version="1.0")

# Permitir peticiones desde cualquier origen (para tu futura app web)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Crear carpeta para almacenar reportes temporales
os.makedirs("reportes", exist_ok=True)

# ============================================
# ENDPOINT 1: Health check
# ============================================
@app.get("/")
def root():
    return {
        "mensaje": "Microsistema GIS API funcionando",
        "endpoints": [
            "/reporte?ciudad=Concepción, Chile",
            "/reporte_json?ciudad=Santiago, Chile",
            "/mapa?ciudad=Valparaíso, Chile"
        ]
    }

# ============================================
# ENDPOINT 2: Reporte completo (JSON)
# ============================================
@app.get("/reporte_json")
def reporte_json(ciudad: str = Query(..., description="Nombre de la ciudad, país")):
    """
    Devuelve estadísticas de infraestructura urbana en formato JSON
    Ejemplo: /reporte_json?ciudad=Santiago, Chile
    """
    try:
        print(f"📡 Procesando solicitud para: {ciudad}")
        
        # Extraer datos
        amenities = ox.features_from_place(
            ciudad,
            tags={"amenity": ["hospital", "school", "bank", "pharmacy", "police"]}
        )
        
        # Limpiar
        amenities_clean = amenities[amenities.geometry.notna()]
        amenities_clean = amenities_clean[amenities_clean.geometry.is_valid]
        
        # Contar por tipo
        tipo_map = {
            "hospital": "Hospitales",
            "school": "Escuelas",
            "bank": "Bancos",
            "pharmacy": "Farmacias",
            "police": "Comisarías"
        }
        
        conteo = {}
        for tipo_key, tipo_nombre in tipo_map.items():
            cantidad = len(amenities_clean[amenities_clean["amenity"] == tipo_key])
            conteo[tipo_nombre] = cantidad
        
        return JSONResponse(content={
            "status": "success",
            "ciudad": ciudad,
            "fecha": datetime.now().isoformat(),
            "total_amenidades": len(amenities_clean),
            "desglose": conteo
        })
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "mensaje": str(e)}
        )

# ============================================
# ENDPOINT 3: Mapa interactivo (HTML)
# ============================================
@app.get("/mapa", response_class=HTMLResponse)
def generar_mapa(ciudad: str = Query(..., description="Nombre de la ciudad, país")):
    """
    Genera un mapa interactivo HTML para la ciudad solicitada
    Ejemplo: /mapa?ciudad=Concepción, Chile
    """
    try:
        print(f"🗺️ Generando mapa para: {ciudad}")
        
        # Extraer datos
        amenities = ox.features_from_place(
            ciudad,
            tags={"amenity": ["hospital", "school", "bank", "pharmacy", "police"]}
        )
        
        streets = ox.graph_from_place(ciudad, network_type="drive")
        streets_gdf = ox.graph_to_gdfs(streets, nodes=False, edges=True)
        
        # Limpiar amenities
        amenities_clean = amenities[amenities.geometry.notna()]
        amenities_clean = amenities_clean[amenities_clean.geometry.is_valid]
        
        # Obtener centro del mapa
        try:
            center_lat = amenities_clean.geometry.y.mean()
            center_lon = amenities_clean.geometry.x.mean()
        except:
            center_lat, center_lon = -36.827, -73.050  # fallback Concepción
        
        # Crear mapa
        m = folium.Map(location=[center_lat, center_lon], zoom_start=13)
        plugins.MeasureControl(position="bottomleft").add_to(m)
        
        # Agregar calles
        for _, row in streets_gdf.head(200).iterrows():
            if row.geometry and row.geometry.type == 'LineString':
                try:
                    coords = [(lat, lon) for lon, lat in row.geometry.coords]
                    folium.PolyLine(locations=coords, color="#888888", weight=1.5, opacity=0.6).add_to(m)
                except:
                    pass
        
        # Colores
        color_map = {
            "hospital": {"color": "red", "icono": "plus", "nombre": "🏥 Hospitales"},
            "school": {"color": "blue", "icono": "education", "nombre": "🏫 Escuelas"},
            "bank": {"color": "green", "icono": "bank", "nombre": "🏦 Bancos"},
            "pharmacy": {"color": "purple", "icono": "medkit", "nombre": "💊 Farmacias"},
            "police": {"color": "orange", "icono": "shield", "nombre": "🚔 Comisarías"}
        }
        
        # Agregar capas
        for tipo, info in color_map.items():
            grupo = folium.FeatureGroup(name=info["nombre"], show=True)
            subset = amenities_clean[amenities_clean["amenity"] == tipo]
            for _, row in subset.iterrows():
                if hasattr(row.geometry, 'y'):
                    nombre = row.get("name", tipo)
                    folium.Marker(
                        location=[row.geometry.y, row.geometry.x],
                        popup=f"<b>{nombre}</b><br>{tipo}",
                        icon=folium.Icon(color=info["color"], icon=info["icono"], prefix='fa')
                    ).add_to(grupo)
            grupo.add_to(m)
        
        folium.LayerControl().add_to(m)
        
        # Leyenda
        leyenda_html = f'''
        <div style="position: fixed; bottom: 30px; right: 30px; width: 180px; 
                    background-color: white; border-radius: 8px; border: 2px solid gray;
                    padding: 10px; z-index: 9999; font-size: 14px;
                    font-family: Arial, sans-serif; box-shadow: 2px 2px 5px rgba(0,0,0,0.3);">
            <b>📋 {ciudad.split(",")[0]}</b><br><hr>
            <span style="color:red;">●</span> Hospitales<br>
            <span style="color:blue;">●</span> Escuelas<br>
            <span style="color:green;">●</span> Bancos<br>
            <span style="color:purple;">●</span> Farmacias<br>
            <span style="color:orange;">●</span> Comisarías<br>
            <hr>
            <b>Total: {len(amenities_clean)}</b> amenidades
        </div>
        '''
        m.get_root().html.add_child(folium.Element(leyenda_html))
        
        # Guardar temporalmente
        filename = f"reportes/mapa_{uuid.uuid4().hex[:8]}.html"
        m.save(filename)
        
        with open(filename, "r", encoding="utf-8") as f:
            html_content = f.read()
        
        return HTMLResponse(content=html_content)
        
    except Exception as e:
        return HTMLResponse(content=f"<h3>Error</h3><p>{str(e)}</p>", status_code=500)

# ============================================
# ENDPOINT 4: Listar ciudades disponibles (ejemplo)
# ============================================
@app.get("/ciudades_ejemplo")
def ciudades_ejemplo():
    return {
        "ejemplos": [
            "Concepción, Chile",
            "Santiago, Chile",
            "Valparaíso, Chile",
            "Temuco, Chile",
            "Puerto Montt, Chile"
        ]
    }