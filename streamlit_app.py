# ==============================================
# 📊 APP STREAMLIT - CLASIFICACIÓN DE AVISOS CMPC
# Nueva arquitectura: archivo persistente limpio y seguro
# ==============================================

from __future__ import annotations
import streamlit as st
import pandas as pd
from io import BytesIO
import os

ARCHIVO_ORIGINAL = "avisos_backlog_gestionados.xlsx"
ARCHIVO_PERSISTENTE = "avisos_backlog_limpio.xlsx"   # <── archivo estable y limpio

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Clasificación de Avisos SAP PM", page_icon="🧠", layout="wide")
st.title("📊 Clasificación Automática de Avisos SAP PM")
st.caption("Versión con archivo persistente limpio y columnas estandarizadas.")

# --- FUNCIONES ---
def cargar_excel(path: str) -> pd.DataFrame:
    df = pd.read_excel(path, engine="openpyxl")
    df.columns = df.columns.astype(str).str.replace(r"[\r\n]+", " ", regex=True).str.strip()
    return df

def crear_persistente_limpio():
    """Carga el archivo original, renombra columnas y crea el persistente limpio."""
    df_raw = cargar_excel(ARCHIVO_ORIGINAL)

    rename_map = {
        "Aviso": "Aviso",
        "Fecha de aviso": "Fecha de aviso",
        "Descripción": "Descripción",
        "Ubicac.técnica_x": "Ubicación técnica",
        "Indicador ABC": "Indicador ABC",
        "Grupo planif.": "Grupo planif.",
        "Clase de aviso": "Clase de aviso",
        "Orden": "Orden de mantenimiento",
        "Denominación": "Denominación",
        "Prioridad": "Prioridad",
        "Txt. cód. mot.": "Cód. motivo",
        "TextoCódProblem": "Descripción motivo",
        "criticidad_predicha": "Criticidad (modelo)",
        "Clase_orden_recomendada": "Clase de orden (modelo)",
        "Cl_actividad_PM_recomendada": "Actividad PM (modelo)",
        "Pto_tbjo_resp_recomendado": "Centro de trabajo (modelo)",
        "Costo_total_estimado": "Costo estimado",
    }

    df_raw.rename(columns=rename_map, inplace=True)

    columnas_objetivo = list(rename_map.values())
    columnas_presentes = [c for c in columnas_objetivo if c in df_raw.columns]
    df = df_raw[columnas_presentes].copy()

    # Columna Gestionado
    df["Gestionado"] = False

    df.to_excel(ARCHIVO_PERSISTENTE, index=False)
    return df

# --- CARGA DE DATOS ---
if os.path.exists(ARCHIVO_PERSISTENTE):
    df_raw = cargar_excel(ARCHIVO_PERSISTENTE)
else:
    df_raw = cargar_excel(ARCHIVO_ORIGINAL)

# MOSTRAR COLUMNAS REALES DEL ARCHIVO
st.write("Columnas detectadas por la app:", df_raw.columns.tolist())

# --- LIMPIEZA ---
if "Fecha de aviso" in df.columns:
    df["Fecha de aviso"] = pd.to_datetime(df["Fecha de aviso"], errors="coerce").dt.date

# --- STATE ---
if "df_data" not in st.session_state:
    st.session_state["df_data"] = df.copy()

df_session = st.session_state["df_data"]

# --- FILTROS ---
with st.sidebar:
    st.header("🔍 Filtros")

    grupo_opts = ["(Todos)"] + sorted(df_session["Grupo planif."].dropna().astype(str).unique().tolist())
    prioridad_opts = ["(Todos)"] + sorted(df_session["Prioridad"].dropna().astype(str).unique().tolist())
    abc_opts = ["(Todos)"] + sorted(df_session["Indicador ABC"].dropna().astype(str).unique().tolist())

    grupo = st.selectbox("Grupo planificador", grupo_opts)
    prioridad = st.selectbox("Prioridad", prioridad_opts)
    abc = st.selectbox("Indicador ABC", abc_opts)

df_filtrado = df_session.copy()
if grupo != "(Todos)":
    df_filtrado = df_filtrado[df_filtrado["Grupo planif."] == grupo]
if prioridad != "(Todos)":
    df_filtrado = df_filtrado[df_filtrado["Prioridad"] == prioridad]
if abc != "(Todos)":
    df_filtrado = df_filtrado[df_filtrado["Indicador ABC"] == abc]

# --- MÉTRICAS ---
st.subheader("📊 Resumen general")
col1, col2, col3 = st.columns(3)

col1.metric("Total avisos", len(df_filtrado))

if "Criticidad (modelo)" in df_filtrado:
    col2.metric("Criticidad promedio", f"{df_filtrado['Criticidad (modelo)'].mean():.1f}")
else:
    col2.metric("Criticidad promedio", "—")

col3.metric("% Gestionados", f"{df_filtrado['Gestionado'].mean()*100:.1f}%")

st.divider()

# --- TABLA EDITABLE ---
st.subheader("📋 Tabla de avisos")

edited_df = st.data_editor(
    df_filtrado,
    hide_index=True,
    use_container_width=True,
    column_config={"Gestionado": st.column_config.CheckboxColumn("Gestionado")},
    key="tabla"
)

df_session.loc[edited_df.index, "Gestionado"] = edited_df["Gestionado"].values
st.session_state["df_data"] = df_session

# --- GUARDADO PERSISTENTE ---
df_session.to_excel(ARCHIVO_PERSISTENTE, index=False)

# --- visualización ---
vista = st.radio("Vista:", ["Todos", "Solo gestionados"], horizontal=True)
df_vista = df_session if vista == "Todos" else df_session[df_session["Gestionado"]]
st.dataframe(df_vista, use_container_width=True)

# --- DESCARGA ---
buffer = BytesIO()
with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
    df_session.to_excel(writer, index=False)
buffer.seek(0)

st.download_button("Descargar Excel", buffer, "avisos_actualizados.xlsx")

# --- HISTOGRAMA ---
st.subheader("📈 Distribución de criticidad")

if "Criticidad (modelo)" in df_filtrado:
    st.bar_chart(df_filtrado["Criticidad (modelo)"])

st.caption("Versión estable — CMPC Cordillera © 2025")
