import re
import streamlit as st
import datetime
import pandas as pd

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
    
    /* Estilos para pantalla de login */
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
    .logout-btn {
        position: fixed;
        top: 10px;
        right: 10px;
        z-index: 9999;
    }
</style>
""", unsafe_allow_html=True)

# ================= ESTADO DE LA SESIÓN =================
if "form_key" not in st.session_state:
    st.session_state.form_key = 0

if "historial_temporal" not in st.session_state:
    st.session_state.historial_temporal = []

if "usuario_logueado" not in st.session_state:
    st.session_state.usuario_logueado = None

if "pdv_seleccionado" not in st.session_state:
    st.session_state.pdv_seleccionado = None

# ================= DATOS DE EJEMPLO (PDVs) =================
pdv_disponibles = {
    "Pdv1": "Punto de Venta 1 - Centro",
    "Pdv2": "Punto de Venta 2 - Norte",
    "Pdv3": "Punto de Venta 3 - Sur",
    "Pdv4": "Punto de Venta 4 - Occidente"
}

# ================= PANTALLA 1: LOGIN =================
if st.session_state.usuario_logueado is None:
    st.markdown("<div style='height: 80px;'></div>", unsafe_allow_html=True)
    
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
            else:
                st.session_state.usuario_logueado = cedula
                st.rerun()
    
    st.stop()

# ================= PANTALLA 2: SELECCIÓN DE PDV =================
if st.session_state.pdv_seleccionado is None:
    st.markdown("<div style='height: 50px;'></div>", unsafe_allow_html=True)
    
    st.markdown("""
    <div class="pdv-selector-container">
        <div class="login-title">📍 Selección de PDV</div>
        <div class="login-subtitle">Vendedor: <strong>{}</strong><br>Seleccione el punto de venta donde realizará la operación</div>
    </div>
    """.format(st.session_state.usuario_logueado), unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
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
            st.rerun()
    
    st.stop()

# ================= BARRA DE INFORMACIÓN DEL USUARIO =================
col_info1, col_info2, col_info3 = st.columns([2, 2, 1])
with col_info1:
    st.markdown(f'<span class="user-badge">👤 Cédula: {st.session_state.usuario_logueado}</span>', unsafe_allow_html=True)
with col_info2:
    st.markdown(f'<span class="user-badge">📍 PDV: {st.session_state.pdv_seleccionado} - {pdv_disponibles[st.session_state.pdv_seleccionado]}</span>', unsafe_allow_html=True)
with col_info3:
    if st.button("🚪 Salir", use_container_width=True):
        st.session_state.usuario_logueado = None
        st.session_state.pdv_seleccionado = None
        st.rerun()

st.markdown("<hr>", unsafe_allow_html=True)

# ================= ESTRUCTURA DE PESTAÑAS =================
st.title("📋 Portal de Gestión Comercial")
tab_registro, tab_historial = st.tabs(["📝 Registrar Nueva Venta", "📜 Historial de Operaciones"])

# ================= PESTAÑA 1: REGISTRO =================
with tab_registro:
    fk = st.session_state.form_key
    datos_guardar = {}
    
    # Guardar automáticamente el usuario y PDV
    datos_guardar["cedula_vendedor"] = st.session_state.usuario_logueado
    datos_guardar["punto_venta"] = st.session_state.pdv_seleccionado

    # --- SECCIÓN 1: DATOS DE VENTA ---
    with st.container(border=True):
        st.subheader("1. DATOS DE LA VENTA")
        col1, col2 = st.columns(2)
        with col1:
            datos_guardar["fecha_venta"] = st.date_input("Fecha de la venta", datetime.date.today(), key=f"fecha_{fk}")
        with col2:
            # Mostrar PDV seleccionado (solo lectura, ya se eligió al inicio)
            st.text_input(
                "Punto de Venta (Seleccionado)", 
                value=f"{st.session_state.pdv_seleccionado} - {pdv_disponibles[st.session_state.pdv_seleccionado]}", 
                disabled=True,
                key=f"pdv_readonly_{fk}"
            )
            # Campo para cambiar PDV si es necesario
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
            datos_guardar["correo"] = st.text_input("Correo Electrónico", key=f"correo_{fk}")
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

    # Inicializar campos opcionales
    campos_opcionales = [
        "referencia", "imei", "iccid", "min", 
        "valor_equipo_claro", "valor_descuento", "valor_equipo", 
        "valor_pagado_cliente", "financiado", "financiera", "valor_credito",
        "plan", "tipo_plan", "valor_plan",
        "ciudad", "indicaciones", "estrato", "campana", "servicios", "renta", "instalacion", "cuenta"
    ]
    for campo in campos_opcionales:
        datos_guardar[campo] = None

    # --- SECCIÓN 3: DETALLES DEL EQUIPO (MODIFICADA) ---
    if tipo_venta in ["Kit Contado", "Kit a Cuotas", "Reposicion a Cuotas", "Reposicion cargo a la factura", "Reposicion pago Inmediato", "Sim card"]:
        with st.container(border=True):
            st.subheader("3. DETALLES DEL EQUIPO")
            
            # Primera fila: Referencia, IMEI, ICCID
            col1, col2, col3 = st.columns(3)
            with col1:
                datos_guardar["referencia"] = st.text_input("Referencia del Equipo", key=f"ref_{fk}")
            with col2:
                datos_guardar["imei"] = st.text_input("IMEI", key=f"imei_{fk}")
            with col3:
                datos_guardar["iccid"] = st.text_input("ICCID", key=f"iccid_{fk}")
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Segunda fila: MIN, Valor Equipo Claro, Valor Descuento
            col4, col5, col6 = st.columns(3)
            with col4:
                datos_guardar["min"] = st.text_input("MIN", key=f"min_{fk}")
            with col5:
                datos_guardar["valor_equipo_claro"] = st.number_input(
                    "Valor del Equipo Claro ($)", 
                    min_value=0, 
                    step=1000,
                    key=f"veq_claro_{fk}"
                )
            with col6:
                datos_guardar["valor_descuento"] = st.number_input(
                    "Valor Descuento ($)", 
                    min_value=0, 
                    step=1000,
                    key=f"vdesc_{fk}"
                )
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Tercera fila: Valor Total Equipo (calculado), Valor Pagado, Financiado
            col7, col8, col9 = st.columns(3)
            with col7:
                # Calcular valor total automáticamente
                valor_total = datos_guardar["valor_equipo_claro"] - datos_guardar["valor_descuento"]
                datos_guardar["valor_equipo"] = valor_total
                st.number_input(
                    "Valor Total Equipo ($)", 
                    value=valor_total, 
                    disabled=True,
                    help="Se calcula automáticamente: Valor Equipo Claro - Valor Descuento",
                    key=f"veq_total_{fk}"
                )
            with col8:
                datos_guardar["valor_pagado_cliente"] = st.number_input(
                    "Valor Pagado por el Cliente ($)", 
                    min_value=0, 
                    step=1000,
                    key=f"vpagado_{fk}"
                )
            with col9:
                datos_guardar["financiado"] = st.selectbox(
                    "¿Financiado?", 
                    ["NO", "SI"], 
                    key=f"financiado_{fk}"
                )
            
            # Sección condicional: Datos de Financiación
            if datos_guardar["financiado"] == "SI":
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown("---")
                st.markdown("#### 💳 Datos de Financiación")
                
                col_fin1, col_fin2 = st.columns(2)
                with col_fin1:
                    datos_guardar["financiera"] = st.selectbox(
                        "Entidad Financiera", 
                        ["Claro", "Addi", "Celya", "Credismart"], 
                        key=f"fin_{fk}"
                    )
                with col_fin2:
                    datos_guardar["valor_credito"] = st.number_input(
                        "Valor Crédito ($)", 
                        min_value=0, 
                        step=1000,
                        key=f"vcredito_{fk}"
                    )

    # --- SECCIÓN 4: DESCRIPCIÓN DEL PLAN ---
    elif tipo_venta == "Postpago":
        with st.container(border=True):
            st.subheader("4. DESCRIPCIÓN DEL PLAN")
            col1, col2, col3 = st.columns(3)
            with col1:
                datos_guardar["plan"] = st.text_input("Nombre del Plan", key=f"plan_{fk}")
            with col2:
                datos_guardar["tipo_plan"] = st.selectbox("Tipo de Plan", ["Linea Nueva", "Migración", "Portabilidad"], key=f"tplan_{fk}")                
            with col3:
                datos_guardar["valor_plan"] = st.number_input("Valor Mensual ($)", min_value=0.0, key=f"vplan_{fk}")

    # --- SECCIÓN 5: SERVICIOS FIJOS ---
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
    if st.button("💾 REGISTRAR VENTA", use_container_width=True, type="primary"):
        if not tipo_venta:
            st.error("⚠️ Es obligatorio seleccionar el **TIPO DE TRANSACCIÓN** (Sección 2) para guardar el registro.")
        else:
            # Si es financiado, validar campos de financiación
            if datos_guardar.get("financiado") == "SI":
                if not datos_guardar.get("financiera"):
                    st.error("⚠️ Si la venta es financiada, debe seleccionar la **Entidad Financiera**.")
                elif not datos_guardar.get("valor_credito") or datos_guardar["valor_credito"] <= 0:
                    st.error("⚠️ Si la venta es financiada, debe ingresar el **Valor del Crédito**.")
                else:
                    st.session_state.historial_temporal.append(datos_guardar)
                    st.success(f"✅ ¡Venta registrada exitosamente! Vendedor: {st.session_state.usuario_logueado}")
                    st.session_state.form_key += 1
                    st.rerun()
            else:
                st.session_state.historial_temporal.append(datos_guardar)
                st.success(f"✅ ¡Venta registrada exitosamente! Vendedor: {st.session_state.usuario_logueado}")
                st.session_state.form_key += 1
                st.rerun()

# ================= PESTAÑA 2: HISTORIAL (FILTRADO POR VENDEDOR) =================
with tab_historial:
    st.subheader("📜 Mi Historial de Operaciones")
    st.caption(f"Mostrando únicamente las ventas del vendedor con cédula: **{st.session_state.usuario_logueado}**")
    
    # Filtrar historial SOLO para el vendedor logueado
    datos_historial = [
        venta for venta in st.session_state.historial_temporal 
        if venta.get("cedula_vendedor") == st.session_state.usuario_logueado
    ]
    
    if not datos_historial:
        st.info("📭 No tiene ventas registradas aún. Vaya a la pestaña 'Registrar Nueva Venta' para comenzar.")
    else:
        df_historial = pd.DataFrame(datos_historial)
        
        with st.container(border=True):
            st.markdown("**Filtros Disponibles**")
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                # Filtro por tipo de venta
                tipos_disponibles = df_historial["tipo_venta"].dropna().unique().tolist()
                if tipos_disponibles:
                    filtro_tipo = st.multiselect("🔍 Filtrar por Tipo de Venta", options=tipos_disponibles)
                else:
                    filtro_tipo = []
            with col_f2:
                # Filtro por PDV
                pdv_disponibles_filtro = df_historial["punto_venta"].dropna().unique().tolist()
                if pdv_disponibles_filtro:
                    filtro_pdv = st.multiselect("🔍 Filtrar por PDV", options=pdv_disponibles_filtro)
                else:
                    filtro_pdv = []
                
            # Aplicar filtros
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
