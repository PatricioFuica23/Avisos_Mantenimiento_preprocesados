# ==============================================
# 📊 APP STREAMLIT - CLASIFICACIÓN DE AVISOS CMPC
# Versión mejorada para presentación del proyecto
# ==============================================

from __future__ import annotations
import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO

# --- CONFIGURACIÓN INICIAL ---
st.set_page_config(page_title="Clasificación de Avisos SAP PM", page_icon="🧠", layout="wide")

# --- TÍTULO Y DESCRIPCIÓN ---
st.title("📊 Clasificación Automática de Avisos SAP PM")
st.caption("Prototipo funcional desarrollado para evaluar el uso de herramientas analíticas en el área de planificación de mantenimiento.")

st.markdown("""
💡 **Objetivo:** Esta aplicación permite visualizar y validar las predicciones del modelo de clasificación automática de avisos, 
explorando su criticidad, clase de orden, clase de actividad PM y puesto responsable.
""")

st.divider()

# --- FUNCIONES AUXILIARES ---
def cargar_datos(path: str) -> pd.DataFrame:
    df = pd.read_excel(path, engine="openpyxl")
    df.columns = df.columns.astype(str).str.replace(r"[\r\n]+", " ", regex=True).str.strip()
    return df

def color_hex_verde_amarillo_rojo(v: float, vmin: float = 1, vmax: float = 100) -> str:
    verde = (46, 204, 113)
    amarillo = (241, 196, 15)
    rojo = (231, 76, 60)
    if pd.isna(v): return "#ffffff"
    t = (float(v) - vmin) / (vmax - vmin)
    t = max(0, min(1, t))
    if t <= 0.5:
        a, b, u = verde, amarillo, t / 0.5
    else:
        a, b, u = amarillo, rojo, (t - 0.5) / 0.5
    r = int(a[0] + (b[0] - a[0]) * u)
    g = int(a[1] + (b[1] - a[1]) * u)
    b_ = int(a[2] + (b[2] - a[2]) * u)
    return f"#{r:02x}{g:02x}{b_:02x}"

def estilos_criticidad(col):
    return [f"background-color: {color_hex_verde_amarillo_rojo(v)}" for v in col]

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Controles")
    st.write("Sube el archivo Excel con las predicciones del modelo (por ejemplo, `ranking_nb.xlsx`).")
    uploaded = st.file_uploader("📂 Cargar archivo", type=["xlsx"])

    st.divider()
    st.subheader("📈 Desempeño del modelo")
    st.metric("Accuracy (Clasificación)", "0.902")
    st.metric("MAE (Criticidad)", "29.7")
    st.metric("R²", "-0.96")
    st.caption("Valores obtenidos en la última versión del modelo (V5 Random Forest).")

# --- CARGA DE DATOS ---
try:
    if uploaded is not None:
        df_raw = cargar_datos(uploaded)
    else:
        df_raw = cargar_datos("ranking_nb.xlsx")
except FileNotFoundError:
    st.error("❌ No se encontró el archivo `ranking_nb.xlsx`. Súbelo desde la barra lateral.")
    st.stop()

# --- SELECCIÓN Y PREPROCESAMIENTO ---
cols_relevantes = [
    "Aviso", "Fecha de aviso", "Descripción", "Ubicac.técnica",
    "Indicador ABC", "Grupo planif.", "Clase de aviso", "Denominación",
    "Prioridad", "Criticidad_1a100", "Rec_ClaseOrden@1",
    "Rec_ClaseAct@1", "Rec_Puesto@1"
]
df = df_raw[[c for c in cols_relevantes if c in df_raw.columns]].copy()

if "Fecha de aviso" in df.columns:
    df["Fecha de aviso"] = pd.to_datetime(df["Fecha de aviso"], errors="coerce").dt.date
if "Criticidad_1a100" in df.columns:
    df["Criticidad_1a100"] = pd.to_numeric(df["Criticidad_1a100"], errors="coerce")

