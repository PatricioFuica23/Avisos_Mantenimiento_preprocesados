import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(
    page_title="Clasificación de Avisos",
    page_icon="📊",
    layout="wide"
)

# ---- Utilidades ----
def cargar_datos(path: str) -> pd.DataFrame:
    df = pd.read_excel(path, engine="openpyxl")
    # Limpia nombres de columnas de \r \n y espacios
    df.columns = df.columns.astype(str).str.replace(r"[\r\n]+", " ", regex=True).str.strip()
    return df

def seleccionar_columnas(df: pd.DataFrame) -> pd.DataFrame:
    columnas_deseadas = [
        "Aviso",
        "Fecha de aviso",
        "Descripción",
        "Ubicac.técnica",
        "Indicador ABC",
        "Grupo planif.",
        "Clase de aviso",
        "Denominación",
        "Prioridad",
        "Criticidad_1a100",
        "Rec_ClaseOrden@1",
        "Rec_ClaseAct@1",
        "Rec_Puesto@1",
    ]
    # Normaliza claves para emparejar
    normalizar = lambda s: s.replace("\n", " ").replace("\r", " ").strip()
    mapa_reales = {normalizar(c): c for c in df.columns}

    columnas_reales = []
    faltantes = []
    for c in columnas_deseadas:
        if c in mapa_reales:
            columnas_reales.append(mapa_reales[c])
        else:
            candidatos = [k for k in mapa_reales if " ".join(k.split()) == c]
            if candidatos:
                columnas_reales.append(mapa_reales[candidatos[0]])
            else:
                faltantes.append(c)

    if faltantes:
        st.warning(
            "No se encontraron estas columnas. Revisa espacios/saltos ocultos en el Excel:\n- " + "\n- ".join(faltantes)
        )

    columnas_reales = [col for col in columnas_reales if col in df.columns]
    return df[columnas_reales]

# ---- Sidebar ----
with st.sidebar:
    st.header("⚙️ Controles")
    st.caption("Sube otro archivo si quieres probar diferente data.")
    uploaded = st.file_uploader("Cargar ranking_nb.xlsx", type=["xlsx"])

# ---- Carga de datos ----
try:
    if uploaded is not None:
        df_raw = pd.read_excel(uploaded, engine="openpyxl")
        df_raw.columns = df_raw.columns.astype(str).str.replace(r"[\r\n]+", " ", regex=True).str.strip()
    else:
        df_raw = cargar_datos("ranking_nb.xlsx")
except FileNotFoundError:
    st.error("No se encontró `ranking_nb.xlsx`. Súbelo desde la barra lateral o colócalo junto a `streamlit_app.py`.")
    st.stop()

# Seleccionar columnas
df = seleccionar_columnas(df_raw)

# ---- Transformaciones de formato ----
if "Fecha de aviso" in df.columns:
    df["Fecha de aviso"] = pd.to_datetime(df["Fecha de aviso"], errors="coerce").dt.date

col_grupo = "Grupo planif."
col_crit = "Criticidad_1a100"

if col_crit in df.columns:
    df[col_crit] = pd.to_numeric(df[col_crit], errors="coerce")

# ---- Filtro por Grupo planif. ----
if col_grupo in df.columns:
    grupos = ["(Todos)"] + sorted([str(x) for x in df[col_grupo].dropna().unique()])
    seleccion = st.sidebar.selectbox("Filtrar por Grupo planif.", grupos, index=0)
    if seleccion != "(Todos)":
        df = df[df[col_grupo].astype(str) == seleccion]

# ---- Layout centrado ----
left, mid, right = st.columns([1, 6, 1])

with mid:
    st.title("📊 Clasificación de Avisos")
    st.caption("Vista de avisos con filtro por Grupo planif. y gradiente de criticidad (1→verde, 100→rojo).")

    if col_crit in df.columns:
        styled = (
            df.style
              .format(precision=0, subset=[col_crit])
              .background_gradient(
                  cmap="RdYlGn_r",   # verde (bajo) → rojo (alto)
                  subset=[col_crit],
                  vmin=1, vmax=100
              )
        )
        st.dataframe(styled, use_container_width=True, hide_index=True)
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)

    st.markdown("---")
    total = len(df)
    if col_grupo in df.columns:
        if 'seleccion' in locals() and seleccion != "(Todos)":
            st.write(f"**Registros mostrados para Grupo planif. = `{seleccion}`:** {total}")
        else:
            st.write(f"**Registros mostrados (todos los grupos):** {total}")
    else:
        st.write(f"**Registros mostrados:** {total}")