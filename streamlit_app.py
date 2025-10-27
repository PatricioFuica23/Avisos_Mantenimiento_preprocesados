from __future__ import annotations

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

# ---- Generador de color (verde→amarillo→rojo) sin matplotlib ----
def color_hex_verde_amarillo_rojo(v: float, vmin: float = 1, vmax: float = 100) -> str:
    """
    Interpola un color entre verde (#2ecc71), amarillo (#f1c40f) y rojo (#e74c3c)
    según el valor v en [vmin, vmax]. Devuelve HEX "#RRGGBB".
    """
    verde = (0x2e, 0xcc, 0x71)
    amarillo = (0xf1, 0xc4, 0x0f)
    rojo = (0xe7, 0x4c, 0x3c)

    if pd.isna(v):
        return "#ffffff"  # blanco para NaN
    v = float(v)
    if vmax == vmin:
        t = 0.0
    else:
        t = (v - vmin) / (vmax - vmin)
    t = max(0.0, min(1.0, t))

    # Dos tramos: 0..0.5 (verde→amarillo), 0.5..1 (amarillo→rojo)
    if t <= 0.5:
        a, b = verde, amarillo
        u = t / 0.5
    else:
        a, b = amarillo, rojo
        u = (t - 0.5) / 0.5

    r = int(round(a[0] + (b[0] - a[0]) * u))
    g = int(round(a[1] + (b[1] - a[1]) * u))
    b_ = int(round(a[2] + (b[2] - a[2]) * u))
    return f"#{r:02x}{g:02x}{b_:02x}"

def estilos_criticidad(col: pd.Series, vmin: float = 1, vmax: float = 100):
    """Devuelve estilos CSS por celda para la columna de criticidad."""
    return [f"background-color: {color_hex_verde_amarillo_rojo(val, vmin, vmax)}" for val in col]

# =========================
# Sidebar (carga de archivo)
# =========================
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

# Seleccionar columnas y formatear
df = seleccionar_columnas(df_raw)

if "Fecha de aviso" in df.columns:
    df["Fecha de aviso"] = pd.to_datetime(df["Fecha de aviso"], errors="coerce").dt.date

col_grupo = "Grupo planif."
col_prior = "Prioridad"
col_abc   = "Indicador ABC"
col_crit  = "Criticidad_1a100"

if col_crit in df.columns:
    df[col_crit] = pd.to_numeric(df[col_crit], errors="coerce")

# =========================
# Sidebar (filtros de negocio)
# =========================
with st.sidebar:
    st.subheader("Filtros")
    # Grupo planif. (select único)
    if col_grupo in df.columns:
        grupos = ["(Todos)"] + sorted([str(x) for x in df[col_grupo].dropna().unique()])
        seleccion_grupo = st.selectbox("Grupo planif.", grupos, index=0)
    else:
        seleccion_grupo = "(Todos)"

    # Prioridad (multi)
    if col_prior in df.columns:
        prioridades_opts = sorted([str(x) for x in df[col_prior].dropna().unique()])
        sel_prioridades = st.multiselect("Prioridad", prioridades_opts, default=prioridades_opts)
    else:
        sel_prioridades = None

    # Indicador ABC (multi)
    if col_abc in df.columns:
        abc_opts = sorted([str(x) for x in df[col_abc].dropna().unique()])
        sel_abc = st.multiselect("Indicador ABC", abc_opts, default=abc_opts)
    else:
        sel_abc = None

# ---- Aplicar filtros ----
df_filtrado = df.copy()

if col_grupo in df_filtrado.columns and seleccion_grupo != "(Todos)":
    df_filtrado = df_filtrado[df_filtrado[col_grupo].astype(str) == seleccion_grupo]

if sel_prioridades is not None and len(sel_prioridades) > 0:
    df_filtrado = df_filtrado[df_filtrado[col_prior].astype(str).isin(sel_prioridades)]

if sel_abc is not None and len(sel_abc) > 0:
    df_filtrado = df_filtrado[df_filtrado[col_abc].astype(str).isin(sel_abc)]

# ---- Layout centrado ----
left, mid, right = st.columns([1, 6, 1])

with mid:
    st.title("📊 Clasificación de Avisos")
    st.caption("Vista de avisos con filtros (Grupo planif., Prioridad, Indicador ABC) y gradiente de criticidad (1→verde, 100→rojo).")

    # Tabla con estilo de criticidad
    if col_crit in df_filtrado.columns:
        styled = df_filtrado.style.format(precision=0, subset=[col_crit])
        styled = styled.apply(lambda col: estilos_criticidad(col, 1, 100), subset=[col_crit])
        st.dataframe(styled, use_container_width=True, hide_index=True)
    else:
        st.dataframe(df_filtrado, use_container_width=True, hide_index=True)

    st.markdown("---")

    # ======= Gráfico dinámico =======
    # Por defecto: conteo por Prioridad. Si no existe, por Indicador ABC.
    if col_prior in df_filtrado.columns and not df_filtrado.empty:
        df_plot = (
            df_filtrado.assign(Prioridad=df_filtrado[col_prior].astype(str).fillna("Sin dato"))
            .groupby("Prioridad", dropna=False)
            .size()
            .sort_values(ascending=False)
            .rename("Avisos")
            .to_frame()
        )
        st.subheader("Distribución de avisos por Prioridad (según filtros)")
        st.bar_chart(df_plot, use_container_width=True)
    elif col_abc in df_filtrado.columns and not df_filtrado.empty:
        df_plot = (
            df_filtrado.assign(**{col_abc: df_filtrado[col_abc].astype(str).fillna("Sin dato")})
            .groupby(col_abc, dropna=False)
            .size()
            .sort_values(ascending=False)
            .rename("Avisos")
            .to_frame()
        )
        st.subheader("Distribución de avisos por Indicador ABC (según filtros)")
        st.bar_chart(df_plot, use_container_width=True)
    else:
        st.info("No se encontraron columnas para graficar (Prioridad o Indicador ABC), o no hay datos tras los filtros.")

    # KPIs simples
    total = len(df_filtrado)
    if col_grupo in df.columns and seleccion_grupo != "(Todos)":
        st.write(f"**Registros mostrados para Grupo planif. = `{seleccion_grupo}`:** {total}")
    else:
        st.write(f"**Registros mostrados (según filtros):** {total}")