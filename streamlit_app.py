# ==============================================
# 📊 APP STREAMLIT - CLASIFICACIÓN DE AVISOS CMPC
# Versión estable con criticidad + semáforo + heatmap + alertas
# ==============================================

from __future__ import annotations
import streamlit as st
import pandas as pd
from io import BytesIO
import os
import tempfile
import shutil

ARCHIVO_ORIGINAL = "avisos_backlog_gestionados.xlsx"
ARCHIVO_PERSISTENTE = "persistente_backlog_v3.xlsx"  # NUEVO persistente limpio

# ---------------------------------------------------
# ⚠️ BORRAR PERSISTENTE SI ESTÁ CORRUPTO O INCOMPLETO
# ---------------------------------------------------
def chequear_persistente():
    if os.path.exists(ARCHIVO_PERSISTENTE):
        try:
            df_test = pd.read_excel(ARCHIVO_PERSISTENTE)

            # ❗ Borrar persistente si NO tiene criticidad
            if "criticidad_predicha" not in df_test.columns and \
               "Criticidad (Modelo)" not in df_test.columns:
                os.remove(ARCHIVO_PERSISTENTE)

        except:
            os.remove(ARCHIVO_PERSISTENTE)

chequear_persistente()

# ---------------------------------------------------
# 🔧 CARGA SEGURO DESDE EXCELl
# ---------------------------------------------------
def cargar_excel(path: str) -> pd.DataFrame:
    df = pd.read_excel(path, engine="openpyxl")
    df.columns = df.columns.astype(str).str.replace(r"[\r\n]+", " ", regex=True).str.strip()
    return df

# ---------------------------------------------------
# 🛠️ CREAR PERSISTENTE LIMPIO DESDE ORIGINAL
# ---------------------------------------------------
def crear_persistente_desde_original():

    df = cargar_excel(ARCHIVO_ORIGINAL)

    # Renombres seguros
    rename_map = {
        "Ubicac.técnica_x": "Ubicación técnica",
        "Txt. cód. mot.": "Cód. motivo",
        "TextoCódProblem": "Descripción motivo",
        "criticidad_predicha": "Criticidad (Modelo)",
        "Clase_orden_recomendada": "Clase de orden (Modelo)",
        "Cl_actividad_PM_recomendada": "Actividad PM (Modelo)",
        "Pto_tbjo_resp_recomendado": "Centro de trabajo (Modelo)",
        "Costo_total_estimado": "Costo estimado",
    }

    for col, new in rename_map.items():
        if col in df.columns:
            df.rename(columns={col: new}, inplace=True)

    # Crear columna Gestionado si no existe
    if "Gestionado" not in df.columns:
        df["Gestionado"] = False

    # Guardado seguro del persistente
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
if "Fecha de aviso" in df_raw.columns:
    df_raw["Fecha de aviso"] = pd.to_datetime(df_raw["Fecha de aviso"], errors="coerce").dt.date

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

    grupo_opts = ["(Todos)"] + sorted(df_session["Grupo planif."].dropna().astype(str).unique().tolist()) if "Grupo planif." in df_session else ["(Todos)"]
    prioridad_opts = ["(Todos)"] + sorted(df_session["Prioridad"].dropna().astype(str).unique().tolist()) if "Prioridad" in df_session else ["(Todos)"]
    abc_opts = ["(Todos)"] + sorted(df_session["Indicador ABC"].dropna().astype(str).unique().tolist()) if "Indicador ABC" in df_session else ["(Todos)"]

    grupo = st.selectbox("Grupo planificador", grupo_opts)
    prioridad = st.selectbox("Prioridad", prioridad_opts)
    abc = st.selectbox("Indicador ABC", abc_opts)

df_filtrado = df_session.copy()
if grupo != "(Todos)" and "Grupo planif." in df_filtrado:
    df_filtrado = df_filtrado[df_filtrado["Grupo planif."].astype(str) == grupo]
if prioridad != "(Todos)" and "Prioridad" in df_filtrado:
    df_filtrado = df_filtrado[df_filtrado["Prioridad"].astype(str) == prioridad]
if abc != "(Todos)" and "Indicador ABC" in df_filtrado:
    df_filtrado = df_filtrado[df_filtrado["Indicador ABC"].astype(str) == abc]

# ---------------------------------------------------
# 📊 MÉTRICAS
# ---------------------------------------------------
st.subheader("📊 Resumen general")
col1, col2, col3, col4, col5 = st.columns(5)

col1.metric("Total avisos", len(df_filtrado))

