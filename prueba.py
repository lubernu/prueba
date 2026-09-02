import re
import streamlit as st
import datetime
import pandas as pd
import os
from supabase import create_client

def _get_app_config(clave, valor_default):
    try:
        return st.secrets["app"].get(clave, valor_default)
    except Exception:
        return valor_default

TABLA_VENTAS = _get_app_config("tabla_ventas", "ventas")
CEDULAS_ADMIN = list(_get_app_config("cedulas_admin", []))

# ================= CONFIGURACIÓN DE FUNCIONES AUXILIARES =================
def validar_campo_numerico(valor_ingresado, longitud_esperada):
    if not valor_ingresado:
        return False, ""
    if not valor_ingresado.isdigit():
        return False, "Solo se permiten números (0-9)."
    if len(valor_ingresado) < longitud_esperada:
        return False, ""  
    if len(valor_ingresado) == longitud_esperada:
        return True, ""
    return False, ""

def validar_formato_correo(correo):
    """Valida el formato del correo electrónico: texto@texto.xx"""
    if not correo:
        return True, ""
    patron = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)*\.[a-zA-Z]{2,}$"
    if re.match(patron, correo.strip()):
        return True, ""
    return False, "Formato inválido. Ej: nombre@dominio.com"

def cargar_asesores(cliente=None):
    """Carga los asesores desde Supabase (tabla 'asesores') o, si no está conectado,
    desde el CSV asesoresAnclu.csv. Retorna (dict {cedula: nombre}, error)."""
    # 1) Intentar leer desde Supabase
    if cliente is not None:
        try:
            respuesta = cliente.table("asesores").select("cedula,nombre").eq("activo", True).execute()
            datos = respuesta.data or []
            if datos:
                dict_asesores = {str(r["cedula"]).strip(): str(r["nombre"]).strip() for r in datos}
                return dict_asesores, None
        except Exception as e:
            # Si la tabla no existe o falla, caemos al CSV
            motivo = str(e)

    # 2) Fallback al CSV
    try:
        # Buscar el archivo en el mismo directorio del script
        ruta_csv = os.path.join(os.path.dirname(os.path.abspath(__file__)), "asesoresAnclu.csv")
        if not os.path.exists(ruta_csv):
            return None, f"⚠️ No se encontró el archivo: {ruta_csv}"
        
        # sep=None + engine="python": detecta automáticamente el separador
        # (funciona con comas, tabulaciones o punto y coma)
        df = pd.read_csv(ruta_csv, dtype=str, sep=None, engine="python")
        # Normalizar nombres de columnos (quitar espacios, pasar a minúsculas)
        df.columns = df.columns.str.strip().str.lower()
        
        # Detectar columnas: buscar cédula y nombre
        col_cedula = None
        col_nombre = None
        for col in df.columns:
            if "cedula" in col or "cc" == col or "documento" in col or "identificacion" in col:
                col_cedula = col
            if "nombre" in col or "asesor" in col or "vendedor" in col or "completo" in col:
                col_nombre = col
                
        # Protección: si ambas coincidencias cayeron en la misma columna,
        # el separador no fue reconocido correctamente
        if col_cedula == col_nombre or len(df.columns) < 2:
            return None, f"⚠️ No se pudo separar las columnas del CSV. Verifique que 'cedula' y 'nombre' estén separados por coma. Columnas detectadas: {list(df.columns)}"
                
        if col_cedula is None or col_nombre is None:
            return None, f"⚠️ El CSV debe tener columnas de 'cedula' y 'nombre'. Columnas encontradas: {list(df.columns)}"
        
        # Limpiar datos: quitar espacios y puntos de la cédula
        df[col_cedula] = df[col_cedula].astype(str).str.strip().str.replace(".", "", regex=False)
        df[col_nombre] = df[col_nombre].astype(str).str.strip()
        
        # Crear diccionario cedula -> nombre
        dict_asesores = dict(zip(df[col_cedula], df[col_nombre]))
        return dict_asesores, None
    except Exception as e:
        return None, f"⚠️ Error al leer el archivo CSV: {str(e)}"

# ================= CONEXIÓN A SUPABASE =================
@st.cache_resource
def obtener_cliente_supabase():
    """Crea el cliente de Supabase con credenciales de .streamlit/secrets.toml o variables de entorno."""
    try:
        claves_detectadas = list(st.secrets.keys())
    except Exception:
        claves_detectadas = []
    try:
        url = str(st.secrets["supabase"].get("url", "") or "")
        key = str(st.secrets["supabase"].get("key", "") or "")
    except Exception:
        url = os.getenv("SUPABASE_URL", "")
        key = os.getenv("SUPABASE_KEY", "")
    if not url or not key:
        return None, f"sin credenciales. Secciones detectadas en secrets: {claves_detectadas}"
    try:
        return create_client(url, key), None
    except Exception as e:
        return None, f"error al crear el cliente: {e}"

def guardar_venta_supabase(cliente, datos):
    """Inserta la venta en la tabla 'ventas' y retorna (exito, resultado)."""
    try:
        registro = dict(datos)
        fv = registro.get("fecha_venta")
        if isinstance(fv, datetime.date):
            registro["fecha_venta"] = fv.isoformat()
        respuesta = cliente.table(TABLA_VENTAS).insert(registro).execute()
        return True, respuesta.data
    except Exception as e:
        return False, str(e)

def cargar_historial_supabase(cliente, cedula):
    """Descarga las ventas del vendedor desde Supabase y retorna (lista, error)."""
    try:
        query = cliente.table(TABLA_VENTAS).select("*")
        if cedula not in CEDULAS_ADMIN:
            query = query.eq("cedula_vendedor", str(cedula))
        respuesta = query.order("created_at", desc=True).execute()
        ventas = respuesta.data or []
        for venta in ventas:
            fv = venta.get("fecha_venta")
            if isinstance(fv, str):
                try:
                    venta["fecha_venta"] = datetime.date.fromisoformat(fv[:10])
                except ValueError:
                    pass
        return ventas, None
    except Exception as e:
        return [], str(e)

def cargar_meta_supabase(cliente, cedula, periodo):
    """Consulta la meta del vendedor para el periodo (ej. '2026-08').
    Retorna (dict de la meta o None, error)."""
    try:
        respuesta = (
            cliente.table("metas")
            .select("*")
            .eq("cedula_vendedor", str(cedula))
            .eq("periodo", periodo)
            .limit(1)
            .execute()
        )
        datos = respuesta.data or []
        return (datos[0] if datos else None), None
    except Exception as e:
        return None, str(e)

def calcular_avance(datos_historial, hoy):
    """Calcula el avance real del vendedor en el mes indicado (hoy) contra sus metas.
    Reglas:
      - POSPAGO:    ventas tipo 'Postpago'
      - ACCESOS:    ventas 'Hogar' con acceso == 'SI'
      - HOGAR:      ventas tipo 'Hogar' (cada una = 1)
      - TERMINALES: suma de valor_equipo_claro de Kit/Reposicion/Tecnologia
      - CLARO_UP:   conteo de ventas con claro_up activado
    Retorna dict {pospago, accesos, hogar, terminales, claro_up} del mes."""
    avance = {"pospago": 0, "accesos": 0, "hogar": 0, "terminales": 0, "claro_up": 0}
    equipos_tipos = [
        "Kit Contado", "Kit a Cuotas", "Reposicion a Cuotas",
        "Reposicion cargo a la factura", "Reposicion pago Inmediato", "Tecnologia",
    ]
    for venta in datos_historial:
        fv = venta.get("fecha_venta")
        if not isinstance(fv, datetime.date):
            continue
        if fv.year != hoy.year or fv.month != hoy.month:
            continue
        tv = venta.get("tipo_venta")
        if tv == "Postpago":
            avance["pospago"] += 1
        elif tv == "Hogar":
            avance["hogar"] += 1
            if venta.get("acceso") == "SI":
                avance["accesos"] += 1
        elif tv in equipos_tipos:
            try:
                avance["terminales"] += float(venta.get("valor_equipo_claro") or 0)
            except (TypeError, ValueError):
                pass
        if venta.get("claro_up") is True or str(venta.get("claro_up")).lower() == "true":
            avance["claro_up"] += 1
    return avance

def calcular_avance_por_asesor(datos_historial, hoy):
    """Agrupa el avance del mes por cedula_vendedor.
    Retorna dict {cedula: {pospago, accesos, hogar, terminales, claro_up}}."""
    resultados = {}
    equipos_tipos = [
        "Kit Contado", "Kit a Cuotas", "Reposicion a Cuotas",
        "Reposicion cargo a la factura", "Reposicion pago Inmediato", "Tecnologia",
    ]
    for venta in datos_historial:
        fv = venta.get("fecha_venta")
        if not isinstance(fv, datetime.date):
            continue
        if fv.year != hoy.year or fv.month != hoy.month:
            continue
        cedula = str(venta.get("cedula_vendedor") or "DESCONOCIDO").strip()
        acc = resultados.setdefault(cedula, {"pospago": 0, "accesos": 0, "hogar": 0, "terminales": 0, "claro_up": 0})
        tv = venta.get("tipo_venta")
        if tv == "Postpago":
            acc["pospago"] += 1
        elif tv == "Hogar":
            acc["hogar"] += 1
            if venta.get("acceso") == "SI":
                acc["accesos"] += 1
        elif tv in equipos_tipos:
            try:
                acc["terminales"] += float(venta.get("valor_equipo_claro") or 0)
            except (TypeError, ValueError):
                pass
        if venta.get("claro_up") is True or str(venta.get("claro_up")).lower() == "true":
            acc["claro_up"] += 1
    return resultados

def cargar_todas_metas_supabase(cliente, periodo):
    """Consulta todas las metas del periodo indicado. Retorna (lista, error)."""
    try:
        respuesta = (
            cliente.table("metas")
            .select("*")
            .eq("periodo", periodo)
            .execute()
        )
        return (respuesta.data or []), None
    except Exception as e:
        return [], str(e)



# ================= CONFIGURACIÓN DE PÁGINA =================
st.set_page_config(page_title="Gestión de Ventas", layout="wide", page_icon="🔴")

# ================= CSS PERSONALIZADO =================
st.markdown("""
<style>
.stApp {
    background-color: #FFFFFF;
}

h1, h2, h3 {
    color: #DA291C !important; 
    font-family: 'Arial', sans-serif;
    font-weight: 700 !important;
}

.stButton > button[kind="primary"] {
    background-color: #DA291C !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 6px !important;
    font-weight: bold !important;
    padding: 10px 24px !important;
    transition: all 0.3s ease;
}

.stButton > button[kind="primary"]:hover {
    background-color: #000000 !important; 
    color: #FFFFFF !important;
    transform: scale(1.02);
}

.stTabs [data-baseweb="tab-list"] {
    border-bottom: 2px solid #E0E0E0;
}
.stTabs [data-baseweb="tab"] {
    color: #000000;
    font-weight: 600;
}
.stTabs [aria-selected="true"] {
    background-color: #DA291C !important;
    color: #FFFFFF !important;
    border-radius: 4px 4px 0px 0px;
}

hr {
    border-top: 2px solid #DA291C !important;
}
.stAlert {
    background-color: #F8F9FA !important;
    border-left: 5px solid #DA291C !important;
    color: #000000 !important;
}

.login-container {
    max-width: 450px;
    margin: 0 auto;
    padding: 40px;
    border: 2px solid #DA291C;
    border-radius: 12px;
    background-color: #FAFAFA;
}
.login-title {
    text-align: center;
    color: #DA291C;
    font-size: 28px;
    font-weight: bold;
    margin-bottom: 10px;
}
.login-subtitle {
    text-align: center;
    color: #666;
    font-size: 14px;
    margin-bottom: 30px;
}
.user-badge {
    background-color: #DA291C;
    color: white;
    padding: 8px 16px;
    border-radius: 20px;
    font-size: 14px;
    display: inline-block;
    margin-bottom: 15px;
}
.pdv-selector-container {
    max-width: 500px;
    margin: 0 auto;
    padding: 40px;
    border: 2px solid #DA291C;
    border-radius: 12px;
    background-color: #FAFAFA;
}
.nombre-vendedor {
    text-align: center;
    color: #DA291C;
    font-size: 22px;
    font-weight: bold;
    margin: 15px 0;
    padding: 12px;
    background-color: #FFF0EF; 
    border-radius: 8px;
    border: 1px solid #DA291C;
}
.csv-error {
    background-color: #FFF3CD;
    border: 1px solid #FFC107;
    color: #856404;
    padding: 15px;
    border-radius: 8px;
    margin-bottom: 20px;
    text-align: center;
}
</style>
""", unsafe_allow_html=True)

