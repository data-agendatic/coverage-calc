import streamlit as st
import requests
import math
import json
from streamlit.components.v1 import html
import numpy as np

# =======================
# CONFIGURACIÓN GENERAL
# =======================
st.set_page_config(page_title="ASEP – Herramientas RF", layout="wide")

st.title("📡 ASEP – Plataforma de Cálculos RF")
st.markdown("Herramientas para cálculos FCC, Delta-H y coberturas con radiales.")

FCC_BASE = "https://geo.fcc.gov/api/contours/distance.json"

# ==========================================================
# FUNCIÓN: ELEVACIONES SRTM (OPENTOPO)
# ==========================================================
def obtener_elevacion_nasadem(lat, lon):
    """
    Consulta NASADEM a través de opentopodata.
    Mucho más limpio que SRTM.
    """
    try:
        url = f"https://api.opentopodata.org/v1/nasadem?locations={lat},{lon}"
        r = requests.get(url, timeout=5)
        data = r.json()

        elev = data["results"][0]["elevation"]
        return elev  # normalmente no devuelve None
    except:
        return None


# ==========================================================
# FUNCIÓN: OFFSET GEOGRÁFICO
# ==========================================================
def geographic_offset(lat0, lon0, dist_km, ang_deg):
    lat = lat0 + (dist_km / 111) * math.cos(math.radians(ang_deg))
    lon = lon0 + (dist_km / (111 * math.cos(math.radians(lat0)))) * math.sin(math.radians(ang_deg))
    return lat, lon

# ==========================================================
# CALCULAR DELTA-H (METODOLOGÍA FCC)
# Puntos entre 10 km – 50 km → percentil 10% y 90%
# ==========================================================
def calcular_delta_h_fcc(lat0, lon0, ang):
    # 81 puntos de 10 a 50 km, cada 0.5 km
    distancias = np.arange(10, 50.1, 0.5)

    # ===============================
    # 1. Construir la lista de puntos
    # ===============================
    puntos = []
    for d in distancias:
        lat, lon = geographic_offset(lat0, lon0, d, ang)
        puntos.append(f"{lat},{lon}")

    # ===============================
    # 2. Llamar la API EN UN SOLO REQUEST
    # ===============================
    locations_param = "|".join(puntos)
    url = f"https://api.opentopodata.org/v1/srtm30m?locations={locations_param}"

    try:
        r = requests.get(url, timeout=6)
        data = r.json()
        elevaciones = [item["elevation"] for item in data["results"] if item["elevation"] is not None]
    except:
        return None, None, None, None

    if len(elevaciones) < 10:
        return None, None, None, None

    elevaciones = np.array(elevaciones)

    # ===============================
    # 3. Calcular percentiles FCC
    # ===============================
    h10 = np.percentile(elevaciones, 10)
    h90 = np.percentile(elevaciones, 90)
    delta_h = h90 - h10

    return h10, h90, delta_h, elevaciones


    if len(elevaciones) < 10:
        return None, None, None, None

    elevaciones = np.array(elevaciones)

    h10 = np.percentile(elevaciones, 10)
    h90 = np.percentile(elevaciones, 90)
    delta_h = h90 - h10

    return h10, h90, delta_h, elevaciones


# =======================
# LAYOUT PRINCIPAL
# =======================
left, right = st.columns([1, 2])

# =======================
# PANEL IZQUIERDO
# =======================
with left:
    st.header("⚙️ Configuración")

    mode = st.radio(
        "Seleccione el modo:",
        ["1) Calcular Delta-H", "2) Calcular Cobertura (72 Radiales)"]
    )

    st.markdown("---")

    st.subheader("📡 Parámetros FCC")
    service_type = st.selectbox("Service Type", ["FM", "TV", "DTV"])
    haat = st.number_input("HAAT (m)", value=150.0, step=10.0)
    field = st.number_input("Field Strength (dBµV/m)", value=60.0, step=0.1)
    channel = st.number_input("Channel", value=200, step=1)

    curve_options = {"F(50,50)": 0, "F(50,10)": 1, "F(50,90)": 2}
    curve = curve_options[st.selectbox("Curva", list(curve_options.keys()))]

