# ==============================================
# 📊 APP STREAMLIT - CLASIFICACIÓN DE AVISOS CMPC
# Versión con DataFrame editable, gestión y tickets
# ==============================================

from __future__ import annotations
import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Clasificación de Avisos SAP PM", page_icon="🧠", layout="wide")

st.title("📊 Clasificación Automática de Avisos SAP PM")
st.caption("Prototipo funcional con sistema de gestión y registro de tickets por aviso.")

st.markdown("""
💡 **Objetivo:** Permitir que los trabajadores visualicen los avisos, conozcan la criticidad calculada por el modelo y marquen aquellos que ya han sido gestionados, para mantener un control del backlog.
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

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Configuración de la aplicación")
    uploaded = st.file_uploader("📂 Cargar archivo de predicciones", type=["xlsx"])
    st.caption("Usa el archivo generado por el modelo, por ejemplo `ranking_nb.xlsx`.")

    st.divider()
    st.subheader("📈 Desempeño del modelo")
    st.metric("Accuracy", "0.902")
    st.metric("MAE", "29.7")
    st.metric("R²", "-0.96")

# --- CARGA DE DATOS ---
try:
    if uploaded is not None:
        df_raw = cargar_datos(uploaded)
    else:
        df_raw = cargar_datos("ranking_nb.xlsx")
except FileNotFoundError:
    st.error("❌ No se encontró `ranking_nb.xlsx`. Súbelo desde la barra lateral.")
    st.stop()

# --- SELECCIÓN DE COLUMNAS RELEVANTES ---
cols_relevantes = [
    "Aviso", "Fecha de aviso", "Descripción", "Ubicac.técnica",
    "Indicador ABC", "Grupo planif.", "Clase de aviso", "Denominación",
    "Prioridad", "Criticidad_1a100", "Rec_ClaseOrden@1",
    "Rec_ClaseAct@1", "Rec_Puesto@1"
]
df = df_raw[[c for c in cols_relevantes if c in df_raw.columns]].copy()

# --- LIMPIEZA Y FORMATEO ---
if "Fecha de aviso" in df.columns:
    df["Fecha de aviso"] = pd.to_datetime(df["Fecha de aviso"], errors="coerce").dt.date
if "Criticidad_1a100" in df.columns:
    df["Criticidad_1a100"] = pd.to_numeric(df["Criticidad_1a100"], errors="coerce")

# --- NUEVAS COLUMNAS (Gestionado y Ticket) ---
if "Gestionado" not in df.columns:
    df["Gestionado"] = False
if "Ticket" not in df.columns:
    df["Ticket"] = ""

# Guardar en sesión (solo la primera vez)
if "df_data" not in st.session_state:
    st.session_state["df_data"] = df.copy()

df_session = st.session_state["df_data"]

# --- FILTROS ---
with st.sidebar:
    st.subheader("🔍 Filtros de visualización")
    grupo = st.selectbox("Grupo planificador", ["(Todos)"] + sorted(df_session["Grupo planif."].dropna().unique().tolist()))
    prioridad = st.selectbox("Prioridad", ["(Todos)"] + sorted(df_session["Prioridad"].dropna().unique().tolist()))
    abc = st.selectbox("Indicador ABC", ["(Todos)"] + sorted(df_session["Indicador ABC"].dropna().unique().tolist()))

# Aplicar filtros
df_filtrado = df_session.copy()
if grupo != "(Todos)": df_filtrado = df_filtrado[df_filtrado["Grupo planif."] == grupo]
if prioridad != "(Todos)": df_filtrado = df_filtrado[df_filtrado["Prioridad"] == prioridad]
if abc != "(Todos)": df_filtrado = df_filtrado[df_filtrado["Indicador ABC"] == abc]

# --- MÉTRICAS GENERALES ---
st.subheader("📊 Resumen general")
col1, col2, col3 = st.columns(3)
col1.metric("Total avisos", len(df_filtrado))
col2.metric("Criticidad promedio", f"{df_filtrado['Criticidad_1a100'].mean():.1f}")
col3.metric("% Gestionados", f"{(df_filtrado['Gestionado'].mean() * 100):.1f}%")

st.divider()

# --- TABLA EDITABLE PRINCIPAL ---
st.subheader("📋 Tabla de avisos (editable)")
st.caption("Puedes marcar un aviso como gestionado y asignarle un número o comentario de ticket. Los cambios se actualizan automáticamente.")

edited_df = st.data_editor(
    df_filtrado,
    num_rows="dynamic",
    use_container_width=True,
    hide_index=True,
    column_config={
        "Gestionado": st.column_config.CheckboxColumn("Gestionado"),
        "Ticket": st.column_config.TextColumn("Ticket", help="Número o comentario de ticket")
    },
    key="editable_table"
)

# Guardar cambios en sesión (actualiza toda la base filtrada)
mask_idx = df_session.index.isin(edited_df.index)
df_session.loc[mask_idx, "Gestionado"] = edited_df["Gestionado"].values
df_session.loc[mask_idx, "Ticket"] = edited_df["Ticket"].values

st.session_state["df_data"] = df_session

# --- SELECCIÓN DE VISTA ---
st.divider()
st.subheader("👁️ Visualización")
vista = st.radio(
    "Selecciona qué avisos visualizar:",
    ["Todos los avisos", "Sólo gestionados"],
    horizontal=True
)

if vista == "Sólo gestionados":
    df_vista = df_session[df_session["Gestionado"] == True]
else:
    df_vista = df_session.copy()

st.dataframe(df_vista, use_container_width=True, hide_index=True)

# --- DESCARGA DE RESULTADOS ---
st.divider()
st.subheader("📥 Descargar resultados")
buffer = BytesIO()
with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
    df_session.to_excel(writer, index=False, sheet_name="Avisos")
buffer.seek(0)
st.download_button(
    "📥 Descargar Excel actualizado",
    data=buffer,
    file_name="avisos_actualizados.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

st.divider()
st.caption("Versión interactiva con control de gestión y tickets — CMPC Cordillera © 2025")
