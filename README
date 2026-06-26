# Luminara Cosméticos · Control de Inventario

App profesional en Streamlit para gestionar inventario y ventas multicanal
de Luminara, con datos en vivo sobre Google Sheets. Responsiva (PC, tablet,
smartphone), con dashboard ejecutivo y análisis de canal.

---

## Qué hace

- **Resumen**: KPIs (inversión, ingresos, ganancia, por cobrar, stock) + gráficas de canal, pagos, top productos, categorías y evolución.
- **Inventario**: ver existencias con stock calculado, editar catálogo, agregar y dar de baja productos.
- **Registrar venta**: descuenta stock automáticamente, valida que no vendás más de lo disponible.
- **Historial de ventas**: filtros por canal/estado/método, edición (ej. confirmar pagos).
- **Análisis de canal**: responde directo *¿se vende más en línea, en Vintage Boutique o dónde?* (ingresos, unidades, margen, ticket promedio, producto estrella y método de pago por canal).

---

## Modelo de datos (2 pestañas en el Google Sheet)

La app crea las pestañas sola si no existen. El stock no se guarda: se calcula
como `cantidad_comprada − Σ ventas`.

### `Productos`
`sku · linea · tono · categoria · pedido · fecha_pedido · costo_unit · envio_unit · cantidad_comprada · precio_venta · activo · notas`

### `Ventas`
`venta_id · fecha · sku · cantidad · canal · precio_venta · cliente · metodo_pago · estado_pago · notas`

Canales por defecto: **En línea · Vintage Boutique · Almacén · Directo · Otro**

---

## Configuración (una sola vez)

1. **Google Cloud** → creá una *Service Account*, activá las APIs de Google
   Sheets y Drive, generá una llave JSON.
2. **Compartí tu Google Sheet** (como *Editor*) con el `client_email` de la
   service account.
3. **Streamlit Cloud → Settings → Secrets**: pegá el contenido de
   `.streamlit/secrets.toml.example` con tus valores reales. El
   `spreadsheet_id` es lo que va entre `/d/` y `/edit` en la URL del Sheet.
   Opcional: `app_password` para proteger el acceso.

Sin secrets configurados la app muestra una pantalla de ayuda en vez de fallar.

---

## Sembrar tus datos actuales (opcional)

Ya generé el seed desde tu Excel:

- `seed_productos.csv` → pegalo en la pestaña **Productos**
- `seed_ventas.csv` → pegalo en la pestaña **Ventas**

> Nota: el canal histórico se infirió de las notas del Excel (Almacén vs
> Directo). De aquí en adelante, al registrar ventas elegís el canal real
> (En línea / Vintage Boutique / etc.). Además, algunos tonos aparecían en dos
> pedidos con costos de envío distintos y el seed los fusionó en un solo SKU;
> revisá `costo_unit`/`envio_unit` de esos casos si querés exactitud al centavo.

Para regenerar el seed: `python migrate_excel.py ruta/al/excel.xlsx`

---

## Deploy (GitHub → Streamlit Cloud)

1. Subí estos archivos al repo (con GitHub Desktop).
2. En Streamlit Cloud apuntá la app a `app.py`.
3. Cargá los Secrets.
4. Reboot. Listo.

**No subás** `.streamlit/secrets.toml` (ya está en `.gitignore`).

---

## Estructura

```
luminara/
├── app.py                       # la app
├── migrate_excel.py             # Excel -> seed CSVs
├── requirements.txt
├── seed_productos.csv
├── seed_ventas.csv
├── assets/luminara_logo.png
└── .streamlit/
    ├── config.toml
    └── secrets.toml.example
```