# =======================
# PANEL DERECHO
# =======================
with right:

    # =====================================================
    #             MODO 1: CALCULAR DELTA-H FCC
    # =====================================================
    if mode.startswith("1"):

        st.header("✏️ Cálculo de Delta-H (72 radiales) – FCC")

        lat = st.number_input("Latitud (°)", value=8.5, step=0.0001, format="%.5f")
        lon = st.number_input("Longitud (°)", value=-80.0, step=0.0001, format="%.5f")

        if st.button("Calcular Delta-H"):

            st.info("Consultando elevaciones SRTM y aplicando metodología FCC...")
            progress = st.progress(0)

            angulos = list(range(0, 360, 5))
            resultados = []
            leaf_points = []

            for i, ang in enumerate(angulos):

                h10, h90, dh, perfil = calcular_delta_h_fcc(lat, lon, ang)
                resultados.append((ang, h10, h90, dh))

                # Guardar puntos del perfil para mapa
                if perfil is not None:
                    distancias = np.arange(10, 50.1, 0.5)
                    for d, h in zip(distancias, perfil):
                        latp, lonp = geographic_offset(lat, lon, d, ang)
                        leaf_points.append([lonp, latp])

                progress.progress(int((i+1) * 100 / 72))

            st.success("✔ Delta-H calculados correctamente")

            # Mostrar en 3 columnas, 24 valores cada una
            colA, colB, colC = st.columns(3)
            columnas = [colA, colB, colC]

            for idx, col in enumerate(columnas):
                with col:
                    for ang, h10, h90, dh in resultados[idx*24:(idx+1)*24]:
                        col.write(
                            f"**{ang}°** → H10={h10:.1f}m | H90={h90:.1f}m | **ΔH={dh:.1f}m**"
                        )

            # =======================
            # MAPA LEAFLET
            # =======================
            coords_js = json.dumps(leaf_points)

            leaflet_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8"/>
                <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
                <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>

                <style>
                    html, body, #map {{
                        height: 100%;
                        margin: 0;
                    }}
                </style>
            </head>
            <body>
                <div id="map"></div>
                <script>
                    var map = L.map('map').setView([{lat}, {lon}], 9);

                    L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                        maxZoom: 18,
                        attribution: '&copy; OpenStreetMap'
                    }}).addTo(map);

                    var puntos = {coords_js};

                    for (var i = 0; i < puntos.length; i++) {{
                        L.circleMarker([puntos[i][1], puntos[i][0]], {{
                            radius: 2,
                            color: 'blue',
                            fillOpacity: 0.7
                        }}).addTo(map);
                    }}

                    L.marker([{lat}, {lon}]).addTo(map)
                        .bindPopup("Sitio transmisor");
                </script>
            </body>
            </html>
            """

            st.subheader("Mapa del perfil 10–50 km")
            html(leaflet_html, height=600)


    # =====================================================
    #      MODO 2 (Tu original): CÁLCULO DE RADIALES FCC
    # =====================================================
    elif mode.startswith("2"):

        st.header("🗺️ Cálculo de Cobertura – 72 radiales")

        colA, colB, colC = st.columns(3)
        erp_vals = [0] * 72
        angles = list(range(0, 360, 5))

        with colA:
            for i in range(24):
                erp_vals[i] = st.number_input(f"ERP {angles[i]}°", min_value=0.0, step=0.1)

        with colB:
            for i in range(24, 48):
                erp_vals[i] = st.number_input(f"ERP {angles[i]}°", min_value=0.0, step=0.1)

        with colC:
            for i in range(48, 72):
                erp_vals[i] = st.number_input(f"ERP {angles[i]}°", min_value=0.0, step=0.1)

        lat0 = st.number_input("Latitud del sitio (°)", value=8.5, format="%.5f")
        lon0 = st.number_input("Longitud del sitio (°)", value=-80.0, format="%.5f")

        if st.button("Calcular Cobertura"):

            st.info("Consultando API FCC…")

            dist_list = []
            for erp in erp_vals:
                params = {
                    "computationMethod": 0,
                    "serviceType": service_type.lower(),
                    "haat": haat,
                    "channel": channel,
                    "field": field,
                    "erp": erp,
                    "curve": curve,
                    "outputcache": "true"
                }

                try:
                    r = requests.get(FCC_BASE, params=params)
                    data = r.json()
                    dist_list.append(data.get("distance", 0))
                except:
                    dist_list.append(0)

            st.success("✔ Radiales calculados correctamente")

            coords = []
            for ang, dist in zip(angles, dist_list):
                latp, lonp = geographic_offset(lat0, lon0, dist, ang)
                coords.append([lonp, latp])
            coords.append(coords[0])

            geojson = {
                "type": "FeatureCollection",
                "features": [{
                    "type": "Feature",
                    "geometry": {"type": "Polygon", "coordinates": [coords]},
                    "properties": {"name": "Cobertura RF"}
                }]
            }

            geojson_str = json.dumps(geojson)

            leaflet_map = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8" />
                <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
                <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
                <style>
                    html, body, #map {{
                        height: 100%;
                        margin: 0;
                    }}
                </style>
            </head>
            <body>
                <div id="map"></div>
                <script>
                    var map = L.map('map').setView([{lat0}, {lon0}], 9);

                    L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png').addTo(map);

                    var geojsonData = {geojson_str};

                    var capa = L.geoJSON(geojsonData, {{
                        style: {{
                            color: "red",
                            weight: 2,
                            fillOpacity: 0.15
                        }}
                    }}).addTo(map);

                    L.marker([{lat0}, {lon0}]).addTo(map).bindPopup("Sitio transmisor");

                    map.fitBounds(capa.getBounds());
                </script>
            </body>
            </html>
            """
            html(leaflet_map, height=700)
