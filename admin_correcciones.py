# -*- coding: utf-8 -*-
"""Módulo de Correcciones para el Superusuario.

Permite buscar una venta por IMEI, MIN o cédula del cliente y editarla en un
formulario (no tabular), guardando los cambios directamente en Supabase.

Módulo independiente de app.py (patrón similar a meta_volante.py): recibe el
cliente de Supabase y renderiza con Streamlit.
Requiere la política RLS de UPDATE en la tabla ventas (ver crear_tabla.sql).
"""

import datetime

import streamlit as st

# ================= ENUMERACIONES (mismas opciones que app.py) =================
TIPOS_VENTA = [
    "Postpago", "Kit Contado", "Kit a Cuotas", "Reposicion a Cuotas",
    "Reposicion cargo a la factura", "Reposicion pago Inmediato",
    "Tecnologia", "Hogar", "Sim card",
]
METODOS_PAGO = [
    None, "Efectivo", "Tarjeta Débito", "Tarjeta Crédito", "QR",
    "Consignación", "Transferencia Bancaria", "Llave Bancolombia",
    "Llave Banco de Bogotá", "Wompi",
]
TIPOS_DOCUMENTO = ["CC", "CE", "NIT", "Pasaporte", "PPT"]
FINANCIADAS = ["NO", "SI"]
FINANCIERAS = ["Claro", "Addi", "Celya", "Krediya", "Credismart", "Vanti", "Alo Credit", "Payjoy"]
TIPOS_PLAN = ["Linea Nueva", "Migración", "Portabilidad"]
ESTRATOS = ["1", "2", "3", "4", "5", "6", "Comercial"]
SERVICIOS_HOGAR = ["Triple", "Doble", "Sencillo"]
SI_NO = ["SI", "NO"]
TRAMITES = ["Repo de sim", "Wellcome back"]

# Definición de campos del formulario:
#   col: columna en Supabase; label: etiqueta;
#   tipo: fecha / select / numero / texto / texto_area / bool
CAMPOS_FORMULARIO = [
    # --- Datos de la venta / vendedor ---
    {"col": "fecha_venta", "label": "Fecha de la venta", "tipo": "fecha"},
    {"col": "tipo_venta", "label": "Tipo de Transacción", "tipo": "select", "opciones": TIPOS_VENTA},
    {"col": "recibido_en", "label": "Método de Pago", "tipo": "select", "opciones": METODOS_PAGO},
    {"col": "punto_venta", "label": "Punto de Venta", "tipo": "texto"},
    {"col": "cedula_vendedor", "label": "Cédula Vendedor", "tipo": "texto"},
    {"col": "nombre_vendedor", "label": "Nombre Vendedor", "tipo": "texto"},

    # --- Datos del cliente ---
    {"col": "nombre_cliente", "label": "Nombre Completo", "tipo": "texto"},
    {"col": "tipo_documento", "label": "Tipo de Documento", "tipo": "select", "opciones": TIPOS_DOCUMENTO},
    {"col": "nro_documento", "label": "Nro. de Documento", "tipo": "texto"},
    {"col": "contacto_cliente", "label": "Teléfono de Contacto", "tipo": "texto"},
    {"col": "direccion", "label": "Dirección de Residencia", "tipo": "texto"},
    {"col": "correo", "label": "Correo Electrónico", "tipo": "texto"},
    {"col": "cliente_convergente", "label": "¿Es Cliente Convergente?", "tipo": "select", "opciones": ["Sí", "No"]},
    {"col": "servicios_adicionales", "label": "Servicios Adicionales Ofrecidos", "tipo": "texto"},
    {"col": "observaciones", "label": "Observaciones", "tipo": "texto_area"},

    # --- Detalles del equipo ---
    {"col": "referencia", "label": "Referencia del Equipo", "tipo": "texto"},
    {"col": "imei", "label": "IMEI", "tipo": "texto"},
    {"col": "iccid", "label": "ICCID", "tipo": "texto"},
    {"col": "min", "label": "MIN", "tipo": "texto"},
    {"col": "valor_equipo_claro", "label": "Valor del Equipo Claro ($)", "tipo": "numero"},
    {"col": "valor_descuento", "label": "Valor Descuento ($)", "tipo": "numero"},
    {"col": "valor_pagado_cliente", "label": "Valor Pagado por el Cliente ($)", "tipo": "numero"},
    {"col": "financiado", "label": "¿Financiado?", "tipo": "select", "opciones": FINANCIADAS},
    {"col": "financiera", "label": "Entidad Financiera", "tipo": "select", "opciones": FINANCIERAS},
    {"col": "valor_credito", "label": "Valor Crédito ($)", "tipo": "numero"},

    # --- Postpago ---
    {"col": "plan", "label": "Nombre del Plan", "tipo": "texto"},
    {"col": "tipo_plan", "label": "Tipo de Plan", "tipo": "select", "opciones": TIPOS_PLAN},
    {"col": "valor_plan", "label": "Valor Mensual ($)", "tipo": "numero"},

    # --- Hogar (servicios fijos) ---
    {"col": "ciudad", "label": "Ciudad de Instalación", "tipo": "texto"},
    {"col": "indicaciones", "label": "Indicaciones (Cómo llegar)", "tipo": "texto_area"},
    {"col": "estrato", "label": "Estrato", "tipo": "select", "opciones": ESTRATOS},
    {"col": "campana", "label": "Campaña Asociada", "tipo": "texto"},
    {"col": "servicios", "label": "Servicios Contratados", "tipo": "select", "opciones": SERVICIOS_HOGAR},
    {"col": "renta", "label": "Valor Renta ($)", "tipo": "numero"},
    {"col": "instalacion", "label": "Costo Instalación ($)", "tipo": "numero"},
    {"col": "cuenta", "label": "Número de Cuenta", "tipo": "texto"},
    {"col": "acceso", "label": "Acceso", "tipo": "select", "opciones": SI_NO},

    # --- Sim card ---
    {"col": "tramite", "label": "Trámite", "tipo": "select", "opciones": TRAMITES},
    {"col": "paquete_bienvenida", "label": "Paquete de Bienvenida", "tipo": "select", "opciones": ["Sí", "No"]},

    # --- Referidos ---
    {"col": "producto_referido", "label": "Producto de interés", "tipo": "texto"},
    {"col": "nombre_referido", "label": "Nombre del Referido", "tipo": "texto"},
    {"col": "cel_referido", "label": "Celular del Referido", "tipo": "texto"},

    # --- Claro Up ---
    {"col": "claro_up", "label": "¿Claro Up?", "tipo": "bool"},
    {"col": "valor_claro_up", "label": "Valor Claro Up ($)", "tipo": "numero"},
]