# ================= CARGAR ASESORES Y CONEXIÓN =================
supabase, motivo_supabase = obtener_cliente_supabase()
dict_asesores, error_csv = cargar_asesores(cliente=supabase)

# ================= ESTADO DE LA SESIÓN =================
if "form_key" not in st.session_state:
    st.session_state.form_key = 0
if "historial_temporal" not in st.session_state:
    st.session_state.historial_temporal = []
if "usuario_logueado" not in st.session_state:
    st.session_state.usuario_logueado = None
if "nombre_vendedor" not in st.session_state:
    st.session_state.nombre_vendedor = None
if "pdv_seleccionado" not in st.session_state:
    st.session_state.pdv_seleccionado = None

# ================= DATOS DE EJEMPLO (PDVs) =================
pdv_disponibles = {
    "ARCA": "ARCABUCO",
    "COOS": "COOSERVICIOS",
    "GACH": "GACHANTIVA",
    "GARA": "GARAGOA",
    "MIRA":"MIRAFLORES",
    "MUIS":"MUISCAS",
    "NOBS":"NOBSA",
    "OTAN":"OTANCHE",
    "PRIN":"PRINCIPAL",
    "QUIP":"QUIPAMA",
    "RAQU":"RAQUIRA",
    "SAMA":"SAMACA",
    "SOGA":"SOGAMOSO",
    "STAS":"SANTA SOFIA",
    "TIBA":"TIBANA",
    "TOCA":"TOCA",
    "TUTA":"TUTA",
    "VILL":"VILLA DE LEYVA"
    
}

# ================= PANTALLA 1: LOGIN =================
if st.session_state.usuario_logueado is None:
    st.markdown("<div style='height: 80px;'></div>", unsafe_allow_html=True)
    
    # Mostrar error del CSV si existe
    if error_csv:
        st.markdown(f'<div class="csv-error">{error_csv}</div>', unsafe_allow_html=True)
        st.stop()
        
    st.markdown("""
    <div class="login-container">
        <div class="login-title">🔴 Data Center Colombia</div>
        <div class="login-subtitle">Portal de Gestión Comercial<br>Ingrese su cédula para continuar</div>
    </div>
    """, unsafe_allow_html=True)
    
    with st.form("login_form"):
        cedula = st.text_input(
            "Número de Cédula del Vendedor", 
            placeholder="Ej: 1098765432",
            max_chars=15,
            key="cedula_login"
        )
        col_btn, col_spacer = st.columns([1, 1])
        with col_btn:
            submit_login = st.form_submit_button("🔑 Ingresar al Sistema", type="primary", use_container_width=True)
            
        if submit_login:
            if not cedula:
                st.error("⚠️ La cédula es obligatoria")
            elif not cedula.isdigit():
                st.error("⚠️ La cédula solo debe contener números")
            elif len(cedula) < 6:
                st.error("⚠️ Ingrese una cédula válida (mínimo 6 dígitos)")
            elif cedula not in dict_asesores:
                st.error(f"❌ La cédula **{cedula}** no está registrada como vendedor activo. Verifique e intente de nuevo.")
            else:
                st.session_state.usuario_logueado = cedula
                st.session_state.nombre_vendedor = dict_asesores[cedula]
                st.rerun()
    st.stop()

