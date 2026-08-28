import re
import streamlit as st
import datetime
import pandas as pd
import os
from supabase import create_client

TABLA_VENTAS = "ventas"
CEDULAS_ADMIN = ["94458575", "1746215"]

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

def cargar_asesores():
    """Carga el archivo CSV de asesores y retorna un diccionario {cedula: nombre}"""
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
dict_asesores, error_csv = cargar_asesores()
supabase, motivo_supabase = obtener_cliente_supabase()

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
    "SAMA":"SAMACA",
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
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                datos_guardar["plan"] = st.text_input("Nombre del Plan", key=f"plan_{fk}")
            with col2:
                datos_guardar["tipo_plan"] = st.selectbox("Tipo de Plan", ["Linea Nueva", "Migración", "Portabilidad"], key=f"tplan_{fk}")
            with col3:
                datos_guardar["valor_plan"] = st.number_input("Valor Mensual ($)", min_value=0.0, key=f"vplan_{fk}")
            with col4:
                equipo_nuevo = st.selectbox("Equipo Nuevo", ["NO", "SI"], key=f"equipo_nuevo_{fk}")
            if equipo_nuevo == "SI":
                st.markdown("---")
                st.markdown("#### 📱 Datos del Equipo Nuevo")
                eq_col1, eq_col2, eq_col3 = st.columns(3)
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
                datos_guardar["servicios"] = st.text_input("Servicios Contratados", key=f"serv_fijo_{fk}")
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