GRUPOS_FORMULARIO = [
    {"titulo": "1. DATOS DE LA VENTA Y VENDEDOR",
     "campos": ["fecha_venta", "tipo_venta", "recibido_en", "punto_venta", "cedula_vendedor", "nombre_vendedor"]},
    {"titulo": "2. DATOS DEL CLIENTE",
     "campos": ["nombre_cliente", "tipo_documento", "nro_documento", "contacto_cliente",
                "direccion", "correo", "cliente_convergente", "servicios_adicionales", "observaciones"]},
    {"titulo": "3. DETALLES DEL EQUIPO",
     "campos": ["referencia", "imei", "iccid", "min", "valor_equipo_claro", "valor_descuento",
                "valor_pagado_cliente", "financiado", "financiera", "valor_credito"]},
    {"titulo": "4. POSTPAGO",
     "campos": ["plan", "tipo_plan", "valor_plan"]},
    {"titulo": "5. HOGAR (SERVICIOS FIJOS)",
     "campos": ["ciudad", "indicaciones", "estrato", "campana", "servicios",
                "renta", "instalacion", "cuenta", "acceso"]},
    {"titulo": "6. SIM CARD",
     "campos": ["tramite", "paquete_bienvenida"]},
    {"titulo": "7. REFERIDOS Y CLARO UP",
     "campos": ["producto_referido", "nombre_referido", "cel_referido", "claro_up", "valor_claro_up"]},
]


def normalizar(valor):
    """Normaliza IMEIs/MINs/cédulas para comparación (quita espacios, '.0' de floats)."""
    s = str(valor or "").strip().upper()
    if s.endswith(".0"):
        s = s[:-2]
    return s


def consultar_todas_ventas(cliente):
    """Descarga todas las ventas de la tabla 'ventas'.

    Retorna (lista, error). La búsqueda se hace en Python para reproducir el
    mismo normalize() de facturacion.py (robusto ante el sufijo '.0').
    """
    try:
        respuesta = cliente.table("ventas").select("*").order("created_at", desc=True).execute()
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


