"""
ProfitInsights AI — Streamlit, app.py única con 3 pestañas
(Resumen General / Análisis de Clientes / Análisis de Productos y Servicios).

Esquema de datos esperado (export tipo QuickBooks):
Year | Client | Job | Date | Type | Num | Memo | Name | Item | Amount
"""

import io
import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

# =============================================================================
# CONFIG & TEMA
# =============================================================================
st.set_page_config(page_title="Dashboard Margenes Servicios/Clientes", page_icon="📊", layout="wide")

COLORS = {
    "primary": "#000000",
    "secondary": "#006a61",
    "secondary_container": "#86f2e4",
    "on_secondary_container": "#006f66",
    "tertiary_accent": "#3980f4",
    "muted_line": "#9aa0a6",
    "error": "#ba1a1a",
    "error_container": "#ffdad6",
    "on_error_container": "#93000a",
    "surface": "#f7f9fb",
    "surface_container_low": "#f2f4f6",
    "surface_container_lowest": "#ffffff",
    "surface_container_high": "#e6e8ea",
    "outline_variant": "#c6c6cd",
    "on_surface": "#191c1e",
    "on_surface_variant": "#45464d",
}

EXPECTED_COLUMNS = ["Year", "Client", "Job", "Date", "Type", "Num", "Memo", "Name", "Item", "Amount"]

MESES_ES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
            "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
MESES_ES_ABR = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
TRIMESTRES = {
    "T1 (Ene-Mar)": [1, 2, 3],
    "T2 (Abr-Jun)": [4, 5, 6],
    "T3 (Jul-Sep)": [7, 8, 9],
    "T4 (Oct-Dic)": [10, 11, 12],
}


