# ==============================================
# 📊 APP STREAMLIT - CLASIFICACIÓN DE AVISOS CMPC
# Adaptada a BACKLOG_PROCESADO_FINAL_V13.xlsx
# ==============================================

from __future__ import annotations
import streamlit as st
import pandas as pd
from io import BytesIO
import os
import tempfile
import shutil

# ---------------------------------------------------
# 📌 AJUSTE DE ANCHO (evita visualización delgada)
# ---------------------------------------------------
st.set_page_config(page_title="Sistema de gestión de Avisos SAP PM", layout="wide")

st.markdown("""
    <style>
    .block-container {
        max-width: 95% !important;
        padding-left: 2rem;
        padding-right: 2rem;
    }
    </style>
""", unsafe_allow_html=True)

st.title("📊 Sistema de Apoyo a la Gestión de Avisos SAP PM")
st.caption("Prototipo funcional para el análisis, priorización y gestión del backlog de mantenimiento.")
st.divider()

# ARCHIVOS ACTUALIZADOS
ARCHIVO_ORIGINAL = "BACKLOG_PROCESADO_FINAL_V13.xlsx"
ARCHIVO_PERSISTENTE = "persistente_backlog_v4.xlsx"


# ---------------------------------------------------
# ⚠️ BORRAR PERSISTENTE SI ESTÁ CORRUPTO O SIN CRITICIDAD
# ---------------------------------------------------
def chequear_persistente():
    if os.path.exists(ARCHIVO_PERSISTENTE):
        try:
            df_test = pd.read_excel(ARCHIVO_PERSISTENTE)

            if "criticidad_final" not in df_test.columns and \
               "Criticidad (Modelo)" not in df_test.columns:
                os.remove(ARCHIVO_PERSISTENTE)

        except:
            os.remove(ARCHIVO_PERSISTENTE)

chequear_persistente()


# ---------------------------------------------------
# 🔧 CARGA SEGURO DESDE EXCEL
# ---------------------------------------------------
def cargar_excel(path: str) -> pd.DataFrame:
    df = pd.read_excel(path)
    df.columns = df.columns.astype(str).str.strip()
    return df


# ---------------------------------------------------
# 🛠️ CREAR PERSISTENTE DESDE ORIGINAL
# ---------------------------------------------------
def crear_persistente_desde_original():

    df = cargar_excel(ARCHIVO_ORIGINAL)

    # Renombres para que encaje con la estructura existente
    rename_map = {
        "Ubicac.técnica_x": "Ubicación técnica",
        "Txt. cód. mot.": "Cód. motivo",
        "TextoCódProblem": "Descripción motivo",
        "criticidad_final": "Criticidad (Modelo)",
        "Clase de orden": "Clase de orden (Modelo)",
        "Clase de actividad_pred": "Actividad PM (Modelo)",
        "Puesto_responsable_pred": "Centro de trabajo (Modelo)",
        "Costo_estimado": "Costo estimado",
    }

    for col, new in rename_map.items():
        if col in df.columns:
            df.rename(columns={col: new}, inplace=True)

    # Crear columna Gestionado si no existe
    if "Gestionado" not in df.columns:
        df["Gestionado"] = False

    # Guardado persistente seguro
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        df.to_excel(tmp.name, index=False)
        shutil.move(tmp.name, ARCHIVO_PERSISTENTE)

    return df


# ---------------------------------------------------
# 🔄 CARGA PRINCIPAL
# ---------------------------------------------------
if os.path.exists(ARCHIVO_PERSISTENTE):
    df_raw = cargar_excel(ARCHIVO_PERSISTENTE)
else:
    df_raw = crear_persistente_desde_original()


# ---------------------------------------------------
# LIMPIEZA
# ---------------------------------------------------
if "Fecha de aviso" in df_raw:
    df_raw["Fecha de aviso"] = pd.to_datetime(df_raw["Fecha de aviso"], errors="coerce").dt.date


# ---------------------------------------------------
# OCULTAR COLUMNAS QUE NO DEBEN APARECER
# ---------------------------------------------------
# ---------------------------------------------------
# OCULTAR COLUMNAS QUE NO DEBEN APARECER
# ---------------------------------------------------
columnas_ocultas = [
    "Ubicac.técnica",
    "texto_total", "antiguedad", "dias_gestion",
    "grupo_area", "criticidad_modelo",
    "score_abc", "texto_act", "texto_resp",
    "texto_full", "anio", "mes",
    "dia_semana",
]

# Aplicar eliminación en df_raw
df_raw = df_raw.drop(columns=columnas_ocultas, errors="ignore")

# Aplicar eliminación también en df_session al cargar datos
if "df_data" not in st.session_state:
    st.session_state["df_data"] = df_raw.copy()
else:
    # Sanear df_session si quedó con columnas antiguas
    st.session_state["df_data"] = st.session_state["df_data"].drop(
        columns=columnas_ocultas, errors="ignore"
    )

df_session = st.session_state["df_data"]



# ---------------------------------------------------
# SESIÓN
# ---------------------------------------------------
if "df_data" not in st.session_state:
    st.session_state["df_data"] = df_raw.copy()

df_session = st.session_state["df_data"]