# --- FILTROS ---
with st.sidebar:
    st.subheader("🔍 Filtros")
    grupo = st.selectbox("Grupo planificador", ["(Todos)"] + sorted(df["Grupo planif."].dropna().unique().tolist()))
    prioridad = st.selectbox("Prioridad", ["(Todos)"] + sorted(df["Prioridad"].dropna().unique().tolist()))
    abc = st.selectbox("Indicador ABC", ["(Todos)"] + sorted(df["Indicador ABC"].dropna().unique().tolist()))

df_filtrado = df.copy()
if grupo != "(Todos)": df_filtrado = df_filtrado[df_filtrado["Grupo planif."] == grupo]
if prioridad != "(Todos)": df_filtrado = df_filtrado[df_filtrado["Prioridad"] == prioridad]
if abc != "(Todos)": df_filtrado = df_filtrado[df_filtrado["Indicador ABC"] == abc]

# --- MÉTRICAS DE RESUMEN ---
st.subheader("📊 Resumen general")
c1, c2, c3, c4, c5 = st.columns(5)
total = len(df_filtrado)
prom = df_filtrado["Criticidad_1a100"].mean() if "Criticidad_1a100" in df_filtrado else np.nan
med = df_filtrado["Criticidad_1a100"].median() if "Criticidad_1a100" in df_filtrado else np.nan
pct_alta = (df_filtrado["Criticidad_1a100"] >= 80).mean() * 100 if "Criticidad_1a100" in df_filtrado else np.nan

c1.metric("Avisos mostrados", f"{total:,}".replace(",", "."))
c2.metric("Criticidad promedio", f"{prom:.1f}" if not np.isnan(prom) else "—")
c3.metric("Mediana criticidad", f"{med:.0f}" if not np.isnan(med) else "—")
c4.metric("% Criticidad ≥ 80", f"{pct_alta:.1f}%" if not np.isnan(pct_alta) else "—")
c5.metric("Grupos distintos", df_filtrado["Grupo planif."].nunique())

st.divider()

# --- GRAFICO DE DISTRIBUCIÓN ---
if "Criticidad_1a100" in df_filtrado:
    st.subheader("📈 Distribución de criticidad (1 a 100)")
    conteo = df_filtrado["Criticidad_1a100"].round().astype(int).value_counts().sort_index()
    st.bar_chart(conteo)
else:
    st.info("No hay datos de criticidad disponibles para graficar.")

st.divider()

# --- TABLA DE DATOS ---
st.subheader("📋 Avisos y recomendaciones del modelo")
styled_df = df_filtrado.style.apply(estilos_criticidad, subset=["Criticidad_1a100"])
st.dataframe(styled_df, use_container_width=True, hide_index=True)

st.divider()

# --- FEEDBACK DE USUARIO ---
st.subheader("🗣️ Retroalimentación del trabajador")
st.markdown("""
Por favor indica si consideras que las recomendaciones del modelo reflejan correctamente la prioridad de atención de los avisos:
""")

col_fb1, col_fb2 = st.columns([2, 3])
opinion = col_fb1.radio(
    "Nivel de acuerdo con las decisiones del modelo:",
    ["Totalmente de acuerdo", "Parcialmente de acuerdo", "En desacuerdo"],
    index=1
)
comentario = col_fb2.text_area("Comentarios adicionales:", "")

if st.button("💾 Enviar opinión"):
    st.success("✅ Opinión registrada. ¡Gracias por tu retroalimentación!")
    st.session_state["ultima_opinion"] = (opinion, comentario)

st.divider()

# --- EXPORTACIÓN ---
st.subheader("💾 Descargar datos filtrados")
buffer = BytesIO()
with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
    df_filtrado.to_excel(writer, index=False, sheet_name="Avisos")
buffer.seek(0)
st.download_button(
    "📥 Descargar Excel con avisos filtrados",
    data=buffer,
    file_name="avisos_filtrados.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
