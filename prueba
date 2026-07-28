import streamlit as st
import datetime
import pandas as pd

# ================= CONFIGURACIÓN DE PÁGINA =================
st.set_page_config(page_title="Gestión de Ventas", layout="wide", page_icon="🔴")

# ================= CSS PERSONALIZADO =================
# Inyección de estilos para aplicar los colores corporativos (Rojo, Blanco, Negro)
st.markdown("""
<style>
    /* Fondo general más limpio */
    .stApp {
        background-color: #FFFFFF;
    }
    
    /* Encabezados principales en Rojo */
    h1, h2, h3 {
        color: #DA291C !important; 
        font-family: 'Arial', sans-serif;
        font-weight: 700 !important;
    }
    
    /* Botón Primario (Guardar) */
    .stButton > button[kind="primary"] {
        background-color: #DA291C !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 6px !important;
        font-weight: bold !important;
        padding: 10px 24px !important;
        transition: all 0.3s ease;
    }
    
    /* Efecto Hover para el botón primario (cambia a negro) */
    .stButton > button[kind="primary"]:hover {
        background-color: #000000 !important; 
        color: #FFFFFF !important;
        transform: scale(1.02);
    }
    
    /* Estilo de las pestañas (Tabs) */
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
    
    /* Alertas y separadores */
    hr {
        border-top: 2px solid #DA291C !important;
    }
    .stAlert {
        background-color: #F8F9FA !important;
        border-left: 5px solid #DA291C !important;
        color: #000000 !important;
    }
</style>
""", unsafe_allow_html=True)

# ================= ESTADO DE LA SESIÓN =================
if "form_key" not in st.session_state:
    st.session_state.form_key = 0

if "historial_temporal" not in st.session_state:
    st.session_state.historial_temporal = []

# ================= DATOS DE EJEMPLO =================
asesores_por_pdv = {
    "Pdv1": ["vendedor1pdv1", "vendedor2pdv1"],
    "Pdv2": ["vendedor1pdv2", "vendedor2pdv2", "vendedor3pdv2"],
    "Pdv3": ["vendedor1pdv3", "vendedor2pdv3"]
}

# ================= ESTRUCTURA DE PESTAÑAS =================
st.title("📋 Portal de Gestión Comercial")
tab_registro, tab_historial = st.tabs(["📝 Registrar Nueva Venta", "📜 Historial de Operaciones"])

