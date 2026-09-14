import datetime
import pandas as pd
import streamlit as st

# ================= CONFIGURACIÓN DE LA CAMPAÑA (Meta Volante) =================
# Este archivo es un módulo independiente de corta duración: al terminar la
# campaña se elimina (detengase con app.py). La configuración está hardcodeada
# aquí para que borrar el archivo elimine todo el tracking.

NOMBRE_CAMPANA = "¡Juntos logramos más!"
SUBTITULO_CAMPANA = "¡TU ESFUERZO TIENE PREMIO!"

FECHA_INICIO = datetime.date(2026, 9, 11)
FECHA_FIN = datetime.date(2026, 9, 17)
MES_CAMPANA = "Septiembre"

REGLA_CIERRE = (
    "Termina por ítem apenas el primer punto de venta logre la meta máxima de cada uno."
)

# Cada categoría: clave, nombre, unidad de medida y niveles (meta -> premio)
CATEGORIAS = [
    {
        "clave": "claro_up",
        "nombre": "Claro Up",
        "unidad": "activaciones",
        "niveles": [
            {"meta": 5, "premio": 100000},
            {"meta": 7, "premio": 150000},
        ],
    },
    {
        "clave": "accesos",
        "nombre": "Accesos",
        "unidad": "accesos",
        "niveles": [
            {"meta": 3, "premio": 100000},
            {"meta": 4, "premio": 150000},
            {"meta": 5, "premio": 200000},
        ],
    },
    {
        "clave": "pospagos",
        "nombre": "Pospagos",
        "unidad": "pospagos",
        "niveles": [
            {"meta": 10, "premio": 100000},
            {"meta": 15, "premio": 200000},
            {"meta": 20, "premio": 300000},
            {"meta": 25, "premio": 400000},
            {"meta": 30, "premio": 500000},
        ],
    },
    {
        "clave": "terminales",
        "nombre": "Terminales",
        "unidad": "en ventas",
        "niveles": [
            {"meta": 30000000, "premio": 200000},
            {"meta": 40000000, "premio": 350000},
            {"meta": 50000000, "premio": 500000},
        ],
    },
]

# Tipos de venta que suman al pote de Terminales (suma valor_equipo_claro)
TIPOS_TERMINALES = [
    "Kit Contado",
    "Kit a Cuotas",
    "Reposicion a Cuotas",
    "Reposicion cargo a la factura",
    "Reposicion pago Inmediato",
    "Tecnologia",
]


def consultar_ventas_pdv(cliente, pdv):
    """Consulta todas las ventas del PDV dentro del rango de la campaña.

    Si viene fuera de rango o sin conexión, devuelve lista vacía.
    """
    try:
        respuesta = (
            cliente.table("ventas")
            .select(
                "punto_venta, fecha_venta, tipo_venta, valor_equipo_claro, "
                "claro_up, acceso"
            )
            .eq("punto_venta", pdv)
            .gte("fecha_venta", FECHA_INICIO.isoformat())
            .lte("fecha_venta", FECHA_FIN.isoformat())
            .execute()
        )
        ventas = respuesta.data or []
        # Normalizar fechas a datetime.date (vienen como string ISO)
        for v in ventas:
            try:
                fv = v.get("fecha_venta")
                if isinstance(fv, str):
                    v["fecha_venta"] = datetime.date.fromisoformat(fv[:10])
            except (ValueError, TypeError):
                v["fecha_venta"] = None
        return ventas
    except Exception:
        return []


def calcular_avance(ventas):
    """Calcula el avance de la campaña para un PDV.

    Reglas (mismas que app.calcular_avance):
      - POSPAGOS:  ventas tipo 'Postpago' (conteo)
      - ACCESOS:   ventas 'Hogar' con acceso == 'SI'
      - CLARO_UP:  ventas con claro_up activado
      - TERMINALES: suma de valor_equipo_claro de Kit/Reposicion/Tecnologia
    Devuelve dict {claro_up, accesos, pospagos, terminales}.
    """
    avance = {"claro_up": 0, "accesos": 0, "pospagos": 0, "terminales": 0}
    for venta in ventas:
        tv = venta.get("tipo_venta")
        if tv == "Postpago":
            avance["pospagos"] += 1
        elif tv == "Hogar":
            if venta.get("acceso") == "SI":
                avance["accesos"] += 1
        elif tv in TIPOS_TERMINALES:
            try:
                avance["terminales"] += float(venta.get("valor_equipo_claro") or 0)
            except (TypeError, ValueError):
                pass
        if venta.get("claro_up") is True or str(venta.get("claro_up")).lower() == "true":
            avance["claro_up"] += 1
    return avance


def _formatear_premio(monto):
    """Formatea un premio en pesos colombianos (ej. $100.000)."""
    return f"${int(monto):,}".replace(",", ".")


def _formatear_meta(cat, meta):
    """Formatea una meta según la categoría (porcentaje o dinero)."""
    if cat == "terminales":
        return f"${int(meta):,}".replace(",", ".")
    return f"{int(meta)}"


def render_meta_volante(cliente, pdv, nombre_pdv):
    """Muestra el tracking de la Meta Volante para el PDV seleccionado.

    Llamada desde app.py tras elegir PDV (pantalla intermedia). Si hoy está
    fuera del rango de la campaña, muestra un aviso y no renderiza.
    """
    hoy = datetime.date.today()

    st.markdown("<div style='height: 30px;'></div>", unsafe_allow_html=True)
    st.markdown(
        f"""
        <div style="text-align:center; padding:24px; border:2px solid #DA291C;
                    border-radius:12px; background:linear-gradient(135deg,#FFF0EF,#FFFFFF);">
            <div style="font-size:30px; font-weight:bold; color:#DA291C;">
                🏆 {NOMBRE_CAMPANA}
            </div>
            <div style="font-size:18px; color:#DA291C; margin-top:4px;">
                {SUBTITULO_CAMPANA}
            </div>
            <div style="font-size:15px; color:#666; margin-top:10px;">
                Del {FECHA_INICIO.day} al {FECHA_FIN.day} de {MES_CAMPANA}
            </div>
            <div style="font-size:13px; color:#888; margin-top:4px; font-style:italic;">
                {REGLA_CIERRE}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if hoy < FECHA_INICIO or hoy > FECHA_FIN:
        st.info("📅 La campaña Meta Volante no está activa en esta fecha.")
        return

    st.markdown(
        f"""
        <div class="nombre-vendedor" style="margin-top:18px;">
            📍 Punto de Venta: {nombre_pdv} ({pdv})
        </div>
        """,
        unsafe_allow_html=True,
    )

    ventas_pdv = consultar_ventas_pdv(cliente, pdv)
    avance = calcular_avance(ventas_pdv)

    st.markdown("---")

    for cat in CATEGORIAS:
        clave = cat["clave"]
        valor = avance[clave]

        # Nivel más alto alcanzado
        niveles_alcanzados = [n for n in cat["niveles"] if valor >= n["meta"]]
        nivel_max = niveles_alcanzados[-1] if niveles_alcanzados else None
        ganado = nivel_max is not None and nivel_max is cat["niveles"][-1]

        with st.container(border=True):
            col_t, col_v = st.columns([4, 2])
            with col_t:
                st.markdown(f"### {cat['nombre']}")
                if cat["clave"] == "terminales":
                    st.metric(
                        "Avance",
                        f"${int(valor):,}".replace(",", "."),
                        help=f"Meta máxima: {_formatear_meta(clave, cat['niveles'][-1]['meta'])} en ventas",
                    )
                else:
                    st.metric(
                        "Avance",
                        f"{int(valor)} {cat['unidad']}",
                        help=f"Meta máxima: {_formatear_meta(clave, cat['niveles'][-1]['meta'])} {cat['unidad']}",
                    )
            with col_v:
                if ganado:
                    st.success("🏁 **Ganado**\n\n¡Meta máxima alcanzada!")
                elif nivel_max:
                    premio = _formatear_premio(nivel_max["premio"])
                    st.info(f"**Hasta {premio} alcanzado**")
                else:
                    st.warning("Sigue esforzándote 💪")

            # Niveles de premio
            filas = []
            for n in cat["niveles"]:
                cumplido = valor >= n["meta"]
                filas.append({
                    "Meta": _formatear_meta(clave, n["meta"]),
                    "Premio": _formatear_premio(n["premio"]),
                    "Estado": "✓ Cumplida" if cumplido else "Pendiente",
                })
            st.dataframe(
                pd.DataFrame(filas),
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Meta": st.column_config.TextColumn("Meta"),
                    "Premio": st.column_config.TextColumn("Premio"),
                    "Estado": st.column_config.TextColumn("Estado"),
                },
            )

    st.markdown("---")
    st.caption(f"Ventas registradas en el PDV durante la campaña: **{len(ventas_pdv)}**")
