import os
import datetime
import pandas as pd


def normalizar(valor):
    """Normaliza cédulas/IMEIs para comparación (quita espacios y '.0' de floats)."""
    s = str(valor or "").strip().upper()
    if s.endswith(".0"):
        s = s[:-2]
    return s


def cargar_facturas_csv(ruta_archivo=None):
    """Carga FacturadoParaCruce.csv y devuelve un DataFrame normalizado.

    Excluye las filas de postpago real (tipo POSTPAGO/PORTABILIDAD con plan
    CONECTADOS), porque el postpago se cruza con Facturado_Postpago.csv.
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
    df_fact["tipo_norm"] = df_fact["tipo"].astype(str).map(normalizar)
    df_fact["plan_norm"] = df_fact["plan"].astype(str).map(normalizar)
    df_fact.dropna(subset=["tipo_norm"], inplace=True)
    df_fact = df_fact[~df_fact.apply(
        lambda r: r["tipo_norm"] in ("POSTPAGO", "PORTABILIDAD") and "CONECTADOS" in r["plan_norm"],
        axis=1,
    )]
    return df_fact


def cargar_facturas_postpago(ruta_archivo=None):
    """Carga Facturado_Postpago.csv y devuelve un DataFrame normalizado.

    La cédula de cliente viene en la columna iden_cliente. Si el archivo no
    existe devuelve None.
    """
    if ruta_archivo is None:
        ruta_archivo = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Facturado_Postpago.csv")
    if not os.path.exists(ruta_archivo):
        return None
    try:
        df_post = pd.read_csv(ruta_archivo, sep=";", encoding="utf-8")
    except UnicodeDecodeError:
        df_post = pd.read_csv(ruta_archivo, sep=";", encoding="latin-1")
    df_post = df_post.fillna("")
    df_post["cedula_norm"] = df_post["iden_cliente"].map(normalizar)
    return df_post


def calcular_estado_facturacion(datos_historial, hoy, df_fact, df_post):
    """Cruza las ventas del mes contra los CSV de facturas.

    Lógica de cruce:
      - Venta tipo "Postpago" -> se cruza por cédula de cliente contra
        Facturado_Postpago.csv (df_post), columna iden_cliente.
      - Resto de ventas -> se cruzan por IMEI contra FacturadoParaCruce.csv
        (df_fact), que ya excluye el postpago real. No hay paso por cédula.
      - Ventas Sim card -> se cruzan por ICCID contra la columna imei de las
        filas tipo AMIGO SIM de FacturadoParaCruce.csv (que almacena ICCIDs).

    Devuelve un DataFrame con columnas:
      Cédula Vendedor, Vendedor, Tipo, Fecha, Cliente, Cédula Cliente,
      IMEI, ICCID, Grupo Factura, Facturado (SÍ/NO).
    Si los CSVs son None o no hay ventas del mes, devuelve un DataFrame vacío.
    """
    if (df_fact is None or df_fact.empty) and (df_post is None or df_post.empty):
        return pd.DataFrame()

    set_imeis_fact = set(df_fact["imei_norm"]) if df_fact is not None else set()
    mapa_grupo_imei = dict(zip(df_fact["imei_norm"], df_fact["grupo_norm"])) if df_fact is not None else {}
    df_sim = df_fact[df_fact["tipo_norm"] == "AMIGO SIM"] if df_fact is not None else pd.DataFrame()
    set_iccids_fact = set(df_sim["imei_norm"]) if not df_sim.empty else set()
    set_cedulas_post = set(df_post["cedula_norm"]) if df_post is not None and not df_post.empty else set()
    mapa_grupo_post = dict(zip(df_post["cedula_norm"], ["POSTPAGO"] * len(df_post))) if df_post is not None and not df_post.empty else {}

    ventas_mes = [
        v for v in datos_historial
        if isinstance(v.get("fecha_venta"), datetime.date)
        and v["fecha_venta"].year == hoy.year
        and v["fecha_venta"].month == hoy.month
    ]

    filas = []
    for v in ventas_mes:
        imei_v = normalizar(v.get("imei"))
        iccid_v = normalizar(v.get("iccid"))
        cedula_c = normalizar(v.get("nro_documento"))
        tipo_v = normalizar(v.get("tipo_venta"))

        facturado = "NO"
        grupo_fact = ""

        if tipo_v == "POSTPAGO":
            if cedula_c and cedula_c in set_cedulas_post:
                facturado = "SÍ"
                grupo_fact = mapa_grupo_post.get(cedula_c, "POSTPAGO")
        else:
            if imei_v and imei_v in set_imeis_fact:
                facturado = "SÍ"
                grupo_fact = mapa_grupo_imei.get(imei_v, "")
            elif tipo_v == "SIM CARD" and iccid_v and iccid_v in set_iccids_fact:
                facturado = "SÍ"
                grupo_fact = "AMIGO SIM"

        filas.append({
            "Cédula Vendedor": v.get("cedula_vendedor", ""),
            "Vendedor": v.get("nombre_vendedor", ""),
            "Tipo": v.get("tipo_venta", ""),
            "Fecha": v.get("fecha_venta", ""),
            "Cliente": v.get("nombre_cliente", ""),
            "Cédula Cliente": cedula_c,
            "IMEI": imei_v,
            "ICCID": iccid_v,
            "Grupo Factura": grupo_fact,
            "Facturado": facturado,
        })

    return pd.DataFrame(filas)