import streamlit as st
import pandas as pd
from datetime import datetime
import io

# =========================================================================
# CONFIGURACIÓN DE PÁGINA Y ESTILOS
# =========================================================================
st.set_page_config(
    page_title="Control de Molienda - Grupo Sánchez",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilo CSS avanzado para apariencia limpia e industrial
st.markdown("""
<style>
    /* Tarjetas de estatus de órdenes activas */
    .code-card {
        padding: 1.25rem;
        border-radius: 10px;
        background-color: #F8F9FA;
        border-left: 6px solid #1F497D;
        margin-bottom: 1rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .code-card-warning {
        border-left-color: #FFA500;
    }
    .code-card-danger {
        border-left-color: #D9534F;
        background-color: #FFF5F5;
    }
    /* Badges de estatus */
    .badge {
        padding: 0.25rem 0.6rem;
        border-radius: 5px;
        font-weight: bold;
        font-size: 0.85rem;
    }
    .badge-normal { background-color: #D4EDDA; color: #155724; }
    .badge-warning { background-color: #FFF3CD; color: #856404; }
    .badge-danger { background-color: #F8D7DA; color: #721C24; }
    
    [data-testid="stMetricValue"] { font-size: 1.8rem; font-weight: bold; }
    .stButton > button { width: 100%; border-radius: 6px; }
</style>
""", unsafe_allow_html=True)

# =========================================================================
# BASE DE DATOS DE CAPACIDADES Y TIEMPOS ESTÁNDAR
# =========================================================================
DB_ESTANDARES = {
    "VQN0074PB": {"puesto": "PTPSBSMP01", "std_cc_hrs": 5.0, "std_env_hrs": 3.0, "std_tot_hrs": 24.0, "lote_prom": 800},
    "FZ9002": {"puesto": "PTPSBSMP01", "std_cc_hrs": 1.0, "std_env_hrs": 1.0, "std_tot_hrs": 6.0, "lote_prom": 800},
    "PSJI930136": {"puesto": "PTPSBSMP01", "std_cc_hrs": 2.0, "std_env_hrs": 1.0, "std_tot_hrs": 3.0, "lote_prom": 800},
    "PSMM951200": {"puesto": "PTPSBSMP01", "std_cc_hrs": 2.0, "std_env_hrs": 1.0, "std_tot_hrs": 3.0, "lote_prom": 800},
    "PSGN6080473": {"puesto": "PTPSBSMP01", "std_cc_hrs": 5.0, "std_env_hrs": 1.0, "std_tot_hrs": 7.0, "lote_prom": 800},
    "RTPS016203": {"puesto": "PTPSBSMP01", "std_cc_hrs": 5.0, "std_env_hrs": 4.0, "std_tot_hrs": 15.0, "lote_prom": 800},
    "HNN0071SA": {"puesto": "PTPSBSMP02", "std_cc_hrs": 5.0, "std_env_hrs": 3.0, "std_tot_hrs": 96.0, "lote_prom": 2300},
    "HPN0075NF": {"puesto": "PTPSBSMP01", "std_cc_hrs": 5.0, "std_env_hrs": 1.0, "std_tot_hrs": 72.0, "lote_prom": 800},
    "HNN0076SA": {"puesto": "PTPSBSMP01", "std_cc_hrs": 5.0, "std_env_hrs": 3.0, "std_tot_hrs": 96.0, "lote_prom": 2400},
    "HPN0071NA": {"puesto": "PTPSBSMP02", "std_cc_hrs": 5.0, "std_env_hrs": 1.0, "std_tot_hrs": 60.0, "lote_prom": 800},
    "VQN0071NA": {"puesto": "PTPSBSMP02", "std_cc_hrs": 5.0, "std_env_hrs": 1.0, "std_tot_hrs": 96.0, "lote_prom": 800},
    "HNB0154NA": {"puesto": "PTPSBSMP03", "std_cc_hrs": 5.0, "std_env_hrs": 3.0, "std_tot_hrs": 24.0, "lote_prom": 2400},
    "VQG0074PB": {"puesto": "PTPSBSMP03", "std_cc_hrs": 5.0, "std_env_hrs": 1.0, "std_tot_hrs": 48.0, "lote_prom": 800},
    "VQB0154PB": {"puesto": "PTPSBSMP03", "std_cc_hrs": 5.0, "std_env_hrs": 1.0, "std_tot_hrs": 48.0, "lote_prom": 800},
    "HNB0151NA": {"puesto": "PTPSBSMP04", "std_cc_hrs": 5.0, "std_env_hrs": 3.0, "std_tot_hrs": 48.0, "lote_prom": 2400},
    "HNG0071NA": {"puesto": "PTPSBSMP04", "std_cc_hrs": 5.0, "std_env_hrs": 1.0, "std_tot_hrs": 72.0, "lote_prom": 800},
    "HPB0155NA": {"puesto": "PTPSBSMP04", "std_cc_hrs": 5.0, "std_env_hrs": 1.0, "std_tot_hrs": 24.0, "lote_prom": 800},
    "HNY0136SA": {"puesto": "PTPSBSMP05", "std_cc_hrs": 5.0, "std_env_hrs": 3.0, "std_tot_hrs": 96.0, "lote_prom": 2400},
    "VQY0134PB": {"puesto": "PTPSBSMP05", "std_cc_hrs": 5.0, "std_env_hrs": 1.0, "std_tot_hrs": 60.0, "lote_prom": 800}
}

CONTRASENA_OPERADOR = "sanchez123"

# =========================================================================
# INICIALIZACIÓN DE ESTADOS
# =========================================================================
if 'ordenes_activas' not in st.session_state:
    st.session_state.ordenes_activas = {}

if 'historial_tiempos' not in st.session_state:
    st.session_state.historial_tiempos = []

if 'programa_ordenes' not in st.session_state:
    st.session_state.programa_ordenes = pd.DataFrame([
        {"ID Orden": "ORD-2026-01", "Código": "VQN0074PB", "Lote": "L-1001", "Cantidad (Kg)": 800, "Estado": "Pendiente"},
        {"ID Orden": "ORD-2026-02", "Código": "HNN0071SA", "Lote": "L-1002", "Cantidad (Kg)": 2300, "Estado": "Pendiente"},
        {"ID Orden": "ORD-2026-03", "Código": "HNB0154NA", "Lote": "L-1003", "Cantidad (Kg)": 2400, "Estado": "Pendiente"}
    ])

# =========================================================================
# FUNCIONES AUXILIARES
# =========================================================================
def obtener_minutos_transcurridos(inicio_str):
    if not inicio_str:
        return 0
    try:
        inicio = datetime.strptime(inicio_str, "%Y-%m-%d %H:%M:%S")
        return int((datetime.now() - inicio).total_seconds() / 60)
    except:
        return 0

def generar_excel_tiempos():
    if not st.session_state.historial_tiempos:
        df = pd.DataFrame(columns=["ID Orden", "Código", "Lote", "Puesto de Trabajo", "Operador", "Fecha Fin", "Pesado (min)", "Humectación (min)", "Molienda (min)", "Envasado (min)", "Total Real (min)", "Std Total (min)", "Estatus"])
    else:
        df = pd.DataFrame(st.session_state.historial_tiempos)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Histórico de Molienda')
    return output.getvalue()

def generar_plantilla_excel():
    df_temp = pd.DataFrame(columns=["ID Orden", "Código", "Lote", "Cantidad (Kg)"])
    df_temp.loc[0] = ["ORD-EJEMPLO", "VQN0074PB", "L-9999", 800]
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_temp.to_excel(writer, index=False, sheet_name='Plantilla')
    return output.getvalue()

# =========================================================================
# SIDEBAR
# =========================================================================
st.sidebar.image("https://img.icons8.com/fluency/96/factory.png", width=60)
st.sidebar.title("🏭 Planta Grupo Sánchez")
st.sidebar.markdown("---")

rol_seleccionado = st.sidebar.radio(
    "📂 Cambiar de Entorno:",
    ["🔍 Panel de Monitoreo (Visual)", "⚙️ Consola Operativa (Ingreso de Datos)"]
)

st.sidebar.markdown("---")
st.sidebar.subheader("📥 Cargar Órdenes Pendientes")
uploaded_file = st.sidebar.file_uploader("Subir archivo Excel (.xlsx)", type=["xlsx"])

if uploaded_file is not None:
    try:
        df_up = pd.read_excel(uploaded_file)
        columnas_obligatorias = {"ID Orden", "Código", "Lote", "Cantidad (Kg)"}
        if columnas_obligatorias.issubset(df_up.columns):
            df_up["Estado"] = "Pendiente"
            st.session_state.programa_ordenes = df_up
            st.sidebar.success("✅ ¡Programa cargado con éxito!")
        else:
            st.sidebar.error("❌ El Excel debe tener columnas: ID Orden, Código, Lote, Cantidad (Kg)")
    except Exception as e:
        st.sidebar.error(f"Error al leer archivo: {e}")

st.sidebar.markdown("---")
st.sidebar.download_button(
    label="📄 Descargar plantilla Excel",
    data=generar_plantilla_excel(),
    file_name="plantilla_ordenes_pendientes.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

# =========================================================================
# VISTA 1: PANEL DE MONITOREO (VISUAL)
# =========================================================================
if rol_seleccionado == "🔍 Panel de Monitoreo (Visual)":
    st.title("🖥️ Tablero de Monitoreo General")
    st.markdown(f"**Estatus de Procesos en Tiempo Real** - Actualizado: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    st.markdown("---")

    # KPIs Principales
    col1, col2, col3, col4 = st.columns(4)
    total_pendientes = len(st.session_state.programa_ordenes[st.session_state.programa_ordenes["Estado"] == "Pendiente"])
    total_activas = len(st.session_state.ordenes_activas)
    total_completadas = len(st.session_state.historial_tiempos)
    
    alertas_activas = 0
    for id_ord, datos in st.session_state.ordenes_activas.items():
        etapa = datos["Etapa"]
        t_trans = obtener_minutos_transcurridos(datos.get(f"Inicio_{etapa}"))
        std_hrs = datos["Est_CC_Min"]/60 if etapa in ["Molienda", "Humectación"] else datos["Est_Env_Min"]/60
        if t_trans > (std_hrs * 60):
            alertas_activas += 1

    col1.metric("📋 Órdenes en Espera", total_pendientes)
    col2.metric("🔄 Fórmulas en Proceso", total_activas)
    col3.metric("🏁 Fórmulas Terminadas", total_completadas)
    col4.metric("🚨 Alertas por Retraso", alertas_activas, delta=f"{alertas_activas} críticas", delta_color="inverse")

    st.markdown("---")

    # PANEL ESTILO KANBAN POR ETAPA
    st.subheader("⚙️ Flujo Automático por Código y Puesto de Trabajo")
    
    if not st.session_state.ordenes_activas:
        st.info("💡 No hay órdenes activas en este momento. El operador debe iniciar una orden desde la Consola Operativa.")
    else:
        col_p, col_h, col_m, col_e = st.columns(4)
        with col_p: st.markdown("##### ⚖️ Pesado")
        with col_h: st.markdown("##### 🧪 Humectación")
        with col_m: st.markdown("##### 🔄 Molienda / CC")
        with col_e: st.markdown("##### 🛍️ Envasado")

        for id_ord, datos in st.session_state.ordenes_activas.items():
            etapa = datos["Etapa"]
            cod = datos["Código"]
            lote = datos["Lote"]
            op = datos["Operador"]
            puesto = datos["Puesto"]
            t_trans = obtener_minutos_transcurridos(datos.get(f"Inicio_{etapa}"))
            
            # Estándar
            std_min = datos["Est_CC_Min"] if etapa in ["Pesado", "Humectación", "Molienda"] else datos["Est_Env_Min"]

            # Determinar color de estatus
            if t_trans > std_min:
                class_card = "code-card code-card-danger"
                badge_html = f'<span class="badge badge-danger">🔴 RETRASADO ({t_trans - int(std_min)} min de exceso)</span>'
            elif t_trans > (std_min * 0.8):
                class_card = "code-card code-card-warning"
                badge_html = '<span class="badge badge-warning">🟡 Cerca del Límite</span>'
            else:
                class_card = "code-card"
                badge_html = '<span class="badge badge-normal">🟢 A Tiempo</span>'

            # 🛠️ DETECTAR EL PASE ACTUAL DINÁMICAMENTE (Solo si está en etapa de Molienda)
            pase_html = ""
            if etapa == "Molienda":
                pases_registrados = datos.get("Pases", [])
                if pases_registrados:
                    # Toma el número de pase del último registro guardado
                    ultimo_pase = pases_registrados[-1]["Pase"]
                    pase_html = f'<br><strong>Pase actual:</strong> <span style="color:#1F497D; font-weight:bold; background-color:#E8F0FE; padding:2px 6px; border-radius:4px;">#{ultimo_pase}</span>'
                else:
                    pase_html = '<br><strong>Pase actual:</strong> <span style="color:gray; font-style:italic;">Sin pases aún</span>'

            # Contenido de la tarjeta (Identificada por el Código y Lote del Material)
            tarjeta_html = f"""
            <div class="{class_card}">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 5px;">
                    <strong style="font-size:1.15rem; color:#1F497D;">{cod}</strong>
                    {badge_html}
                </div>
                <strong>Puesto de Trabajo:</strong> {puesto}<br>
                <strong>Lote:</strong> {lote}<br>
                <strong>ID Orden:</strong> {id_ord}<br>
                <strong>Operador de Etapa:</strong> {op}<br>
                {pase_html}
                <hr style="margin:8px 0; border:0; border-top:1px solid #ddd;">
                <strong>Tiempo etapa:</strong> {t_trans} / {int(std_min)} min
            </div>
            """

            # Ubicar en la columna correspondiente
            if etapa == "Pesado":
                with col_p: st.markdown(tarjeta_html, unsafe_allow_html=True)
            elif etapa == "Humectación":
                with col_h: st.markdown(tarjeta_html, unsafe_allow_html=True)
            elif etapa == "Molienda":
                with col_m: st.markdown(tarjeta_html, unsafe_allow_html=True)
            elif etapa == "Envasado":
                with col_e: st.markdown(tarjeta_html, unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("📅 Programa General de Órdenes")
    st.dataframe(st.session_state.programa_ordenes, use_container_width=True)

# =========================================================================
# VISTA 2: CONSOLA OPERATIVA (EDICIÓN / INGRESO DE DATOS)
# =========================================================================
elif rol_seleccionado == "⚙️ Consola Operativa (Ingreso de Datos)":
    st.title("🛠️ Panel de Control Operativo de Piso")
    
    password = st.text_input("🔑 Introduce la clave de operador para desbloquear cambios:", type="password")
    
    if password != CONTRASENA_OPERADOR:
        st.warning("🔒 Acceso protegido. Introduce la contraseña correcta para operar.")
    else:
        st.success("🔓 Permisos de operador autorizados.")
        
        tab_iniciar, tab_avanzar, tab_historial_excel = st.tabs([
            "🚀 Iniciar / Cargar Orden", "🔧 Actualizar Estatus de Etapas", "📊 Historial de Tiempos y Descarga"
        ])

        # TAB 1: INICIAR ORDEN
        with tab_iniciar:
            st.subheader("Cargar Nueva Fórmula a Proceso")
            
            col_ini1, col_ini2 = st.columns(2)
            
            with col_ini1:
                # Filtrar órdenes con estatus "Pendiente"
                filtro_pendientes = st.session_state.programa_ordenes[st.session_state.programa_ordenes["Estado"] == "Pendiente"]
                if not filtro_pendientes.empty:
                    id_orden_sel = st.selectbox("Seleccionar Orden Programada:", filtro_pendientes["ID Orden"].tolist())
                else:
                    st.info("No hay órdenes pendientes en el programa.")
                    id_orden_sel = None
            
            with col_ini2:
                operador = st.text_input("Operador a Cargo (Inicio):", placeholder="Ej. Juan Pérez")
            
            if st.button("🚀 INICIAR PROCESO", type="primary"):
                if id_orden_sel and operador:
                    detalles_orden = filtro_pendientes[filtro_pendientes["ID Orden"] == id_orden_sel].iloc[0]
                    codigo_prod = detalles_orden["Código"]
                    
                    # Buscar el estándar y puesto automáticamente basándonos en el CÓDIGO
                    estandar = DB_ESTANDARES.get(codigo_prod, {"puesto": "PTPSBSMP_GEN", "std_cc_hrs": 5.0, "std_env_hrs": 3.0, "std_tot_hrs": 24.0})
                    
                    st.session_state.ordenes_activas[id_orden_sel] = {
                        "ID Orden": id_orden_sel,
                        "Código": codigo_prod,
                        "Lote": detalles_orden["Lote"],
                        "Cantidad": detalles_orden["Cantidad (Kg)"],
                        "Operador": operador,
                        "Puesto": estandar["puesto"], # Puesto de trabajo recuperado de forma automática
                        "Etapa": "Pesado",
                        "Inicio_Pesado": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "Est_CC_Min": estandar["std_cc_hrs"] * 60,
                        "Est_Env_Min": estandar["std_env_hrs"] * 60,
                        "Est_Tot_Min": estandar["std_tot_hrs"] * 60,
                        "Pases": []
                    }
                    
                    # Cambiar estado en el programa general
                    st.session_state.programa_ordenes.loc[
                        st.session_state.programa_ordenes["ID Orden"] == id_orden_sel, "Estado"
                    ] = "En Proceso"
                    
                    st.success(f"✅ ¡Fórmula {codigo_prod} (Orden: {id_orden_sel}) iniciada automáticamente en Puesto {estandar['puesto']}!")
                    st.rerun()
                else:
                    st.error("⚠️ Faltan rellenar campos obligatorios.")

        # TAB 2: AVANZAR ETAPAS (CON CAMBIO DE OPERADOR POR ETAPA)
        with tab_avanzar:
            st.subheader("Actualización de Etapas Activas")
            
            if not st.session_state.ordenes_activas:
                st.info("No hay procesos activos en este momento.")
            else:
                # El operador selecciona la orden directamente por su Código e ID
                opciones_activas = {f"{datos['Código']} (Lote: {datos['Lote']}) - Orden: {datos['ID Orden']}": id_ord 
                                   for id_ord, datos in st.session_state.ordenes_activas.items()}
                
                orden_activa_sel = st.selectbox("Seleccione el proceso que desea actualizar:", list(opciones_activas.keys()))
                id_orden_mod = opciones_activas[orden_activa_sel]
                orden = st.session_state.ordenes_activas[id_orden_mod]
                etapa_actual = orden["Etapa"]
                
                st.info(f"📋 **Código:** {orden['Código']} | **Puesto Estándar:** {orden['Puesto']} | **Etapa actual:** {etapa_actual}")

                # 👤 SECCIÓN DE CAMBIO DINÁMICO DE OPERADOR
                st.markdown("##### 👤 Operador en Turno para esta Etapa")
                cambio_op = st.text_input(
                    "Nombre del operador a cargo:", 
                    value=orden["Operador"], 
                    key=f"op_etapa_{id_orden_mod}",
                    help="Modifica este campo si un nuevo operador tomó el relevo en esta etapa."
                )
                orden["Operador"] = cambio_op # Se actualiza dinámicamente en el estado global
                
                st.markdown("---")

                # ETAPA 1: PESADO
                if etapa_actual == "Pesado":
                    if st.button("✔️ Completar Pesado"):
                        orden["Fin_Pesado"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        orden["Etapa"] = "Humectación"
                        orden["Inicio_Humectación"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        st.success("Pesado completado. Avanzado a Humectación.")
                        st.rerun()

                # ETAPA 2: HUMECTACIÓN
                elif etapa_actual == "Humectación":
                    col_h1, col_h2 = st.columns(2)
                    with col_h1:
                        pm = st.text_input("PM Mezclador:", key="pm_h")
                        solidos = st.number_input("% Sólidos:", min_value=0.0, max_value=100.0, value=50.0)
                    with col_h2:
                        visc = st.number_input("Viscosidad (cps):", min_value=0)
                        temp = st.number_input("Temperatura (°C):", min_value=0)
                    
                    if st.button("✔️ Completar Humectación"):
                        orden["Fin_Humectación"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        orden["Datos_Humectacion"] = {"PM": pm, "% Solidos": solidos, "Viscosidad": visc, "Temp": temp}
                        orden["Etapa"] = "Molienda"
                        orden["Inicio_Molienda"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        st.success("Humectación completada. Avanzando a Molienda.")
                        st.rerun()

                # ETAPA 3: MOLIENDA
                elif etapa_actual == "Molienda":
                    st.markdown("##### 🔄 Captura de Pases de Molino")
                    col_p1, col_p2, col_p3 = st.columns(3)
                    with col_p1:
                        n_pase = st.number_input("Pase #:", min_value=1, step=1)
                        rpm_m = st.number_input("RPM Molino:", min_value=0, step=50)
                    with col_p2:
                        temp_m = st.number_input("Temperatura de salida (°C):", min_value=0)
                        pres_m = st.number_input("Presión (bar):", min_value=0.0, step=0.1)
                    with col_p3:
                        st.markdown("<br>", unsafe_allow_html=True)
                        if st.button("📥 Agregar Registro de Pase"):
                            orden["Pases"].append({
                                "Pase": n_pase,
                                "RPM": rpm_m,
                                "Temp": temp_m,
                                "Presión": pres_m,
                                "Hora": datetime.now().strftime("%H:%M:%S")
                            })
                            st.toast("✅ Pase guardado")
                    
                    if orden["Pases"]:
                        st.markdown("**Pases registrados en este lote:**")
                        st.table(pd.DataFrame(orden["Pases"]))

                    st.markdown("---")
                    if st.button("✔️ Completar Molienda y Pasar a Envasado"):
                        orden["Fin_Molienda"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        orden["Etapa"] = "Envasado"
                        orden["Inicio_Envasado"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        st.success("Molienda completada. Avanzando a Envasado.")
                        st.rerun()

                # ETAPA 4: ENVASADO
                elif etapa_actual == "Envasado":
                    col_e1, col_e2 = st.columns(2)
                    with col_e1:
                        cant_real = st.number_input("Cantidad Real Obtenida (Kg):", min_value=0.0, value=float(orden["Cantidad"]))
                    with col_e2:
                        obs = st.text_area("Observaciones del Lote:")

                    if st.button("🏁 CONCLUIR PROCESO Y GUARDAR REGISTROS"):
                        fin_fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        
                        # Cálculo de tiempos reales consumidos
                        t_pesado = obtener_minutos_transcurridos(orden.get("Inicio_Pesado"))
                        t_hum = obtener_minutos_transcurridos(orden.get("Inicio_Humectación"))
                        t_molienda = obtener_minutos_transcurridos(orden.get("Inicio_Molienda"))
                        t_envasado = obtener_minutos_transcurridos(orden.get("Inicio_Envasado"))
                        t_total_real = t_pesado + t_hum + t_molienda + t_envasado
                        
                        estatus_final = "A Tiempo"
                        if t_total_real > orden["Est_Tot_Min"]:
                            estatus_final = "Retrasado"

                        # Guardar histórico
                        st.session_state.historial_tiempos.append({
                            "ID Orden": orden["ID Orden"],
                            "Código": orden["Código"],
                            "Lote": orden["Lote"],
                            "Puesto de Trabajo": orden["Puesto"], # Guardado automático
                            "Operador": orden["Operador"], # Guarda al operador final que concluyó
                            "Fecha Fin": fin_fecha,
                            "Pesado (min)": t_pesado,
                            "Humectación (min)": t_hum,
                            "Molienda (min)": t_molienda,
                            "Envasado (min)": t_envasado,
                            "Total Real (min)": t_total_real,
                            "Std Total (min)": int(orden["Est_Tot_Min"]),
                            "Estatus": estatus_final,
                            "Observaciones": obs
                        })
                        
                        st.session_state.programa_ordenes.loc[
                            st.session_state.programa_ordenes["ID Orden"] == orden["ID Orden"], "Estado"
                        ] = "Terminado"
                        
                        del st.session_state.ordenes_activas[id_orden_mod]
                        
                        st.success(f"🎉 Orden {id_orden_mod} finalizada exitosamente por {orden['Operador']} en el puesto {orden['Puesto']}.")
                        st.rerun()

        # TAB 3: EXPORTACIÓN
        with tab_historial_excel:
            st.subheader("Histórico de Tiempos Realizados")
            
            if not st.session_state.historial_tiempos:
                st.info("No hay datos históricos grabados todavía.")
            else:
                df_hist = pd.DataFrame(st.session_state.historial_tiempos)
                st.dataframe(df_hist, use_container_width=True)
                
                st.download_button(
                    label="📥 Exportar Base de Tiempos a Excel",
                    data=generar_excel_tiempos(),
                    file_name=f"registro_tiempos_molienda_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )