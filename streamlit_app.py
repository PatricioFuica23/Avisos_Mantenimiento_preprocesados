# ==============================================
# 📊 APP STREAMLIT - CLASIFICACIÓN DE AVISOS CMPC
# Adaptada a 'predicciones_avisos_sin_gestionar_rf_v5.xlsx'
# ==============================================

from __future__ import annotations
import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Clasificación de Avisos SAP PM", page_icon="🧠", layout="wide")

st.title("📊 Clasificación Automática de Avisos SAP PM")
st.caption("Prototipo funcional de modelo automático de avisos de mantenimiento (Random Forest v5)")

st.markdown("""
💡 **Objetivo:** Visualizar los avisos clasificados por el modelo, revisar su criticidad, 
y permitir a los trabajadores marcar cuáles fueron gestionados y asignar un ticket para trazabilidad.
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

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Configuración de la aplicación")
    uploaded = st.file_uploader("📂 Cargar archivo de predicciones", type=["xlsx"])
    st.caption("Por defecto se usará `predicciones_avisos_sin_gestionar_rf_v5.xlsx` si no se carga otro archivo.")

# --- CARGA DE DATOS ---
try:
    if uploaded is not None:
        df_raw = cargar_datos(uploaded)
    else:
        df_raw = cargar_datos("predicciones_avisos_sin_gestionar_rf_v5.xlsx")
except FileNotFoundError:
    st.error("❌ No se encontró `predicciones_avisos_sin_gestionar_rf_v5.xlsx`. Súbelo desde la barra lateral.")
    st.stop()

# --- SELECCIÓN DE COLUMNAS RELEVANTES ---
# Estas columnas están ajustadas al archivo 'predicciones_avisos_sin_gestionar_rf_v5.xlsx'
columnas_presentes = df_raw.columns.tolist()

cols_relevantes = [c for c in [
    "Aviso", "Fecha de aviso", "Descripción", "Ubicac.técnica", "Indicador ABC", 
    "Grupo planif.", "Clase de aviso" "Denominación", "Prioridad", "Txt. cód. mot.", 
    "TextoCódProblem", "criticidad_final", "Clase de orden_pred", "Cl.actividad PM_pred",  
    "Pto.tbjo.resp._pred", "Nivel criticidad"
] if c in columnas_presentes]

df = df_raw[cols_relevantes].copy()

# --- LIMPIEZA Y FORMATEO ---
if "Fecha de aviso" in df.columns:
    df["Fecha de aviso"] = pd.to_datetime(df["Fecha de aviso"], errors="coerce").dt.date
if "criticidad_final" in df.columns:
    df["criticidad_final"] = pd.to_numeric(df["criticidad_final"], errors="coerce")

# --- NUEVAS COLUMNAS (Gestionado y Ticket) ---
if "Gestionado" not in df.columns:
    df["Gestionado"] = False
if "Ticket" not in df.columns:
    df["Ticket"] = ""

# Guardar en sesión (solo primera vez)
if "df_data" not in st.session_state:
    st.session_state["df_data"] = df.copy()

df_session = st.session_state["df_data"]

# --- FILTROS ---
with st.sidebar:
    st.subheader("🔍 Filtros de visualización")
    grupo_opts = ["(Todos)"] + sorted(df_session["Grupo planif."].dropna().unique().astype(str).tolist()) if "Grupo planif." in df_session.columns else ["(Todos)"]
    prioridad_opts = ["(Todos)"] + sorted(df_session["Prioridad"].dropna().unique().astype(str).tolist()) if "Prioridad" in df_session.columns else ["(Todos)"]
    abc_opts = ["(Todos)"] + sorted(df_session["Indicador ABC"].dropna().unique().astype(str).tolist()) if "Indicador ABC" in df_session.columns else ["(Todos)"]

    grupo = st.selectbox("Grupo planificador", grupo_opts)
    prioridad = st.selectbox("Prioridad", prioridad_opts)
    abc = st.selectbox("Indicador ABC", abc_opts)

# Aplicar filtros
df_filtrado = df_session.copy()
if "Grupo planif." in df_filtrado.columns and grupo != "(Todos)":
    df_filtrado = df_filtrado[df_filtrado["Grupo planif."].astype(str) == grupo]
if "Prioridad" in df_filtrado.columns and prioridad != "(Todos)":
    df_filtrado = df_filtrado[df_filtrado["Prioridad"].astype(str) == prioridad]
if "Indicador ABC" in df_filtrado.columns and abc != "(Todos)":
    df_filtrado = df_filtrado[df_filtrado["Indicador ABC"].astype(str) == abc]

# --- MÉTRICAS GENERALES ---
st.subheader("📊 Resumen general")
col1, col2, col3 = st.columns(3)
col1.metric("Total avisos", len(df_filtrado))
col2.metric("Criticidad promedio", f"{df_filtrado['criticidad_final'].mean():.1f}" if "criticidad_final" in df_filtrado else "—")
col3.metric("% Gestionados", f"{(df_filtrado['Gestionado'].mean() * 100):.1f}%")

st.divider()

# --- TABLA EDITABLE PRINCIPAL ---
st.subheader("📋 Tabla de avisos (editable)")
st.caption("Marca los avisos como gestionados y asigna un número o comentario de ticket. Los cambios se actualizan automáticamente.")

edited_df = st.data_editor(
    df_filtrado,
    num_rows="dynamic",
    use_container_width=True,
    hide_index=True,
    column_config={
        "Gestionado": st.column_config.CheckboxColumn("Gestionado"),
        "Ticket": st.column_config.TextColumn("Ticket", help="Número o comentario del ticket")
    },
    key="editable_table"
)

# Actualizar sesión
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
# --- HISTOGRAMA DE CRITICIDAD ---
st.divider()
st.subheader("📈 Distribución de criticidad (1 → 100)")

if "Criticidad_1a100" in df_filtrado.columns and not df_filtrado.empty:
    # Convertimos a números válidos y redondeamos
    crit = pd.to_numeric(df_filtrado["Criticidad_1a100"], errors="coerce").dropna()
    crit = crit.clip(lower=1, upper=100).round().astype(int)

    # Contamos frecuencia de cada nivel de criticidad
    conteo = (
        crit.value_counts()
        .reindex(range(1, 101), fill_value=0)
        .sort_index()
        .rename("Cantidad de avisos")
        .to_frame()
    )

    # Mostrar histograma de barras
    st.bar_chart(conteo, use_container_width=True)

    # Indicador complementario
    st.caption("Distribución del backlog según el nivel de criticidad predicho por el modelo.")
else:
    st.info("No hay datos de criticidad disponibles para graficar tras los filtros aplicados.")
