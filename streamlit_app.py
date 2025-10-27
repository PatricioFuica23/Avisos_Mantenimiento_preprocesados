from __future__ import annotations

import streamlit as st
import pandas as pd
import numpy as np
from datetime import date

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
    según el valor v en el rango [vmin, vmax]. Devuelve HEX "#RRGGBB".
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

# ---- Sidebar (solo carga de archivo) ----
with st.sidebar:
    st.header("📁 Datos")
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
# Fecha a tipo date
if "Fecha de aviso" in df.columns:
    df["Fecha de aviso"] = pd.to_datetime(df["Fecha de aviso"], errors="coerce").dt.date

col_grupo = "Grupo planif."
col_crit = "Criticidad_1a100"
col_prio = "Prioridad"
col_indicador = "Indicador ABC"

# Criticidad numérica
if col_crit in df.columns:
    df[col_crit] = pd.to_numeric(df[col_crit], errors="coerce")

# ---- Layout con columna derecha ancha para filtros ----
# Aumentamos ancho de la columna derecha para acomodar los controles
left, mid, right = st.columns([1, 6, 2], gap="large")

# ---- Filtros (derecha) ----
with right:
    st.header("🔎 Filtros")

    # 1) Filtro por Grupo planif. (opcional)
    seleccion = "(Todos)"
    if col_grupo in df.columns:
        grupos = ["(Todos)"] + sorted([str(x) for x in df[col_grupo].dropna().unique()])
        seleccion = st.selectbox("Grupo planif.", grupos, index=0)

    # 2) Filtro por prioridad (opcional)
    seleccion = "(Todos)"
    if  col_prio in df.columns:
        grupos = ["(Todos)"] + sorted([str(x) for x in df[col_prio].dropna().unique()])
        seleccion = st.selectbox("Prioridad", grupos, index=0)

    # 3) Filtro por Indicador ABC (opcional)
    seleccion = "(Todos)"
    if col_indicador in df.columns:
        grupos = ["(Todos)"] + sorted([str(x) for x in df[col_indicador].dropna().unique()])
        seleccion = st.selectbox("Indicador ABC", grupos, index=0)

    # 2) Rango de fecha de aviso
    fecha_min, fecha_max = None, None
    if "Fecha de aviso" in df.columns:
        # Detecta min y max ignorando NaN
        if df["Fecha de aviso"].notna().any():
            fmin = df["Fecha de aviso"].min()
            fmax = df["Fecha de aviso"].max()
            # Por seguridad, castea a date
            if not isinstance(fmin, date):
                fmin = pd.to_datetime(fmin, errors="coerce").date()
            if not isinstance(fmax, date):
                fmax = pd.to_datetime(fmax, errors="coerce").date()
            fecha_min, fecha_max = st.date_input(
                "Fecha de aviso (rango)",
                value=(fmin, fmax),
                min_value=fmin,
                max_value=fmax
            )
        else:
            st.info("No hay fechas válidas para filtrar.")

    # 3) Rango de criticidad
    criticidad_rango = None
    if col_crit in df.columns:
        # Definir límites reales dentro de [1, 100]
        cmin = int(np.nanmin([v for v in df[col_crit].values if pd.notna(v)]) if df[col_crit].notna().any() else 1)
        cmax = int(np.nanmax([v for v in df[col_crit].values if pd.notna(v)]) if df[col_crit].notna().any() else 100)
        # Acotar a 1..100
        cmin = max(1, min(100, cmin))
        cmax = max(1, min(100, cmax))
        if cmin > cmax:
            cmin, cmax = cmax, cmin
        criticidad_rango = st.slider(
            "Criticidad_1a100 (rango)",
            min_value=1, max_value=100,
            value=(cmin, cmax)
        )

# ---- Aplicar filtros a los datos ----
df_filtrado = df.copy()

# Grupo planif.
if col_grupo in df_filtrado.columns and seleccion != "(Todos)":
    df_filtrado = df_filtrado[df_filtrado[col_grupo].astype(str) == seleccion]

# Fecha de aviso
if "Fecha de aviso" in df_filtrado.columns and fecha_min and fecha_max:
    df_filtrado = df_filtrado[
        df_filtrado["Fecha de aviso"].between(fecha_min, fecha_max)
    ]

# Criticidad
if col_crit in df_filtrado.columns and criticidad_rango:
    c_low, c_high = criticidad_rango
    df_filtrado = df_filtrado[
        (df_filtrado[col_crit] >= c_low) & (df_filtrado[col_crit] <= c_high)
    ]

# ---- Centro: tabla ----
with mid:
    st.title("📊 Clasificación de Avisos")
    st.caption("Tabla centrada con filtros a la derecha y gradiente de criticidad (1→verde, 100→rojo).")

    if col_crit in df_filtrado.columns:
        styled = df_filtrado.style.format(precision=0, subset=[col_crit])
        styled = styled.apply(lambda col: estilos_criticidad(col, 1, 100), subset=[col_crit])
        st.dataframe(styled, use_container_width=True, hide_index=True)
    else:
        st.dataframe(df_filtrado, use_container_width=True, hide_index=True)

    st.markdown("---")
    total = len(df_filtrado)
    if col_grupo in df.columns and seleccion != "(Todos)":
        st.write(f"**Registros mostrados para Grupo planif. = `{seleccion}`:** {total}")
    else:
        st.write(f"**Registros mostrados:** {total}")