"""
Luminara Cosméticos — Control de Inventario
============================================
App profesional de inventario y ventas multicanal sobre Google Sheets.

Modelo de datos (2 pestañas en el Sheet):
  · Productos : catálogo + compra
  · Ventas    : un registro por venta (incluye CANAL)

Stock disponible = cantidad_comprada − Σ ventas.cantidad
"""

import uuid
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st
import plotly.graph_objects as go

# ──────────────────────────────────────────────────────────────────────────────
#  CONFIGURACIÓN GLOBAL
# ──────────────────────────────────────────────────────────────────────────────
ASSETS = Path(__file__).parent / "assets"
LOGO = str(ASSETS / "luminara_logo.png")

PRODUCTOS_TAB = "Productos"
VENTAS_TAB = "Ventas"
PAGOS_TAB = "Pagos"

PRODUCTOS_COLS = [
    "sku", "linea", "tono", "categoria", "pedido", "fecha_pedido",
    "costo_unit", "envio_unit", "cantidad_comprada", "precio_venta",
    "activo", "notas",
]
VENTAS_COLS = [
    "venta_id", "fecha", "sku", "cantidad", "canal", "precio_venta",
    "cliente", "metodo_pago", "estado_pago", "notas",
]
PAGOS_COLS = [
    "pago_id", "fecha", "cliente", "monto", "metodo_pago", "tipo",
    "referencia", "ventas_ids", "comprobante", "notas",
]

CANALES = ["En línea", "Vintage Boutique", "Almacén", "Directo", "Otro"]
METODOS_PAGO = ["Transferencia", "Efectivo", "Tarjeta", "Otro"]
PAGOS_METODOS = ["Transferencia", "Efectivo", "Depósito", "Tarjeta", "Cheque", "Otro"]
TIPOS_PAGO = ["Pago completo", "Abono", "Apartado"]
ESTADOS_PAGO = ["Pagado", "Pendiente", "Apartado"]
CATEGORIAS = ["Labios", "Rostro", "Ojos", "Labios y Mejillas", "Brochas", "General"]

# Paleta Luminara (extraída del logo)
GOLD = "#BFA15F"
GOLD_DARK = "#9C7E3F"
BLUSH = "#EBD8CF"
ROSE = "#C99B9B"
MAUVE = "#B98A8A"
CREAM = "#FBF4EF"
ESPRESSO = "#3A2E2A"
MUTED = "#9A8A82"
CANAL_COLORS = {
    "En línea": GOLD,
    "Vintage Boutique": MAUVE,
    "Almacén": ROSE,
    "Directo": "#D9C4A3",
    "Otro": "#CFC2BA",
}

st.set_page_config(
    page_title="Luminara · Inventario",
    page_icon=LOGO if Path(LOGO).exists() else "✦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────────────────────────────────────────
#  ESTILO (CSS luxe + responsivo)
# ──────────────────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@500;600;700&family=Inter:wght@300;400;500;600&display=swap');

:root {{
  --gold:{GOLD}; --gold-dark:{GOLD_DARK}; --blush:{BLUSH}; --rose:{ROSE};
  --cream:{CREAM}; --espresso:{ESPRESSO}; --muted:{MUTED};
}}

html, body, [class*="css"], .stApp {{
  font-family: 'Inter', sans-serif;
  color: var(--espresso);
}}
.stApp {{
  background: linear-gradient(180deg, #FDF8F4 0%, {CREAM} 100%);
}}

h1, h2, h3, h4 {{ font-family: 'Playfair Display', serif !important; color: var(--espresso); letter-spacing:.2px; }}

/* Sidebar */
[data-testid="stSidebar"] {{
  background: linear-gradient(180deg, #FFFFFF 0%, #FBF1EB 100%);
  border-right: 1px solid #EADFD7;
}}
[data-testid="stSidebar"] .stRadio label {{ font-weight:500; }}

/* Header del módulo */
.module-head {{ margin: .2rem 0 1.4rem 0; }}
.module-head .eyebrow {{
  font-family:'Inter'; font-size:.72rem; letter-spacing:.28em; text-transform:uppercase;
  color: var(--gold-dark); font-weight:600; margin-bottom:.2rem;
}}
.module-head h1 {{ font-size: 2.05rem; margin:0; line-height:1.1; }}
.module-head .sub {{ color: var(--muted); font-size:.92rem; margin-top:.35rem; }}

/* KPI grid responsivo */
.kpi-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(170px,1fr)); gap:14px; margin:.4rem 0 1.2rem 0; }}
.kpi {{
  background:#FFFFFF; border:1px solid #EFE5DD; border-radius:16px; padding:18px 18px 16px;
  box-shadow:0 4px 18px rgba(150,120,90,.06); position:relative; overflow:hidden;
}}
.kpi::before {{ content:''; position:absolute; top:0; left:0; width:100%; height:3px;
  background:linear-gradient(90deg,var(--gold),var(--rose)); opacity:.85; }}
.kpi .label {{ font-size:.72rem; letter-spacing:.12em; text-transform:uppercase; color:var(--muted); font-weight:600; }}
.kpi .value {{ font-family:'Playfair Display',serif; font-size:1.7rem; font-weight:600; margin-top:.25rem; line-height:1; }}
.kpi .delta {{ font-size:.78rem; color:var(--gold-dark); margin-top:.35rem; font-weight:500; }}

/* Cards de sección */
.panel {{ background:#FFFFFF; border:1px solid #EFE5DD; border-radius:18px; padding:20px 22px;
  box-shadow:0 4px 18px rgba(150,120,90,.05); margin-bottom:1rem; }}
.panel h3 {{ margin-top:0; font-size:1.15rem; }}

/* Botones */
.stButton>button, .stDownloadButton>button, .stFormSubmitButton>button {{
  background:linear-gradient(135deg,var(--gold) 0%,var(--gold-dark) 100%);
  color:#FFF; border:none; border-radius:10px; padding:.5rem 1.1rem; font-weight:600;
  letter-spacing:.02em; box-shadow:0 3px 10px rgba(160,130,80,.25); transition:.15s;
}}
.stButton>button:hover, .stDownloadButton>button:hover, .stFormSubmitButton>button:hover {{
  filter:brightness(1.06); transform:translateY(-1px); }}

/* Inputs */
[data-testid="stTextInput"] input, [data-testid="stNumberInput"] input,
.stSelectbox div[data-baseweb="select"]>div, .stDateInput input, textarea {{
  border-radius:10px !important;
}}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {{ gap:6px; }}
.stTabs [data-baseweb="tab"] {{ border-radius:10px 10px 0 0; padding:8px 16px; font-weight:500; }}
.stTabs [aria-selected="true"] {{ background:var(--blush); color:var(--espresso); }}