def buscar_ventas(ventas, criterio, termino):
    """Filtra las ventas según el criterio (IMEI / MIN / cédula del cliente)."""
    term = normalizar(termino)
    if not term:
        return []
    columna = {"IMEI": "imei", "MIN": "min", "Cédula del Cliente": "nro_documento"}.get(criterio)
    if not columna:
        return []
    return [v for v in ventas if normalizar(v.get(columna)) == term]


def _render_campo(def_campo, venta, prefijo):
    """Renderiza el widget Streamlit de un campo y devuelve su valor editado."""
    col = def_campo["col"]
    tipo = def_campo["tipo"]
    label = def_campo["label"]
    key = f"{prefijo}_{col}"
    valor_original = venta.get(col)

    if tipo == "fecha":
        valor = valor_original
        if isinstance(valor, str):
            try:
                valor = datetime.date.fromisoformat(valor[:10])
            except ValueError:
                valor = datetime.date.today()
        if valor is None:
            valor = datetime.date.today()
        return st.date_input(label, value=valor, key=key)

    if tipo == "bool":
        return st.checkbox(label, value=bool(valor_original), key=key)

    if tipo == "numero":
        try:
            valor = float(valor_original or 0)
        except (TypeError, ValueError):
            valor = 0.0
        return st.number_input(
            label, min_value=0.0, value=valor, step=1000.0, format="%.0f", key=key
        )

    if tipo == "select":
        opciones = list(def_campo["opciones"])
        if valor_original is not None and valor_original in opciones:
            indice = opciones.index(valor_original)
        else:
            # Si el valor histórico no está en la lista (o es nulo), se ofrece primero
            # para no forzar una opción por defecto ni perder datos viejos.
            opciones.insert(0, valor_original)
            indice = 0
        return st.selectbox(label, options=opciones, index=indice, key=key)

    if tipo == "texto_area":
        return st.text_area(label, value=str(valor_original or ""), height=68, key=key)

    return st.text_input(label, value=str(valor_original or ""), key=key)


def _render_formulario(venta):
    """Dibuja el formulario editable de la venta.

    Retorna (valores, guardar) donde 'guardar' es True cuando se presiona el
    botón de guardado del formulario.
    """
    id_venta = venta.get("id")
    prefijo = f"corr_{id_venta}"
    mapa = {c["col"]: c for c in CAMPOS_FORMULARIO if c["col"] in venta}
    valores = {}

    with st.form(f"form_correccion_{id_venta}"):
        st.caption(
            f"Editando venta **#{id_venta}** · Creada el {(venta.get('created_at') or '')[:19]}"
        )

        for grupo in GRUPOS_FORMULARIO:
            cols_grupo = [c for c in grupo["campos"] if c in mapa]
            if not cols_grupo:
                continue
            st.subheader(grupo["titulo"])
            with st.container(border=True):
                for i in range(0, len(cols_grupo), 2):
                    col1, col2 = st.columns(2)
                    with col1:
                        valores[cols_grupo[i]] = _render_campo(mapa[cols_grupo[i]], venta, prefijo)
                    if i + 1 < len(cols_grupo):
                        with col2:
                            valores[cols_grupo[i + 1]] = _render_campo(mapa[cols_grupo[i + 1]], venta, prefijo)

        # Valor total del equipo (se recalcula automáticamente)
        if "valor_equipo_claro" in valores and "valor_descuento" in valores:
            v_total = float(valores.get("valor_equipo_claro") or 0) - float(valores.get("valor_descuento") or 0)
            valores["valor_equipo"] = v_total
            st.number_input(
                "Valor Total Equipo ($)",
                value=v_total,
                disabled=True,
                help="Se recalcula automáticamente: Valor Equipo Claro - Valor Descuento.",
                key=f"{prefijo}_valor_equipo_ro",
            )

        guardar = st.form_submit_button("💾 Guardar Cambios", type="primary", use_container_width=True)

    return valores, guardar


def _normalizar_comp(valor):
    """Comparable simple para detectar cambios (fechas a ISO, números sin ceros)."""
    if valor is None:
        return ""
    if isinstance(valor, datetime.date):
        return valor.isoformat()
    if isinstance(valor, float):
        return f"{valor:g}"
    return str(valor).strip()