# Criticidad promedio
if "Criticidad (Modelo)" in df_filtrado:
    crit_mean = pd.to_numeric(df_filtrado["Criticidad (Modelo)"], errors="coerce").mean()
    col2.metric("Criticidad promedio", f"{crit_mean:.1f}")
else:
    col2.metric("Criticidad promedio", "—")

# % gestionados
if "Gestionado" in df_filtrado:
    pct = df_filtrado["Gestionado"].mean() * 100
    col3.metric("% Gestionados", f"{pct:.1f}%")
else:
    col3.metric("% Gestionados", "0.0%")

# Costo promedio
Costo_prom = pd.to_numeric(df_filtrado["Costo estimado"], errors="coerce").mean()
if pd.notna(Costo_prom):
    Costo_prom_fmt = f"${round(Costo_prom):,}".replace(",", ".")
else:
    Costo_prom_fmt = "$0"
col4.metric("Costo promedio estimado", Costo_prom_fmt)

# Costo total
Costo_total = pd.to_numeric(df_filtrado["Costo estimado"], errors="coerce").sum()
if pd.notna(Costo_total):
    Costo_total_fmt = f"${round(Costo_total):,}".replace(",", ".")
else:
    Costo_total_fmt = "$0"
col5.metric("Costo total estimado", Costo_total_fmt)

# ---------------------------------------------------
# 🔦 SEMÁFORO DE CRITICIDAD
# ---------------------------------------------------
st.subheader("🔦 Semáforo de criticidad")

if "Criticidad (Modelo)" in df_filtrado:
    if crit_mean <= 33:
        nivel = "🟢 Criticidad Baja"
    elif crit_mean <= 66:
        nivel = "🟡 Criticidad Media"
    else:
        nivel = "🔴 Criticidad Alta"

    st.markdown(
        f"<div style='padding:12px; font-size:22px; font-weight:600;'>{nivel} — Promedio: {crit_mean:.1f}</div>",
        unsafe_allow_html=True
    )

# ---------------------------------------------------
# 🚨 ALERTA CRÍTICOS > 90
# ---------------------------------------------------
if "Criticidad (Modelo)" in df_session:
    criticos = df_session[pd.to_numeric(df_session["Criticidad (Modelo)"], errors="coerce") > 90]

    if len(criticos) > 0:
        st.error(f"⚠️ {len(criticos)} avisos con Criticidad > 90. Revisar urgente.")
        st.dataframe(
            criticos[["Aviso", "Descripción", "Criticidad (Modelo)", "Grupo planif.", "Prioridad"]],
            use_container_width=True
        )

st.divider()

# ---------------------------------------------------
# 📋 TABLA EDITABLE
# ---------------------------------------------------
st.subheader("📋 Avisos en Backlog")

edited_df = st.data_editor(
    df_filtrado,
    hide_index=True,
    use_container_width=True,
    column_config={"Gestionado": st.column_config.CheckboxColumn("Gestionado")},
    key="tabla_editable"
)

if "Gestionado" in edited_df:
    df_session.loc[edited_df.index, "Gestionado"] = edited_df["Gestionado"].values
    st.session_state["df_data"] = df_session

# Guardado seguro
with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
    df_session.to_excel(tmp.name, index=False)
    shutil.move(tmp.name, ARCHIVO_PERSISTENTE)

# ---------------------------------------------------
# 🌡️ HEATMAP POR GRUPO PLANIFICADOR
# ---------------------------------------------------
st.subheader("🌡️ Mapa de calor por Grupo Planificador")

if "Grupo planif." in df_session and "Criticidad (Modelo)" in df_session:
    dfh = df_session.copy()
    dfh["Criticidad (Modelo)"] = pd.to_numeric(dfh["Criticidad (Modelo)"], errors="coerce")

    heat = dfh.pivot_table(index="Grupo planif.", values="Criticidad (Modelo)", aggfunc="mean")
    heat = heat.fillna(0)

    st.dataframe(
        heat.style.background_gradient(cmap="RdYlGn_r"),
        use_container_width=True
    )

# ---------------------------------------------------
# 📈 HISTOGRAMA
# ---------------------------------------------------
st.subheader("📈 Distribución de criticidad")

if "Criticidad (Modelo)" in df_filtrado:
    crit_vals = pd.to_numeric(df_filtrado["Criticidad (Modelo)"], errors="coerce").dropna()

    bins = list(range(1, 102))
    hist = pd.cut(crit_vals, bins=bins, right=False)
    freq = hist.value_counts().sort_index()

    freq_df = pd.DataFrame({"Criticidad": range(1, 101), "Cantidad": freq.values})
    st.bar_chart(freq_df.set_index("Criticidad"))

st.caption("CMPC Cordillera © 2025 - Subgerencia de mantenimiento")