def inject_css():
    st.markdown(
        f"""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@500&display=swap');
            html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; }}
            .stApp {{ background-color: {COLORS['surface']}; }}
            section[data-testid="stSidebar"] {{
                background-color: {COLORS['surface_container_low']};
                border-right: 1px solid {COLORS['outline_variant']};
            }}
            .pi-title {{ font-size: 30px; font-weight: 700; letter-spacing: -0.02em; color: {COLORS['on_surface']}; margin-bottom: 0; }}
            .pi-subtitle {{ color: {COLORS['on_surface_variant']}; font-size: 14px; margin-top: 2px; }}
            .pi-card {{
                background-color: {COLORS['surface_container_lowest']};
                border: 1px solid {COLORS['outline_variant']};
                border-radius: 12px; padding: 20px;
                box-shadow: 0px 4px 6px -1px rgba(15,23,42,0.05);
                height: 100%;
            }}
            .pi-card-label {{ font-size: 12px; font-weight: 600; letter-spacing: 0.05em; text-transform: uppercase; color: {COLORS['on_surface_variant']}; }}
            .pi-card-value {{ font-size: 26px; font-weight: 700; color: {COLORS['on_surface']}; margin-top: 6px; }}
            .pi-card-delta-up {{ color: {COLORS['secondary']}; font-size: 12px; font-weight: 600; margin-top: 4px; }}
            .pi-card-delta-down {{ color: {COLORS['error']}; font-size: 12px; font-weight: 600; margin-top: 4px; }}
            .pi-badge {{ display: inline-block; padding: 3px 10px; border-radius: 9999px; font-size: 11px; font-weight: 700; white-space: nowrap; }}
            .pi-badge-a {{ background-color: {COLORS['secondary_container']}; color: {COLORS['on_secondary_container']}; }}
            .pi-badge-b {{ background-color: {COLORS['surface_container_high']}; color: {COLORS['on_surface_variant']}; }}
            .pi-badge-c {{ background-color: {COLORS['error_container']}; color: {COLORS['on_error_container']}; }}
            .stTabs [data-baseweb="tab"] {{ font-weight: 600; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


# -----------------------------------------------------------------------
# IMPORTANTE: todo el HTML embebido se construye en una sola línea (sin
# saltos de línea ni indentación) porque Streamlit/markdown interpreta 4+
# espacios de indentación como bloque de código y rompe el render (esto
# causaba el bug de ver literalmente "</div>" en pantalla).
# -----------------------------------------------------------------------

def kpi_card(label, value, delta=None, positive=True):
    delta_html = ""
    if delta:
        arrow = "▲" if positive else "▼"
        cls = "pi-card-delta-up" if positive else "pi-card-delta-down"
        delta_html = f'<div class="{cls}">{arrow} {delta}</div>'
    html = (f'<div class="pi-card"><div class="pi-card-label">{label}</div>'
            f'<div class="pi-card-value">{value}</div>{delta_html}</div>')
    st.markdown(html, unsafe_allow_html=True)


def tier_badge(tier: str) -> str:
    label = {"A": "Cliente Clave", "B": "Estándar", "C": "Cola Larga"}.get(tier, tier)
    cls = {"A": "pi-badge-a", "B": "pi-badge-b", "C": "pi-badge-c"}.get(tier, "pi-badge-b")
    return f'<span class="pi-badge {cls}">{label}</span>'


def yoy_line_chart(labels, current_vals, ly_vals, year_actual, year_ly, y_title="Ingresos ($)", ly_has_data=True):
    """Gráfico de línea comparando 'año actual' vs 'año anterior', sin relleno debajo."""
    fig = go.Figure()
    if ly_has_data:
        fig.add_trace(go.Scatter(
            x=labels, y=ly_vals, mode="lines+markers", name=f"Año anterior ({year_ly})",
            line=dict(color=COLORS["muted_line"], width=2, dash="dash"),
            marker=dict(size=5, color=COLORS["muted_line"]),
        ))
    fig.add_trace(go.Scatter(
        x=labels, y=current_vals, mode="lines+markers", name=f"Este año ({year_actual})",
        line=dict(color=COLORS["secondary"], width=3),
        marker=dict(size=6, color=COLORS["surface_container_lowest"], line=dict(color=COLORS["secondary"], width=2)),
    ))
    fig.update_layout(
        template="plotly_white", plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=10, b=10), height=360,
        font=dict(family="Inter, sans-serif", color=COLORS["on_surface_variant"]),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        yaxis=dict(title=y_title, gridcolor=COLORS["outline_variant"]),
        xaxis=dict(gridcolor="rgba(0,0,0,0)"),
        hovermode="x unified",
    )
    return fig


def bar_ranking(labels, values, color):
    fig = go.Figure(go.Bar(
        x=values, y=labels, orientation="h", marker_color=color,
        text=[f"${v:,.0f}" for v in values], textposition="outside",
    ))
    fig.update_layout(
        template="plotly_white", plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=50, t=10, b=10), height=280,
        font=dict(family="Inter, sans-serif", color=COLORS["on_surface_variant"]),
        yaxis=dict(autorange="reversed"), xaxis=dict(showgrid=False, visible=False),
    )
    return fig


def render_html_table(df, columns, headers, page_key, page_size=10):
    n_pages = max(1, int(np.ceil(len(df) / page_size)))
    page = st.number_input("Página", min_value=1, max_value=n_pages, value=1, step=1, key=page_key) if n_pages > 1 else 1
    view = df.iloc[(page - 1) * page_size: page * page_size]

    html = "<table style='width:100%; border-collapse:collapse;'>"
    html += f"<thead><tr style='background:{COLORS['surface_container_low']}; text-align:left;'>"
    for h in headers:
        html += f"<th style='padding:10px 12px;'>{h}</th>"
    html += "</tr></thead><tbody>"
    for _, r in view.iterrows():
        html += f"<tr style='border-top:1px solid {COLORS['outline_variant']};'>"
        for c in columns:
            html += f"<td style='padding:10px 12px;'>{r[c]}</td>"
        html += "</tr>"
    html += "</tbody></table>"
    st.markdown(html, unsafe_allow_html=True)
    st.caption(f"Mostrando {len(view)} de {len(df)} filas")


# =============================================================================
# CAPA DE DATOS
# =============================================================================
def clean_amount(series: pd.Series) -> pd.Series:
    return (
        series.astype(str)
        .str.replace(r"[^0-9\.\-]", "", regex=True)
        .replace("", np.nan)
        .astype(float)
    )


def enrich(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["Amount"] = clean_amount(df["Amount"])
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce", format="mixed", dayfirst=False)
    df = df.dropna(subset=["Date"])
    df["Year"] = df["Date"].dt.year
    df["MonthNum"] = df["Date"].dt.month
    df["Month"] = df["Date"].dt.to_period("M").dt.to_timestamp()
    df["Quarter"] = df["Date"].dt.quarter
    df["Item"] = df["Item"].fillna("Sin clasificar")
    split = df["Item"].str.split(":", n=1, expand=True)
    df["ItemCategory"] = split[0]
    df["ItemDetail"] = split[1].fillna(split[0]) if split.shape[1] > 1 else split[0]
    return df


def excel_template_bytes() -> bytes:
    template = pd.DataFrame(columns=EXPECTED_COLUMNS)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        template.to_excel(writer, index=False, sheet_name="Data")
    return buf.getvalue()


def try_parse_upload(uploaded_file) -> pd.DataFrame:
    name = uploaded_file.name.lower()

    if name.endswith((".xlsx", ".xls")):
        df = pd.read_excel(uploaded_file)
    else:
        raw = uploaded_file.read()
        df = None
        last_err = None
        for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
            try:
                text = raw.decode(enc)
                df = pd.read_csv(io.StringIO(text), sep=None, engine="python")
                break
            except (UnicodeDecodeError, Exception) as e:
                last_err = e
                continue
        if df is None:
            raise ValueError(
                "No se pudo leer el archivo (se probaron las codificaciones "
                f"utf-8, cp1252 y latin-1). Error: {last_err}"
            )

    df.columns = [str(c).strip().lstrip("\ufeff") for c in df.columns]
    missing = [c for c in EXPECTED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(
            "Faltan columnas en el archivo: " + ", ".join(missing)
            + f". Columnas encontradas: {list(df.columns)}"
        )
    return df[EXPECTED_COLUMNS]


def abc_tiers(group_df: pd.DataFrame, value_col: str) -> pd.DataFrame:
    """Clasificación ABC / Pareto: A = clientes o ítems que en conjunto generan
    hasta el 80% de los ingresos, B = hasta el 95%, C = el resto (cola larga).
    Se usa en vez de margen de ganancia porque el archivo no trae columna de costo."""
    g = group_df.sort_values(value_col, ascending=False).copy()
    total = g[value_col].sum()
    g["PctOfTotal"] = g[value_col] / total * 100 if total else 0
    g["CumPct"] = g["PctOfTotal"].cumsum()
    g["Tier"] = np.where(g["CumPct"] <= 80, "A", np.where(g["CumPct"] <= 95, "B", "C"))
    return g


def monthly_series(df: pd.DataFrame, year: int, months: list) -> list:
    sub = df[df["Year"] == year]
    grouped = sub.groupby("MonthNum")["Amount"].sum()
    return [float(grouped.get(m, 0.0)) for m in months]


# =============================================================================
# SIDEBAR — carga de archivo
# =============================================================================
inject_css()

with st.sidebar:
    st.markdown('<div style="font-weight:700; font-size:20px;">Dashboard Margenes Servicios/Clientes</div>', unsafe_allow_html=True)

    uploaded = st.file_uploader("Subir archivo CSV / Excel", type=["csv", "xlsx", "xls"])
    if uploaded is not None:
        try:
            raw = try_parse_upload(uploaded)
            st.session_state["pi_raw"] = raw
            st.session_state["pi_source"] = uploaded.name
            st.success(f"{len(raw):,} filas cargadas de {uploaded.name}")
        except Exception as e:
            st.error(str(e))

    st.download_button(
        "⬇ Descargar plantilla CSV",
        data=pd.DataFrame(columns=EXPECTED_COLUMNS).to_csv(index=False).encode("utf-8"),
        file_name="profitinsights_plantilla.csv", mime="text/csv",
    )

    if st.session_state.get("pi_raw") is not None:
        if st.button("Quitar archivo cargado"):
            st.session_state.pop("pi_raw", None)
            st.session_state.pop("pi_source", None)
            st.rerun()

raw_df = st.session_state.get("pi_raw")

if raw_df is None:
    st.markdown('<div class="pi-title">Dashboard Margenes Servicios/Clientes</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="pi-subtitle">Sube tu archivo CSV o Excel desde el panel izquierdo para comenzar el análisis.</div>',
        unsafe_allow_html=True,
    )
    st.info(
        "Columnas esperadas: **Year, Client, Job, Date, Type, Num, Memo, Name, Item, Amount**. "
        "Puedes descargar la plantilla exacta desde el sidebar.",
        icon="📄",
    )
    st.stop()

df = enrich(raw_df)

if df.empty:
    st.error("El archivo se cargó pero no se pudo interpretar ninguna fecha válida. Revisa el formato de la columna 'Date'.")
    st.stop()

# ---- Filtro de tipos de transacción ----------------------------------------
all_types = sorted(df["Type"].dropna().unique().tolist())
default_types = [t for t in all_types if t.lower() in ("invoice", "credit memo")] or all_types
with st.sidebar:
    st.caption("TIPOS DE TRANSACCIÓN")
    selected_types = st.multiselect(
        "Tipos", all_types, default=default_types, label_visibility="collapsed",
        help="Selecciona solo los tipos que representan ingresos reales (normalmente Invoice y Credit Memo) "
             "para evitar contar el mismo dinero dos veces si el archivo también trae filas de tipo Payment.",
    )
df = df[df["Type"].isin(selected_types)] if selected_types else df

# ---- Filtro de período: Año + Mes / Trimestre / Total ----------------------
years_available = sorted(df["Year"].dropna().unique().astype(int).tolist())
if not years_available:
    st.error("No hay años válidos en los datos.")
    st.stop()

with st.sidebar:
    st.divider()
    st.caption("PERÍODO")
    year_actual = st.selectbox("Año", years_available, index=len(years_available) - 1)
    periodo_tipo = st.radio("Ver por", ["Mes", "Trimestre", "Total"], index=2, horizontal=True)

    mes_sel_num = None
    trimestre_sel_meses = None
    if periodo_tipo == "Mes":
        mes_sel_nombre = st.selectbox("Mes", MESES_ES, index=0)
        mes_sel_num = MESES_ES.index(mes_sel_nombre) + 1
    elif periodo_tipo == "Trimestre":
        trimestre_sel_nombre = st.selectbox("Trimestre", list(TRIMESTRES.keys()), index=0)
        trimestre_sel_meses = TRIMESTRES[trimestre_sel_nombre]

year_ly = year_actual - 1

# df_kpi: dataset filtrado exactamente al período elegido (para KPIs y tablas)
if periodo_tipo == "Mes":
    df_kpi = df[(df["Year"] == year_actual) & (df["MonthNum"] == mes_sel_num)]
    df_kpi_ly = df[(df["Year"] == year_ly) & (df["MonthNum"] == mes_sel_num)]
elif periodo_tipo == "Trimestre":
    df_kpi = df[(df["Year"] == year_actual) & (df["MonthNum"].isin(trimestre_sel_meses))]
    df_kpi_ly = df[(df["Year"] == year_ly) & (df["MonthNum"].isin(trimestre_sel_meses))]
else:
    df_kpi = df[df["Year"] == year_actual]
    df_kpi_ly = df[df["Year"] == year_ly]

# meses a graficar: si el período es "Mes", el gráfico se queda en el año completo (Ene-Dic);
# si es Trimestre, el gráfico se ajusta a esos 3 meses; si es Total, año completo.
if periodo_tipo == "Mes":
    meses_grafico = list(range(1, 13))
elif periodo_tipo == "Trimestre":
    meses_grafico = trimestre_sel_meses
else:
    meses_grafico = list(range(1, 13))

labels_grafico = [MESES_ES_ABR[m - 1] for m in meses_grafico]
ly_year_present = year_ly in years_available


def kpi_delta(curr, prev):
    if prev:
        return (curr - prev) / prev * 100
    return 0.0


# =============================================================================
# PESTAÑAS
# =============================================================================
tab_overview, tab_customer, tab_product = st.tabs(
    ["📊 Resumen General", "🧑‍💼 Análisis de Clientes", "📦 Análisis de Productos y Servicios"]
)

# -----------------------------------------------------------------------
# PESTAÑA 1 — RESUMEN GENERAL
# -----------------------------------------------------------------------
with tab_overview:
    c1, c2 = st.columns([3, 1])
    with c1:
        st.markdown('<div class="pi-title">Resumen General</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="pi-subtitle">Análisis de ingresos y concentración de clientes en tiempo real.</div>',
            unsafe_allow_html=True,
        )
    with c2:
        st.write("")
        st.download_button("⬇ Exportar CSV", data=df_kpi.to_csv(index=False).encode("utf-8"),
                            file_name="resumen_general.csv", width="stretch", key="ov_export")

    if df_kpi.empty:
        st.info("No hay datos para el período seleccionado.")
    else:
        total_revenue = df_kpi["Amount"].sum()
        total_revenue_ly = df_kpi_ly["Amount"].sum()
        active_clients = df_kpi["Client"].nunique()
        top_item = df_kpi.groupby("Item")["Amount"].sum().idxmax()
        n_transacciones = df_kpi["Num"].nunique()
        rev_delta = kpi_delta(total_revenue, total_revenue_ly)

        k1, k2, k3, k4 = st.columns(4)
        with k1:
            kpi_card("Ingresos Totales", f"${total_revenue:,.0f}",
                     f"{rev_delta:+.1f}% vs. año anterior" if ly_year_present else None, rev_delta >= 0)
        with k2:
            kpi_card("Clientes Activos", f"{active_clients:,}")
        with k3:
            kpi_card("Transacciones", f"{n_transacciones:,}")
        with k4:
            kpi_card("Servicio Principal", top_item.split(":")[-1])

        st.write("")
        st.markdown("#### Tendencia de Ingresos")
        st.caption(f"Comparación mensual: {year_actual} vs. {year_ly}")
        cur_vals = monthly_series(df, year_actual, meses_grafico)
        ly_vals = monthly_series(df, year_ly, meses_grafico)
        st.plotly_chart(
            yoy_line_chart(labels_grafico, cur_vals, ly_vals, year_actual, year_ly,
                           "Ingresos ($)", ly_year_present),
            width="stretch", key="ov_trend",
        )
        if not ly_year_present:
            st.caption(f"No hay datos de {year_ly} en el archivo para comparar.")

        st.write("")
        st.markdown("#### Matriz de Concentración de Clientes")
        st.caption(
            "Clasificación ABC (Pareto): 'Cliente Clave' = clientes que en conjunto generan el 80% de los "
            "ingresos, 'Estándar' hasta el 95%, 'Cola Larga' el resto. **No incluye margen de ganancia real "
            "porque el archivo no trae columna de costo** — si la tienes, dime y la conecto."
        )

        client_rev = df_kpi.groupby("Client")["Amount"].sum().reset_index()
        core_item = df_kpi.groupby("Client").apply(lambda g: g.groupby("Item")["Amount"].sum().idxmax()).rename("Ítem Principal")
        matrix = client_rev.merge(core_item, on="Client")
        matrix = abc_tiers(matrix, "Amount")
        matrix["StatusHtml"] = matrix["Tier"].apply(tier_badge)

        search = st.text_input("🔍 Buscar cliente", placeholder="ej. Grupo Ramos", key="ov_search")
        view = matrix[matrix["Client"].str.contains(search, case=False, na=False)] if search else matrix

        table_df = pd.DataFrame({
            "Cliente": view["Client"],
            "Ítem Principal": view["Ítem Principal"].apply(lambda s: s.split(":")[-1]),
            "Ingresos (RD$)": view["Amount"].map(lambda v: f"${v:,.0f}"),
            "% del Total": view["PctOfTotal"].map(lambda v: f"{v:.1f}%"),
            "Estado": view["StatusHtml"],
        })
        render_html_table(table_df, table_df.columns.tolist(), table_df.columns.tolist(), page_key="ov_page")

# -----------------------------------------------------------------------
# PESTAÑA 2 — ANÁLISIS DE CLIENTES
# -----------------------------------------------------------------------
with tab_customer:
    if df_kpi.empty:
        st.info("No hay datos para el período seleccionado.")
    else:
        clients_sorted = df_kpi.groupby("Client")["Amount"].sum().sort_values(ascending=False).index.tolist()
        st.caption("DASHBOARD  ›  ANÁLISIS DE CLIENTES")
        sel_col, job_col = st.columns([2, 1])
        with sel_col:
            client = st.selectbox("Cliente", clients_sorted, key="cust_client")
        cdf_client_all_period = df_kpi[df_kpi["Client"] == client]
        jobs = ["Todos los Jobs"] + sorted(cdf_client_all_period["Job"].dropna().unique().tolist())
        with job_col:
            job_sel = st.selectbox("Job", jobs, key="cust_job")
        cdf = cdf_client_all_period if job_sel == "Todos los Jobs" else cdf_client_all_period[cdf_client_all_period["Job"] == job_sel]

        # dataset del cliente sin filtro de período (para ranking global, última factura, etc.)
        cdf_full = df[(df["Client"] == client) & ((df["Job"] == job_sel) if job_sel != "Todos los Jobs" else True)]

        st.markdown(
            f'<div class="pi-title">Inteligencia de Cliente: <span style="color:{COLORS["secondary"]}">{client}</span></div>',
            unsafe_allow_html=True,
        )
        st.write("")

        if cdf.empty:
            st.info("No hay transacciones para este cliente en el período seleccionado.")
        else:
            ingresos_periodo = cdf["Amount"].sum()
            cdf_ly = df_kpi_ly[(df_kpi_ly["Client"] == client) & ((df_kpi_ly["Job"] == job_sel) if job_sel != "Todos los Jobs" else True)]
            ingresos_ly = cdf_ly["Amount"].sum()
            delta_ingresos = kpi_delta(ingresos_periodo, ingresos_ly)

            # posición en el ranking de todos los clientes (por ingresos totales del período)
            ranking = df_kpi.groupby("Client")["Amount"].sum().sort_values(ascending=False)
            posicion = list(ranking.index).index(client) + 1 if client in ranking.index else None

            # última factura y frecuencia de facturación (histórico completo, no solo el período)
            ultima_fecha = cdf_full["Date"].max()
            dias_desde_ultima = (pd.Timestamp.today().normalize() - ultima_fecha).days if pd.notna(ultima_fecha) else None
            n_facturas_historico = cdf_full["Num"].nunique()
            meses_activos = cdf_full["Month"].nunique()
            ticket_promedio = cdf["Amount"].sum() / cdf["Num"].nunique() if cdf["Num"].nunique() else 0

            k1, k2, k3, k4 = st.columns(4)
            with k1:
                kpi_card("Ingresos en el Período", f"${ingresos_periodo:,.0f}",
                         f"{delta_ingresos:+.1f}% vs. año anterior" if ly_year_present else None, delta_ingresos >= 0)
            with k2:
                kpi_card("Posición en Ranking", f"#{posicion} de {len(ranking)}" if posicion else "—")
            with k3:
                if dias_desde_ultima is not None:
                    kpi_card("Última Facturación", f"Hace {dias_desde_ultima} días",
                             "⚠ Sin actividad reciente" if dias_desde_ultima > 45 else "Activo", dias_desde_ultima <= 45)
                else:
                    kpi_card("Última Facturación", "—")
            with k4:
                kpi_card("Ticket Promedio", f"${ticket_promedio:,.0f}")

            st.write("")
            left, right = st.columns([1, 2])
            with left:
                st.markdown(
                    f'<div class="pi-card" style="min-height: 220px;">'
                    f'<div style="display:flex; align-items:center; gap:14px; margin-bottom: 18px;">'
                    f'<div style="width:56px; height:56px; border-radius:12px; background:{COLORS["secondary_container"]};'
                    f'display:flex; align-items:center; justify-content:center; font-size:24px;">🏢</div>'
                    f'<div><div style="font-weight:700; font-size:16px;">{client}</div>'
                    f'<div style="color:{COLORS["on_surface_variant"]}; font-size:13px;">{job_sel}</div></div></div>'
                    f'<div class="pi-card-label">Meses con Actividad (histórico)</div>'
                    f'<div class="pi-card-value" style="font-size:22px;">{meses_activos}</div>'
                    f'<div class="pi-card-label" style="margin-top:12px;">Facturas Emitidas (histórico)</div>'
                    f'<div class="pi-card-value" style="font-size:22px;">{n_facturas_historico}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with right:
                st.markdown("###### Evolución de Ingresos")
                st.caption(f"Comparación mensual: {year_actual} vs. {year_ly}")
                cur_vals_c = monthly_series(cdf_full, year_actual, meses_grafico)
                ly_vals_c = monthly_series(cdf_full, year_ly, meses_grafico)
                st.plotly_chart(
                    yoy_line_chart(labels_grafico, cur_vals_c, ly_vals_c, year_actual, year_ly,
                                   "Ingresos ($)", ly_year_present),
                    width="stretch", key="cust_evo",
                )

            st.write("")
            st.markdown("###### Distribución por Categoría de Servicio")
            cat_dist = cdf.groupby("ItemCategory")["Amount"].sum().sort_values(ascending=False)
            if len(cat_dist):
                st.plotly_chart(bar_ranking(cat_dist.index.tolist(), cat_dist.values.tolist(), COLORS["tertiary_accent"]),
                                 width="stretch", key="cust_cat")

            st.write("")
            col1, col2 = st.columns(2)
            item_rev = cdf.groupby("Item")["Amount"].sum().sort_values(ascending=False)
            with col1:
                st.markdown("###### 📈 Ítems Más Facturados")
                top3 = item_rev.head(5)
                if len(top3):
                    labels = [i.split(":")[-1] for i in top3.index]
                    st.plotly_chart(bar_ranking(labels, top3.values.tolist(), COLORS["secondary"]),
                                     width="stretch", key="cust_top")
            with col2:
                st.markdown("###### 📉 Ítems Menos Facturados")
                bottom3 = item_rev.tail(5).sort_values()
                if len(bottom3):
                    labels = [i.split(":")[-1] for i in bottom3.index]
                    st.plotly_chart(bar_ranking(labels, bottom3.values.tolist(), COLORS["error"]),
                                     width="stretch", key="cust_bottom")

            st.write("")
            st.markdown("###### Transacciones Detalladas")
            st.caption(f"{len(cdf)} transacciones en el período seleccionado")
            table = cdf.sort_values("Date", ascending=False)[["Date", "Type", "Num", "Item", "Memo", "Amount"]].copy()
            table["Date"] = table["Date"].dt.strftime("%d %b %Y")
            table["Amount"] = table["Amount"].map(lambda v: f"${v:,.2f}")
            table = table.rename(columns={"Date": "Fecha", "Type": "Tipo", "Num": "Número",
                                           "Item": "Ítem", "Memo": "Memo", "Amount": "Monto"})
            st.dataframe(table, width="stretch", hide_index=True, height=380)
            st.download_button("⬇ Descargar Datos", data=cdf.to_csv(index=False).encode("utf-8"),
                                file_name=f"{client.replace(' ', '_')}_transacciones.csv", key="cust_dl")

# -----------------------------------------------------------------------
# PESTAÑA 3 — ANÁLISIS DE PRODUCTOS Y SERVICIOS
# -----------------------------------------------------------------------
with tab_product:
    st.markdown('<div class="pi-title">Rendimiento de Productos y Servicios</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="pi-subtitle">Análisis de ingresos por ítem/servicio facturado.</div>',
        unsafe_allow_html=True,
    )
    st.caption(
        "⚠️ Los márgenes de ganancia no son reales ya que el archivo no incluye columna de costo. "
        "Todo lo mostrado aquí se basa únicamente en ingresos facturados."
    )
    st.write("")

    if df_kpi.empty:
        st.info("No hay datos para el período seleccionado.")
    else:
        total_revenue = df_kpi["Amount"].sum()
        active_items = df_kpi["Item"].nunique()
        top_category = df_kpi.groupby("ItemCategory")["Amount"].sum().idxmax()
        avg_ticket = df_kpi["Amount"].mean()

        k1, k2, k3, k4 = st.columns(4)
        with k1:
            kpi_card("Ingresos Totales", f"${total_revenue:,.0f}")
        with k2:
            kpi_card("Ítems/Servicios Activos", f"{active_items:,}")
        with k3:
            kpi_card("Categoría Principal", top_category)
        with k4:
            kpi_card("Transacción Promedio", f"${avg_ticket:,.0f}")

        st.write("")
        st.markdown("###### Ingresos por Categoría")
        cat = df_kpi.groupby("ItemCategory")["Amount"].sum().sort_values(ascending=False)
        st.plotly_chart(bar_ranking(cat.index.tolist(), cat.values.tolist(), COLORS["secondary"]),
                         width="stretch", key="prod_cat")

        st.write("")
        st.markdown("###### Evolución de Ventas")
        st.caption(f"Comparación mensual: {year_actual} vs. {year_ly}")
        cur_vals_p = monthly_series(df, year_actual, meses_grafico)
        ly_vals_p = monthly_series(df, year_ly, meses_grafico)
        st.plotly_chart(
            yoy_line_chart(labels_grafico, cur_vals_p, ly_vals_p, year_actual, year_ly,
                           "Ingresos ($)", ly_year_present),
            width="stretch", key="prod_trend",
        )

        st.write("")
        item_summary_full = df.groupby("Item").agg(
            IngresosHist=("Amount", "sum"), Clientes=("Client", "nunique"),
        ).reset_index()
        item_summary = df_kpi.groupby("Item").agg(
            Revenue=("Amount", "sum"), Clientes=("Client", "nunique"), Transacciones=("Num", "nunique"),
        ).reset_index()
        item_summary = abc_tiers(item_summary, "Revenue")
        item_summary["StatusHtml"] = item_summary["Tier"].apply(tier_badge)
        item_summary["ItemLabel"] = item_summary["Item"].apply(lambda s: s.split(":")[-1])

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("###### 🏆 Ítems con Más Ingresos")
            top = item_summary.sort_values("Revenue", ascending=False).head(10)[["ItemLabel", "Transacciones", "Revenue"]]
            top["Revenue"] = top["Revenue"].map(lambda v: f"${v:,.0f}")
            st.dataframe(top.rename(columns={"ItemLabel": "Ítem", "Transacciones": "Transacciones", "Revenue": "Ingresos"}),
                         width="stretch", hide_index=True)
        with col2:
            st.markdown("###### 📉 Ítems con Menos Ingresos")
            bottom = item_summary.sort_values("Revenue", ascending=True).head(10)[["ItemLabel", "Transacciones", "Revenue"]]
            bottom["Revenue"] = bottom["Revenue"].map(lambda v: f"${v:,.0f}")
            st.dataframe(bottom.rename(columns={"ItemLabel": "Ítem", "Transacciones": "Transacciones", "Revenue": "Ingresos"}),
                         width="stretch", hide_index=True)

        # ---- Valor agregado: servicios facturados el año anterior que dejaron de facturarse ----
        st.write("")
        st.markdown("###### ⚠️ Servicios Sin Actividad Reciente")
        st.caption(
            f"Ítems que se facturaron en {year_ly} pero no tienen ninguna transacción en {year_actual} "
            "dentro del período seleccionado — posibles servicios descontinuados o clientes perdidos que vale la pena revisar."
        )
        items_ly = set(df[(df["Year"] == year_ly)]["Item"].unique())
        items_actual = set(df_kpi["Item"].unique())
        items_perdidos = items_ly - items_actual
        if items_perdidos:
            perdidos_rev = df[(df["Year"] == year_ly) & (df["Item"].isin(items_perdidos))].groupby("Item")["Amount"].sum().sort_values(ascending=False)
            perdidos_df = pd.DataFrame({
                "Ítem": [i.split(":")[-1] for i in perdidos_rev.index],
                "Categoría": [i.split(":")[0] for i in perdidos_rev.index],
                f"Ingresos en {year_ly}": perdidos_rev.values,
            })
            perdidos_df[f"Ingresos en {year_ly}"] = perdidos_df[f"Ingresos en {year_ly}"].map(lambda v: f"${v:,.0f}")
            st.dataframe(perdidos_df, width="stretch", hide_index=True)
        else:
            st.success("No se detectaron servicios que hayan dejado de facturarse.")

        st.write("")
        st.markdown("###### Todos los Ítems / Servicios")
        st.caption("Listado completo con participación en ingresos y clasificación ABC.")
        search = st.text_input("🔍 Buscar ítem", placeholder="ej. Conserjería", key="prod_search")
        view = item_summary
        if search:
            view = view[view["Item"].str.contains(search, case=False, na=False)]
        view = view.sort_values("Revenue", ascending=False)

        table_df = pd.DataFrame({
            "Ítem": view["ItemLabel"],
            "Categoría": view["Item"].apply(lambda s: s.split(":")[0]),
            "Ingresos (RD$)": view["Revenue"].map(lambda v: f"${v:,.0f}"),
            "% del Total": view["PctOfTotal"].map(lambda v: f"{v:.1f}%"),
            "Clientes": view["Clientes"],
            "Estado": view["StatusHtml"],
        })
        render_html_table(table_df, table_df.columns.tolist(), table_df.columns.tolist(), page_key="prod_page")

        st.download_button(
            "⬇ Descargar Reporte de Servicios",
            data=item_summary.drop(columns=["StatusHtml"]).to_csv(index=False).encode("utf-8"),
            file_name="reporte_productos.csv", key="prod_dl",
        )