# ================= PANTALLA 2: SELECCIÓN DE PDV =================
if st.session_state.pdv_seleccionado is None:
    st.markdown("<div style='height: 50px;'></div>", unsafe_allow_html=True)
    st.markdown("""
    <div class="pdv-selector-container">
        <div class="login-title">📍 Selección de PDV</div>
        <div class="login-subtitle">Seleccione el punto de venta donde realizará la operación</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Mostrar el nombre del vendedor
    st.markdown(f"""
    <div class="nombre-vendedor">
        👤 Vendedor: {st.session_state.nombre_vendedor}
        <br><span style="font-size:14px; color:#666; font-weight:normal;">Cédula: {st.session_state.usuario_logueado}</span>
    </div>
    """, unsafe_allow_html=True)
    
    pdv_seleccion = st.selectbox(
        "Punto de Venta",
        options=list(pdv_disponibles.keys()),
        format_func=lambda x: pdv_disponibles[x],
        key="pdv_selector"
    )
    
    col_btn1, col_btn2 = st.columns([1, 1])
    with col_btn1:
        if st.button("✅ Continuar", type="primary", use_container_width=True):
            st.session_state.pdv_seleccionado = pdv_seleccion
            st.rerun()
    with col_btn2:
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            st.session_state.usuario_logueado = None
            st.session_state.nombre_vendedor = None
            st.rerun()
    st.stop()

# ================= BARRA DE INFORMACIÓN DEL USUARIO =================
col_info1, col_info2, col_info3 = st.columns([2, 2, 1])
with col_info1:
    st.markdown(f'<span class="user-badge">👤 {st.session_state.nombre_vendedor} (CC: {st.session_state.usuario_logueado})</span>', unsafe_allow_html=True)
with col_info2:
    st.markdown(f'<span class="user-badge">📍 PDV: {st.session_state.pdv_seleccionado} - {pdv_disponibles[st.session_state.pdv_seleccionado]}</span>', unsafe_allow_html=True)
with col_info3:
    if st.button("🚪 Salir", use_container_width=True):
        st.session_state.usuario_logueado = None
        st.session_state.nombre_vendedor = None
        st.session_state.pdv_seleccionado = None
        st.rerun()

st.markdown("<hr>", unsafe_allow_html=True)

if supabase is None:
    st.warning(
        "⚠️ **Supabase no configurado.** Edite `.streamlit/secrets.toml` con la URL y la anon key de su proyecto. "
        "Las ventas se guardarán solo en memoria y se perderán al cerrar la app.\n\n"
        f"Motivo: `{motivo_supabase}`"
    )

# ================= ESTRUCTURA DE PESTAÑAS =================
st.title("📋 Portal de Gestión Comercial")
tab_registro, tab_historial = st.tabs(["📝 Registrar Nueva Venta", "📜 Historial de Operaciones"])

# ================= PESTAÑA 1: REGISTRO =================
with tab_registro:
    fk = st.session_state.form_key
    datos_guardar = {}
    
    # Guardar automáticamente el usuario, nombre y PDV
    datos_guardar["cedula_vendedor"] = st.session_state.usuario_logueado
    datos_guardar["nombre_vendedor"] = st.session_state.nombre_vendedor
    datos_guardar["punto_venta"] = st.session_state.pdv_seleccionado
    
    # --- SECCIÓN 1: DATOS DE VENTA ---
    with st.container(border=True):
        st.subheader("1. DATOS DE LA VENTA")
        col1, col2 = st.columns(2)
        with col1:
            datos_guardar["fecha_venta"] = st.date_input("Fecha de la venta", datetime.date.today(), key=f"fecha_{fk}")
        with col2:
            st.text_input(
                "Punto de Venta (Seleccionado)", 
                value=f"{st.session_state.pdv_seleccionado} - {pdv_disponibles[st.session_state.pdv_seleccionado]}", 
                disabled=True,
                key=f"pdv_readonly_{fk}"
            )
            cambiar_pdv = st.checkbox("¿Cambiar de PDV para esta venta?", key=f"cambiar_pdv_{fk}")
            if cambiar_pdv:
                nuevo_pdv = st.selectbox(
                    "Seleccionar otro PDV",
                    options=list(pdv_disponibles.keys()),
                    format_func=lambda x: pdv_disponibles[x],
                    key=f"nuevo_pdv_{fk}"
                )
                datos_guardar["punto_venta"] = nuevo_pdv
                
    # --- SECCIÓN 2: DATOS DEL CLIENTE ---
    with st.container(border=True):
        st.subheader("2. DATOS DEL CLIENTE")
        col1, col2, col3 = st.columns(3)
        with col1:
            datos_guardar["nombre_cliente"] = st.text_input("Nombre Completo", key=f"nom_cli_{fk}")
            datos_guardar["tipo_documento"] = st.selectbox("Tipo de Documento", ["CC", "CE", "NIT", "Pasaporte", "PPT"], key=f"tdoc_{fk}")
            datos_guardar["contacto_cliente"] = st.text_input("Teléfono de Contacto", key=f"tel_{fk}")
        with col2:
            datos_guardar["nro_documento"] = st.text_input("Nro. de Documento", key=f"ndoc_{fk}")
            datos_guardar["direccion"] = st.text_input("Dirección de Residencia", key=f"dir_{fk}")
            datos_guardar["cliente_convergente"] = st.selectbox("¿Es Cliente Convergente?", ["Sí", "No"], key=f"conv_{fk}")
        with col3:
            datos_guardar["correo"] = st.text_input("Correo Electrónico", key=f"correo_{fk}", placeholder="Ej: nombre@dominio.com")
            if datos_guardar["correo"]:
                es_valido, msg_error = validar_formato_correo(datos_guardar["correo"])
                if not es_valido:
                    st.error(f"**Correo Electrónico:** {msg_error}")
            datos_guardar["servicios_adicionales"] = st.text_input("Servicios Adicionales Ofrecidos", key=f"serv_ad_{fk}")
            datos_guardar["observaciones"] = st.text_area("Observaciones", height=68, key=f"obs_{fk}")
            
        st.markdown("<br>", unsafe_allow_html=True)
        tipo_venta = st.selectbox(
            "📍 TIPO DE TRANSACCIÓN", 
            ["Postpago", "Kit Contado", "Kit a Cuotas", "Reposicion a Cuotas", "Reposicion cargo a la factura", "Reposicion pago Inmediato", "Tecnologia", "Hogar", "Sim card"],
            index=None,
            placeholder="Seleccione el producto para desplegar los campos correspondientes...",
            key=f"tventa_{fk}"
        )
        datos_guardar["tipo_venta"] = tipo_venta
        
    # Inicializar campos opcionales (Se agregaron tramite y paquete_bienvenida)
    campos_opcionales = [
        "referencia", "imei", "iccid", "min", 
        "valor_equipo_claro", "valor_descuento", "valor_equipo", 
        "valor_pagado_cliente", "financiado", "financiera", "valor_credito",
        "plan", "tipo_plan", "valor_plan",
        "ciudad", "indicaciones", "estrato", "campana", "servicios", "renta", "instalacion", "cuenta", "acceso",
        "tramite", "paquete_bienvenida","claro_up","valor_claro_up"
    ]
    for campo in campos_opcionales:
        datos_guardar[campo] = False if campo == "claro_up" else None
        
    # --- SECCIÓN 3: DETALLES DEL EQUIPO (Se quitó "Sim card" de esta lista) ---
    if tipo_venta in ["Kit Contado", "Kit a Cuotas", "Reposicion a Cuotas", "Reposicion cargo a la factura", "Reposicion pago Inmediato","Tecnologia"]:
        with st.container(border=True):
            st.subheader("3. DETALLES DEL EQUIPO")
            col1, col2, col3 = st.columns(3)
            with col1:
                datos_guardar["referencia"] = st.text_input("Referencia del Equipo", key=f"ref_{fk}")
            with col2:
                datos_guardar["imei"] = st.text_input(
                    "IMEI", 
                    key=f"imei_{fk}", 
                    max_chars=15, 
                    placeholder="Ej: 356938035643809 (15 dígitos)"
                )
                if datos_guardar["imei"]:
                    es_valido, msg_error = validar_campo_numerico(datos_guardar["imei"], 15)
                    if msg_error:
                        st.error(f"**IMEI:** {msg_error}")
            with col3:
                datos_guardar["iccid"] = st.text_input(
                    "ICCID",
                    key=f"iccid_{fk}",
                    max_chars=17,
                    placeholder="Máximo 17 dígitos"
                )
                if datos_guardar["iccid"]:
                    es_valido, msg_error = validar_campo_numerico(datos_guardar["iccid"], 17)
                    if msg_error:
                        st.error(f"**ICCID:** {msg_error}")
            st.markdown("<br>", unsafe_allow_html=True)
            col4, col5, col6 = st.columns(3)
            with col4:
                datos_guardar["min"] = st.text_input(
                    "MIN", 
                    key=f"min_{fk}", 
                    max_chars=10, 
                    placeholder="Ej: 3001234567 (10 dígitos)"
                )
                if datos_guardar["min"]:
                    es_valido, msg_error = validar_campo_numerico(datos_guardar["min"], 10)
                    if msg_error:
                        st.error(f"**MIN:** {msg_error}")
            with col5:
                datos_guardar["valor_equipo_claro"] = st.number_input("Valor del Equipo Claro ($)", min_value=0, step=1000, key=f"veq_claro_{fk}")
            with col6:
                datos_guardar["valor_descuento"] = st.number_input("Valor Descuento ($)", min_value=0, step=1000, key=f"vdesc_{fk}")
            st.markdown("<br>", unsafe_allow_html=True)
            col7, col8, col9 = st.columns(3)
            with col7:
                valor_total = datos_guardar["valor_equipo_claro"] - datos_guardar["valor_descuento"]
                datos_guardar["valor_equipo"] = valor_total
                st.number_input("Valor Total Equipo ($)", value=valor_total, disabled=True, help="Se calcula automáticamente: Valor Equipo Claro - Valor Descuento", key=f"veq_total_{fk}")
            with col8:
                datos_guardar["valor_pagado_cliente"] = st.number_input("Valor Pagado por el Cliente ($)", min_value=0, step=1000, key=f"vpagado_{fk}")
            with col9:
                datos_guardar["financiado"] = st.selectbox("¿Financiado?", ["NO", "SI"], key=f"financiado_{fk}")
                
            if datos_guardar["financiado"] == "SI":
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown("---")
                st.markdown("#### 💳 Datos de Financiación")
                col_fin1, col_fin2 = st.columns(2)
                with col_fin1:
                    datos_guardar["financiera"] = st.selectbox("Entidad Financiera", ["Claro", "Addi", "Celya", "Krediya","Credismart","Vanti","Alo Credit","Payjoy"], key=f"fin_{fk}")
                with col_fin2:
                    datos_guardar["valor_credito"] = st.number_input("Valor Crédito ($)", min_value=0, step=1000, key=f"vcredito_{fk}")
                    
            if tipo_venta in ["Reposicion a Cuotas", "Reposicion cargo a la factura", "Reposicion pago Inmediato"]:
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown("---")
                st.markdown("#### 🚀 Claro Up")
                datos_guardar["claro_up"] = st.checkbox("¿Claro Up?", key=f"claro_up_{fk}")
                if datos_guardar["claro_up"]:
                    datos_guardar["valor_claro_up"] = st.number_input("Valor Claro Up ($)", min_value=0, step=1000, key=f"valor_claro_up_{fk}")
                    
    # --- NUEVA SECCIÓN: DETALLE SIM (Solo para Sim card) ---
    elif tipo_venta == "Sim card":
        with st.container(border=True):
            st.subheader("3. DETALLE SIM")
            col1, col2 = st.columns(2)
            with col1:
                datos_guardar["iccid"] = st.text_input(
                    "ICCID",
                    key=f"iccid_{fk}",
                    max_chars=17,
                    placeholder="Máximo 17 dígitos"
                )
                if datos_guardar["iccid"]:
                    es_valido, msg_error = validar_campo_numerico(datos_guardar["iccid"], 17)
                    if msg_error:
                        st.error(f"**ICCID:** {msg_error}")
                datos_guardar["valor_equipo_claro"] = st.number_input(
                    "Valor del Equipo Claro ($)", 
                    min_value=0, 
                    step=1000,
                    key=f"veq_claro_{fk}"
                )
            with col2:
                datos_guardar["tramite"] = st.selectbox(
                    "Trámite", 
                    ["Repo de sim", "Wellcome back"], 
                    key=f"tramite_{fk}"
                )
                datos_guardar["paquete_bienvenida"] = st.selectbox(
                    "Paquete de Bienvenida", 
                    ["Sí", "No"], 
                    key=f"paq_bien_{fk}"
                )

    elif tipo_venta == "Postpago":
        with st.container(border=True):
            st.subheader("4. DESCRIPCIÓN DEL PLAN")
            col1, col2, col3, col4, col5 = st.columns(5)
            with col1:
                datos_guardar["plan"] = st.text_input("Nombre del Plan", key=f"plan_{fk}")
            with col2:
                datos_guardar["tipo_plan"] = st.selectbox("Tipo de Plan", ["Linea Nueva", "Migración", "Portabilidad"], key=f"tplan_{fk}")
            with col3:
                datos_guardar["valor_plan"] = st.number_input("Valor Mensual ($)", min_value=0.0, key=f"vplan_{fk}")
            with col4:
                datos_guardar["valor_pagado_cliente"] = st.number_input(
                    "Valor Pagado Cliente ($)",
                    min_value=0.0,
                    step=1000.0,
                    key=f"vpagado_post_{fk}",
                    help="Valor que efectivamente paga el cliente (después de descuentos en el plan)."
                )
            with col5:
                equipo_nuevo = st.selectbox("Equipo Nuevo", ["NO", "SI"], key=f"equipo_nuevo_{fk}")
            if equipo_nuevo == "SI":
                st.markdown("---")
                st.markdown("#### 📱 Datos del Equipo Nuevo")
                eq_col1, eq_col2, eq_col3, eq_col4 = st.columns(4)
                with eq_col1:
                    datos_guardar["referencia"] = st.text_input("Referencia del Equipo", key=f"ref_{fk}")
                with eq_col2:
                    datos_guardar["imei"] = st.text_input(
                        "IMEI",
                        key=f"imei_{fk}",
                        max_chars=15,
                        placeholder="Ej: 356938035643809 (15 dígitos)"
                    )
                    if datos_guardar["imei"]:
                        es_valido, msg_error = validar_campo_numerico(datos_guardar["imei"], 15)
                        if msg_error:
                            st.error(f"**IMEI:** {msg_error}")
                with eq_col3:
                    datos_guardar["iccid"] = st.text_input(
                        "ICCID",
                        key=f"iccid_{fk}",
                        max_chars=17,
                        placeholder="Máximo 17 dígitos"
                    )
                    if datos_guardar["iccid"]:
                        es_valido, msg_error = validar_campo_numerico(datos_guardar["iccid"], 17)
                        if msg_error:
                            st.error(f"**ICCID:** {msg_error}")
                with eq_col4:
                    datos_guardar["valor_equipo_claro"] = st.number_input(
                        "Valor del Equipo ($)",
                        min_value=0,
                        step=1000,
                        key=f"valor_equipo_post_{fk}"
                    )
                total_postpago = float(datos_guardar.get("valor_equipo_claro") or 0) + float(datos_guardar.get("valor_plan") or 0)
                st.markdown(
                    f"### 💰 Total (Equipo + Plan): <span style='color:#DA291C'>${total_postpago:,.0f}</span>",
                    unsafe_allow_html=True,
                )
                
    elif tipo_venta in ["Hogar"]:
        with st.container(border=True):
            st.subheader("5. SERVICIOS FIJOS")
            col1, col2, col3 = st.columns(3)
            with col1:
                datos_guardar["ciudad"] = st.text_input("Ciudad de Instalación", key=f"ciu_{fk}")
                datos_guardar["estrato"] = st.selectbox("Estrato", ["1", "2", "3", "4", "5", "6", "Comercial"], key=f"est_{fk}")
                datos_guardar["renta"] = st.number_input("Valor Renta ($)", min_value=0, key=f"renta_{fk}")
            with col2:
                datos_guardar["indicaciones"] = st.text_area("Indicaciones (Cómo llegar)", height=68, key=f"ind_{fk}")
                datos_guardar["instalacion"] = st.number_input("Costo Instalación ($)", min_value=0, key=f"inst_{fk}")
                datos_guardar["campana"] = st.text_input("Campaña Asociada", key=f"camp_{fk}")
            with col3:                
                datos_guardar["servicios"] = st.selectbox("Servicios Contratados", ["Triple", "Doble", "Sencillo"], key=f"serv_fijo_{fk}")
                datos_guardar["cuenta"] = st.text_input("Número de Cuenta", key=f"cta_{fk}")
                datos_guardar["acceso"] = st.selectbox("Acceso", ["SI", "NO"], key=f"acc_{fk}")
                
    # --- SECCIÓN 6: REFERIDOS ---
    with st.container(border=True):
        st.subheader("6. PROGRAMA DE REFERIDOS")
        col1, col2, col3 = st.columns(3)
        with col1:
            datos_guardar["producto_referido"] = st.text_input("Producto de interés", key=f"pref_{fk}")
        with col2:
            datos_guardar["nombre_referido"] = st.text_input("Nombre del Referido", key=f"nref_{fk}")
        with col3:
            datos_guardar["cel_referido"] = st.text_input(
                "Celular del Referido", 
                key=f"cel_referido_{fk}", 
                max_chars=10, 
                placeholder="Ej: 3001234567 (10 dígitos)"
            )
            if datos_guardar["cel_referido"]:
                es_valido, msg_error = validar_campo_numerico(datos_guardar["cel_referido"], 10)
                if msg_error: 
                    st.error(f"**Celular Referido:** {msg_error}")
            st.markdown("<br>", unsafe_allow_html=True)
            
    # --- BOTÓN DE GUARDAR ---
    st.markdown("<br>", unsafe_allow_html=True)

    def registrar_venta():
        if supabase is not None:
            exito, resultado = guardar_venta_supabase(supabase, datos_guardar)
            if not exito:
                st.error(f"❌ Error al guardar en la base de datos: {resultado}")
                return
        else:
            st.session_state.historial_temporal.append(datos_guardar)
        st.success(f"✅ ¡Venta registrada exitosamente! Vendedor: {st.session_state.nombre_vendedor}")
        st.session_state.form_key += 1
        st.rerun()

    if st.button("💾 REGISTRAR VENTA", use_container_width=True, type="primary"):
        if not tipo_venta:
            st.error("⚠️ Es obligatorio seleccionar el **TIPO DE TRANSACCIÓN** (Sección 2) para guardar el registro.")
        elif datos_guardar.get("financiado") == "SI":
            if not datos_guardar.get("financiera"):
                st.error("⚠️ Si la venta es financiada, debe seleccionar la **Entidad Financiera**.")
            elif not datos_guardar.get("valor_credito") or datos_guardar["valor_credito"] <= 0:
                st.error("⚠️ Si la venta es financiada, debe ingresar el **Valor del Crédito**.")
            else:
                registrar_venta()
        else:
            registrar_venta()

# ================= PESTAÑA 2: HISTORIAL =================
with tab_historial:
    st.subheader("📜 Mi Historial de Operaciones")
    if st.session_state.usuario_logueado in CEDULAS_ADMIN:
        st.caption("👑 Modo Administrador: Mostrando TODAS las ventas de todos los vendedores.")
    else:
        st.caption(f"Mostrando únicamente las ventas de: {st.session_state.nombre_vendedor} (CC: {st.session_state.usuario_logueado})")
    
    if supabase is not None:
        ventas_db, error_db = cargar_historial_supabase(supabase, st.session_state.usuario_logueado)
        if error_db:
            st.error(f"❌ Error al consultar el historial en Supabase: {error_db}")
            ventas_db = []
    else:
        ventas_db = st.session_state.historial_temporal

    if st.session_state.usuario_logueado in CEDULAS_ADMIN:
        datos_historial = ventas_db
    else:
        datos_historial = [
            venta for venta in ventas_db
            if venta.get("cedula_vendedor") == st.session_state.usuario_logueado
        ]
    
    # ================= RESUMEN DEL MES ACTUAL POR TIPO DE TRANSACCIÓN =================
    hoy = datetime.date.today()
    st.markdown("---")
    st.subheader(f"📊 Resumen de Ventas - {hoy.strftime('%B %Y').capitalize()}")
    tipos_del_mes = [
        venta.get("tipo_venta") for venta in datos_historial
        if isinstance(venta.get("fecha_venta"), datetime.date)
        and venta["fecha_venta"].year == hoy.year
        and venta["fecha_venta"].month == hoy.month
        and venta.get("tipo_venta")
    ]
    
    if tipos_del_mes:
        df_resumen = (
            pd.DataFrame({"Tipo de Transacción": tipos_del_mes})
            .groupby("Tipo de Transacción")
            .size()
            .reset_index(name="Ventas del Mes")
            .sort_values("Ventas del Mes", ascending=False, ignore_index=True)
        )
        total_mes = int(df_resumen["Ventas del Mes"].sum())
        fila_total = pd.DataFrame(
            [{"Tipo de Transacción": "TOTAL", "Ventas del Mes": total_mes}]
        )
        df_resumen = pd.concat([df_resumen, fila_total], ignore_index=True)
        
        col_res1, col_res2 = st.columns(2)
        with col_res1:
            st.markdown("**Resumen por Tipo de Transacción**")
            st.dataframe(df_resumen, use_container_width=True, hide_index=True)
            st.metric(label="Total Ventas del Mes", value=total_mes)
        with col_res2:
            st.markdown("**Ventas por Asesor y Tipo**")
            ventas_mes = [
                v for v in datos_historial
                if isinstance(v.get("fecha_venta"), datetime.date)
                and v["fecha_venta"].year == hoy.year
                and v["fecha_venta"].month == hoy.month
                and v.get("tipo_venta") and v.get("nombre_vendedor")
            ]
            if ventas_mes:
                df_pivot = pd.crosstab(
                    index=pd.Series([v["nombre_vendedor"] for v in ventas_mes]),
                    columns=pd.Series([v["tipo_venta"] for v in ventas_mes]),
                    margins=True,
                    margins_name="TOTAL"
                )
                df_pivot.index.name = "Asesor"
                df_pivot.columns.name = None
                st.dataframe(df_pivot, use_container_width=True)
    else:
        st.info("📭 Aún no tiene ventas registradas en el mes actual.")

    # ================= MIS METAS DEL MES =================
    periodo_actual = hoy.strftime("%Y-%m")
    if supabase is not None:
        meta_vendedor, error_meta = cargar_meta_supabase(
            supabase, st.session_state.usuario_logueado, periodo_actual
        )
        if error_meta:
            meta_vendedor = None
    else:
        meta_vendedor = None

    es_admin = st.session_state.usuario_logueado in CEDULAS_ADMIN

    if meta_vendedor or es_admin:
        avance = calcular_avance(datos_historial, hoy)

        def mostrar_meta(label, avance_val, meta_val, es_dinero=False):
            if meta_val <= 0:
                return
            pct = (avance_val / meta_val * 100) if meta_val else 0
            pct = max(0, min(100, pct))
            meta_str = f"${meta_val:,.0f}" if es_dinero else f"{int(meta_val)}"
            av_str = f"${avance_val:,.0f}" if es_dinero else f"{int(avance_val)}"
            color = "#2ECC71" if pct >= 100 else ("#F39C12" if pct >= 50 else "#E74C3C")
            st.markdown(
                f"<div style='display:flex;justify-content:space-between;'>"
                f"<b>{label}</b><span><b style='color:{color}'>{av_str}</b> / {meta_str} ({pct:.0f}%)</span></div>",
                unsafe_allow_html=True,
            )
            st.progress(pct / 100)

        st.markdown("---")
        if not st.session_state.usuario_logueado in CEDULAS_ADMIN:
            st.subheader("🎯 Mis Metas del Mes")
            st.caption(f"Meta vigente en {periodo_actual} para: {st.session_state.nombre_vendedor}")
            with st.container(border=True):
                c1, c2 = st.columns(2)
                with c1:
                    mostrar_meta("Postpago", avance["pospago"], float(meta_vendedor.get("pospago") or 0))
                    mostrar_meta("Accesos", avance["accesos"], float(meta_vendedor.get("accesos") or 0))
                    mostrar_meta("Claro Up", avance["claro_up"], float(meta_vendedor.get("claro_up") or 0))
                with c2:
                    mostrar_meta("Hogar", avance["hogar"], float(meta_vendedor.get("hogar") or 0))
                    mostrar_meta("Terminales", avance["terminales"], float(meta_vendedor.get("terminales") or 0), es_dinero=True)
        else:
            # ===== VISTA ADMINISTRADOR: metas de todos los asesores =====
            meta_vendedor = None
            metas_todas, error_metas = cargar_todas_metas_supabase(supabase, periodo_actual)
            if error_metas:
                st.error(f"❌ Error al consultar las metas: {error_metas}")
                metas_todas = []
            if metas_todas:
                avance_por_asesor = calcular_avance_por_asesor(datos_historial, hoy)

                # --- Tabla numérica consolidada ---
                filas = []
                for m in metas_todas:
                    cedula = str(m.get("cedula_vendedor") or "").strip()
                    nombre = dict_asesores.get(cedula, cedula)
                    av = avance_por_asesor.get(cedula, {"pospago": 0, "accesos": 0, "hogar": 0, "terminales": 0, "claro_up": 0})
                    
                    def celda(avv, mv, es_dinero=False):
                        if mv <= 0:
                            return "—"
                        pct = (avv / mv * 100) if mv else 0
                        fmt = lambda x: f"${x:,.0f}" if es_dinero else f"{int(x)}"
                        return f"{fmt(avv)}/{fmt(mv)} ({pct:.0f}%)"
                    
                    filas.append({
                        "Asesor": nombre,
                        "Cédula": cedula,
                        "Postpago": celda(av["pospago"], float(m.get("pospago") or 0)),
                        "Hogar": celda(av["hogar"], float(m.get("hogar") or 0)),
                        "Accesos": celda(av["accesos"], float(m.get("accesos") or 0)),
                        "Terminales": celda(av["terminales"], float(m.get("terminales") or 0), es_dinero=True),
                        "Claro Up": celda(av["claro_up"], float(m.get("claro_up") or 0)),
                    })
                df_metas = pd.DataFrame(filas)

                st.markdown("### 🎯 Metas del Mes - Todos los Asesores")
                st.caption(f"Avance / Meta ({periodo_actual})")
                st.dataframe(df_metas, use_container_width=True, hide_index=True)
                csv_metas = df_metas.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Exportar Metas (CSV)",
                    data=csv_metas,
                    file_name=f"metas_{periodo_actual}.csv",
                    mime="text/csv",
                )

                # --- Tarjetas con barra de progreso por asesor ---
                st.markdown("#### Progreso por Asesor")
                for m in metas_todas:
                    cedula = str(m.get("cedula_vendedor") or "").strip()
                    nombre = dict_asesores.get(cedula, cedula)
                    av = avance_por_asesor.get(cedula, {"pospago": 0, "accesos": 0, "hogar": 0, "terminales": 0, "claro_up": 0})
                    st.markdown(f"<b>{nombre} (CC: {cedula})</b>", unsafe_allow_html=True)
                    with st.container(border=True):
                        c1, c2 = st.columns(2)
                        with c1:
                            mostrar_meta("Postpago", av["pospago"], float(m.get("pospago") or 0))
                            mostrar_meta("Accesos", av["accesos"], float(m.get("accesos") or 0))
                            mostrar_meta("Claro Up", av["claro_up"], float(m.get("claro_up") or 0))
                        with c2:
                            mostrar_meta("Hogar", av["hogar"], float(m.get("hogar") or 0))
                            mostrar_meta("Terminales", av["terminales"], float(m.get("terminales") or 0), es_dinero=True)
            else:
                st.info("📭 Aún no hay metas cargadas para este mes.")

    st.markdown("---")
    
    if not datos_historial:
        st.info("📭 No tiene ventas registradas aún. Vaya a la pestaña 'Registrar Nueva Venta' para comenzar.")
    else:
        df_historial = pd.DataFrame(datos_historial)
        with st.container(border=True):
            st.markdown("**Filtros Disponibles**")
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                tipos_disponibles = df_historial["tipo_venta"].dropna().unique().tolist()
                if tipos_disponibles:
                    filtro_tipo = st.multiselect("🔍 Filtrar por Tipo de Venta", options=tipos_disponibles)
                else:
                    filtro_tipo = []
            with col_f2:
                pdv_disponibles_filtro = df_historial["punto_venta"].dropna().unique().tolist()
                if pdv_disponibles_filtro:
                    filtro_pdv = st.multiselect("🔍 Filtrar por PDV", options=pdv_disponibles_filtro)
                else:
                    filtro_pdv = []
                    
            if filtro_tipo:
                df_historial = df_historial[df_historial["tipo_venta"].isin(filtro_tipo)]
            if filtro_pdv:
                df_historial = df_historial[df_historial["punto_venta"].isin(filtro_pdv)]
                
            st.markdown(f"**Total de registros encontrados:** {len(df_historial)}")
            st.dataframe(df_historial, use_container_width=True, hide_index=True)
            
            csv = df_historial.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Exportar Mi Reporte (CSV)",
                data=csv,
                file_name=f"reporte_ventas_{st.session_state.usuario_logueado}_{datetime.date.today()}.csv",
                mime="text/csv",
            )
