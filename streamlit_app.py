from __future__ import annotations

import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO

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
    verde = (0x2e, 0xcc, 0x71)
    amarillo = (0xf1, 0xc4, 0x0f)
    rojo = (0xe7, 0x4c, 0x3c)

    if pd.isna(v):
        return "#ffffff"
    v = float(v)
    if vmax == vmin:
        t = 0.0
    else:
        t = (v - vmin) / (vmax - vmin)
    t = max(0.0, min(1.0, t))

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

    # Prioridad (select único, igual que Grupo)
    if col_prior in df.columns:
        prioridades_opts = ["(Todos)"] + sorted([str(x) for x in df[col_prior].dropna().unique()])
        sel_prioridades = st.selectbox("Prioridad", prioridades_opts, index=0)
    else:
        sel_prioridades = "(Todos)"

    # Indicador ABC (select único, igual que Grupo)
    if col_abc in df.columns:
        abc_opts = ["(Todos)"] + sorted([str(x) for x in df[col_abc].dropna().unique()])
        sel_abc = st.selectbox("Indicador ABC", abc_opts, index=0)
    else:
        sel_abc = "(Todos)"

# ---- Aplicar filtros ----
df_filtrado = df.copy()

if col_grupo in df_filtrado.columns and seleccion_grupo != "(Todos)":
    df_filtrado = df_filtrado[df_filtrado[col_grupo].astype(str) == seleccion_grupo]

if col_prior in df_filtrado.columns and sel_prioridades != "(Todos)":
    df_filtrado = df_filtrado[df_filtrado[col_prior].astype(str) == sel_prioridades]

if col_abc in df_filtrado.columns and sel_abc != "(Todos)":
    df_filtrado = df_filtrado[df_filtrado[col_abc].astype(str) == sel_abc]

# =========================
# Layout centrado
# =========================
left, mid, right = st.columns([1, 6, 1])

with mid:
    st.title("📊 Clasificación de Avisos")

    # ===== KPIs (indicadores) arriba =====
    total_registros = len(df_filtrado)
    grupos_mostrados = df_filtrado[col_grupo].nunique() if col_grupo in df_filtrado.columns else None
    if col_crit in df_filtrado.columns:
        serie_crit = pd.to_numeric(df_filtrado[col_crit], errors="coerce").dropna()
    else:
        serie_crit = pd.Series(dtype=float)

    prom = f"{serie_crit.mean():.1f}" if not serie_crit.empty else "—"
    med  = f"{serie_crit.median():.0f}" if not serie_crit.empty else "—"
    pct_alta = f"{(serie_crit.ge(80).mean() * 100):.1f}%" if not serie_crit.empty else "—"

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Avisos mostrados", f"{total_registros:,}".replace(",", "."))
    k2.metric("Grupos planif. mostrados", grupos_mostrados if grupos_mostrados is not None else "—")
    k3.metric("Criticidad promedio", prom)
    k4.metric("Mediana criticidad", med)
    k5.metric("% criticidad ≥ 80", pct_alta)

    st.markdown("---")

    # ===== Gráfico: X=Criticidad (1..100), Y=frecuencia =====
    if col_crit in df_filtrado.columns and not df_filtrado.empty:
        crit = pd.to_numeric(df_filtrado[col_crit], errors="coerce").dropna()
        crit = crit.round().astype(int)
        crit = crit.clip(lower=1, upper=100)

        index_1_100 = pd.RangeIndex(1, 101, name="Criticidad")
        conteo = (
            crit.value_counts(dropna=False)
                .reindex(index_1_100, fill_value=0)
                .rename("Avisos")
                .to_frame()
        )

        st.subheader("Frecuencia de avisos por Criticidad (1 → 100) (según filtros)")
        st.bar_chart(conteo, use_container_width=True)
    else:
        st.info("No hay datos de 'Criticidad_1a100' para graficar tras los filtros.")

    st.markdown("---")

    # ===== Tabla editable alternativa (sin experimental_data_editor) =====
    st.caption("Vista de avisos con filtros. Marca 'Gestionado' para indicar que un ticket ya fue gestionado.")

    # Identificador para mapear estados; usamos "Aviso" si existe, si no creamos "Aviso_id"
    id_col = "Aviso"
    if id_col not in df_filtrado.columns:
        id_col = "Aviso_id"
        df_filtrado = df_filtrado.reset_index(drop=True).copy()
        df_filtrado[id_col] = df_filtrado.index.astype(str)

    flag_col = "Gestionado"

    # Creamos columna flag si no existe
    if flag_col not in df_filtrado.columns:
        df_filtrado[flag_col] = False
    df_filtrado[flag_col] = df_filtrado[flag_col].astype(bool)

    # Inicializar session_state map (id -> bool) para persistencia entre reruns
    map_key = "gestionados_map"
    ids_visibles = tuple(df_filtrado[id_col].astype(str).tolist())
    if map_key not in st.session_state:
        st.session_state[map_key] = {i: False for i in ids_visibles}
    else:
        # Si cambió la lista de ids visibles (filtros o archivo nuevo), sincronizamos (mantener valores previos si existen)
        prev = st.session_state[map_key]
        new_map = {i: prev.get(i, False) for i in ids_visibles}
        st.session_state[map_key] = new_map

    # Reflejar el mapa en df_filtrado
    df_filtrado[flag_col] = df_filtrado[id_col].astype(str).map(st.session_state[map_key]).fillna(False).astype(bool)

    # Añadir columna visual _Estado
    df_para_mostrar = df_filtrado.copy()
    df_para_mostrar["_Estado"] = df_para_mostrar[flag_col].map(lambda x: "✅ Gestionado" if x else "")

    # Reorder to show id and estado early if exist
    cols = list(df_para_mostrar.columns)
    if id_col in cols:
        cols.remove(id_col)
        cols = [id_col] + cols
    if "_Estado" in cols:
        cols.remove("_Estado")
        cols = cols[:1] + ["_Estado"] + cols[1:]
    df_para_mostrar = df_para_mostrar[cols]

    # Mostrar tabla (no editable aquí)
    st.dataframe(df_para_mostrar, use_container_width=True, hide_index=True)

    st.markdown("### ✏️ Editar estados (paginado)")
    st.info("Usa el panel paginado para marcar/desmarcar varios avisos. Los cambios se guardan en la sesión.")

    # Parámetros de paginación
    page_size = st.number_input("Filas por página", min_value=10, max_value=200, value=25, step=5)
    page = st.number_input("Página", min_value=1, value=1, step=1)
    page = int(page)
    page_size = int(page_size)

    start = (page - 1) * page_size
    end = start + page_size
    sub = df_filtrado.reset_index(drop=True).iloc[start:end]

    if sub.empty:
        st.warning("No hay filas en esta página (ajusta la página o filtros).")
    else:
        st.write(f"Mostrando filas {start+1} → {min(end, len(df_filtrado))} de {len(df_filtrado)}")
        # Mostrar filas con checkboxes
        for idx, row in sub.iterrows():
            rid = str(row[id_col])
            cols_row = st.columns([1, 3, 2, 1])  # Ajusta anchos: checkbox, descripción, prioridad/abc, criticidad
            checked_key = f"chk_{rid}"
            # Crear checkbox con estado actual
            current = st.session_state[map_key].get(rid, False)
            new_val = cols_row[0].checkbox("", value=current, key=checked_key)
            # Mostrar información relevante
            descr = str(row.get("Descripción", ""))[:120]
            cols_row[1].write(f"**{rid}** — {descr}")
            p = row.get(col_prior, "")
            abc = row.get(col_abc, "")
            cols_row[2].write(f"Prioridad: `{p}`  \nABC: `{abc}`")
            crit = row.get(col_crit, "")
            cols_row[3].write(f"{crit}")

            # Si cambió, actualizar el mapa
            if new_val != current:
                st.session_state[map_key][rid] = new_val
                # también reflejar en df_para_mostrar (visible en la tabla superior)
                # actualizamos la variable local para que al final refleje los cambios en la descarga
                df_para_mostrar.loc[df_para_mostrar[id_col].astype(str) == rid, "_Estado"] = "✅ Gestionado" if new_val else ""
                df_filtrado.loc[df_filtrado[id_col].astype(str) == rid, flag_col] = new_val

    st.markdown("---")

    # ===== Opciones para exportar/guardar cambios =====
    col_down1, col_down2, col_action = st.columns([1,1,2])

    with col_down1:
        # Construir dataframe resultante a descargar (estado aplicado)
        result_df = df_filtrado.copy()
        csv = result_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "📥 Descargar CSV",
            data=csv,
            file_name="avisos_gestionados.csv",
            mime="text/csv"
        )

    with col_down2:
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            result_df.to_excel(writer, index=False, sheet_name="Avisos")
        buffer.seek(0)
        st.download_button(
            "📥 Descargar XLSX",
            data=buffer,
            file_name="avisos_gestionados.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    with col_action:
        if st.button("🔁 Resetear flags (poner todos False)"):
            st.session_state[map_key] = {i: False for i in st.session_state[map_key].keys()}
            st.experimental_rerun()

    st.markdown("---")

    total = len(df_filtrado)
    if col_grupo in df.columns and seleccion_grupo != "(Todos)":
        st.write(f"**Registros mostrados para Grupo planif. = `{seleccion_grupo}`:** {total}")
    else:
        st.write(f"**Registros mostrados (según filtros):** {total}")
