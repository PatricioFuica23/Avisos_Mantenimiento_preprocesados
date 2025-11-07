# ==============================================
# 📊 APP STREAMLIT - CLASIFICACIÓN DE AVISOS CMPC
# Versión con sistema de tickets gestionados
# ==============================================

from __future__ import annotations
import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
from datetime import datetime

# --- CONFIGURACIÓN INICIAL ---
st.set_page_config(page_title="Clasificación de Avisos SAP PM", page_icon="🧠", layout="wide")

st.title("📊 Clasificación Automática de Avisos SAP PM")
st.caption("Prototipo funcional con registro de gestión de avisos y generación de tickets de seguimiento.")

st.markdown("""
💡 **Objetivo:** Visualizar las recomendaciones del modelo, filtrar por criticidad o grupo planificador,
y registrar qué avisos fueron efectivamente gestionados por los trabajadores.
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
    st.write("Sube el archivo Excel con las predicciones del modelo (`ranking_nb.xlsx`).")
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

# --- SISTEMA DE TICKETS ---
st.subheader("🎫 Gestión de Avisos (crear tickets)")
st.markdown("Marca los avisos que han sido gestionados y genera tickets de seguimiento.")

# Inicializar estructura en session_state
if "tickets" not in st.session_state:
    st.session_state["tickets"] = []

for idx, row in df_filtrado.iterrows():
    aviso = row.get("Aviso", "")
    descripcion = str(row.get("Descripción", ""))[:100]
    criticidad = row.get("Criticidad_1a100", "")
    grupo_p = row.get("Grupo planif.", "")
    col1, col2, col3, col4 = st.columns([1, 3, 1, 1])
    with col1:
        marcado = st.checkbox(f"{aviso}", key=f"chk_{aviso}")
    with col2:
        st.write(f"**{descripcion}**")
    with col3:
        st.write(f"🔧 {grupo_p}")
    with col4:
        st.write(f"🔥 {criticidad}")

    if marcado:
        nombre = st.text_input(f"👷 Nombre del trabajador para aviso {aviso}:", key=f"trab_{aviso}")
        comentario = st.text_input(f"💬 Comentario:", key=f"com_{aviso}")
        if st.button(f"➕ Crear ticket #{aviso}", key=f"btn_{aviso}"):
            ticket = {
                "Aviso": aviso,
                "Fecha gestión": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Trabajador": nombre,
                "Comentario": comentario,
                "Criticidad": criticidad,
                "Grupo planif.": grupo_p
            }
            st.session_state["tickets"].append(ticket)
            st.success(f"🎫 Ticket para aviso {aviso} registrado correctamente.")

st.divider()

# --- DESCARGA DE TICKETS ---
st.subheader("📥 Descargar tickets gestionados")
if st.session_state["tickets"]:
    df_tickets = pd.DataFrame(st.session_state["tickets"])
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df_tickets.to_excel(writer, index=False, sheet_name="Tickets")
    buffer.seek(0)
    st.download_button(
        "📥 Descargar tickets en Excel",
        data=buffer,
        file_name="tickets_gestionados.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    st.info("No hay tickets registrados todavía.")

st.divider()
st.caption("Versión con registro de tickets — CMPC Cordillera © 2025")