/* Dataframe */
[data-testid="stDataFrame"] {{ border-radius:12px; overflow:hidden; }}

/* Login */
.login-wrap {{ max-width:420px; margin:4vh auto; text-align:center; }}
.login-card {{ background:#FFF; border:1px solid #EFE5DD; border-radius:22px; padding:34px 30px;
  box-shadow:0 10px 40px rgba(150,120,90,.10); }}
.brandline {{ letter-spacing:.34em; text-transform:uppercase; font-size:.7rem; color:var(--gold-dark); font-weight:600; }}

footer, #MainMenu {{ visibility:hidden; }}
.block-container {{ padding-top:1.6rem; padding-bottom:3rem; }}

@media (max-width:640px) {{
  .module-head h1 {{ font-size:1.6rem; }}
  .kpi .value {{ font-size:1.45rem; }}
  .block-container {{ padding-left:.6rem; padding-right:.6rem; }}
}}
</style>
""", unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────────────
#  CAPA DE DATOS (Google Sheets vía gspread)
# ──────────────────────────────────────────────────────────────────────────────
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/devstorage.read_write",
]


def _secrets_ok() -> bool:
    return "gcp_service_account" in st.secrets and "luminara" in st.secrets


@st.cache_resource(show_spinner=False)
def get_spreadsheet():
    import gspread
    from google.oauth2.service_account import Credentials

    info = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    gc = gspread.authorize(creds)
    cfg = st.secrets["luminara"]
    if cfg.get("spreadsheet_id"):
        return gc.open_by_key(cfg["spreadsheet_id"])
    if cfg.get("spreadsheet_url"):
        return gc.open_by_url(cfg["spreadsheet_url"])
    return gc.open(cfg.get("spreadsheet_name", "Luminara"))


@st.cache_resource(show_spinner=False)
def ensure_schema():
    ss = get_spreadsheet()
    existing = {w.title: w for w in ss.worksheets()}
    for name, cols in [(PRODUCTOS_TAB, PRODUCTOS_COLS), (VENTAS_TAB, VENTAS_COLS),
                       (PAGOS_TAB, PAGOS_COLS)]:
        if name not in existing:
            ws = ss.add_worksheet(title=name, rows=300, cols=len(cols))
            ws.update([cols], "A1")
        else:
            ws = existing[name]
            if not ws.row_values(1):
                ws.update([cols], "A1")
    return True


@st.cache_data(ttl=20, show_spinner=False)
def read_tab(name: str, cols: list) -> pd.DataFrame:
    ws = get_spreadsheet().worksheet(name)
    records = ws.get_all_records()
    df = pd.DataFrame(records)
    for c in cols:
        if c not in df.columns:
            df[c] = ""
    return df[cols]


def write_tab(name: str, df: pd.DataFrame, cols: list):
    ws = get_spreadsheet().worksheet(name)
    df = df.reindex(columns=cols)
    clean = df.where(pd.notna(df), "")
    values = [cols] + clean.astype(object).values.tolist()
    ws.clear()
    ws.update(values, "A1", value_input_option="USER_ENTERED")
    read_tab.clear()


def append_venta(row: dict):
    ws = get_spreadsheet().worksheet(VENTAS_TAB)
    ws.append_row([row.get(c, "") for c in VENTAS_COLS], value_input_option="USER_ENTERED")
    read_tab.clear()


def append_pago(row: dict):
    ws = get_spreadsheet().worksheet(PAGOS_TAB)
    ws.append_row([row.get(c, "") for c in PAGOS_COLS], value_input_option="USER_ENTERED")
    read_tab.clear()


def mark_ventas_pagadas(venta_ids: list):
    """Marca como Pagado las ventas indicadas (reescribe la pestaña Ventas)."""
    if not venta_ids:
        return
    df = read_tab(VENTAS_TAB, VENTAS_COLS).copy()
    df.loc[df["venta_id"].astype(str).isin([str(v) for v in venta_ids]), "estado_pago"] = "Pagado"
    write_tab(VENTAS_TAB, df, VENTAS_COLS)


# ── Google Cloud Storage (comprobantes) ───────────────────────────────────────
def gcs_enabled() -> bool:
    return bool(st.secrets.get("luminara", {}).get("gcs_bucket"))


@st.cache_resource(show_spinner=False)
def get_bucket():
    from google.cloud import storage
    from google.oauth2.service_account import Credentials

    info = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(info)
    client = storage.Client(project=info.get("project_id"), credentials=creds)
    return client.bucket(st.secrets["luminara"]["gcs_bucket"])


def upload_comprobante(uploaded_file) -> str:
    ext = Path(uploaded_file.name).suffix.lower() or ".bin"
    blob_name = f"comprobantes/{date.today():%Y/%m}/{uuid.uuid4().hex}{ext}"
    blob = get_bucket().blob(blob_name)
    blob.upload_from_file(uploaded_file, content_type=getattr(uploaded_file, "type", None))
    return blob_name


@st.cache_data(ttl=1800, show_spinner=False)
def comprobante_url(blob_name: str) -> str:
    if not blob_name or not gcs_enabled():
        return ""
    try:
        return get_bucket().blob(blob_name).generate_signed_url(
            expiration=timedelta(hours=12), version="v4")
    except Exception:
        return ""


# ──────────────────────────────────────────────────────────────────────────────
#  TRANSFORMACIONES / MÉTRICAS
# ──────────────────────────────────────────────────────────────────────────────
NUM_PROD = ["costo_unit", "envio_unit", "cantidad_comprada", "precio_venta"]
NUM_VENTA = ["cantidad", "precio_venta"]


def load_data():
    prod = read_tab(PRODUCTOS_TAB, PRODUCTOS_COLS).copy()
    vent = read_tab(VENTAS_TAB, VENTAS_COLS).copy()

    for c in NUM_PROD:
        prod[c] = pd.to_numeric(prod[c], errors="coerce").fillna(0)
    for c in NUM_VENTA:
        vent[c] = pd.to_numeric(vent[c], errors="coerce").fillna(0)

    prod["activo"] = prod["activo"].astype(str).str.upper().isin(["TRUE", "1", "SI", "SÍ", "VERDADERO", "X"])
    prod["costo_con_envio"] = prod["costo_unit"] + prod["envio_unit"]
    prod["inversion"] = prod["costo_con_envio"] * prod["cantidad_comprada"]
    prod["ganancia_unidad"] = prod["precio_venta"] - prod["costo_con_envio"]
    prod["nombre"] = (prod["tono"].astype(str).str.strip() + " " + prod["linea"].astype(str).str.strip()).str.strip()

    # vendido por sku
    vendidos = vent.groupby("sku")["cantidad"].sum() if not vent.empty else pd.Series(dtype=float)
    prod["vendidos"] = prod["sku"].map(vendidos).fillna(0).astype(int)
    prod["stock"] = (prod["cantidad_comprada"] - prod["vendidos"]).clip(lower=0)
    prod["valor_stock_costo"] = prod["stock"] * prod["costo_con_envio"]
    prod["valor_stock_venta"] = prod["stock"] * prod["precio_venta"]

    # enriquecer ventas con costo para ganancia realizada
    if not vent.empty:
        cmap = prod.set_index("sku")["costo_con_envio"].to_dict()
        nmap = prod.set_index("sku")["nombre"].to_dict()
        catmap = prod.set_index("sku")["categoria"].to_dict()
        vent["costo_con_envio"] = vent["sku"].map(cmap).fillna(0)
        vent["nombre"] = vent["sku"].map(nmap).fillna(vent["sku"])
        vent["categoria"] = vent["sku"].map(catmap).fillna("General")
        vent["ingreso"] = vent["precio_venta"] * vent["cantidad"]
        vent["ganancia"] = (vent["precio_venta"] - vent["costo_con_envio"]) * vent["cantidad"]
        vent["fecha_dt"] = pd.to_datetime(vent["fecha"], errors="coerce")
    return prod, vent


def load_pagos() -> pd.DataFrame:
    pg = read_tab(PAGOS_TAB, PAGOS_COLS).copy()
    if pg.empty:
        return pg
    pg["monto"] = pd.to_numeric(pg["monto"], errors="coerce").fillna(0)
    pg["fecha_dt"] = pd.to_datetime(pg["fecha"], errors="coerce")
    return pg


# ──────────────────────────────────────────────────────────────────────────────
#  HELPERS DE FORMATO / UI
# ──────────────────────────────────────────────────────────────────────────────
def q(x) -> str:
    try:
        return f"Q{float(x):,.2f}"
    except (TypeError, ValueError):
        return "Q0.00"


def head(eyebrow, title, sub=""):
    st.markdown(
        f"""<div class="module-head"><div class="eyebrow">{eyebrow}</div>
        <h1>{title}</h1>{f'<div class="sub">{sub}</div>' if sub else ''}</div>""",
        unsafe_allow_html=True,
    )


def kpi_grid(items):
    cards = "".join(
        f"""<div class="kpi"><div class="label">{lbl}</div>
        <div class="value">{val}</div>{f'<div class="delta">{d}</div>' if d else ''}</div>"""
        for lbl, val, d in items
    )
    st.markdown(f'<div class="kpi-grid">{cards}</div>', unsafe_allow_html=True)


def style_fig(fig, h=320):
    fig.update_layout(
        height=h, margin=dict(l=10, r=10, t=30, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color=ESPRESSO, size=12),
        legend=dict(orientation="h", yanchor="bottom", y=-0.25, x=0),
        hoverlabel=dict(bgcolor="#FFF", font_size=12),
    )
    fig.update_xaxes(showgrid=False, linecolor="#E6DAD1")
    fig.update_yaxes(showgrid=True, gridcolor="#F0E7DF", zeroline=False)
    return fig


# ──────────────────────────────────────────────────────────────────────────────
#  PÁGINA · RESUMEN (Dashboard)
# ──────────────────────────────────────────────────────────────────────────────
def page_resumen():
    head("Panorama general", "Resumen ejecutivo", "Inventario, ventas y rentabilidad en un vistazo")
    prod, vent = load_data()

    if prod.empty:
        st.info("Todavía no hay productos. Empezá en **Inventario** agregando tu catálogo.")
        return

    inversion = prod["inversion"].sum()
    ingresos = vent["ingreso"].sum() if not vent.empty else 0
    ganancia_real = vent["ganancia"].sum() if not vent.empty else 0
    gan_proy = (prod["ganancia_unidad"] * prod["cantidad_comprada"]).sum()
    unidades_vendidas = int(vent["cantidad"].sum()) if not vent.empty else 0
    unidades_stock = int(prod["stock"].sum())
    valor_stock = prod["valor_stock_venta"].sum()
    pendiente = (
        vent.loc[vent["estado_pago"].isin(["Pendiente", "Apartado"]), "ingreso"].sum()
        if not vent.empty else 0
    )

    kpi_grid([
        ("Inversión total", q(inversion), f"{int(prod['cantidad_comprada'].sum())} unidades compradas"),
        ("Ingresos", q(ingresos), f"{unidades_vendidas} unidades vendidas"),
        ("Ganancia realizada", q(ganancia_real), f"Proyectada: {q(gan_proy)}"),
        ("Por cobrar", q(pendiente), "pendiente + apartado"),
        ("En inventario", f"{unidades_stock} u.", f"Valor venta: {q(valor_stock)}"),
    ])

    c1, c2 = st.columns([1.05, 1])
    with c1:
        st.markdown('<div class="panel"><h3>Ventas por canal</h3>', unsafe_allow_html=True)
        if not vent.empty:
            ch = vent.groupby("canal").agg(ingresos=("ingreso", "sum"),
                                           unidades=("cantidad", "sum")).reset_index()
            ch = ch.sort_values("ingresos", ascending=False)
            fig = go.Figure(go.Pie(
                labels=ch["canal"], values=ch["ingresos"], hole=.62,
                marker=dict(colors=[CANAL_COLORS.get(c, GOLD) for c in ch["canal"]],
                            line=dict(color="#FFF", width=2)),
                textinfo="label+percent", textfont=dict(size=11),
                hovertemplate="%{label}<br>%{value:,.0f} Q<br>%{percent}<extra></extra>",
            ))
            top = ch.iloc[0]
            fig.add_annotation(text=f"<b>{top['canal']}</b><br>lidera",
                               showarrow=False, font=dict(size=13, color=ESPRESSO))
            st.plotly_chart(style_fig(fig, 300), use_container_width=True, config={"displayModeBar": False})
            st.caption(f"Canal líder por ingresos: **{top['canal']}** ({q(top['ingresos'])}, "
                       f"{int(top['unidades'])} u.)")
        else:
            st.caption("Sin ventas registradas aún.")
        st.markdown("</div>", unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="panel"><h3>Estado de pagos</h3>', unsafe_allow_html=True)
        if not vent.empty:
            pg = vent.groupby("estado_pago")["ingreso"].sum().reindex(ESTADOS_PAGO).fillna(0)
            colors = {"Pagado": "#9FBF8F", "Pendiente": ROSE, "Apartado": GOLD}
            fig = go.Figure(go.Bar(
                x=pg.values, y=pg.index, orientation="h",
                marker=dict(color=[colors[s] for s in pg.index]),
                text=[q(v) for v in pg.values], textposition="auto",
                hovertemplate="%{y}: %{x:,.0f} Q<extra></extra>",
            ))
            st.plotly_chart(style_fig(fig, 300), use_container_width=True, config={"displayModeBar": False})
        else:
            st.caption("Sin datos.")
        st.markdown("</div>", unsafe_allow_html=True)

    c3, c4 = st.columns([1, 1])
    with c3:
        st.markdown('<div class="panel"><h3>Top productos por ingresos</h3>', unsafe_allow_html=True)
        if not vent.empty:
            top = (vent.groupby("nombre")["ingreso"].sum().sort_values(ascending=False).head(8))
            fig = go.Figure(go.Bar(
                x=top.values, y=top.index, orientation="h",
                marker=dict(color=GOLD), text=[q(v) for v in top.values], textposition="auto",
                hovertemplate="%{y}: %{x:,.0f} Q<extra></extra>",
            ))
            fig.update_layout(yaxis=dict(autorange="reversed"))
            st.plotly_chart(style_fig(fig, 340), use_container_width=True, config={"displayModeBar": False})
        else:
            st.caption("Sin ventas.")
        st.markdown("</div>", unsafe_allow_html=True)

    with c4:
        st.markdown('<div class="panel"><h3>Inventario por categoría</h3>', unsafe_allow_html=True)
        cat = prod.groupby("categoria").agg(stock=("stock", "sum"),
                                            valor=("valor_stock_venta", "sum")).reset_index()
        cat = cat.sort_values("valor", ascending=False)
        _pal = [GOLD, MAUVE, ROSE, "#D9C4A3", BLUSH, GOLD_DARK, "#CFC2BA"]
        _colors = [_pal[i % len(_pal)] for i in range(len(cat))]
        fig = go.Figure(go.Bar(
            x=cat["categoria"], y=cat["valor"],
            marker=dict(color=_colors),
            text=cat["stock"].astype(int).astype(str) + " u.", textposition="outside",
            hovertemplate="%{x}<br>Valor: %{y:,.0f} Q<extra></extra>",
        ))
        st.plotly_chart(style_fig(fig, 340), use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)

    if not vent.empty and vent["fecha_dt"].notna().any():
        st.markdown('<div class="panel"><h3>Evolución de ventas</h3>', unsafe_allow_html=True)
        ts = (vent.dropna(subset=["fecha_dt"]).set_index("fecha_dt")
              .resample("D")["ingreso"].sum().reset_index())
        fig = go.Figure(go.Scatter(
            x=ts["fecha_dt"], y=ts["ingreso"], mode="lines+markers",
            line=dict(color=GOLD_DARK, width=2.5), fill="tozeroy",
            fillcolor="rgba(191,161,95,.12)",
            hovertemplate="%{x|%d %b}: %{y:,.0f} Q<extra></extra>",
        ))
        st.plotly_chart(style_fig(fig, 280), use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────────────
#  PÁGINA · INVENTARIO
# ──────────────────────────────────────────────────────────────────────────────
def page_inventario():
    head("Catálogo y existencias", "Inventario", "Ver, editar, agregar y dar de baja productos")
    prod, vent = load_data()

    f1, f2, f3 = st.columns([2, 1.2, 1.2])
    busca = f1.text_input("Buscar", placeholder="Línea, tono o SKU…", label_visibility="collapsed")
    cat_f = f2.selectbox("Categoría", ["Todas"] + CATEGORIAS, label_visibility="collapsed")
    estado_f = f3.selectbox("Estado", ["Solo activos", "Todos", "Sin stock"], label_visibility="collapsed")

    view = prod.copy()
    if busca:
        b = busca.lower()
        view = view[view["nombre"].str.lower().str.contains(b) | view["sku"].str.lower().str.contains(b)]
    if cat_f != "Todas":
        view = view[view["categoria"] == cat_f]
    if estado_f == "Solo activos":
        view = view[view["activo"]]
    elif estado_f == "Sin stock":
        view = view[view["stock"] <= 0]

    bajo_stock = int((prod[prod["activo"]]["stock"].between(1, 1)).sum())
    agotados = int((prod[prod["activo"]]["stock"] <= 0).sum())
    kpi_grid([
        ("Productos activos", str(int(prod['activo'].sum())), f"{len(prod)} en total"),
        ("Unidades en stock", str(int(prod['stock'].sum())), ""),
        ("Stock bajo (≤1)", str(bajo_stock), "revisar reposición"),
        ("Agotados", str(agotados), ""),
    ])

    tab_ver, tab_edit, tab_add = st.tabs(["📋 Existencias", "✏️ Editar catálogo", "➕ Agregar producto"])

    with tab_ver:
        show = view[["sku", "nombre", "categoria", "pedido", "costo_con_envio",
                     "precio_venta", "ganancia_unidad", "cantidad_comprada",
                     "vendidos", "stock", "valor_stock_venta"]].copy()
        show.columns = ["SKU", "Producto", "Categoría", "Pedido", "Costo", "Precio",
                        "Gan./u", "Comprado", "Vendido", "Stock", "Valor stock"]
        _maxc = prod["cantidad_comprada"].max()
        stock_max = int(_maxc) if pd.notna(_maxc) and _maxc > 0 else 1
        st.dataframe(
            show, use_container_width=True, hide_index=True,
            column_config={
                "Costo": st.column_config.NumberColumn(format="Q%.2f"),
                "Precio": st.column_config.NumberColumn(format="Q%.2f"),
                "Gan./u": st.column_config.NumberColumn(format="Q%.2f"),
                "Valor stock": st.column_config.NumberColumn(format="Q%.2f"),
                "Stock": st.column_config.ProgressColumn(
                    format="%d", min_value=0, max_value=stock_max),
            },
        )

    with tab_edit:
        st.caption("Editá precios, costos, cantidades o desactivá productos. Guardá para escribir al Google Sheet.")
        edit_cols = PRODUCTOS_COLS
        editable = prod[edit_cols].copy()
        edited = st.data_editor(
            editable, use_container_width=True, hide_index=True, num_rows="dynamic",
            key="ed_prod",
            column_config={
                "sku": st.column_config.TextColumn("SKU", required=True),
                "linea": st.column_config.TextColumn("Línea", required=True),
                "tono": st.column_config.TextColumn("Tono"),
                "categoria": st.column_config.SelectboxColumn("Categoría", options=CATEGORIAS),
                "pedido": st.column_config.TextColumn("Pedido"),
                "fecha_pedido": st.column_config.TextColumn("Fecha pedido"),
                "costo_unit": st.column_config.NumberColumn("Costo unit.", format="%.2f", min_value=0),
                "envio_unit": st.column_config.NumberColumn("Envío unit.", format="%.2f", min_value=0),
                "cantidad_comprada": st.column_config.NumberColumn("Comprado", min_value=0, step=1),
                "precio_venta": st.column_config.NumberColumn("Precio venta", format="%.2f", min_value=0),
                "activo": st.column_config.CheckboxColumn("Activo"),
                "notas": st.column_config.TextColumn("Notas"),
            },
        )
        if st.button("💾 Guardar cambios de catálogo", type="primary"):
            df_save = edited.copy()
            df_save["activo"] = df_save["activo"].map(lambda v: "TRUE" if bool(v) else "FALSE")
            try:
                write_tab(PRODUCTOS_TAB, df_save, PRODUCTOS_COLS)
                st.success("Catálogo actualizado en Google Sheets.")
                st.rerun()
            except Exception as e:
                st.error(f"No se pudo guardar: {e}")

    with tab_add:
        with st.form("nuevo_prod", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            linea = c1.text_input("Línea *", placeholder="Hydra Lipgloss")
            tono = c2.text_input("Tono", placeholder="06")
            categoria = c3.selectbox("Categoría", CATEGORIAS)
            c4, c5, c6 = st.columns(3)
            costo = c4.number_input("Costo unitario *", min_value=0.0, step=1.0, format="%.2f")
            envio = c5.number_input("Envío unitario", min_value=0.0, step=1.0, format="%.2f")
            cantidad = c6.number_input("Cantidad comprada *", min_value=0, step=1)
            c7, c8, c9 = st.columns(3)
            precio = c7.number_input("Precio de venta *", min_value=0.0, step=1.0, format="%.2f")
            pedido = c8.text_input("Pedido / lote", placeholder="Pedido 4")
            fecha_p = c9.date_input("Fecha del pedido", value=date.today())
            sugerido = (costo + envio) * 1.30
            st.caption(f"Precio sugerido (+30%): **{q(sugerido)}**  ·  Ganancia/u con precio actual: "
                       f"**{q(precio - (costo + envio))}**")
            notas = st.text_input("Notas")
            if st.form_submit_button("➕ Agregar al inventario", type="primary"):
                if not linea or cantidad <= 0 or precio <= 0:
                    st.error("Línea, cantidad y precio de venta son obligatorios.")
                else:
                    sku_base = (f"{tono}-{linea}" if tono else linea).upper()
                    sku = "".join(ch if ch.isalnum() else "-" for ch in sku_base).strip("-")
                    existentes = set(prod["sku"])
                    sku_f, i = sku, 1
                    while sku_f in existentes:
                        i += 1
                        sku_f = f"{sku}-{i}"
                    nuevo = pd.DataFrame([{
                        "sku": sku_f, "linea": linea, "tono": tono, "categoria": categoria,
                        "pedido": pedido, "fecha_pedido": fecha_p.isoformat(),
                        "costo_unit": costo, "envio_unit": envio, "cantidad_comprada": int(cantidad),
                        "precio_venta": precio, "activo": "TRUE", "notas": notas,
                    }])
                    base = read_tab(PRODUCTOS_TAB, PRODUCTOS_COLS)
                    try:
                        write_tab(PRODUCTOS_TAB, pd.concat([base, nuevo], ignore_index=True), PRODUCTOS_COLS)
                        st.success(f"Producto **{sku_f}** agregado.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"No se pudo agregar: {e}")


# ──────────────────────────────────────────────────────────────────────────────
#  PÁGINA · REGISTRAR VENTA
# ──────────────────────────────────────────────────────────────────────────────
def page_registrar():
    head("Nueva transacción", "Registrar venta", "El stock se descuenta automáticamente")
    prod, _ = load_data()

    disponibles = prod[(prod["activo"]) & (prod["stock"] > 0)].copy()
    if disponibles.empty:
        st.warning("No hay productos con stock disponible. Agregá o reabastecé en **Inventario**.")
        return

    disponibles["etq"] = disponibles.apply(
        lambda r: f"{r['nombre']}  ·  {q(r['precio_venta'])}  ·  stock {int(r['stock'])}", axis=1)
    opciones = dict(zip(disponibles["etq"], disponibles["sku"]))

    with st.form("nueva_venta", clear_on_submit=True):
        c1, c2 = st.columns([2, 1])
        etq = c1.selectbox("Producto *", list(opciones.keys()))
        sku = opciones[etq]
        row = disponibles[disponibles["sku"] == sku].iloc[0]
        max_stock = int(row["stock"])
        cantidad = c2.number_input("Cantidad *", min_value=1, max_value=max_stock, value=1, step=1)

        c3, c4, c5 = st.columns(3)
        canal = c3.selectbox("Canal *", CANALES)
        precio = c4.number_input("Precio de venta *", min_value=0.0,
                                 value=float(row["precio_venta"]), step=1.0, format="%.2f")
        fecha_v = c5.date_input("Fecha", value=date.today())

        c6, c7, c8 = st.columns(3)
        cliente = c6.text_input("Cliente")
        metodo = c7.selectbox("Método de pago", METODOS_PAGO)
        estado = c8.selectbox("Estado de pago", ESTADOS_PAGO)
        notas = st.text_input("Notas")

        ganancia = (precio - row["costo_con_envio"]) * cantidad
        st.markdown(
            f"""<div class="panel" style="margin-top:.4rem">
            <b>Resumen:</b> {int(cantidad)} × {row['nombre']} &nbsp;·&nbsp;
            Ingreso <b>{q(precio*cantidad)}</b> &nbsp;·&nbsp;
            Ganancia <b style="color:{GOLD_DARK}">{q(ganancia)}</b> &nbsp;·&nbsp;
            Stock tras venta: <b>{max_stock-int(cantidad)}</b></div>""",
            unsafe_allow_html=True,
        )

        if st.form_submit_button("✓ Registrar venta", type="primary"):
            venta = {
                "venta_id": str(uuid.uuid4())[:8], "fecha": fecha_v.isoformat(), "sku": sku,
                "cantidad": int(cantidad), "canal": canal, "precio_venta": precio,
                "cliente": cliente, "metodo_pago": metodo, "estado_pago": estado, "notas": notas,
            }
            try:
                append_venta(venta)
                st.success(f"Venta registrada · {int(cantidad)} × {row['nombre']} por {q(precio*cantidad)}")
                st.balloons()
                st.rerun()
            except Exception as e:
                st.error(f"No se pudo registrar: {e}")


# ──────────────────────────────────────────────────────────────────────────────
#  PÁGINA · HISTORIAL DE VENTAS
# ──────────────────────────────────────────────────────────────────────────────
def page_ventas():
    head("Movimientos", "Historial de ventas", "Filtrá, revisá y editá registros")
    prod, vent = load_data()
    if vent.empty:
        st.info("Aún no hay ventas registradas.")
        return

    f1, f2, f3, f4 = st.columns(4)
    canal_f = f1.selectbox("Canal", ["Todos"] + sorted(vent["canal"].unique().tolist()))
    estado_f = f2.selectbox("Estado", ["Todos"] + ESTADOS_PAGO)
    metodo_f = f3.selectbox("Método", ["Todos"] + sorted(vent["metodo_pago"].unique().tolist()))
    busca = f4.text_input("Cliente / producto", placeholder="Buscar…")

    v = vent.copy()
    if canal_f != "Todos":
        v = v[v["canal"] == canal_f]
    if estado_f != "Todos":
        v = v[v["estado_pago"] == estado_f]
    if metodo_f != "Todos":
        v = v[v["metodo_pago"] == metodo_f]
    if busca:
        b = busca.lower()
        v = v[v["cliente"].str.lower().str.contains(b) | v["nombre"].str.lower().str.contains(b)]

    kpi_grid([
        ("Registros", str(len(v)), ""),
        ("Unidades", str(int(v["cantidad"].sum())), ""),
        ("Ingresos", q(v["ingreso"].sum()), ""),
        ("Ganancia", q(v["ganancia"].sum()), ""),
    ])

    tab_ver, tab_edit = st.tabs(["📋 Ver", "✏️ Editar"])
    with tab_ver:
        show = v[["fecha", "nombre", "canal", "cantidad", "precio_venta", "ingreso",
                  "ganancia", "cliente", "metodo_pago", "estado_pago", "notas"]].copy()
        show.columns = ["Fecha", "Producto", "Canal", "Cant.", "Precio", "Ingreso",
                        "Ganancia", "Cliente", "Pago", "Estado", "Notas"]
        st.dataframe(
            show.sort_values("Fecha", ascending=False), use_container_width=True, hide_index=True,
            column_config={
                "Precio": st.column_config.NumberColumn(format="Q%.2f"),
                "Ingreso": st.column_config.NumberColumn(format="Q%.2f"),
                "Ganancia": st.column_config.NumberColumn(format="Q%.2f"),
            },
        )
    with tab_edit:
        st.caption("Editá registros (ej. confirmar pagos) y guardá. Para anular, borrá la fila.")
        editable = vent[VENTAS_COLS].copy()
        edited = st.data_editor(
            editable, use_container_width=True, hide_index=True, num_rows="dynamic", key="ed_vent",
            column_config={
                "venta_id": st.column_config.TextColumn("ID", disabled=True),
                "fecha": st.column_config.TextColumn("Fecha"),
                "sku": st.column_config.TextColumn("SKU"),
                "cantidad": st.column_config.NumberColumn("Cant.", min_value=1, step=1),
                "canal": st.column_config.SelectboxColumn("Canal", options=CANALES),
                "precio_venta": st.column_config.NumberColumn("Precio", format="%.2f"),
                "cliente": st.column_config.TextColumn("Cliente"),
                "metodo_pago": st.column_config.SelectboxColumn("Pago", options=METODOS_PAGO),
                "estado_pago": st.column_config.SelectboxColumn("Estado", options=ESTADOS_PAGO),
                "notas": st.column_config.TextColumn("Notas"),
            },
        )
        if st.button("💾 Guardar cambios de ventas", type="primary"):
            try:
                write_tab(VENTAS_TAB, edited, VENTAS_COLS)
                st.success("Ventas actualizadas en Google Sheets.")
                st.rerun()
            except Exception as e:
                st.error(f"No se pudo guardar: {e}")


# ──────────────────────────────────────────────────────────────────────────────
#  PÁGINA · ANÁLISIS DE CANAL
# ──────────────────────────────────────────────────────────────────────────────
def page_analisis():
    head("Inteligencia comercial", "Análisis de canal", "¿Dónde se vende más y dónde rinde mejor?")
    prod, vent = load_data()
    if vent.empty:
        st.info("Necesitás ventas registradas para el análisis.")
        return

    ch = vent.groupby("canal").agg(
        unidades=("cantidad", "sum"), ingresos=("ingreso", "sum"),
        ganancia=("ganancia", "sum"), tickets=("venta_id", "count"),
    ).reset_index().sort_values("ingresos", ascending=False)
    ch["ticket_prom"] = ch["ingresos"] / ch["tickets"].replace(0, 1)
    ch["margen"] = (ch["ganancia"] / ch["ingresos"].replace(0, 1) * 100).round(1)

    lider_ing = ch.iloc[0]
    lider_u = ch.sort_values("unidades", ascending=False).iloc[0]
    lider_m = ch.sort_values("margen", ascending=False).iloc[0]
    kpi_grid([
        ("Canal líder (ingresos)", lider_ing["canal"], q(lider_ing["ingresos"])),
        ("Canal líder (unidades)", lider_u["canal"], f"{int(lider_u['unidades'])} u."),
        ("Mejor margen", lider_m["canal"], f"{lider_m['margen']}%"),
        ("Canales activos", str(len(ch)), ""),
    ])

    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="panel"><h3>Ingresos y ganancia por canal</h3>', unsafe_allow_html=True)
        fig = go.Figure()
        fig.add_bar(x=ch["canal"], y=ch["ingresos"], name="Ingresos", marker_color=GOLD)
        fig.add_bar(x=ch["canal"], y=ch["ganancia"], name="Ganancia", marker_color=MAUVE)
        fig.update_layout(barmode="group")
        st.plotly_chart(style_fig(fig, 320), use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="panel"><h3>Participación de unidades</h3>', unsafe_allow_html=True)
        fig = go.Figure(go.Pie(
            labels=ch["canal"], values=ch["unidades"], hole=.55,
            marker=dict(colors=[CANAL_COLORS.get(c, GOLD) for c in ch["canal"]],
                        line=dict(color="#FFF", width=2)),
            textinfo="label+percent",
        ))
        st.plotly_chart(style_fig(fig, 320), use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="panel"><h3>Tabla comparativa por canal</h3>', unsafe_allow_html=True)
    tabla = ch.copy()
    tabla.columns = ["Canal", "Unidades", "Ingresos", "Ganancia", "Tickets", "Ticket prom.", "Margen %"]
    st.dataframe(
        tabla, use_container_width=True, hide_index=True,
        column_config={
            "Ingresos": st.column_config.NumberColumn(format="Q%.2f"),
            "Ganancia": st.column_config.NumberColumn(format="Q%.2f"),
            "Ticket prom.": st.column_config.NumberColumn(format="Q%.2f"),
            "Margen %": st.column_config.NumberColumn(format="%.1f%%"),
        },
    )
    st.markdown("</div>", unsafe_allow_html=True)

    c3, c4 = st.columns(2)
    with c3:
        st.markdown('<div class="panel"><h3>Producto más vendido por canal</h3>', unsafe_allow_html=True)
        pivot = (vent.groupby(["canal", "nombre"])["cantidad"].sum()
                 .reset_index().sort_values("cantidad", ascending=False)
                 .drop_duplicates("canal"))
        pivot.columns = ["Canal", "Producto estrella", "Unidades"]
        st.dataframe(pivot, use_container_width=True, hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)
    with c4:
        st.markdown('<div class="panel"><h3>Método de pago por canal</h3>', unsafe_allow_html=True)
        mp = vent.groupby(["canal", "metodo_pago"])["ingreso"].sum().reset_index()
        fig = go.Figure()
        for m in mp["metodo_pago"].unique():
            sub = mp[mp["metodo_pago"] == m]
            fig.add_bar(x=sub["canal"], y=sub["ingreso"], name=m)
        fig.update_layout(barmode="stack")
        st.plotly_chart(style_fig(fig, 300), use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────────────
#  PÁGINA · PAGOS (comprobantes)
# ──────────────────────────────────────────────────────────────────────────────
def page_pagos():
    head("Cobros y comprobantes", "Registrar pagos",
         "Adjuntá el comprobante, registrá el método y saldá ventas pendientes")
    prod, vent = load_data()
    pagos = load_pagos()

    por_cobrar = (vent.loc[vent["estado_pago"].isin(["Pendiente", "Apartado"]), "ingreso"].sum()
                  if not vent.empty else 0)
    cobrado = pagos["monto"].sum() if not pagos.empty else 0
    n_pagos = len(pagos)
    con_comp = int((pagos["comprobante"].astype(str).str.len() > 0).sum()) if not pagos.empty else 0
    kpi_grid([
        ("Por cobrar", q(por_cobrar), "ventas pendientes + apartadas"),
        ("Total cobrado", q(cobrado), f"{n_pagos} pagos registrados"),
        ("Con comprobante", f"{con_comp}/{n_pagos}" if n_pagos else "0", ""),
        ("Almacenamiento", "GCS activo" if gcs_enabled() else "sin adjuntos", ""),
    ])

    if not gcs_enabled():
        st.info("📎 Para adjuntar fotos o PDFs, configurá `gcs_bucket` en los Secrets "
                "(ver README). Mientras tanto podés registrar pagos sin comprobante.")

    tab_reg, tab_hist = st.tabs(["💳 Registrar pago", "🧾 Historial de pagos"])

    # ── Registrar ──────────────────────────────────────────────────────────
    with tab_reg:
        pendientes = pd.DataFrame()
        if not vent.empty:
            pendientes = vent[vent["estado_pago"].isin(["Pendiente", "Apartado"])].copy()

        sel_ids, sel_cliente, sugerido = [], "", 0.0
        if not pendientes.empty:
            st.markdown("**Ventas pendientes** (opcional: seleccioná las que se están saldando)")
            pendientes["etq"] = pendientes.apply(
                lambda r: f"{r['venta_id']} · {r['nombre']} · {r['cliente']} · {q(r['ingreso'])} ({r['estado_pago']})",
                axis=1)
            elegidas = st.multiselect("Ventas a saldar", pendientes["etq"].tolist(),
                                      label_visibility="collapsed")
            chosen = pendientes[pendientes["etq"].isin(elegidas)]
            sel_ids = chosen["venta_id"].tolist()
            sugerido = float(chosen["ingreso"].sum())
            if not chosen.empty:
                sel_cliente = chosen["cliente"].iloc[0]
        else:
            st.caption("No hay ventas pendientes. Podés registrar un pago general igual.")

        ukey = st.session_state.get("pago_ukey", 0)
        with st.form("nuevo_pago", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            cliente = c1.text_input("Cliente", value=sel_cliente)
            monto = c2.number_input("Monto recibido *", min_value=0.0,
                                    value=round(sugerido, 2), step=10.0, format="%.2f")
            fecha_p = c3.date_input("Fecha", value=date.today())
            c4, c5, c6 = st.columns(3)
            metodo = c4.selectbox("Método *", PAGOS_METODOS)
            tipo = c5.selectbox("Tipo", TIPOS_PAGO)
            referencia = c6.text_input("Referencia / No. transacción")
            comprobante = st.file_uploader(
                "Comprobante (foto o PDF)", type=["png", "jpg", "jpeg", "webp", "pdf"],
                key=f"comp_{ukey}", disabled=not gcs_enabled(),
                help=None if gcs_enabled() else "Configurá GCS para habilitar adjuntos")
            notas = st.text_input("Notas")
            marcar = st.checkbox("Marcar las ventas seleccionadas como **Pagadas**",
                                 value=bool(sel_ids), disabled=not sel_ids)

            if st.form_submit_button("✓ Registrar pago", type="primary"):
                if monto <= 0:
                    st.error("El monto debe ser mayor a cero.")
                else:
                    blob = ""
                    try:
                        if comprobante is not None and gcs_enabled():
                            with st.spinner("Subiendo comprobante…"):
                                blob = upload_comprobante(comprobante)
                        pago = {
                            "pago_id": str(uuid.uuid4())[:8], "fecha": fecha_p.isoformat(),
                            "cliente": cliente, "monto": monto, "metodo_pago": metodo,
                            "tipo": tipo, "referencia": referencia,
                            "ventas_ids": ",".join(map(str, sel_ids)), "comprobante": blob,
                            "notas": notas,
                        }
                        append_pago(pago)
                        if marcar and sel_ids:
                            mark_ventas_pagadas(sel_ids)
                        st.session_state["pago_ukey"] = ukey + 1
                        st.success(f"Pago de {q(monto)} registrado"
                                   + (" · comprobante adjuntado" if blob else ""))
                        st.rerun()
                    except Exception as e:
                        st.error(f"No se pudo registrar el pago: {e}")

    # ── Historial ──────────────────────────────────────────────────────────
    with tab_hist:
        if pagos.empty:
            st.info("Aún no hay pagos registrados.")
            return
        f1, f2 = st.columns([1, 2])
        met_f = f1.selectbox("Método", ["Todos"] + PAGOS_METODOS)
        busca = f2.text_input("Buscar cliente / referencia", placeholder="Buscar…")
        v = pagos.sort_values("fecha_dt", ascending=False, na_position="last").copy()
        if met_f != "Todos":
            v = v[v["metodo_pago"] == met_f]
        if busca:
            b = busca.lower()
            v = v[v["cliente"].astype(str).str.lower().str.contains(b)
                  | v["referencia"].astype(str).str.lower().str.contains(b)]

        for _, p in v.iterrows():
            with st.container():
                col_a, col_b = st.columns([2.4, 1])
                with col_a:
                    st.markdown(
                        f"""<div class="panel" style="margin-bottom:.6rem">
                        <div style="display:flex;justify-content:space-between;align-items:baseline">
                          <span style="font-family:'Playfair Display',serif;font-size:1.3rem">{q(p['monto'])}</span>
                          <span style="color:{GOLD_DARK};font-weight:600;font-size:.8rem">{p['metodo_pago']} · {p['tipo']}</span>
                        </div>
                        <div style="color:var(--muted);font-size:.85rem;margin-top:.25rem">
                          {p['cliente'] or '—'} &nbsp;·&nbsp; {p['fecha'] or 's/f'}
                          {f"&nbsp;·&nbsp; Ref: {p['referencia']}" if p['referencia'] else ""}
                        </div>
                        {f'<div style="margin-top:.4rem;font-size:.85rem">{p["notas"]}</div>' if p['notas'] else ''}
                        </div>""",
                        unsafe_allow_html=True)
                with col_b:
                    blob = str(p["comprobante"])
                    if blob:
                        url = comprobante_url(blob)
                        if blob.lower().endswith(".pdf"):
                            if url:
                                st.link_button("📄 Ver comprobante (PDF)", url, use_container_width=True)
                        elif url:
                            st.image(url, use_container_width=True)
                    else:
                        st.caption("Sin comprobante")


# ──────────────────────────────────────────────────────────────────────────────
#  PANTALLAS DE SISTEMA: configuración pendiente / login
# ──────────────────────────────────────────────────────────────────────────────
def screen_setup():
    if Path(LOGO).exists():
        st.image(LOGO, width=260)
    head("Configuración", "Falta conectar el Google Sheet",
         "Agregá las credenciales en los Secrets de Streamlit para activar la app")
    st.markdown("""
