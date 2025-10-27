from __future__ import annotations

import io
import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.cm as cm

st.set_page_config(
    page_title="Clasificación de Avisos",
    page_icon="📊",
    layout="wide"
)

# =========================
# Utilidades
# =========================
@st.cache_data(show_spinner=False)
def cargar_excel(path: str) -> pd.DataFrame:
    df = pd.read_excel(path, engine="openpyxl")
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

    reales, faltantes = [], []
    for c in columnas_deseadas:
        if c in mapa_reales:
            reales.append(mapa_reales[c])
        else:
            # Intento flexible (colapsa espacios múltiples)
            candidatos = [k for k in mapa_reales if " ".join(k.split()) == c]
            if candidatos:
                reales.append(mapa_reales[candidatos[0]])
            else:
                faltantes.append(c)

    if faltantes:
        st.warning(
            "No se encontraron estas columnas en el archivo. "
            "Revisa posibles espacios/saltos de línea en el Excel:\n- " + "\n- ".join(faltantes)
        )

    reales = [c for c in reales if c in df.columns]
    return df[reales]

def to_csv_download(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")

def kpis_criticidad(serie: pd.Series) -> dict:
    s = pd.to_numeric(serie, errors="coerce").dropna()
    if s.empty:
        return {
            "total": 0,
            "promedio": None,
            "mediana": None,
            "pct_alta": None,
        }
    return {
        "total": len(s),
        "promedio": float(s.mean()),
        "mediana": float(s.median()),
        "pct_alta": float((s >= 80).mean() * 100.0),  # umbral de alta criticidad (ajustable)
    }

def histograma_criticidad(s: pd.Series, bins: int = 20):
    """Dibuja histograma 1..100 con colores RdYlGn_r según el centro del bin."""
    s = pd.to_numeric(s, errors="coerce").dropna()
    if s.empty:
        st.info("No hay datos numéricos en **Criticidad_1a100** para graficar.")
        return
    vmin, vmax = 1, 100
    counts, edges = np.histogram(s, bins=bins, range=(vmin, vmax))
    centers = (edges[:-1] + edges[1:]) / 2.0
    # Colores por bin usando colormap
    cmap = cm.get_cmap("RdYlGn_r")
    normed = (centers - vmin) / (vmax - vmin)
    colors = [cmap(np.clip(x, 0, 1)) for x in normed]

    fig, ax = plt.subplots(figsize=(8, 3))
    ax.bar(centers, counts, width=(edges[1] - edges[0]) * 0.95, color=colors, edgecolor="none")
    ax.set_title("Distribución de Criticidad (1→verde, 100→rojo)")
    ax.set_xlabel("Criticidad_1a100")
    ax.set_ylabel("Frecuencia")
    ax.set_xlim(vmin, vmax)
    ax.grid(axis="y", alpha=0.25)
    st.pyplot(fig, clear_figure=True)

# =========================
# Sidebar
# =========================
with st.sidebar:
    st.header("⚙️ Controles")
    uploaded = st.file_uploader("Cargar ranking_nb.xlsx", type=["xlsx"])
    st.caption("También puedes dejar el archivo `ranking_nb.xlsx` junto a `streamlit_app.py`.")

# =========================
# Carga de datos
# =========================
try:
    if uploaded is not None:
        df_raw = pd.read_excel(uploaded, engine="openpyxl")
        df_raw.columns = df_raw.columns.astype(str).str.replace(r"[\r\n]+", " ", regex=True).str.strip()
    else:
        df_raw = cargar_excel("ranking_nb.xlsx")
except FileNotFoundError:
    st.error("No se encontró `ranking_nb.xlsx`. Súbelo desde la barra lateral o colócalo junto a `streamlit_app.py`.")
    st.stop()

df = seleccionar_columnas(df_raw)

# Casts y formatos
if "Fecha de aviso" in df.columns:
    df["Fecha de aviso"] = pd.to_datetime(df["Fecha de aviso"], errors="coerce").dt.date

col_grupo = "Grupo planif."
col_crit = "Criticidad_1a100"
if col_crit in df.columns:
    df[col_crit] = pd.to_numeric(df[col_crit], errors="coerce")

# =========================
# Filtros
# =========================
seleccion = None
if col_grupo in df.columns:
    grupos = ["(Todos)"] + sorted([str(x) for x in df[col_grupo].dropna().unique()])
    seleccion = st.sidebar.selectbox("Filtrar por Grupo planif.", grupos, index=0)
    if seleccion != "(Todos)":
        df = df[df[col_grupo].astype(str) == seleccion]

# =========================
# Layout centrado
# =========================
left, mid, right = st.columns([1, 6, 1])

with mid:
    st.title("📊 Clasificación de Avisos")

    # ===== KPIs (arriba de todo) =====
    total_registros = len(df)
    grupos_mostrados = df[col_grupo].nunique() if col_grupo in df.columns else None
    kpis = kpis_criticidad(df[col_crit]) if col_crit in df.columns else {"total":0,"promedio":None,"mediana":None,"pct_alta":None}

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Avisos mostrados", f"{total_registros:,}".replace(",", "."))
    c2.metric("Grupos planif. mostrados", grupos_mostrados if grupos_mostrados is not None else "—")
    c3.metric("Criticidad promedio", f"{kpis['promedio']:.1f}" if kpis["promedio"] is not None else "—")
    c4.metric("Mediana criticidad", f"{kpis['mediana']:.0f}" if kpis["mediana"] is not None else "—")
    c5.metric("% criticidad ≥ 80", f"{kpis['pct_alta']:.1f}%" if kpis["pct_alta"] is not None else "—")

    st.markdown("")

    # ===== Botón de descarga del resultado filtrado =====
    nombre_archivo = f"avisos_filtrados_{seleccion if seleccion and seleccion!='(Todos)' else 'todos'}.csv"
    st.download_button(
        label="⬇️ Descargar CSV filtrado",
        data=to_csv_download(df),
        file_name=nombre_archivo,
        mime="text/csv",
        use_container_width=True
    )

    st.markdown("---")

    # ===== Histograma de criticidad =====
    if col_crit in df.columns:
        histograma_criticidad(df[col_crit], bins=20)

    st.markdown("---")

    # ===== Tabla con gradiente (matplotlib) =====
    st.caption("Vista de avisos con filtro por Grupo planif. y gradiente de criticidad (1→verde, 100→rojo).")

    if col_crit in df.columns:
        styled = (
            df.style
              .format(precision=0, subset=[col_crit])
              .background_gradient(
                  cmap="RdYlGn_r",    # verde (bajo) → rojo (alto)
                  subset=[col_crit],
                  vmin=1, vmax=100
              )
        )
        st.dataframe(styled, use_container_width=True, hide_index=True)
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)