# ================= PESTAÑA 1: REGISTRO =================
with tab_registro:
    fk = st.session_state.form_key
    datos_guardar = {}

    # --- SECCIÓN 1: DATOS DE VENTA ---
    with st.container(border=True):
        st.subheader("1. DATOS DE LA VENTA")
        col1, col2, col3 = st.columns(3)
        with col1:
            datos_guardar["fecha_venta"] = st.date_input("Fecha de la venta", datetime.date.today(), key=f"fecha_{fk}")
        with col2:
            pdv_seleccionado = st.selectbox("Punto de Venta", list(asesores_por_pdv.keys()), key=f"pdv_{fk}")
            datos_guardar["punto_venta"] = pdv_seleccionado
        with col3:
            asesores_disponibles = asesores_por_pdv.get(pdv_seleccionado, [])
            datos_guardar["asesor_comercial"] = st.selectbox("Asesor Comercial", asesores_disponibles, key=f"asesor_{fk}")

    # --- SECCIÓN 2: DATOS DEL CLIENTE ---
    with st.container(border=True):
        st.subheader("2. DATOS DEL CLIENTE")
        col1, col2, col3 = st.columns(3)
        with col1:
            datos_guardar["nombre_cliente"] = st.text_input("Nombre Completo", key=f"nom_cli_{fk}")
            datos_guardar["tipo_documento"] = st.selectbox("Tipo de Documento", ["CC", "CE", "NIT", "Pasaporte"], key=f"tdoc_{fk}")
            datos_guardar["contacto_cliente"] = st.text_input("Teléfono de Contacto", key=f"tel_{fk}")
        with col2:
            datos_guardar["nro_documento"] = st.text_input("Nro. de Documento", key=f"ndoc_{fk}")
            datos_guardar["direccion"] = st.text_input("Dirección de Residencia", key=f"dir_{fk}")
            datos_guardar["cliente_convergente"] = st.selectbox("¿Es Cliente Convergente?", ["Sí", "No"], key=f"conv_{fk}")
        with col3:
            datos_guardar["correo"] = st.text_input("Correo Electrónico", key=f"correo_{fk}")
            datos_guardar["servicios_adicionales"] = st.text_input("Servicios Adicionales", key=f"serv_ad_{fk}")
            datos_guardar["observaciones"] = st.text_area("Observaciones", height=68, key=f"obs_{fk}")

        st.markdown("<br>", unsafe_allow_html=True)
        tipo_venta = st.selectbox(
            "📍 TIPO DE TRANSACCIÓN", 
            ["Postpago", "Prepago", "Prepago Cuotas", "Reposicion", "Claro fijo", "DTH", "SIM"],
            index=None,
            placeholder="Seleccione el producto para desplegar los campos correspondientes...",
            key=f"tventa_{fk}"
        )
        datos_guardar["tipo_venta"] = tipo_venta

    # Inicializar campos opcionales
    campos_opcionales = [
        "referencia", "imei", "iccid", "min", "valor_equipo", "financiera",
        "plan", "tipo_plan", "valor_plan",
        "ciudad", "indicaciones", "estrato", "campana", "servicios", "renta", "instalacion", "cuenta"
    ]
    for campo in campos_opcionales:
        datos_guardar[campo] = None

    # --- SECCIONES CONDICIONALES ---
    if tipo_venta in ["Prepago", "Prepago Cuotas", "Reposicion", "SIM"]:
        with st.container(border=True):
            st.subheader("3. DETALLES DEL EQUIPO")
            col1, col2 = st.columns(2)
            with col1:
                datos_guardar["referencia"] = st.text_input("Referencia del Equipo", key=f"ref_{fk}")
                datos_guardar["imei"] = st.text_input("IMEI", key=f"imei_{fk}")
                datos_guardar["iccid"] = st.text_input("ICCID", key=f"iccid_{fk}")
            with col2:
                datos_guardar["min"] = st.text_input("MIN", key=f"min_{fk}")
                datos_guardar["valor_equipo"] = st.number_input("Valor del Equipo ($)", min_value=0, key=f"veq_{fk}")
                datos_guardar["financiera"] = st.text_input("Entidad Financiera", key=f"fin_{fk}")

    elif tipo_venta == "Postpago":
        with st.container(border=True):
            st.subheader("4. DESCRIPCIÓN DEL PLAN")
            col1, col2, col3 = st.columns(3)
            with col1:
                datos_guardar["plan"] = st.text_input("Nombre del Plan", key=f"plan_{fk}")
            with col2:
                datos_guardar["tipo_plan"] = st.text_input("Tipo de Plan", key=f"tplan_{fk}")
            with col3:
                datos_guardar["valor_plan"] = st.number_input("Valor Mensual ($)", min_value=0.0, key=f"vplan_{fk}")

    elif tipo_venta in ["Claro fijo", "DTH"]:
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
            with col3:
                datos_guardar["campana"] = st.text_input("Campaña Asociada", key=f"camp_{fk}")
                datos_guardar["servicios"] = st.text_input("Servicios Contratados", key=f"serv_fijo_{fk}")
                datos_guardar["cuenta"] = st.text_input("Número de Cuenta", key=f"cta_{fk}")

    # --- SECCIÓN 6: REFERIDOS ---
    with st.container(border=True):
        st.subheader("6. PROGRAMA DE REFERIDOS")
        col1, col2, col3 = st.columns(3)
        with col1:
            datos_guardar["producto_referido"] = st.text_input("Producto de interés", key=f"pref_{fk}")
        with col2:
            datos_guardar["nombre_referido"] = st.text_input("Nombre del Referido", key=f"nref_{fk}")
        with col3:
            datos_guardar["cel_referido"] = st.text_input("Celular del Referido", key=f"cref_{fk}")

    st.markdown("<br>", unsafe_allow_html=True)
    
    # --- BOTÓN DE GUARDAR ---
    if st.button("💾 REGISTRAR VENTA", use_container_width=True, type="primary"):
        if not tipo_venta:
            st.error("⚠️ Es obligatorio seleccionar el **TIPO DE TRANSACCIÓN** (Sección 2) para guardar el registro.")
        else:
            # Aquí va el código real de guardado en base de datos
            st.session_state.historial_temporal.append(datos_guardar)
            st.success(f"✅ ¡Excelente! La venta de {datos_guardar['asesor_comercial']} ha sido registrada en el sistema.")
            
            # Limpiar formulario
            st.session_state.form_key += 1
            st.rerun()

# ================= PESTAÑA 2: HISTORIAL =================
with tab_historial:
    st.subheader("Base de Datos de Ventas Recientes")
    datos_historial = st.session_state.historial_temporal
    
    if not datos_historial:
        st.info("El historial está vacío por el momento. Registra una venta para verla aquí.")
    else:
        df_historial = pd.DataFrame(datos_historial)
        
        with st.container(border=True):
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                filtro_asesor = st.multiselect("🔍 Filtrar por Asesor", options=df_historial["asesor_comercial"].unique())
            with col_f2:
                filtro_tipo = st.multiselect("🔍 Filtrar por Tipo", options=df_historial["tipo_venta"].unique())
                
            if filtro_asesor:
                df_historial = df_historial[df_historial["asesor_comercial"].isin(filtro_asesor)]
            if filtro_tipo:
                df_historial = df_historial[df_historial["tipo_venta"].isin(filtro_tipo)]
                
            st.dataframe(df_historial, use_container_width=True, hide_index=True)
            
            csv = df_historial.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Exportar Reporte (CSV)",
                data=csv,
                file_name=f"reporte_ventas_{datetime.date.today()}.csv",
                mime="text/csv",
            )

# C:\Users\lubernu\Desktop\streamlit\prueba2.py