**1.** En Google Cloud creá una *Service Account*, descargá el JSON y compartí tu Google Sheet
(como *Editor*) con el correo `client_email` de esa cuenta.

**2.** En Streamlit Cloud → *Settings → Secrets*, pegá:
    """)
    st.code('''[gcp_service_account]
type = "service_account"
project_id = "tu-proyecto"
private_key_id = "..."
private_key = "-----BEGIN PRIVATE KEY-----\\n...\\n-----END PRIVATE KEY-----\\n"
client_email = "luminara@tu-proyecto.iam.gserviceaccount.com"
client_id = "..."
token_uri = "https://oauth2.googleapis.com/token"

[luminara]
spreadsheet_id = "ID_DE_TU_SHEET"      # el que va entre /d/ y /edit en la URL
app_password = "una-clave-opcional"    # opcional: protege el acceso
''', language="toml")
    st.caption("La app crea las pestañas **Productos** y **Ventas** automáticamente si no existen. "
               "Podés sembrar datos pegando seed_productos.csv y seed_ventas.csv.")


def screen_login() -> bool:
    pwd = st.secrets.get("luminara", {}).get("app_password", "")
    if not pwd:
        return True
    if st.session_state.get("auth_ok"):
        return True
    st.markdown('<div class="login-wrap">', unsafe_allow_html=True)
    if Path(LOGO).exists():
        st.image(LOGO, use_container_width=True)
    st.markdown('<div class="login-card"><div class="brandline">Acceso privado</div>',
                unsafe_allow_html=True)
    entry = st.text_input("Contraseña", type="password", label_visibility="collapsed",
                          placeholder="Contraseña")
    if st.button("Entrar", type="primary", use_container_width=True):
        if entry == pwd:
            st.session_state["auth_ok"] = True
            st.rerun()
        else:
            st.error("Contraseña incorrecta.")
    st.markdown("</div></div>", unsafe_allow_html=True)
    return False


# ──────────────────────────────────────────────────────────────────────────────
#  MAIN
# ──────────────────────────────────────────────────────────────────────────────
def main():
    if not _secrets_ok():
        screen_setup()
        return
    if not screen_login():
        return

    try:
        ensure_schema()
    except Exception as e:
        st.error(f"No se pudo conectar al Google Sheet: {e}")
        st.info("Verificá que el Sheet esté compartido con la service account y que el ID sea correcto.")
        return

    # Sidebar
    with st.sidebar:
        if Path(LOGO).exists():
            st.image(LOGO, use_container_width=True)
        st.markdown(
            '<div style="text-align:center;letter-spacing:.3em;font-size:.62rem;'
            'color:#9C7E3F;font-weight:600;margin:-6px 0 14px">CONTROL DE INVENTARIO</div>',
            unsafe_allow_html=True)

    PAGINAS = {
        "✦  Resumen": page_resumen,
        "📦  Inventario": page_inventario,
        "🛒  Registrar venta": page_registrar,
        "💳  Registrar pagos": page_pagos,
        "🧾  Historial de ventas": page_ventas,
        "📊  Análisis de canal": page_analisis,
    }
    seleccion = st.sidebar.radio("Navegación", list(PAGINAS.keys()), label_visibility="collapsed")

    with st.sidebar:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("↻ Refrescar datos", use_container_width=True):
            read_tab.clear()
            st.rerun()
        st.markdown(
            '<div style="text-align:center;color:#B7A89F;font-size:.68rem;margin-top:1rem">'
            'Luminara Cosméticos · datos en vivo desde Google Sheets</div>',
            unsafe_allow_html=True)

    PAGINAS[seleccion]()


if __name__ == "__main__":
    main()