# ---------------------------------------------------
# SIDEBAR FILTROS
# ---------------------------------------------------
with st.sidebar:
    st.header("🔍 Filtros")

    grupo_opts = ["(Todos)"] + sorted(df_session["Grupo planif."].dropna().astype(str).unique())
    prioridad_opts = ["(Todos)"] + sorted(df_session["Prioridad"].dropna().astype(str).unique())
    abc_opts = ["(Todos)"] + sorted(df_session["Indicador ABC"].dropna().astype(str).unique())

    grupo = st.selectbox("Grupo planificador", grupo_opts)
    prioridad = st.selectbox("Prioridad", prioridad_opts)
    abc = st.selectbox("Indicador ABC", abc_opts)

df_filtrado = df_session.copy()
if grupo != "(Todos)":
    df_filtrado = df_filtrado[df_filtrado["Grupo planif."].astype(str) == grupo]
if prioridad != "(Todos)":
    df_filtrado = df_filtrado[df_filtrado["Prioridad"].astype(str) == prioridad]
if abc != "(Todos)":
    df_filtrado = df_filtrado[df_filtrado["Indicador ABC"].astype(str) == abc]


# ---------------------------------------------------
# 📊 MÉTRICAS PRINCIPALES
# ---------------------------------------------------
st.subheader("📊 Métricas generales dadas por el modelo de inteligencia artificial")
col1, col2, col3, col4, col5 = st.columns(5)

col1.metric("Total avisos", len(df_filtrado))

crit_mean = pd.to_numeric(df_filtrado["Criticidad (Modelo)"], errors="coerce").mean()
col2.metric("Criticidad promedio", f"{crit_mean:.1f}")

pct = df_filtrado["Gestionado"].mean() * 100
col3.metric("% Gestionados", f"{pct:.1f}%")

Costo_prom = df_filtrado["Costo estimado"].mean()
col4.metric("Costo promedio estimado", f"${round(Costo_prom):,}".replace(",", "."))

Costo_total = df_filtrado["Costo estimado"].sum()
col5.metric("Costo total estimado", f"${round(Costo_total):,}".replace(",", "."))


# ---------------------------------------------------
# 🔦 SEMÁFORO DE CRITICIDAD
# ---------------------------------------------------
if crit_mean <= 35:
    nivel = "🟢 Criticidad Baja"
elif crit_mean <= 70:
    nivel = "🟡 Criticidad Media"
else:
    nivel = "🔴 Criticidad Alta"

st.markdown(
    f"<div style='padding:12px; font-size:22px; font-weight:600;'>{nivel} — Promedio: {crit_mean:.1f}</div>",
    unsafe_allow_html=True
)


# ---------------------------------------------------
# 🚨 ALERTAS CRÍTICOS > 90
# ---------------------------------------------------
criticos = df_session[pd.to_numeric(df_session["Criticidad (Modelo)"], errors="coerce") > 90]

if len(criticos) > 0:
    st.error(f"⚠️ {len(criticos)} avisos con Criticidad > 90. Revisar urgente.")


st.divider()


# ---------------------------------------------------
# 📋 TABLA EDITABLE
# ---------------------------------------------------
st.subheader("📋 Avisos en Backlog")

df_filtrado = df_filtrado.sort_values(by="Criticidad (Modelo)", ascending=False)

edited_df = st.data_editor(
    df_filtrado,
    hide_index=True,
    use_container_width=True,
    column_config={"Gestionado": st.column_config.CheckboxColumn("Gestionado")},
    key="tabla_editable"
)

df_session.loc[edited_df.index, "Gestionado"] = edited_df["Gestionado"]
st.session_state["df_data"] = df_session

# Guardado seguro
with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
    df_session.to_excel(tmp.name, index=False)
    shutil.move(tmp.name, ARCHIVO_PERSISTENTE)


# ---------------------------------------------------
# 👁️ VISTAS DEL BACKLOG
# ---------------------------------------------------
st.subheader("👁️ Visualización del backlog")

vista = st.radio("Seleccionar vista:", ["Todos", "Gestionados", "No gestionados"], horizontal=True)

if vista == "Todos":
    df_vista = df_session
elif vista == "Gestionados":
    df_vista = df_session[df_session["Gestionado"] == True]
else:
    df_vista = df_session[df_session["Gestionado"] == False]

df_vista = df_vista.sort_values(by="Criticidad (Modelo)", ascending=False)

st.dataframe(df_vista, use_container_width=True, hide_index=True)


# ---------------------------------------------------
# 🌡️ HEATMAP
# ---------------------------------------------------
st.subheader("🌡️ Mapa de calor por Grupo Planificador")

dfh = df_session.copy()
dfh["Criticidad (Modelo)"] = pd.to_numeric(dfh["Criticidad (Modelo)"], errors="coerce")

heat = dfh.pivot_table(index="Grupo planif.", values="Criticidad (Modelo)", aggfunc="mean").fillna(0)

st.dataframe(
    heat.style.background_gradient(cmap="RdYlGn_r"),
    use_container_width=True
)


# ---------------------------------------------------
# 📈 HISTOGRAMA
# ---------------------------------------------------
st.subheader("📈 Distribución de criticidad")

crit_vals = pd.to_numeric(df_filtrado["Criticidad (Modelo)"], errors="coerce").dropna()

bins = list(range(1, 102))
hist = pd.cut(crit_vals, bins=bins, right=False)
freq = hist.value_counts().sort_index()

freq_df = pd.DataFrame({"Criticidad": range(1, 101), "Cantidad": freq.values})
st.bar_chart(freq_df.set_index("Criticidad"))

st.caption("CMPC Cordillera © 2025 - Subgerencia de mantenimiento")
