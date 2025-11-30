# ==============================================
# 📊 APP STREAMLIT - CLASIFICACIÓN DE AVISOS CMPC
# SIN carga manual de archivo + SIN columna Ticket
# ==============================================

from __future__ import annotations
import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
import os

ARCHIVO_PERSISTENTE = "avisos_guardados.xlsx"

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Clasificación de Avisos SAP PM", page_icon="🧠", layout="wide")

st.title("📊 Clasificación Automática de Avisos SAP PM")
st.caption("Algoritmo de apoyo a la gestion de avisos de mantenimiento")

st.markdown("""
💡 **Objetivo:** Visualizar los avisos clasificados por el modelo, revisar su criticidad,
y permitir a los trabajadores marcar cuáles fueron gestionados.
""")

st.divider()

# --- FUNCIONES AUXILIARES ---
def cargar_datos(path: str) -> pd.DataFrame:
    df = pd.read_excel(path, engine="openpyxl")
    df.columns = df.columns.astype(str).str.replace(r"[\r\n]+", " ", regex=True).str.strip()
    return df

def color_hex_verde_amarillo_rojo(v: float, vmin: float = 1, vmax: float = 100) -> str:
    verde, amarillo, rojo = (46, 204, 113), (241, 196, 15), (231, 76, 60)
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

# --- CARGA DE DATOS ---
# 1️⃣ Si existe archivo persistente guardado, cargarlo
if os.path.exists(ARCHIVO_PERSISTENTE):
    df_raw = cargar_datos(ARCHIVO_PERSISTENTE)
else:
    # 2️⃣ Cargar archivo original desde GitHub / local
    try:
        df_raw = cargar_datos("predicciones_avisos_sin_gestionar_rf_v5.xlsx")
    except FileNotFoundError:
        st.error("❌ No se encontró `predicciones_avisos_sin_gestionar_rf_v5.xlsx`.")
        st.stop()

# --- SELECCIÓN DE COLUMNAS RELEVANTES ---
columnas_presentes = df_raw.columns.tolist()

cols_relevantes = [c for c in [
    "Aviso", "Fecha de aviso", "Descripción", "Ubicac.técnica", "Indicador ABC",
    "Grupo planif.", "Clase de aviso", "Denominación", "Prioridad",
    "Txt. cód. mot.", "TextoCódProblem",
    "criticidad_final", "Clase de orden_pred", "Cl.actividad PM_pred",
    "Pto.tbjo.resp._pred", "Nivel criticidad",
    "Gestionado"
] if c in columnas_presentes]

df = df_raw[cols_relevantes].copy()

# --- LIMPIEZA Y FORMATEO ---
if "Fecha de aviso" in df.columns:
    df["Fecha de aviso"] = pd.to_datetime(df["Fecha de aviso"], errors="coerce").dt.date
if "criticidad_final" in df.columns:
    df["criticidad_final"] = pd.to_numeric(df["criticidad_final"], errors="coerce")

# --- NUEVA COLUMNA (Gestionado) ---
if "Gestionado" not in df.columns:
    df["Gestionado"] = False

# --- SESSION STATE ---
if "df_data" not in st.session_state:
    st.session_state["df_data"] = df.copy()

df_session = st.session_state["df_data"]

# --- SIDEBAR FILTROS ---
with st.sidebar:
    st.header("🔍 Filtros")

    grupo_opts = ["(Todos)"] + sorted(df_session["Grupo planif."].dropna().unique().astype(str).tolist()) if "Grupo planif." in df_session else ["(Todos)"]
    prioridad_opts = ["(Todos)"] + sorted(df_session["Prioridad"].dropna().unique().astype(str).tolist()) if "Prioridad" in df_session else ["(Todos)"]
    abc_opts = ["(Todos)"] + sorted(df_session["Indicador ABC"].dropna().unique().astype(str).tolist()) if "Indicador ABC" in df_session else ["(Todos)"]
    nivel_opts = ["(Todos)"] + sorted(df_session["Nivel criticidad"].dropna().unique().astype(str).tolist()) if "Nivel criticidad" in df_session else ["(Todos)"]

    grupo = st.selectbox("Grupo planificador", grupo_opts)
    prioridad = st.selectbox("Prioridad", prioridad_opts)
    abc = st.selectbox("Indicador ABC", abc_opts)
    Nivel_criticidad = st.selectbox("Nivel criticidad", nivel_opts)

# --- APLICAR FILTROS ---
df_filtrado = df_session.copy()
if grupo != "(Todos)":
    df_filtrado = df_filtrado[df_filtrado["Grupo planif."].astype(str) == grupo]
if prioridad != "(Todos)":
    df_filtrado = df_filtrado[df_filtrado["Prioridad"].astype(str) == prioridad]
if abc != "(Todos)":
    df_filtrado = df_filtrado[df_filtrado["Indicador ABC"].astype(str) == abc]
if Nivel_criticidad != "(Todos)":
    df_filtrado = df_filtrado[df_filtrado["Nivel criticidad"].astype(str) == Nivel_criticidad]

# --- MÉTRICAS ---
st.subheader("📊 Resumen general")
col1, col2, col3 = st.columns(3)
col1.metric("Total avisos", len(df_filtrado))
col2.metric("Criticidad promedio", f"{df_filtrado['criticidad_final'].mean():.1f}" if "criticidad_final" in df_filtrado else "—")
col3.metric("% Gestionados", f"{(df_filtrado['Gestionado'].mean() * 100):.1f}%")

st.divider()

# --- TABLA EDITABLE ---
st.subheader("📋 Tabla de avisos (editable)")

edited_df = st.data_editor(
    df_filtrado,
    num_rows="dynamic",
    use_container_width=True,
    hide_index=True,
    column_config={"Gestionado": st.column_config.CheckboxColumn("Gestionado")},
    key="editable_table"
)

# --- ACTUALIZAR Y GUARDAR ---
mask_idx = df_session.index.isin(edited_df.index)
df_session.loc[mask_idx, "Gestionado"] = edited_df["Gestionado"].values
st.session_state["df_data"] = df_session

# Guardado persistente
df_session.to_excel(ARCHIVO_PERSISTENTE, index=False)

# --- VISTA ---
st.subheader("👁️ Visualización")
vista = st.radio("Selecciona qué avisos visualizar:", ["Todos los avisos", "Sólo gestionados"], horizontal=True)
df_vista = df_session if vista == "Todos los avisos" else df_session[df_session["Gestionado"]]

st.dataframe(df_vista, use_container_width=True, hide_index=True)

# --- DESCARGA ---
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

# --- HISTOGRAMA ---
st.divider()
st.subheader("📈 Distribución de criticidad (1 → 100)")

if "criticidad_final" in df_filtrado and not df_filtrado.empty:
    crit = pd.to_numeric(df_filtrado["criticidad_final"], errors="coerce").dropna()
    crit = crit.clip(lower=1, upper=100).round().astype(int)

    conteo = (
        crit.value_counts()
        .reindex(range(1, 101), fill_value=0)
        .sort_index()
        .rename("Cantidad de avisos")
        .to_frame()
    )

    st.bar_chart(conteo, use_container_width=True)
else:
    st.info("No hay datos de criticidad para graficar.")

st.caption("Versión interactiva con control de gestión — CMPC Cordillera © 2025")
