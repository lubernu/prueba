import os
import datetime
import pandas as pd


def normalizar(valor):
    """Normaliza cédulas/IMEIs para comparación (quita espacios y '.0' de floats)."""
    s = str(valor or "").strip()
    if s.endswith(".0"):
        s = s[:-2]
    return s


def cargar_facturas_csv(ruta_archivo=None):
    """Carga FacturadoParaCruce.csv y devuelve un DataFrame normalizado.

    Si el archivo no existe devuelve None.
    """
    if ruta_archivo is None:
        ruta_archivo = os.path.join(os.path.dirname(os.path.abspath(__file__)), "FacturadoParaCruce.csv")
    if not os.path.exists(ruta_archivo):
        return None
    try:
        df_fact = pd.read_csv(ruta_archivo, sep=";", encoding="utf-8")
    except UnicodeDecodeError:
        df_fact = pd.read_csv(ruta_archivo, sep=";", encoding="latin-1")
    df_fact = df_fact.fillna("")
    df_fact["imei_norm"] = df_fact["imei"].map(normalizar)
    df_fact["cedula_norm"] = df_fact["cedula"].map(normalizar)
    df_fact["grupo_norm"] = df_fact["grupo"].map(normalizar)
    return df_fact


def calcular_estado_facturacion(datos_historial, hoy, df_fact):
    """Cruza las ventas del mes contra el CSV de facturas.

    Lógica de cruce:
      Paso 1: cruzar por IMEI (imei de la venta vs imei del CSV).
      Paso 2: las ventas que no cruzaron en paso 1 y tienen IMEI,
              se cruzan por cédula de cliente (nro_documento vs cedula del CSV).
      Ventas sin IMEI -> Pendiente (no entran al paso 2).

    Devuelve un DataFrame con columnas:
      Cédula Vendedor, Vendedor, Tipo, Fecha, Cliente, Cédula Cliente,
      IMEI, Grupo Factura, Facturado (SÍ/NO).
    Si df_fact es None o no hay ventas del mes, devuelve un DataFrame vacío.
    """
    if df_fact is None or df_fact.empty:
        return pd.DataFrame()

    set_imeis_fact = set(df_fact["imei_norm"])
    set_cedulas_fact = set(df_fact["cedula_norm"])
    mapa_grupo_imei = dict(zip(df_fact["imei_norm"], df_fact["grupo_norm"]))
    mapa_grupo_cedula = dict(zip(df_fact["cedula_norm"], df_fact["grupo_norm"]))

    ventas_mes = [
        v for v in datos_historial
        if isinstance(v.get("fecha_venta"), datetime.date)
        and v["fecha_venta"].year == hoy.year
        and v["fecha_venta"].month == hoy.month
    ]

    filas = []
    for v in ventas_mes:
        imei_v = normalizar(v.get("imei"))
        cedula_c = normalizar(v.get("nro_documento"))

        facturado = "NO"
        grupo_fact = ""

        if imei_v:
            if imei_v in set_imeis_fact:
                facturado = "SÍ"
                grupo_fact = mapa_grupo_imei.get(imei_v, "")
            elif cedula_c and cedula_c in set_cedulas_fact:
                facturado = "SÍ"
                grupo_fact = mapa_grupo_cedula.get(cedula_c, "")

        filas.append({
            "Cédula Vendedor": v.get("cedula_vendedor", ""),
            "Vendedor": v.get("nombre_vendedor", ""),
            "Tipo": v.get("tipo_venta", ""),
            "Fecha": v.get("fecha_venta", ""),
            "Cliente": v.get("nombre_cliente", ""),
            "Cédula Cliente": cedula_c,
            "IMEI": imei_v,
            "Grupo Factura": grupo_fact,
            "Facturado": facturado,
        })

    return pd.DataFrame(filas)