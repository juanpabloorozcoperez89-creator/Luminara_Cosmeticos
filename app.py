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
import os
import hmac
import hashlib
import unicodedata
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
USUARIOS_TAB = "Usuarios"

PRODUCTOS_COLS = [
    "sku", "linea", "tono", "categoria", "pedido", "fecha_pedido",
    "costo_unit", "envio_unit", "cantidad_comprada", "precio_venta",
    "activo", "notas",
]
VENTAS_COLS = [
    "venta_id", "fecha", "sku", "cantidad", "canal", "precio_venta",
    "cliente", "metodo_pago", "estado_pago", "notas",
    "precio_lista", "descuento_pct",
]
PAGOS_COLS = [
    "pago_id", "fecha", "cliente", "monto", "metodo_pago", "tipo",
    "referencia", "ventas_ids", "comprobante", "notas",
]
USUARIOS_COLS = ["username", "nombre", "email", "rol", "pass_hash", "creado"]

# Quien registre con estos correos o nombres entra como administrador
ADMIN_EMAILS = {"juanpabloorozcoperez89@gmail.com"}
ADMIN_NAMES = {"pablo orozco"}
# Nombre con que se saluda a personas conocidas, sin importar cómo lo escriban
DISPLAY_OVERRIDES = {
    "pablo orozco": "Pablo Orozco",
    "keren orozco": "Licda. Keren Orozco",
}

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
.block-container {{ max-width: 1240px; margin: 0 auto; padding-top:1.4rem; padding-bottom:3rem; }}

/* Densidad / tamaños en pantallas grandes */
@media (min-width:1100px) {{
  .module-head h1 {{ font-size:1.85rem; }}
  .kpi .value {{ font-size:1.5rem; }}
  .kpi {{ padding:16px 16px 14px; }}
  .panel {{ padding:18px 20px; }}
}}

@media (max-width:640px) {{
  .module-head h1 {{ font-size:1.6rem; }}
  .kpi .value {{ font-size:1.4rem; }}
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
                       (PAGOS_TAB, PAGOS_COLS), (USUARIOS_TAB, USUARIOS_COLS)]:
        if name not in existing:
            ws = ss.add_worksheet(title=name, rows=300, cols=len(cols))
            ws.update([cols], "A1")
        else:
            ws = existing[name]
            cur = ws.row_values(1)
            if not cur:
                ws.update([cols], "A1")
            elif any(c not in cur for c in cols):
                # Migración: añade columnas nuevas al final preservando el orden existente
                nuevo = cur + [c for c in cols if c not in cur]
                if ws.col_count < len(nuevo):
                    ws.add_cols(len(nuevo) - ws.col_count)
                ws.update([nuevo], "A1")
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


# ── Autenticación (usuarios en pestaña Usuarios) ───────────────────────────────
def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower().strip()
    return " ".join(s.split())


def hash_password(password: str, iterations: int = 200_000) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    return f"pbkdf2${iterations}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iters, salt_hex, hash_hex = str(stored).split("$")
        if algo != "pbkdf2":
            return False
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), int(iters))
        return hmac.compare_digest(dk.hex(), hash_hex)
    except Exception:
        return False


def load_usuarios() -> pd.DataFrame:
    return read_tab(USUARIOS_TAB, USUARIOS_COLS).copy()


def _rol_para(nombre: str, email: str) -> str:
    if _norm(email) in ADMIN_EMAILS or _norm(nombre) in ADMIN_NAMES:
        return "admin"
    return "usuario"


def register_user(username, nombre, email, password):
    df = load_usuarios()
    uname = str(username).strip()
    password = str(password).strip()
    if not uname or not password:
        return False, "Usuario y contraseña son obligatorios."
    if len(password) < 6:
        return False, "La contraseña debe tener al menos 6 caracteres."
    if not df.empty and (df["username"].astype(str).str.lower() == uname.lower()).any():
        return False, "Ese nombre de usuario ya existe."
    display = DISPLAY_OVERRIDES.get(_norm(nombre), str(nombre).strip() or uname)
    row = {
        "username": uname, "nombre": display, "email": str(email).strip(),
        "rol": _rol_para(nombre, email), "pass_hash": hash_password(password),
        "creado": date.today().isoformat(),
    }
    ws = get_spreadsheet().worksheet(USUARIOS_TAB)
    ws.append_row([row[c] for c in USUARIOS_COLS], value_input_option="RAW")
    read_tab.clear()
    return True, row


def authenticate(login_id, password):
    df = load_usuarios()
    if df.empty:
        return None
    lid = str(login_id).strip().lower()
    password = str(password).strip()
    mask = ((df["username"].astype(str).str.strip().str.lower() == lid)
            | (df["email"].astype(str).str.strip().str.lower() == lid))
    rows = df[mask]
    if rows.empty:
        return None
    u = rows.iloc[0]
    if verify_password(password, str(u["pass_hash"]).strip()):
        return {"username": u["username"], "nombre": u["nombre"],
                "rol": u["rol"], "email": u["email"]}
    return None


def reset_password(login_id, new_password):
    """Restablece la contraseña de un usuario por username o correo."""
    df = load_usuarios()
    new_password = str(new_password).strip()
    if len(new_password) < 6:
        return False, "La contraseña debe tener al menos 6 caracteres."
    lid = str(login_id).strip().lower()
    mask = ((df["username"].astype(str).str.strip().str.lower() == lid)
            | (df["email"].astype(str).str.strip().str.lower() == lid))
    if not mask.any():
        return False, "No encontré ese usuario o correo."
    df.loc[mask, "pass_hash"] = hash_password(new_password)
    write_tab(USUARIOS_TAB, df, USUARIOS_COLS)
    return True, df[mask].iloc[0]["nombre"]


