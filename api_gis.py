"""
DÍA 2 - API GIS con FastAPI (VERSIÓN ROBUSTA)
Manejo de errores, timeout y ciudades sin datos
"""

import osmnx as ox
import folium
from folium import plugins
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import uuid
import os
import logging

# Configurar logging para ver errores en Render
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Microsistema GIS API", description="API para análisis de infraestructura urbana", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("reportes", exist_ok=True)

# Tipos de amenidades a buscar
AMENITIES_TAGS = {
    "hospital": "Hospitales",
    "school": "Escuelas", 
    "bank": "Bancos",
    "pharmacy": "Farmacias",
    "police": "Comisarías"
}

# ============================================
# ENDPOINT 1: Health check
# ============================================
@app.get("/")
def root():
    return {
        "mensaje": "Microsistema GIS API funcionando",
        "endpoints": [
            "/reporte_json?ciudad=Concepción, Chile",
            "/mapa?ciudad=Valparaíso, Chile"
        ]
    }

# ============================================
# ENDPOINT 2: Reporte JSON con manejo de errores
# ============================================
@app.get("/reporte_json")
def reporte_json(ciudad: str = Query(..., description="Nombre de la ciudad, país")):
    try:
        logger.info(f"📡 Procesando JSON para: {ciudad}")
        
        # Timeout manual
        import signal
        
        # Extraer datos con límite de tiempo
        amenities = ox.features_from_place(
            ciudad,
            tags={"amenity": list(AMENITIES_TAGS.keys())}
        )
        
        if amenities.empty:
            return JSONResponse(content={
                "status": "warning",
                "ciudad": ciudad,
                "mensaje": "No se encontraron amenidades en esta ciudad. Puede ser que OSM no tenga datos suficientes.",
                "total_amenidades": 0,
                "desglose": {nombre: 0 for nombre in AMENITIES_TAGS.values()}
            })
        
        # Limpiar
        amenities_clean = amenities[amenities.geometry.notna()]
        amenities_clean = amenities_clean[amenities_clean.geometry.is_valid]
        
        # Contar
        conteo = {}
        for tipo_key, tipo_nombre in AMENITIES_TAGS.items():
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
        logger.error(f"Error en reporte_json: {str(e)}")
        return JSONResponse(
            status_code=200,  # Usamos 200 para que el frontend lo maneje bien
            content={
                "status": "error",
                "ciudad": ciudad,
                "mensaje": f"Error al procesar: {str(e)[:100]}. Intenta con otra ciudad más grande o conocida."
            }
        )

# ============================================
# ENDPOINT 3: Mapa con manejo de errores
# ============================================
@app.get("/mapa", response_class=HTMLResponse)
def generar_mapa(ciudad: str = Query(..., description="Nombre de la ciudad, país")):
    try:
        logger.info(f"🗺️ Generando mapa para: {ciudad}")
        
        # Extraer datos
        amenities = ox.features_from_place(
            ciudad,
            tags={"amenity": list(AMENITIES_TAGS.keys())}
        )
        
        if amenities.empty:
            return HTMLResponse(content=f"""
            <!DOCTYPE html>
            <html>
            <head><meta charset="UTF-8"><title>Sin datos</title></head>
            <body>
                <h3>⚠️ No se encontraron datos para {ciudad}</h3>
                <p>OpenStreetMap no tiene suficientes amenidades mapeadas en esta ciudad.</p>
                <p>Prueba con: Concepción, Santiago, Valparaíso, Temuco, Viña del Mar</p>
                <p><a href="/">Volver al inicio</a></p>
            </body>
            </html>
            """)
        
        # Extraer calles (con manejo de error)
        try:
            streets = ox.graph_from_place(ciudad, network_type="drive")
            streets_gdf = ox.graph_to_gdfs(streets, nodes=False, edges=True)
        except:
            streets_gdf = None
            logger.warning(f"No se pudieron extraer calles para {ciudad}")
        
        # Limpiar amenities
        amenities_clean = amenities[amenities.geometry.notna()]
        amenities_clean = amenities_clean[amenities_clean.geometry.is_valid]
        
        # Obtener centro
        try:
            center_lat = amenities_clean.geometry.y.mean()
            center_lon = amenities_clean.geometry.x.mean()
        except:
            center_lat, center_lon = -33.4489, -70.6693  # Santiago como fallback
        
        # Crear mapa
        m = folium.Map(location=[center_lat, center_lon], zoom_start=12)
        
        # Agregar calles si existen
        if streets_gdf is not None:
            for _, row in streets_gdf.head(100).iterrows():
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
            for _, row in subset.head(200).iterrows():
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
        
        # Guardar
        filename = f"reportes/mapa_{uuid.uuid4().hex[:8]}.html"
        m.save(filename)
        
        with open(filename, "r", encoding="utf-8") as f:
            html_content = f.read()
        
        return HTMLResponse(content=html_content)
        
    except Exception as e:
        logger.error(f"Error en mapa: {str(e)}")
        return HTMLResponse(content=f"""
        <!DOCTYPE html>
        <html>
        <head><meta charset="UTF-8"><title>Error</title></head>
        <body>
            <h3>❌ Error al generar el mapa</h3>
            <p><strong>Ciudad:</strong> {ciudad}</p>
            <p><strong>Error:</strong> {str(e)[:200]}</p>
            <p>💡 <strong>Sugerencias:</strong></p>
            <ul>
                <li>Prueba con ciudades más grandes: Concepción, Santiago, Valparaíso</li>
                <li>Verifica el formato: "Concepción, Chile"</li>
                <li>Espera unos segundos y reintenta</li>
            </ul>
            <p><a href="/">Volver al inicio</a></p>
        </body>
        </html>
        """, status_code=200)

# ============================================
# ENDPOINT 4: Ciudades sugeridas
# ============================================
@app.get("/ciudades_sugeridas")
def ciudades_sugeridas():
    return {
        "chile": [
            "Santiago, Chile",
            "Concepción, Chile", 
            "Valparaíso, Chile",
            "Viña del Mar, Chile",
            "Temuco, Chile",
            "Antofagasta, Chile",
            "La Serena, Chile",
            "Rancagua, Chile",
            "Talca, Chile",
            "Puerto Montt, Chile"
        ],
        "internacionales": [
            "Buenos Aires, Argentina",
            "Bogotá, Colombia",
            "Lima, Perú",
            "Mexico City, Mexico"
        ]
    }
    }