import streamlit as st
import requests

# ---- Título ----
st.title("📡 ASEP - Calculadora de Distancias FCC (ALVEO-SANTOS)")
st.markdown("Calcula distancia, campo o ERP según las curvas FCC F(50,50), F(50,10) y F(50,90).")

# ---- Variables base ----
base_url = "https://geo.fcc.gov/api/contours"
output_format = "json"

# ---- Entradas del usuario ----
service_type = st.selectbox("Service Type", ["FM", "TV", "DTV"])
haat = st.number_input("HAAT (m)", value=150.0, step=10.0)
erp = st.number_input("ERP (kW)", value=5.0, step=0.1)
field = st.number_input("Field Strength (dBµV/m)", value=60.0, step=0.1)
channel = st.number_input("Channel", value=200, step=1)

# ---- Selector de curvas ----
curve_options = {
    "F(50,50) – Campo mediano / tiempo mediano": 0,
    "F(50,10) – Campo mediano / tiempo desfavorable (10%)": 1,
    "F(50,90) – Campo mediano / tiempo favorable (90%)": 2
}
curve_label = st.selectbox("Tipo de curva de propagación", list(curve_options.keys()))
curve = curve_options[curve_label]

# ---- Selector del método de cálculo ----
method_options = {
    "0 – Calcular distancia (dada la intensidad de campo)": 0,
    "1 – Calcular campo (dada la distancia)": 1,
    "2 – Calcular ERP (dada distancia y campo)": 2
}
method_label = st.selectbox("Método de cálculo", list(method_options.keys()))
computation_method = method_options[method_label]

# ---- Botón principal ----
if st.button("Calcular"):
    endpoint = f"{base_url}/distance.{output_format}"
    params = {
        "computationMethod": computation_method,
        "serviceType": service_type.lower(),
        "haat": haat,
        "channel": channel,
        "field": field,
        "erp": erp,
        "curve": curve,
        "outputcache": "true"
    }

    try:
        response = requests.get(endpoint, params=params)
        response.raise_for_status()
        data = response.json()

        # ---- Mostrar solo el resultado limpio ----
        if "distance" in data:
            st.success(f"📏 Distancia estimada: **{data['distance']:.2f} {data.get('distance_unit', 'km')}**")
        elif "field" in data and data.get("computedField") == "field":
            st.success(f"📡 Campo estimado: **{data['field']:.2f} {data.get('field_unit', 'dBµV/m')}**")
        elif "erp" in data and data.get("computedField") == "erp":
            st.success(f"⚙️ Potencia radiada efectiva (ERP): **{data['erp']:.2f} {data.get('erp_unit', 'kW')}**")
        else:
            st.warning("No se encontró un valor directo de salida. Revisa la respuesta de la API.")

    except Exception as e:
        st.error(f"Error al consultar la API: {e}")