# ──────────────────────────────────────────────────────────────────────────────
#  TRANSFORMACIONES / MÉTRICAS
# ──────────────────────────────────────────────────────────────────────────────
NUM_PROD = ["costo_unit", "envio_unit", "cantidad_comprada", "precio_venta"]
NUM_VENTA = ["cantidad", "precio_venta", "precio_lista", "descuento_pct"]


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
        # Descuentos: precio_lista (normalizado) vs precio real
        vent["precio_lista"] = pd.to_numeric(vent.get("precio_lista", 0), errors="coerce").fillna(0)
        vent["descuento_pct"] = pd.to_numeric(vent.get("descuento_pct", 0), errors="coerce").fillna(0)
        sin_lista = vent["precio_lista"] <= 0
        vent.loc[sin_lista, "precio_lista"] = vent.loc[sin_lista, "precio_venta"]
        vent["descuento_monto"] = ((vent["precio_lista"] - vent["precio_venta"]) * vent["cantidad"]).clip(lower=0)
        recalc = vent["descuento_pct"] <= 0
        vent.loc[recalc, "descuento_pct"] = (
            (1 - vent.loc[recalc, "precio_venta"] / vent.loc[recalc, "precio_lista"].replace(0, pd.NA)) * 100
        ).fillna(0).round(1)
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
    head("Nueva transacción", "Registrar venta",
         "El stock se descuenta solo · soporta descuentos y muestra la ganancia al instante")
    prod, _ = load_data()

    disponibles = prod[(prod["activo"]) & (prod["stock"] > 0)].copy()
    if disponibles.empty:
        st.warning("No hay productos con stock disponible. Agregá o reabastecé en **Inventario**.")
        return

    vk = st.session_state.get("venta_key", 0)
    disponibles["etq"] = disponibles.apply(
        lambda r: f"{r['nombre']}  ·  {r['categoria']}  ·  {q(r['precio_venta'])}  ·  stock {int(r['stock'])}",
        axis=1)
    opciones = dict(zip(disponibles["etq"], disponibles["sku"]))

    c1, c2 = st.columns([2, 1])
    etq = c1.selectbox("Producto *", list(opciones.keys()), key=f"prod_{vk}")
    sku = opciones[etq]
    row = disponibles[disponibles["sku"] == sku].iloc[0]
    max_stock = int(row["stock"])
    lista = float(row["precio_venta"])
    costo = float(row["costo_con_envio"])
    cantidad = c2.number_input("Cantidad *", min_value=1, max_value=max_stock, value=1,
                               step=1, key=f"cant_{vk}")

    st.markdown(
        f"""<div class="panel" style="margin:.2rem 0 .6rem">
        <span style="color:var(--muted);font-size:.8rem">CATEGORÍA</span> <b>{row['categoria']}</b>
        &nbsp;·&nbsp; <span style="color:var(--muted);font-size:.8rem">PRECIO DE LISTA</span> <b>{q(lista)}</b>
        &nbsp;·&nbsp; <span style="color:var(--muted);font-size:.8rem">COSTO</span> <b>{q(costo)}</b>
        </div>""", unsafe_allow_html=True)

    # Precio y descuento
    modo = st.radio("Precio", ["Precio de lista", "Aplicar descuento %", "Precio final personalizado"],
                    horizontal=True, key=f"modo_{vk}")
    if modo == "Aplicar descuento %":
        desc = st.number_input("Descuento %", min_value=0.0, max_value=100.0, value=0.0,
                               step=5.0, format="%.1f", key=f"desc_{vk}")
        precio = round(lista * (1 - desc / 100), 2)
    elif modo == "Precio final personalizado":
        precio = st.number_input("Precio final por unidad *", min_value=0.0, value=lista,
                                 step=1.0, format="%.2f", key=f"pf_{vk}_{sku}")
        desc = round((1 - precio / lista) * 100, 1) if lista > 0 else 0.0
    else:
        precio = lista
        desc = 0.0

    c3, c4, c5 = st.columns(3)
    canal = c3.selectbox("Canal *", CANALES, key=f"canal_{vk}")
    metodo = c4.selectbox("Método de pago", METODOS_PAGO, key=f"met_{vk}")
    estado = c5.selectbox("Estado de pago", ESTADOS_PAGO, key=f"est_{vk}")
    c6, c7 = st.columns([2, 1])
    cliente = c6.text_input("Cliente", key=f"cli_{vk}")
    fecha_v = c7.date_input("Fecha", value=date.today(), key=f"fec_{vk}")
    notas = st.text_input("Notas", key=f"not_{vk}")

    ingreso = precio * cantidad
    desc_monto = max(lista - precio, 0) * cantidad
    ganancia = (precio - costo) * cantidad
    color_gan = GOLD_DARK if ganancia >= 0 else "#C0392B"
    desc_txt = (f'&nbsp;·&nbsp; Descuento <b style="color:{MAUVE}">{q(desc_monto)} ({desc:.0f}%)</b>'
                if desc_monto > 0 else "")
    st.markdown(
        f"""<div class="panel" style="margin-top:.2rem">
        <b>Resumen:</b> {int(cantidad)} × {row['nombre']} &nbsp;·&nbsp;
        Precio unitario <b>{q(precio)}</b> {desc_txt} &nbsp;·&nbsp;
        Ingreso <b>{q(ingreso)}</b> &nbsp;·&nbsp;
        Ganancia <b style="color:{color_gan}">{q(ganancia)}</b> &nbsp;·&nbsp;
        Stock tras venta: <b>{max_stock - int(cantidad)}</b></div>""",
        unsafe_allow_html=True)
    if ganancia < 0:
        st.warning("⚠️ Esta venta da pérdida: el precio quedó por debajo del costo.")

    if st.button("✓ Registrar venta", type="primary", key=f"btn_{vk}"):
        venta = {
            "venta_id": str(uuid.uuid4())[:8], "fecha": fecha_v.isoformat(), "sku": sku,
            "cantidad": int(cantidad), "canal": canal, "precio_venta": round(precio, 2),
            "cliente": cliente, "metodo_pago": metodo, "estado_pago": estado, "notas": notas,
            "precio_lista": round(lista, 2), "descuento_pct": round(desc, 1),
        }
        try:
            append_venta(venta)
            st.session_state["venta_key"] = vk + 1
            st.success(f"Venta registrada · {int(cantidad)} × {row['nombre']} por {q(ingreso)}"
                       + (f" (descuento {desc:.0f}%)" if desc_monto > 0 else ""))
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

    f1, f2, f3, f4, f5 = st.columns(5)
    canal_f = f1.selectbox("Canal", ["Todos"] + sorted(vent["canal"].unique().tolist()))
    cat_f = f2.selectbox("Categoría", ["Todas"] + sorted(vent["categoria"].unique().tolist()))
    estado_f = f3.selectbox("Estado", ["Todos"] + ESTADOS_PAGO)
    metodo_f = f4.selectbox("Método", ["Todos"] + sorted(vent["metodo_pago"].unique().tolist()))
    busca = f5.text_input("Cliente / producto", placeholder="Buscar…")

    v = vent.copy()
    if canal_f != "Todos":
        v = v[v["canal"] == canal_f]
    if cat_f != "Todas":
        v = v[v["categoria"] == cat_f]
    if estado_f != "Todos":
        v = v[v["estado_pago"] == estado_f]
    if metodo_f != "Todos":
        v = v[v["metodo_pago"] == metodo_f]
    if busca:
        b = busca.lower()
        v = v[v["cliente"].str.lower().str.contains(b) | v["nombre"].str.lower().str.contains(b)]

    pendiente = v.loc[v["estado_pago"] == "Pendiente", "ingreso"].sum()
    apartado = v.loc[v["estado_pago"] == "Apartado", "ingreso"].sum()
    por_cobrar = pendiente + apartado
    kpi_grid([
        ("Registros", str(len(v)), f"{int(v['cantidad'].sum())} unidades"),
        ("Ingresos", q(v["ingreso"].sum()), ""),
        ("Ganancia", q(v["ganancia"].sum()), ""),
        ("Por cobrar", q(por_cobrar), f"Pendiente {q(pendiente)} · Apartado {q(apartado)}"),
        ("Descuentos", q(v["descuento_monto"].sum()), "total concedido"),
    ])
    if canal_f != "Todos":
        st.caption(f"Mostrando **{canal_f}**: vendido {q(v['ingreso'].sum())} · "
                   f"por cobrar {q(por_cobrar)} ({len(v[v['estado_pago'].isin(['Pendiente','Apartado'])])} ventas).")

    tab_ver, tab_edit = st.tabs(["📋 Ver", "✏️ Editar"])
    with tab_ver:
        show = v[["fecha", "nombre", "categoria", "canal", "cantidad", "precio_lista",
                  "precio_venta", "descuento_pct", "ingreso", "ganancia", "cliente",
                  "metodo_pago", "estado_pago", "notas"]].copy()
        show.columns = ["Fecha", "Producto", "Categoría", "Canal", "Cant.", "Lista",
                        "Precio", "Desc. %", "Ingreso", "Ganancia", "Cliente", "Pago",
                        "Estado", "Notas"]
        st.dataframe(
            show.sort_values("Fecha", ascending=False), use_container_width=True, hide_index=True,
            column_config={
                "Lista": st.column_config.NumberColumn(format="Q%.2f"),
                "Precio": st.column_config.NumberColumn(format="Q%.2f"),
                "Desc. %": st.column_config.NumberColumn(format="%.0f%%"),
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
                "precio_lista": st.column_config.NumberColumn("Precio lista", format="%.2f"),
                "descuento_pct": st.column_config.NumberColumn("Desc. %", format="%.1f"),
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
def _tab_canales(prod, vent):
    if vent.empty:
        st.info("Necesitás ventas registradas para el análisis de canal.")
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
#  PÁGINA · ANÁLISIS (inteligencia ejecutiva)
# ──────────────────────────────────────────────────────────────────────────────
def page_analisis():
    head("Inteligencia de negocio", "Análisis",
         "Rentabilidad, rotación, canales, clientes y cartera")
    prod, vent = load_data()
    pagos = load_pagos()

    if prod.empty:
        st.info("Cargá tu catálogo y ventas para ver el análisis.")
        return

    # KPIs globales
    ingresos = vent["ingreso"].sum() if not vent.empty else 0
    ganancia = vent["ganancia"].sum() if not vent.empty else 0
    inversion = prod["inversion"].sum()
    margen_global = (ganancia / ingresos * 100) if ingresos else 0
    comprado = prod["cantidad_comprada"].sum()
    vendido = prod["vendidos"].sum()
    sell_through = (vendido / comprado * 100) if comprado else 0
    dead = prod[(prod["activo"]) & (prod["vendidos"] == 0) & (prod["stock"] > 0)]
    capital_muerto = dead["valor_stock_costo"].sum()
    roi = (ganancia / inversion * 100) if inversion else 0

    kpi_grid([
        ("Margen bruto", f"{margen_global:.1f}%", f"Ganancia {q(ganancia)}"),
        ("Sell-through", f"{sell_through:.0f}%", f"{int(vendido)}/{int(comprado)} u. vendidas"),
        ("ROI realizado", f"{roi:.0f}%", f"sobre {q(inversion)}"),
        ("Ticket promedio", q(ingresos / len(vent)) if not vent.empty and len(vent) else "Q0.00", ""),
        ("Capital inmóvil", q(capital_muerto), f"{len(dead)} prod. sin rotar"),
    ])

    t1, t2, t3, t4, t5 = st.tabs([
        "💎 Rentabilidad", "🛍️ Ventas & canales", "📦 Rotación",
        "👑 Clientes", "💰 Cartera",
    ])

    # ── Rentabilidad ────────────────────────────────────────────────────────
    with t1:
        if vent.empty:
            st.info("Sin ventas para analizar rentabilidad.")
        else:
            c1, c2 = st.columns(2)
            with c1:
                st.markdown('<div class="panel"><h3>Margen por categoría</h3>', unsafe_allow_html=True)
                cm = vent.groupby("categoria").agg(ing=("ingreso", "sum"),
                                                   gan=("ganancia", "sum")).reset_index()
                cm["margen"] = (cm["gan"] / cm["ing"].replace(0, 1) * 100).round(1)
                cm = cm.sort_values("margen", ascending=False)
                fig = go.Figure(go.Bar(
                    x=cm["categoria"], y=cm["margen"], marker_color=GOLD,
                    text=[f"{m:.0f}%" for m in cm["margen"]], textposition="outside",
                    hovertemplate="%{x}: %{y:.1f}%<extra></extra>"))
                st.plotly_chart(style_fig(fig, 300), use_container_width=True,
                                config={"displayModeBar": False})
                st.markdown("</div>", unsafe_allow_html=True)
            with c2:
                st.markdown('<div class="panel"><h3>Top productos por ganancia</h3>', unsafe_allow_html=True)
                tg = vent.groupby("nombre")["ganancia"].sum().sort_values(ascending=False).head(10)
                fig = go.Figure(go.Bar(
                    x=tg.values, y=tg.index, orientation="h", marker_color=MAUVE,
                    text=[q(v) for v in tg.values], textposition="auto",
                    hovertemplate="%{y}: %{x:,.0f} Q<extra></extra>"))
                fig.update_layout(yaxis=dict(autorange="reversed"))
                st.plotly_chart(style_fig(fig, 300), use_container_width=True,
                                config={"displayModeBar": False})
                st.markdown("</div>", unsafe_allow_html=True)

            st.markdown('<div class="panel"><h3>Contribución a la ganancia (categoría → producto)</h3>',
                        unsafe_allow_html=True)
            tg = vent.groupby(["categoria", "nombre"])["ganancia"].sum().reset_index()
            tg = tg[tg["ganancia"] > 0]
            labels = ["Ganancia total"] + tg["categoria"].unique().tolist() + \
                     (tg["categoria"] + " · " + tg["nombre"]).tolist()
            parents = [""] + ["Ganancia total"] * tg["categoria"].nunique() + tg["categoria"].tolist()
            values = [0] + [0] * tg["categoria"].nunique() + tg["ganancia"].tolist()
            fig = go.Figure(go.Treemap(
                labels=labels, parents=parents, values=values, branchvalues="remainder",
                marker=dict(colors=[GOLD, MAUVE, ROSE, "#D9C4A3", BLUSH, GOLD_DARK] * 20),
                textinfo="label+value+percent parent",
                hovertemplate="%{label}<br>%{value:,.0f} Q<extra></extra>"))
            st.plotly_chart(style_fig(fig, 380), use_container_width=True,
                            config={"displayModeBar": False})
            st.markdown("</div>", unsafe_allow_html=True)

            st.markdown('<div class="panel"><h3>ROI por pedido</h3>', unsafe_allow_html=True)
            ped = prod.groupby("pedido").agg(inversion=("inversion", "sum")).reset_index()
            gv = vent.groupby(prod.set_index("sku")["pedido"].reindex(vent["sku"]).values)["ganancia"].sum() \
                if not vent.empty else pd.Series(dtype=float)
            ped["ganancia"] = ped["pedido"].map(gv).fillna(0)
            ped["ROI %"] = (ped["ganancia"] / ped["inversion"].replace(0, 1) * 100).round(0)
            ped.columns = ["Pedido", "Inversión", "Ganancia realizada", "ROI %"]
            st.dataframe(ped, use_container_width=True, hide_index=True, column_config={
                "Inversión": st.column_config.NumberColumn(format="Q%.2f"),
                "Ganancia realizada": st.column_config.NumberColumn(format="Q%.2f"),
                "ROI %": st.column_config.NumberColumn(format="%.0f%%")})
            st.markdown("</div>", unsafe_allow_html=True)

    # ── Ventas & canales ──────────────────────────────────────────────────────
    with t2:
        _tab_canales(prod, vent)
        if not vent.empty and vent["fecha_dt"].notna().any():
            st.markdown('<div class="panel"><h3>Tendencia de ingresos</h3>', unsafe_allow_html=True)
            ts = (vent.dropna(subset=["fecha_dt"]).set_index("fecha_dt")
                  .resample("W")["ingreso"].sum().reset_index())
            fig = go.Figure(go.Scatter(x=ts["fecha_dt"], y=ts["ingreso"], mode="lines+markers",
                                       line=dict(color=GOLD_DARK, width=2.5), fill="tozeroy",
                                       fillcolor="rgba(191,161,95,.12)"))
            st.plotly_chart(style_fig(fig, 280), use_container_width=True,
                            config={"displayModeBar": False})
            st.markdown("</div>", unsafe_allow_html=True)

    # ── Rotación / inventario ────────────────────────────────────────────────
    with t3:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="panel"><h3>Sell-through por producto</h3>', unsafe_allow_html=True)
            st_df = prod[prod["cantidad_comprada"] > 0].copy()
            st_df["st"] = (st_df["vendidos"] / st_df["cantidad_comprada"] * 100).round(0)
            st_df = st_df.sort_values("st", ascending=False).head(12)
            fig = go.Figure(go.Bar(
                x=st_df["st"], y=st_df["nombre"], orientation="h",
                marker=dict(color=st_df["st"], colorscale=[[0, ROSE], [1, GOLD]]),
                text=[f"{v:.0f}%" for v in st_df["st"]], textposition="auto",
                hovertemplate="%{y}: %{x:.0f}%<extra></extra>"))
            fig.update_layout(yaxis=dict(autorange="reversed"))
            st.plotly_chart(style_fig(fig, 360), use_container_width=True,
                            config={"displayModeBar": False})
            st.markdown("</div>", unsafe_allow_html=True)
        with c2:
            st.markdown('<div class="panel"><h3>Análisis ABC (Pareto de ingresos)</h3>',
                        unsafe_allow_html=True)
            if not vent.empty:
                pareto = vent.groupby("nombre")["ingreso"].sum().sort_values(ascending=False).reset_index()
                pareto["cum"] = (pareto["ingreso"].cumsum() / pareto["ingreso"].sum() * 100).round(1)
                fig = go.Figure()
                fig.add_bar(x=pareto["nombre"], y=pareto["ingreso"], marker_color=GOLD, name="Ingresos")
                fig.add_trace(go.Scatter(x=pareto["nombre"], y=pareto["cum"], yaxis="y2",
                                         mode="lines+markers", line=dict(color=MAUVE, width=2.5),
                                         name="% acumulado"))
                fig.update_layout(yaxis2=dict(overlaying="y", side="right", range=[0, 105],
                                              showgrid=False, ticksuffix="%"),
                                  xaxis=dict(showticklabels=False))
                st.plotly_chart(style_fig(fig, 360), use_container_width=True,
                                config={"displayModeBar": False})
                n_a = int((pareto["cum"] <= 80).sum()) or 1
                st.caption(f"**{n_a} productos** ({n_a/len(pareto)*100:.0f}% del catálogo vendido) "
                           f"generan el ~80% de los ingresos. Esos son tus productos **A**: priorizá "
                           f"su reposición.")
            else:
                st.caption("Sin ventas.")
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="panel"><h3>⚠️ Inventario sin rotación (capital inmóvil)</h3>',
                    unsafe_allow_html=True)
        if not dead.empty:
            dd = dead[["nombre", "categoria", "pedido", "stock", "costo_con_envio",
                       "valor_stock_costo", "valor_stock_venta"]].copy()
            dd.columns = ["Producto", "Categoría", "Pedido", "Stock", "Costo unit.",
                          "Capital (costo)", "Potencial (venta)"]
            st.dataframe(dd.sort_values("Capital (costo)", ascending=False),
                         use_container_width=True, hide_index=True, column_config={
                             "Costo unit.": st.column_config.NumberColumn(format="Q%.2f"),
                             "Capital (costo)": st.column_config.NumberColumn(format="Q%.2f"),
                             "Potencial (venta)": st.column_config.NumberColumn(format="Q%.2f")})
            st.caption(f"Tenés **{q(capital_muerto)}** inmovilizados en {len(dead)} productos que aún "
                       f"no venden ni una unidad. Considerá promoción, bundle o reubicación de canal.")
        else:
            st.success("Todo tu inventario activo ha tenido al menos una venta. Excelente rotación.")
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Clientes ──────────────────────────────────────────────────────────────
    with t4:
        if vent.empty or vent["cliente"].astype(str).str.strip().eq("").all():
            st.info("Registrá ventas con cliente para el análisis de clientes.")
        else:
            cl = vent[vent["cliente"].astype(str).str.strip() != ""].copy()
            cli = cl.groupby("cliente").agg(
                ingresos=("ingreso", "sum"), compras=("venta_id", "count"),
                unidades=("cantidad", "sum")).reset_index()
            cli["ticket"] = (cli["ingresos"] / cli["compras"].replace(0, 1)).round(2)
            pend = cl[cl["estado_pago"].isin(["Pendiente", "Apartado"])].groupby("cliente")["ingreso"].sum()
            cli["pendiente"] = cli["cliente"].map(pend).fillna(0)
            cli = cli.sort_values("ingresos", ascending=False)

            c1, c2 = st.columns([1.3, 1])
            with c1:
                st.markdown('<div class="panel"><h3>Top clientes por ingresos</h3>', unsafe_allow_html=True)
                top = cli.head(10)
                fig = go.Figure(go.Bar(
                    x=top["ingresos"], y=top["cliente"], orientation="h", marker_color=GOLD,
                    text=[q(v) for v in top["ingresos"]], textposition="auto",
                    hovertemplate="%{y}: %{x:,.0f} Q<extra></extra>"))
                fig.update_layout(yaxis=dict(autorange="reversed"))
                st.plotly_chart(style_fig(fig, 360), use_container_width=True,
                                config={"displayModeBar": False})
                st.markdown("</div>", unsafe_allow_html=True)
            with c2:
                st.markdown('<div class="panel"><h3>Concentración</h3>', unsafe_allow_html=True)
                top3 = cli.head(3)["ingresos"].sum()
                conc = top3 / cli["ingresos"].sum() * 100 if cli["ingresos"].sum() else 0
                kpi_grid([
                    ("Clientes únicos", str(len(cli)), ""),
                    ("Top 3 = % ingresos", f"{conc:.0f}%", "concentración"),
                    ("Mejor cliente", cli.iloc[0]["cliente"][:18], q(cli.iloc[0]["ingresos"])),
                ])
                st.markdown("</div>", unsafe_allow_html=True)

            st.markdown('<div class="panel"><h3>Detalle por cliente</h3>', unsafe_allow_html=True)
            tab = cli[["cliente", "compras", "unidades", "ingresos", "ticket", "pendiente"]].copy()
            tab.columns = ["Cliente", "Compras", "Unidades", "Ingresos", "Ticket prom.", "Por cobrar"]
            st.dataframe(tab, use_container_width=True, hide_index=True, column_config={
                "Ingresos": st.column_config.NumberColumn(format="Q%.2f"),
                "Ticket prom.": st.column_config.NumberColumn(format="Q%.2f"),
                "Por cobrar": st.column_config.NumberColumn(format="Q%.2f")})
            st.markdown("</div>", unsafe_allow_html=True)

    # ── Cartera / cobros ───────────────────────────────────────────────────────
    with t5:
        if vent.empty:
            st.info("Sin ventas para analizar cartera.")
        else:
            c1, c2 = st.columns(2)
            with c1:
                st.markdown('<div class="panel"><h3>Estado de la cartera</h3>', unsafe_allow_html=True)
                est = vent.groupby("estado_pago")["ingreso"].sum().reindex(ESTADOS_PAGO).fillna(0)
                colors = {"Pagado": "#9FBF8F", "Pendiente": ROSE, "Apartado": GOLD}
                fig = go.Figure(go.Pie(labels=est.index, values=est.values, hole=.58,
                                       marker=dict(colors=[colors[s] for s in est.index],
                                                   line=dict(color="#FFF", width=2)),
                                       textinfo="label+percent"))
                st.plotly_chart(style_fig(fig, 300), use_container_width=True,
                                config={"displayModeBar": False})
                pendiente_total = est.get("Pendiente", 0) + est.get("Apartado", 0)
                st.caption(f"Por cobrar: **{q(pendiente_total)}**")
                st.markdown("</div>", unsafe_allow_html=True)
            with c2:
                st.markdown('<div class="panel"><h3>Cobrado por método</h3>', unsafe_allow_html=True)
                if not pagos.empty:
                    mm = pagos.groupby("metodo_pago")["monto"].sum().sort_values(ascending=False)
                    fig = go.Figure(go.Bar(x=mm.values, y=mm.index, orientation="h",
                                           marker_color=MAUVE, text=[q(v) for v in mm.values],
                                           textposition="auto",
                                           hovertemplate="%{y}: %{x:,.0f} Q<extra></extra>"))
                    st.plotly_chart(style_fig(fig, 300), use_container_width=True,
                                    config={"displayModeBar": False})
                    con_comp = int((pagos["comprobante"].astype(str).str.len() > 0).sum())
                    st.caption(f"**{con_comp}/{len(pagos)}** pagos con comprobante adjunto.")
                else:
                    st.caption("Aún no hay pagos registrados en el módulo de Pagos.")
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

    tab_reg, tab_cobrar, tab_hist = st.tabs(
        ["💳 Registrar pago", "📋 Cuentas por cobrar", "🧾 Historial de pagos"])

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

    # ── Cuentas por cobrar (quién debe) ──────────────────────────────────────
    with tab_cobrar:
        if vent.empty:
            st.info("Sin ventas registradas.")
        else:
            ctc = vent[vent["estado_pago"].isin(["Pendiente", "Apartado"])].copy()
            if ctc.empty:
                st.success("No hay cuentas por cobrar. Todo está pagado. 🎉")
            else:
                ctc["cliente_norm"] = ctc["cliente"].astype(str).str.strip().replace("", "(Sin nombre)")
                piv = ctc.pivot_table(index="cliente_norm", columns="estado_pago",
                                      values="ingreso", aggfunc="sum", fill_value=0)
                for col in ["Pendiente", "Apartado"]:
                    if col not in piv.columns:
                        piv[col] = 0
                resumen = piv.reset_index()
                resumen["total"] = resumen["Pendiente"] + resumen["Apartado"]
                cnt = ctc.groupby("cliente_norm")["venta_id"].count()
                resumen["ventas"] = resumen["cliente_norm"].map(cnt).fillna(0).astype(int)
                resumen = resumen.rename(columns={"Pendiente": "pendiente", "Apartado": "apartado"})
                resumen = resumen[["cliente_norm", "pendiente", "apartado", "total", "ventas"]]
                resumen = resumen.sort_values("total", ascending=False)
                kpi_grid([
                    ("Clientes que deben", str(len(resumen)), ""),
                    ("Pendiente de pago", q(resumen["pendiente"].sum()), ""),
                    ("Apartado (reservado)", q(resumen["apartado"].sum()), ""),
                    ("Total por cobrar", q(resumen["total"].sum()), ""),
                ])
                tab = resumen.copy()
                tab.columns = ["Cliente", "Pendiente", "Apartado", "Total", "Ventas"]
                st.dataframe(tab, use_container_width=True, hide_index=True, column_config={
                    "Pendiente": st.column_config.NumberColumn(format="Q%.2f"),
                    "Apartado": st.column_config.NumberColumn(format="Q%.2f"),
                    "Total": st.column_config.NumberColumn(format="Q%.2f")})

                st.markdown("**Detalle por venta**")
                det = ctc[["fecha", "cliente_norm", "nombre", "canal", "cantidad",
                           "ingreso", "estado_pago", "metodo_pago"]].copy()
                det.columns = ["Fecha", "Cliente", "Producto", "Canal", "Cant.",
                               "Monto", "Estado", "Método"]
                st.dataframe(det.sort_values(["Estado", "Cliente"]), use_container_width=True,
                             hide_index=True, column_config={
                                 "Monto": st.column_config.NumberColumn(format="Q%.2f")})
                st.caption("Para registrar el cobro y marcarlas como pagadas, usá la pestaña "
                           "**Registrar pago**.")

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
# gcs_bucket = "luminara-comprobantes" # opcional: para adjuntar comprobantes
# registro_codigo = "clave-de-invitacion"  # opcional: exige código al registrarse
''', language="toml")
    st.caption("La app crea las pestañas **Productos**, **Ventas**, **Pagos** y **Usuarios** "
               "automáticamente. El primer usuario que se registre con el correo o nombre de "
               "Pablo Orozco entra como administrador.")


def screen_auth() -> bool:
    """Login / registro. Devuelve True si hay sesión activa."""
    if st.session_state.get("user"):
        return True

    try:
        usuarios = load_usuarios()
    except Exception as e:
        st.error(f"No se pudo leer la lista de usuarios: {e}")
        return False
    primer_uso = usuarios.empty

    st.markdown('<div class="login-wrap">', unsafe_allow_html=True)
    if Path(LOGO).exists():
        st.image(LOGO, use_container_width=True)
    st.markdown('<div class="login-card"><div class="brandline">Acceso privado</div><br>',
                unsafe_allow_html=True)

    if primer_uso:
        st.info("Primer ingreso: creá tu cuenta. Pablo Orozco entra como administrador.")

    tab_in, tab_reg, tab_rec = st.tabs(["Ingresar", "Crear cuenta", "Recuperar acceso"])

    with tab_in:
        lid = st.text_input("Usuario o correo", key="li_user")
        pw = st.text_input("Contraseña", type="password", key="li_pw")
        if st.button("Entrar", type="primary", use_container_width=True, key="li_btn"):
            user = authenticate(lid, pw)
            if user:
                st.session_state["user"] = user
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos.")

    with tab_reg:
        codigo_req = st.secrets.get("luminara", {}).get("registro_codigo", "")
        nombre = st.text_input("Nombre completo", key="rg_nombre",
                               placeholder="Ej. Keren Orozco")
        username = st.text_input("Nombre de usuario", key="rg_user",
                                 placeholder="keren")
        email = st.text_input("Correo", key="rg_email")
        p1 = st.text_input("Contraseña", type="password", key="rg_p1")
        p2 = st.text_input("Repetir contraseña", type="password", key="rg_p2")
        codigo = ""
        if codigo_req:
            codigo = st.text_input("Código de registro", type="password", key="rg_code")
        if st.button("Crear cuenta", type="primary", use_container_width=True, key="rg_btn"):
            if codigo_req and codigo != codigo_req:
                st.error("Código de registro inválido.")
            elif p1 != p2:
                st.error("Las contraseñas no coinciden.")
            else:
                ok, res = register_user(username, nombre, email, p1)
                if ok:
                    st.session_state["user"] = {
                        "username": res["username"], "nombre": res["nombre"],
                        "rol": res["rol"], "email": res["email"]}
                    st.success(f"¡Bienvenida, {res['nombre']}!")
                    st.rerun()
                else:
                    st.error(res)

    with tab_rec:
        recovery = st.secrets.get("luminara", {}).get("recovery_code", "")
        if not recovery:
            st.info("Para recuperar tu contraseña, pedile al administrador (Pablo) que te la "
                    "restablezca desde la sección **Usuarios**. Si sos el administrador y querés "
                    "recuperación propia, agregá `recovery_code = \"tu-clave\"` en los Secrets.")
        else:
            st.caption("Ingresá tu usuario, el código de recuperación y tu nueva contraseña.")
            rec_id = st.text_input("Usuario o correo", key="rc_id")
            rec_code = st.text_input("Código de recuperación", type="password", key="rc_code")
            rec_p1 = st.text_input("Nueva contraseña", type="password", key="rc_p1")
            rec_p2 = st.text_input("Repetir nueva contraseña", type="password", key="rc_p2")
            if st.button("Restablecer contraseña", type="primary", use_container_width=True, key="rc_btn"):
                if rec_code.strip() != str(recovery).strip():
                    st.error("Código de recuperación inválido.")
                elif rec_p1 != rec_p2:
                    st.error("Las contraseñas no coinciden.")
                else:
                    ok, res = reset_password(rec_id, rec_p1)
                    if ok:
                        st.success(f"Listo, {res}. Ya podés ingresar con tu nueva contraseña.")
                    else:
                        st.error(res)

    st.markdown("</div></div>", unsafe_allow_html=True)
    return False


def page_usuarios():
    head("Administración", "Usuarios", "Gestioná accesos al sistema")
    df = load_usuarios()
    if df.empty:
        st.info("No hay usuarios registrados.")
        return
    show = df[["nombre", "username", "email", "rol", "creado"]].copy()
    show.columns = ["Nombre", "Usuario", "Correo", "Rol", "Creado"]
    st.dataframe(show, use_container_width=True, hide_index=True)

    st.markdown('<div class="panel"><h3>Gestionar un usuario</h3>', unsafe_allow_html=True)
    objetivo = st.selectbox("Usuario", df["username"].tolist())
    fila = df[df["username"] == objetivo].iloc[0]
    c1, c2, c3 = st.columns(3)
    nuevo_rol = c1.selectbox("Rol", ["usuario", "admin"],
                             index=0 if fila["rol"] != "admin" else 1)
    nueva_pw = c2.text_input("Nueva contraseña (opcional)", type="password")
    accion = c3.selectbox("Acción", ["Actualizar", "Eliminar usuario"])
    if st.button("Aplicar", type="primary"):
        me = st.session_state.get("user", {}).get("username")
        if accion == "Eliminar usuario":
            if objetivo == me:
                st.error("No podés eliminar tu propia cuenta mientras la usás.")
            else:
                ndf = df[df["username"] != objetivo]
                write_tab(USUARIOS_TAB, ndf, USUARIOS_COLS)
                st.success(f"Usuario {objetivo} eliminado.")
                st.rerun()
        else:
            df.loc[df["username"] == objetivo, "rol"] = nuevo_rol
            if nueva_pw:
                if len(nueva_pw) < 6:
                    st.error("La contraseña debe tener al menos 6 caracteres.")
                    st.stop()
                df.loc[df["username"] == objetivo, "pass_hash"] = hash_password(nueva_pw)
            write_tab(USUARIOS_TAB, df, USUARIOS_COLS)
            st.success("Usuario actualizado.")
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────────────
#  MAIN
# ──────────────────────────────────────────────────────────────────────────────
def main():
    if not _secrets_ok():
        screen_setup()
        return

    try:
        ensure_schema()
    except Exception as e:
        st.error(f"No se pudo conectar al Google Sheet: {e}")
        st.info("Verificá que el Sheet esté compartido con la service account y que el ID sea correcto.")
        return

    if not screen_auth():
        return

    user = st.session_state["user"]
    es_admin = str(user.get("rol", "")).lower() == "admin"

    # Sidebar
    with st.sidebar:
        if Path(LOGO).exists():
            st.image(LOGO, use_container_width=True)
        st.markdown(
            '<div style="text-align:center;letter-spacing:.3em;font-size:.62rem;'
            'color:#9C7E3F;font-weight:600;margin:-6px 0 10px">CONTROL DE INVENTARIO</div>',
            unsafe_allow_html=True)
        st.markdown(
            f'<div style="text-align:center;margin-bottom:12px">'
            f'<span style="font-family:\'Playfair Display\',serif;font-size:1.02rem">'
            f'Hola, {user["nombre"]}</span><br>'
            f'<span style="font-size:.66rem;color:#B7A89F;letter-spacing:.08em">'
            f'{"ADMINISTRADORA" if es_admin else "USUARIA"}</span></div>',
            unsafe_allow_html=True)

    PAGINAS = {
        "✦  Resumen": page_resumen,
        "📦  Inventario": page_inventario,
        "🛒  Registrar venta": page_registrar,
        "💳  Registrar pagos": page_pagos,
        "🧾  Historial de ventas": page_ventas,
        "📈  Análisis": page_analisis,
    }
    if es_admin:
        PAGINAS["👤  Usuarios"] = page_usuarios

    seleccion = st.sidebar.radio("Navegación", list(PAGINAS.keys()), label_visibility="collapsed")

    with st.sidebar:
        st.markdown("<br>", unsafe_allow_html=True)
        cda, cdb = st.columns(2)
        if cda.button("↻ Refrescar", use_container_width=True):
            read_tab.clear()
            st.rerun()
        if cdb.button("⎋ Salir", use_container_width=True):
            st.session_state.pop("user", None)
            st.rerun()
        st.markdown(
            '<div style="text-align:center;color:#B7A89F;font-size:.66rem;margin-top:1rem">'
            'Luminara Cosméticos · datos en vivo desde Google Sheets</div>',
            unsafe_allow_html=True)

    PAGINAS[seleccion]()


if __name__ == "__main__":
    main()
