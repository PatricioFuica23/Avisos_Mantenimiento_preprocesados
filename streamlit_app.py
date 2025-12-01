# ==============================================
# 📊 APP STREAMLIT - CLASIFICACIÓN DE AVISOS CMPC
# Fuente: avisos_backlog_gestionados.xlsx
# Persistente nuevo y limpio (v2)
# ==============================================

from __future__ import annotations
import streamlit as st
import pandas as pd
from io import BytesIO
import os

ARCHIVO_ORIGINAL = "avisos_backlog_gestionados.xlsx"
ARCHIVO_PERSISTENTE1 = "persistente_backlog_v2.xlsx"   # NUEVO ARCHIVO PERSISTENTE

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Sistema de gestión de Avisos SAP PM", page_icon="🧠", layout="wide")

st.title("📊 Clasificación Automática de Avisos SAP PM")
st.caption("Prototipo funcional para visualizar y gestionar avisos no tratados.")

# --- FUNCIONES ---
def cargar_excel(path: str) -> pd.DataFrame:
    df = pd.read_excel(path, engine="openpyxl")
    df.columns = df.columns.astype(str).str.replace(r"[\r\n]+", " ", regex=True).str.strip()
    return df

def crear_persistente_desde_original():
    """Carga archivo original, renombra columnas válidas y genera persistente limpio."""
    df = cargar_excel(ARCHIVO_ORIGINAL)

    rename_map = {
        "Ubicac.técnica_x": "Ubicación técnica",
        "Txt. cód. mot.": "Cód. motivo",
        "TextoCódProblem": "Descripción motivo",
        "criticidad_predicha": "Criticidad (modelo)",
        "Clase_orden_recomendada": "Clase de orden (modelo)",
        "Cl_actividad_PM_recomendada": "Actividad PM (modelo)",
        "Pto_tbjo_resp_recomendado": "Centro de trabajo (modelo)",
        "Costo_total_estimado": "Costo estimado",
    }

    # Renombrado seguro
    for col, new in rename_map.items():
        if col in df.columns:
            df.rename(columns={col: new}, inplace=True)

    # Crear columna Gestionado si no existe
    if "Gestionado" not in df.columns:
        df["Gestionado"] = False

    df.to_excel(ARCHIVO_PERSISTENTE1, index=False)
    return df

# --- CARGA ROBUSTA ---
if os.path.exists(ARCHIVO_PERSISTENTE1):
    df_raw = cargar_excel(ARCHIVO_PERSISTENTE1)
else:
    df_raw = crear_persistente_desde_original()

# Mostrar columnas detectadas (diagnóstico)
# st.write("Columnas detectadas por la app:", df_raw.columns.tolist())

# --- LIMPIEZA ---
if "Fecha de aviso" in df_raw.columns:
    df_raw["Fecha de aviso"] = pd.to_datetime(df_raw["Fecha de aviso"], errors="coerce").dt.date

# --- GUARDAR EN SESIÓN ---
if "df_data" not in st.session_state:
    st.session_state["df_data"] = df_raw.copy()

df_session = st.session_state["df_data"]

# -----------------------------
# 🔍 SIDEBAR - FILTROS
# -----------------------------
with st.sidebar:
    st.header("🔍 Filtros")

    grupo_opts = ["(Todos)"] + sorted(df_session["Grupo planif."].dropna().astype(str).unique().tolist()) if "Grupo planif." in df_session else ["(Todos)"]
    prioridad_opts = ["(Todos)"] + sorted(df_session["Prioridad"].dropna().astype(str).unique().tolist()) if "Prioridad" in df_session else ["(Todos)"]
    abc_opts = ["(Todos)"] + sorted(df_session["Indicador ABC"].dropna().astype(str).unique().tolist()) if "Indicador ABC" in df_session else ["(Todos)"]

    grupo = st.selectbox("Grupo planificador", grupo_opts)
    prioridad = st.selectbox("Prioridad", prioridad_opts)
    abc = st.selectbox("Indicador ABC", abc_opts)

# Aplicar filtros
df_filtrado = df_session.copy()
if grupo != "(Todos)" and "Grupo planif." in df_filtrado:
    df_filtrado = df_filtrado[df_filtrado["Grupo planif."].astype(str) == grupo]
if prioridad != "(Todos)" and "Prioridad" in df_filtrado:
    df_filtrado = df_filtrado[df_filtrado["Prioridad"].astype(str) == prioridad]
if abc != "(Todos)" and "Indicador ABC" in df_filtrado:
    df_filtrado = df_filtrado[df_filtrado["Indicador ABC"].astype(str) == abc]

# -----------------------------
# 📊 MÉTRICAS
# -----------------------------
st.subheader("📊 Resumen general")
col1, col2, col3, col4, col5 = st.columns(5)

col1.metric("Total avisos", len(df_filtrado))

# Criticidad promedio seguro
if "Criticidad (modelo)" in df_filtrado:
    crit_mean = pd.to_numeric(df_filtrado["Criticidad (modelo)"], errors="coerce").mean()
    col2.metric("Criticidad promedio", f"{crit_mean:.1f}")
else:
    col2.metric("Criticidad promedio", "—")

# Porcentaje gestionados
if "Gestionado" in df_filtrado:
    pct_gest = df_filtrado["Gestionado"].mean() * 100
    col3.metric("% Gestionados", f"{pct_gest:.1f}%")
else:
    col3.metric("% Gestionados", "0.0%")

Costo_prom = pd.to_numeric(df_filtrado["Costo estimado"], errors="coerce").mean()
# Redondear y formatear como dinero CLP
if pd.notna(Costo_prom):
    Costo_prom = round(Costo_prom)
    Costo_prom_fmt = f"${Costo_prom:,.0f}".replace(",", ".")
else:
    Costo_prom_fmt = "$0"

col4.metric("Costo promedio estimado del Backlog", Costo_prom_fmt)

Costo_total = pd.to_numeric(df_filtrado["Costo estimado"], errors="coerce").sum()
# Redondear y formatear como dinero CLP
if pd.notna(Costo_total):
    Costo_total = round(Costo_total)
    Costo_total_fmt = f"${Costo_total:,.0f}".replace(",", ".")
else:
    Costo_total_fmt = "$0"

col5.metric("Costo total estimado del Backlog", Costo_total_fmt)


st.divider()

# -----------------------------
# 📋 TABLA EDITABLE
# -----------------------------
st.subheader("📋 Tabla de avisos")

edited_df = st.data_editor(
    df_filtrado,
    hide_index=True,
    use_container_width=True,
    column_config={
        "Gestionado": st.column_config.CheckboxColumn("Gestionado")
    },
    key="tabla_editable"
)

# Guardar cambios
if "Gestionado" in edited_df.columns:
    df_session.loc[edited_df.index, "Gestionado"] = edited_df["Gestionado"].values
    st.session_state["df_data"] = df_session

# Guardar persistente nuevo
df_session.to_excel(ARCHIVO_PERSISTENTE1, index=False)

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

st.download_button("Descargar archivo actualizado", buffer, "avisos_actualizados.xlsx")

# -----------------------------
# 📈 HISTOGRAMA
# -----------------------------
st.subheader("📈 Distribución de criticidad")

if "Criticidad (modelo)" in df_filtrado:
    crit_vals = pd.to_numeric(df_filtrado["Criticidad (modelo)"], errors="coerce")
    st.bar_chart(crit_vals)

st.caption("Versión estable — CMPC Cordillera © 2025")
