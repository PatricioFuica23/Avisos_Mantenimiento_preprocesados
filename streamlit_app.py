# ==============================================
# 📊 APP STREAMLIT - CLASIFICACIÓN DE AVISOS CMPC
# Fuente: avisos_backlog_gestionados.xlsx
# Opción A + columnas renombradas + sin Ticket + sin carga manual
# ==============================================

from __future__ import annotations
import streamlit as st
import pandas as pd
from io import BytesIO
import os

ARCHIVO_PERSISTENTE = "avisos_guardados.xlsx"
ARCHIVO_ORIGINAL = "avisos_backlog_gestionados.xlsx"

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Clasificación de Avisos SAP PM", page_icon="🧠", layout="wide")

st.title("📊 Clasificación Automática de Avisos SAP PM")
st.caption("Prototipo funcional para visualizar y gestionar avisos no tratados.")

# --- FUNCIONES AUXILIARES ---
def cargar_excel(path: str) -> pd.DataFrame:
    df = pd.read_excel(path, engine="openpyxl")
    df.columns = df.columns.astype(str).str.replace(r"[\r\n]+", " ", regex=True).str.strip()
    return df

# --- CARGA DE DATOS ---
if os.path.exists(ARCHIVO_PERSISTENTE):
    df_raw = cargar_excel(ARCHIVO_PERSISTENTE)
else:
    try:
        df_raw = cargar_excel(ARCHIVO_ORIGINAL)
    except FileNotFoundError:
        st.error(f"❌ No se encontró el archivo {ARCHIVO_ORIGINAL}.")
        st.stop()

# --- SELECCIÓN DE COLUMNAS (Opción A) ---
columnas = {
    "Aviso": "Aviso",
    "Fecha de aviso": "Fecha de aviso",
    "Descripción": "Descripción",
    "Ubicac.técnica_x": "Ubicación técnica",
    "Indicador ABC": "Indicador ABC",
    "Grupo planif.": "Grupo planif.",
    "Clase de aviso": "Clase de aviso",
    "Denominación": "Denominación",
    "Prioridad": "Prioridad",
    "Txt. cód. mot.": "Cód. motivo",
    "TextoCódProblem": "Descripción motivo",
    "criticidad_predicha": "Criticidad (modelo)",
    "Clase_orden_recomendada": "Clase de orden (modelo)",
    "Cl_actividad_PM_recomendada": "Actividad PM (modelo)",
    "Pto_tbjo_resp_recomendado": "Centro de trabajo (modelo)",
    "Costo_total_estimado": "Costo estimado"
}

columnas_presentes = [c for c in columnas.keys() if c in df_raw.columns]

df = df_raw[columnas_presentes].copy()
df.rename(columns=columnas, inplace=True)

# --- LIMPIEZA Y FORMATEO ---
if "Fecha de aviso" in df.columns:
    df["Fecha de aviso"] = pd.to_datetime(df["Fecha de aviso"], errors="coerce").dt.date

# Crear columna Gestionado si no existe
if "Gestionado" not in df_raw.columns:
    df["Gestionado"] = False
else:
    df["Gestionado"] = df_raw["Gestionado"]

# --- STATE ---
if "df_data" not in st.session_state:
    st.session_state["df_data"] = df.copy()

df_session = st.session_state["df_data"]

# -----------------------------
# 🔍 SIDEBAR - FILTROS
# -----------------------------
with st.sidebar:
    st.header("🔍 Filtros de visualización")

    grupo_opts = ["(Todos)"] + sorted(df_session["Grupo planif."].dropna().astype(str).unique().tolist())
    prioridad_opts = ["(Todos)"] + sorted(df_session["Prioridad"].dropna().astype(str).unique().tolist())
    abc_opts = ["(Todos)"] + sorted(df_session["Indicador ABC"].dropna().astype(str).unique().tolist())

    grupo = st.selectbox("Grupo planificador", grupo_opts)
    prioridad = st.selectbox("Prioridad", prioridad_opts)
    abc = st.selectbox("Indicador ABC", abc_opts)

# Aplicar filtros
df_filtrado = df_session.copy()
if grupo != "(Todos)": df_filtrado = df_filtrado[df_filtrado["Grupo planif."] == grupo]
if prioridad != "(Todos)": df_filtrado = df_filtrado[df_filtrado["Prioridad"] == prioridad]
if abc != "(Todos)": df_filtrado = df_filtrado[df_filtrado["Indicador ABC"] == abc]

# -----------------------------
# 📊 MÉTRICAS
# -----------------------------
st.subheader("📊 Resumen general")
col1, col2, col3 = st.columns(3)

col1.metric("Total avisos", len(df_filtrado))
col2.metric("Criticidad promedio", f"{df_filtrado["Criticidad (modelo)"].mean():.1f}")
col3.metric("% Gestionados", f"{df_filtrado['Gestionado'].mean()*100:.1f}%")

st.divider()

# -----------------------------
# 📋 TABLA EDITABLE
# -----------------------------
st.subheader("📋 Tabla de avisos (editable)")

edited_df = st.data_editor(
    df_filtrado,
    hide_index=True,
    use_container_width=True,
    column_config={
        "Gestionado": st.column_config.CheckboxColumn("Gestionado")
    },
    key="tabla_edicion"
)

# Actualizar cambios en toda la base
df_session.loc[edited_df.index, "Gestionado"] = edited_df["Gestionado"].values
st.session_state["df_data"] = df_session

# Guardado persistente
df_session.to_excel(ARCHIVO_PERSISTENTE, index=False)

# -----------------------------
# 👁️ VISUALIZACIÓN
# -----------------------------
vista = st.radio("Vista:", ["Todos", "Solo gestionados"], horizontal=True)

df_vista = df_session if vista == "Todos" else df_session[df_session["Gestionado"]]

st.dataframe(df_vista, use_container_width=True, hide_index=True)

# -----------------------------
# 📥 DESCARGA
# -----------------------------
st.subheader("📥 Descargar Excel")

buffer = BytesIO()
with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
    df_session.to_excel(writer, index=False)
buffer.seek(0)

st.download_button(
    "Descargar archivo actualizado",
    buffer,
    "avisos_actualizados.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

# -----------------------------
# 📈 HISTOGRAMA DE CRITICIDAD
# -----------------------------
st.subheader("📈 Distribución de criticidad (modelo)")

if "Criticidad (modelo)" in df_filtrado:
    crit = df_filtrado["Criticidad (modelo)"].fillna(0).astype(float)
    st.bar_chart(crit, use_container_width=True)

st.caption("Versión actualizada — CMPC Cordillera © 2025")