def _son_iguales(original, nuevo):
    """Indica si el valor original de la BD es igual al valor editado."""
    if isinstance(original, datetime.date) and isinstance(nuevo, str):
        try:
            return original == datetime.date.fromisoformat(nuevo[:10])
        except ValueError:
            pass
    if isinstance(original, bool) or isinstance(nuevo, bool):
        return bool(original) == bool(nuevo)
    return _normalizar_comp(original) == _normalizar_comp(nuevo)


def _armar_registro_cambios(venta, valores):
    """Construye el dict de UPDATE con solo los campos que cambiaron."""
    tipos = {c["col"]: c["tipo"] for c in CAMPOS_FORMULARIO}
    registro = {}

    for col, nuevo in valores.items():
        if col == "valor_equipo":
            continue
        original = venta.get(col)

        if tipos.get(col) == "numero" and (original is None or original == "") and float(nuevo or 0) == 0:
            # No tocar nulos numéricos si el administrador no digitó un valor.
            continue
        if _son_iguales(original, nuevo):
            continue

        if col == "fecha_venta" and isinstance(nuevo, datetime.date):
            nuevo = nuevo.isoformat()
        if col == "claro_up":
            nuevo = bool(nuevo)
        if nuevo is None or nuevo == "":
            nuevo = None
        registro[col] = nuevo

    if "valor_equipo" in valores and not _son_iguales(venta.get("valor_equipo"), valores["valor_equipo"]):
        registro["valor_equipo"] = float(valores["valor_equipo"])

    return registro


def render_admin_correcciones(cliente):
    """Punto de entrada del módulo (llamado desde app.py).

    Solo debería mostrarse al Superusuario; el control de acceso lo hace app.py.
    """
    st.subheader("⚙️ Corrección de Ventas")
    st.caption(
        "Busque la venta por IMEI, MIN o cédula del cliente y edítela en el "
        "formulario. Los cambios se guardan directamente en Supabase."
    )

    criterio = st.radio(
        "Buscar por",
        options=["IMEI", "MIN", "Cédula del Cliente"],
        horizontal=True,
        key="corr_criterio",
    )
    termino = st.text_input(
        "Valor a buscar",
        placeholder="Ej: 356938035643809 (IMEI) · 3001234567 (MIN) · 1098765432 (Cédula)",
        key="corr_termino",
    )

    ventas, error = consultar_todas_ventas(cliente)
    if error:
        st.error(f"❌ Error al consultar las ventas: {error}")

    if not termino:
        st.info("📭 Escriba un valor y presione **Buscar**.")
        return

    if st.button("🔍 Buscar", type="primary"):
        st.session_state["corr_resultados"] = buscar_ventas(ventas, criterio, termino)

    resultados = st.session_state.get("corr_resultados")
    if resultados is None:
        return

    if not resultados:
        st.info("📭 No se encontraron ventas con ese valor.")
        st.session_state["corr_resultados"] = None
        return

    st.success(f"✅ Se encontraron {len(resultados)} ventas.")

    def _etiqueta(v):
        fecha = v.get("fecha_venta")
        fe_str = fecha.strftime("%d/%m/%Y") if isinstance(fecha, datetime.date) else str(fecha or "?")
        return (
            f"#{v.get('id')} · {fe_str} · {v.get('tipo_venta') or '?'} · "
            f"{v.get('nombre_cliente') or '?'} · IMEI {v.get('imei') or '-'} · MIN {v.get('min') or '-'}"
        )

    etiquetas = [_etiqueta(v) for v in resultados]

    if len(resultados) > 1:
        indice = st.selectbox(
            "Seleccione la venta a corregir",
            options=range(len(etiquetas)),
            format_func=lambda i: etiquetas[i],
            key="corr_selector_venta",
        )
        venta_seleccionada = resultados[indice]
    else:
        venta_seleccionada = resultados[0]
        st.caption(etiquetas[0])

    st.markdown("---")

    valores, guardar = _render_formulario(venta_seleccionada)

    if guardar:
        registro = _armar_registro_cambios(venta_seleccionada, valores)
        if not registro:
            st.info("ℹ️ No hubo cambios para guardar.")
        else:
            try:
                cliente.table("ventas").update(registro).eq("id", venta_seleccionada["id"]).execute()
                st.success(f"✅ Cambios guardados para la venta #{venta_seleccionada['id']}.")
                st.session_state["corr_resultados"] = None
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error al guardar los cambios: {e}")
