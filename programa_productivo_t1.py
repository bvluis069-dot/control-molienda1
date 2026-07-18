import streamlit as st
import pandas as pd
from datetime import datetime
import io
import sqlite3
import json

# =========================================================================
# CONFIGURACIÓN DE PÁGINA Y ESTILOS
# =========================================================================
st.set_page_config(
    page_title="Control de Molienda - Grupo Sánchez",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .code-card {
        padding: 1.25rem;
        border-radius: 10px;
        background-color: #F8F9FA;
        border-left: 6px solid #1F497D;
        margin-bottom: 1rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .code-card-warning { border-left-color: #FFA500; }
    .code-card-danger { border-left-color: #D9534F; background-color: #FFF5F5; }
    .badge { padding: 0.25rem 0.6rem; border-radius: 5px; font-weight: bold; font-size: 0.85rem; }
    .badge-normal { background-color: #D4EDDA; color: #155724; }
    .badge-warning { background-color: #FFF3CD; color: #856404; }
    .badge-danger { background-color: #F8D7DA; color: #721C24; }
    .badge-cc { background-color: #CCE5FF; color: #004085; }
    .box-cc {
        background-color: #EAF4FF;
        border: 2px solid #1F497D;
        border-radius: 10px;
        padding: 1rem;
        margin-bottom: 1rem;
    }
    .box-prod {
        background-color: #FFF8E1;
        border: 2px dashed #FFA500;
        border-radius: 10px;
        padding: 1rem;
        margin-bottom: 1rem;
    }
    [data-testid="stMetricValue"] { font-size: 1.8rem; font-weight: bold; }
    .stButton > button { width: 100%; border-radius: 6px; }
</style>
""", unsafe_allow_html=True)

# =========================================================================
# CONTRASEÑAS
# =========================================================================
CONTRASENA_OPERADOR  = "sanchez123"   # Producción
CONTRASENA_CALIDAD   = "calidad456"   # Control de Calidad

# =========================================================================
# ESTÁNDARES DE PRODUCTO
# =========================================================================
DB_ESTANDARES = {
    "VQN0074PB":  {"std_cc_hrs": 5.0, "std_env_hrs": 3.0,  "std_tot_hrs": 24.0,  "lote_prom": 800},
    "FZ9002":     {"std_cc_hrs": 1.0, "std_env_hrs": 1.0,  "std_tot_hrs": 6.0,   "lote_prom": 800},
    "PSJI930136": {"std_cc_hrs": 2.0, "std_env_hrs": 1.0,  "std_tot_hrs": 3.0,   "lote_prom": 800},
    "PSMM951200": {"std_cc_hrs": 2.0, "std_env_hrs": 1.0,  "std_tot_hrs": 3.0,   "lote_prom": 800},
    "PSGN6080473":{"std_cc_hrs": 5.0, "std_env_hrs": 1.0,  "std_tot_hrs": 7.0,   "lote_prom": 800},
    "RTPS016203": {"std_cc_hrs": 5.0, "std_env_hrs": 4.0,  "std_tot_hrs": 15.0,  "lote_prom": 800},
    "HNN0071SA":  {"std_cc_hrs": 5.0, "std_env_hrs": 3.0,  "std_tot_hrs": 96.0,  "lote_prom": 2300},
    "HPN0075NF":  {"std_cc_hrs": 5.0, "std_env_hrs": 1.0,  "std_tot_hrs": 72.0,  "lote_prom": 800},
    "HNN0076SA":  {"std_cc_hrs": 5.0, "std_env_hrs": 3.0,  "std_tot_hrs": 96.0,  "lote_prom": 2400},
    "HPN0071NA":  {"std_cc_hrs": 5.0, "std_env_hrs": 1.0,  "std_tot_hrs": 60.0,  "lote_prom": 800},
    "VQN0071NA":  {"std_cc_hrs": 5.0, "std_env_hrs": 1.0,  "std_tot_hrs": 96.0,  "lote_prom": 800},
    "HNB0154NA":  {"std_cc_hrs": 5.0, "std_env_hrs": 3.0,  "std_tot_hrs": 24.0,  "lote_prom": 2400},
    "VQG0074PB":  {"std_cc_hrs": 5.0, "std_env_hrs": 1.0,  "std_tot_hrs": 48.0,  "lote_prom": 800},
    "VQB0154PB":  {"std_cc_hrs": 5.0, "std_env_hrs": 1.0,  "std_tot_hrs": 48.0,  "lote_prom": 800},
    "HNB0151NA":  {"std_cc_hrs": 5.0, "std_env_hrs": 3.0,  "std_tot_hrs": 48.0,  "lote_prom": 2400},
    "HNG0071NA":  {"std_cc_hrs": 5.0, "std_env_hrs": 1.0,  "std_tot_hrs": 72.0,  "lote_prom": 800},
    "HPB0155NA":  {"std_cc_hrs": 5.0, "std_env_hrs": 1.0,  "std_tot_hrs": 24.0,  "lote_prom": 800},
    "HNY0136SA":  {"std_cc_hrs": 5.0, "std_env_hrs": 3.0,  "std_tot_hrs": 96.0,  "lote_prom": 2400},
    "VQY0134PB":  {"std_cc_hrs": 5.0, "std_env_hrs": 1.0,  "std_tot_hrs": 60.0,  "lote_prom": 800},
}

# =========================================================================
# BASE DE DATOS SQLite
# =========================================================================
DB_FILE = "molienda_database.db"

def conectar_db():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

def inicializar_base_datos():
    conn = conectar_db()
    cur = conn.cursor()

    # Programa de órdenes
    cur.execute("""
        CREATE TABLE IF NOT EXISTS programa_ordenes (
            id_orden TEXT PRIMARY KEY,
            codigo TEXT,
            lote TEXT,
            cantidad REAL,
            estado TEXT DEFAULT 'Pendiente'
        )
    """)

    # Órdenes activas — columna puesto ya no viene de estándar, el usuario la pone
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ordenes_activas (
            id_orden           TEXT PRIMARY KEY,
            codigo             TEXT,
            lote               TEXT,
            cantidad           REAL,
            puesto             TEXT,
            etapa              TEXT,
            -- Operadores por etapa
            op_pesado          TEXT,
            op_humectacion     TEXT,
            op_molienda        TEXT,
            op_envasado        TEXT,
            -- Marcas de tiempo
            inicio_pesado      TEXT,
            inicio_humectacion TEXT,
            inicio_molienda    TEXT,
            inicio_envasado    TEXT,
            -- Estándares (minutos)
            est_cc_min         REAL,
            est_env_min        REAL,
            est_tot_min        REAL,
            -- Datos de proceso
            pases              TEXT,
            datos_dispersion   TEXT,   -- Lo que captura Producción en Humectación
            datos_cc_hum       TEXT,   -- Lo que captura Calidad en Humectación
            cc_aprobado        INTEGER DEFAULT 0  -- 0=pendiente, 1=aprobado
        )
    """)

    # Histórico — incluye operador por etapa
    cur.execute("""
        CREATE TABLE IF NOT EXISTS historial_tiempos (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            id_orden         TEXT,
            codigo           TEXT,
            lote             TEXT,
            puesto           TEXT,
            op_pesado        TEXT,
            op_humectacion   TEXT,
            op_molienda      TEXT,
            op_envasado      TEXT,
            fecha_fin        TEXT,
            t_pesado         REAL,
            t_hum            REAL,
            t_molienda       REAL,
            t_envasado       REAL,
            t_total_real     REAL,
            std_total        REAL,
            estatus          TEXT,
            observaciones    TEXT,
            -- Parámetros de dispersión (Producción)
            disp_pm          TEXT,
            disp_solidos     REAL,
            disp_visc        REAL,
            disp_temp        REAL,
            -- Parámetros CC Humectación (Calidad)
            cc_analista      TEXT,
            cc_ph            REAL,
            cc_visc_cc       REAL,
            cc_observaciones TEXT
        )
    """)

    # Datos de prueba
    cur.execute("SELECT COUNT(*) FROM programa_ordenes")
    if cur.fetchone()[0] == 0:
        cur.executemany("""
            INSERT INTO programa_ordenes (id_orden, codigo, lote, cantidad, estado)
            VALUES (?, ?, ?, ?, ?)
        """, [
            ("ORD-2026-01", "VQN0074PB", "L-1001", 800,  "Pendiente"),
            ("ORD-2026-02", "HNN0071SA", "L-1002", 2300, "Pendiente"),
            ("ORD-2026-03", "HNB0154NA", "L-1003", 2400, "Pendiente"),
        ])

    conn.commit()
    conn.close()

inicializar_base_datos()

# ─── Helpers de DB ────────────────────────────────────────────────────────────

def obtener_programa_db():
    conn = conectar_db()
    df = pd.read_sql_query("SELECT * FROM programa_ordenes", conn)
    conn.close()
    return df

def guardar_programa_excel_db(df_up):
    conn = conectar_db()
    cur = conn.cursor()
    for _, row in df_up.iterrows():
        cur.execute("""
            INSERT OR REPLACE INTO programa_ordenes (id_orden, codigo, lote, cantidad, estado)
            VALUES (?, ?, ?, ?, 'Pendiente')
        """, (str(row["ID Orden"]), str(row["Código"]), str(row["Lote"]), float(row["Cantidad (Kg)"])))
    conn.commit()
    conn.close()

def actualizar_estado_orden_db(id_orden, estado):
    conn = conectar_db()
    cur = conn.cursor()
    cur.execute("UPDATE programa_ordenes SET estado=? WHERE id_orden=?", (estado, id_orden))
    conn.commit()
    conn.close()

def _row_to_orden(row_dict):
    d = row_dict
    return {
        "ID Orden":           d["id_orden"],
        "Código":             d["codigo"],
        "Lote":               d["lote"],
        "Cantidad":           d["cantidad"],
        "Puesto":             d["puesto"],
        "Etapa":              d["etapa"],
        "Op_Pesado":          d.get("op_pesado") or "",
        "Op_Humectacion":     d.get("op_humectacion") or "",
        "Op_Molienda":        d.get("op_molienda") or "",
        "Op_Envasado":        d.get("op_envasado") or "",
        "Inicio_Pesado":      d.get("inicio_pesado"),
        "Inicio_Humectación": d.get("inicio_humectacion"),
        "Inicio_Molienda":    d.get("inicio_molienda"),
        "Inicio_Envasado":    d.get("inicio_envasado"),
        "Est_CC_Min":         d["est_cc_min"],
        "Est_Env_Min":        d["est_env_min"],
        "Est_Tot_Min":        d["est_tot_min"],
        "Pases":              json.loads(d["pases"]) if d.get("pases") else [],
        "Datos_Dispersion":   json.loads(d["datos_dispersion"]) if d.get("datos_dispersion") else {},
        "Datos_CC_Hum":       json.loads(d["datos_cc_hum"]) if d.get("datos_cc_hum") else {},
        "CC_Aprobado":        bool(d.get("cc_aprobado", 0)),
    }

def obtener_ordenes_activas_db():
    conn = conectar_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM ordenes_activas")
    rows = cur.fetchall()
    cols = [c[0] for c in cur.description]
    conn.close()
    return {r[0]: _row_to_orden(dict(zip(cols, r))) for r in rows}

def guardar_orden_activa_db(id_orden, d):
    conn = conectar_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT OR REPLACE INTO ordenes_activas (
            id_orden, codigo, lote, cantidad, puesto, etapa,
            op_pesado, op_humectacion, op_molienda, op_envasado,
            inicio_pesado, inicio_humectacion, inicio_molienda, inicio_envasado,
            est_cc_min, est_env_min, est_tot_min,
            pases, datos_dispersion, datos_cc_hum, cc_aprobado
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        id_orden, d["Código"], d["Lote"], d["Cantidad"], d["Puesto"], d["Etapa"],
        d.get("Op_Pesado",""), d.get("Op_Humectacion",""),
        d.get("Op_Molienda",""), d.get("Op_Envasado",""),
        d.get("Inicio_Pesado"), d.get("Inicio_Humectación"),
        d.get("Inicio_Molienda"), d.get("Inicio_Envasado"),
        d["Est_CC_Min"], d["Est_Env_Min"], d["Est_Tot_Min"],
        json.dumps(d.get("Pases", [])),
        json.dumps(d.get("Datos_Dispersion", {})),
        json.dumps(d.get("Datos_CC_Hum", {})),
        1 if d.get("CC_Aprobado") else 0,
    ))
    conn.commit()
    conn.close()

def eliminar_orden_activa_db(id_orden):
    conn = conectar_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM ordenes_activas WHERE id_orden=?", (id_orden,))
    conn.commit()
    conn.close()

def guardar_en_historico_db(h):
    conn = conectar_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO historial_tiempos (
            id_orden, codigo, lote, puesto,
            op_pesado, op_humectacion, op_molienda, op_envasado,
            fecha_fin, t_pesado, t_hum, t_molienda, t_envasado,
            t_total_real, std_total, estatus, observaciones,
            disp_pm, disp_solidos, disp_visc, disp_temp,
            cc_analista, cc_ph, cc_visc_cc, cc_observaciones
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        h["ID Orden"], h["Código"], h["Lote"], h["Puesto"],
        h["Op_Pesado"], h["Op_Humectacion"], h["Op_Molienda"], h["Op_Envasado"],
        h["Fecha Fin"], h["t_pesado"], h["t_hum"], h["t_molienda"], h["t_envasado"],
        h["t_total_real"], h["std_total"], h["estatus"], h.get("observaciones",""),
        h.get("disp_pm",""), h.get("disp_solidos",0), h.get("disp_visc",0), h.get("disp_temp",0),
        h.get("cc_analista",""), h.get("cc_ph",0), h.get("cc_visc_cc",0), h.get("cc_observaciones",""),
    ))
    conn.commit()
    conn.close()

def obtener_historico_db():
    conn = conectar_db()
    df = pd.read_sql_query("""
        SELECT
            id_orden         AS "ID Orden",
            codigo           AS "Código",
            lote             AS "Lote",
            puesto           AS "Puesto de Trabajo",
            op_pesado        AS "Operador Pesado",
            op_humectacion   AS "Operador Humectación",
            op_molienda      AS "Operador Molienda",
            op_envasado      AS "Operador Envasado",
            fecha_fin        AS "Fecha Fin",
            t_pesado         AS "Pesado (min)",
            t_hum            AS "Humectación (min)",
            t_molienda       AS "Molienda (min)",
            t_envasado       AS "Envasado (min)",
            t_total_real     AS "Total Real (min)",
            std_total        AS "Std Total (min)",
            estatus          AS "Estatus",
            observaciones    AS "Observaciones",
            disp_pm          AS "Dispersión - PM Mezclador",
            disp_solidos     AS "Dispersión - % Sólidos",
            disp_visc        AS "Dispersión - Viscosidad (cps)",
            disp_temp        AS "Dispersión - Temperatura (°C)",
            cc_analista      AS "CC - Analista",
            cc_ph            AS "CC - pH",
            cc_visc_cc       AS "CC - Viscosidad CC (cps)",
            cc_observaciones AS "CC - Observaciones"
        FROM historial_tiempos
        ORDER BY id DESC
    """, conn)
    conn.close()
    return df

# ─── Auxiliares de tiempo ─────────────────────────────────────────────────────

def minutos_transcurridos(inicio_str):
    if not inicio_str:
        return 0
    try:
        inicio = datetime.strptime(inicio_str, "%Y-%m-%d %H:%M:%S")
        return int((datetime.now() - inicio).total_seconds() / 60)
    except:
        return 0

def ahora():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# ─── Generadores Excel ────────────────────────────────────────────────────────

def generar_excel_historico():
    df = obtener_historico_db()
    if df.empty:
        df = pd.DataFrame()
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
        # Hoja 1: Histórico completo
        df.to_excel(writer, index=False, sheet_name="Histórico Completo")

        # Hoja 2: Resumen por operador
        if not df.empty:
            operadores = {}
            for col_op, etapa in [
                ("Operador Pesado",      "Pesado"),
                ("Operador Humectación", "Humectación"),
                ("Operador Molienda",    "Molienda"),
                ("Operador Envasado",    "Envasado"),
            ]:
                if col_op in df.columns:
                    for _, row in df.iterrows():
                        op = str(row[col_op]).strip()
                        if op and op != "nan":
                            if op not in operadores:
                                operadores[op] = {"Operador": op}
                            key = f"# Etapas {etapa}"
                            operadores[op][key] = operadores[op].get(key, 0) + 1

            if operadores:
                df_ops = pd.DataFrame(list(operadores.values())).fillna(0)
                df_ops.to_excel(writer, index=False, sheet_name="Participación Operadores")

        # Hoja 3: Parámetros de proceso
        cols_proceso = [
            "ID Orden","Código","Lote","Fecha Fin",
            "Dispersión - PM Mezclador","Dispersión - % Sólidos",
            "Dispersión - Viscosidad (cps)","Dispersión - Temperatura (°C)",
            "CC - Analista","CC - pH","CC - Viscosidad CC (cps)","CC - Observaciones"
        ]
        cols_disp = [c for c in cols_proceso if c in df.columns]
        if cols_disp:
            df[cols_disp].to_excel(writer, index=False, sheet_name="Parámetros de Proceso")

    return buf.getvalue()

def generar_plantilla_excel():
    df_temp = pd.DataFrame([["ORD-EJEMPLO", "VQN0074PB", "L-9999", 800]],
                           columns=["ID Orden", "Código", "Lote", "Cantidad (Kg)"])
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
        df_temp.to_excel(writer, index=False, sheet_name="Plantilla")
    return buf.getvalue()

# =========================================================================
# CARGA DE DATOS
# =========================================================================
df_programa_raw  = obtener_programa_db()
ordenes_activas  = obtener_ordenes_activas_db()

df_programa_ui = df_programa_raw.rename(columns={
    "id_orden": "ID Orden", "codigo": "Código",
    "lote": "Lote", "cantidad": "Cantidad (Kg)", "estado": "Estado"
})

# =========================================================================
# SIDEBAR
# =========================================================================
st.sidebar.image("https://img.icons8.com/fluency/96/factory.png", width=60)
st.sidebar.title("🏭 Planta Grupo Sánchez")
st.sidebar.markdown("---")

rol_seleccionado = st.sidebar.radio(
    "📂 Seleccionar Vista:",
    ["🔍 Panel de Monitoreo (Visual)", "⚙️ Consola Operativa (Producción)", "🔬 Consola Calidad"]
)

st.sidebar.markdown("---")
st.sidebar.subheader("📥 Cargar Órdenes (Excel)")
uploaded_file = st.sidebar.file_uploader("Subir archivo .xlsx", type=["xlsx"])

if uploaded_file is not None:
    try:
        df_up = pd.read_excel(uploaded_file)
        cols_req = {"ID Orden", "Código", "Lote", "Cantidad (Kg)"}
        if cols_req.issubset(df_up.columns):
            guardar_programa_excel_db(df_up)
            st.sidebar.success("✅ Programa cargado correctamente.")
            st.rerun()
        else:
            st.sidebar.error("❌ El Excel necesita: ID Orden, Código, Lote, Cantidad (Kg)")
    except Exception as e:
        st.sidebar.error(f"Error: {e}")

st.sidebar.download_button(
    "📄 Descargar plantilla Excel",
    data=generar_plantilla_excel(),
    file_name="plantilla_ordenes.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

# =========================================================================
# VISTA 1: PANEL DE MONITOREO
# =========================================================================
if rol_seleccionado == "🔍 Panel de Monitoreo (Visual)":

    col_t1, col_t2 = st.columns([4, 1])
    with col_t1:
        st.title("🖥️ Tablero de Monitoreo General")
        st.markdown(f"**Actualizado:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    with col_t2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 Sincronizar"):
            st.rerun()

    st.markdown("---")

    # KPIs
    total_pendientes  = len(df_programa_ui[df_programa_ui["Estado"] == "Pendiente"])
    total_activas     = len(ordenes_activas)
    df_hist_kpi       = obtener_historico_db()
    total_completadas = len(df_hist_kpi)

    alertas = sum(
        1 for d in ordenes_activas.values()
        if minutos_transcurridos(d.get(f"Inicio_{d['Etapa']}")) >
           (d["Est_CC_Min"] if d["Etapa"] in ["Pesado","Humectación","Molienda"] else d["Est_Env_Min"])
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📋 En Espera",    total_pendientes)
    c2.metric("🔄 En Proceso",   total_activas)
    c3.metric("🏁 Terminadas",   total_completadas)
    c4.metric("🚨 Alertas",      alertas, delta=f"{alertas} críticas", delta_color="inverse")

    st.markdown("---")
    st.subheader("⚙️ Flujo de Procesos Activos")

    if not ordenes_activas:
        st.info("💡 No hay órdenes activas en este momento.")
    else:
        col_p, col_h, col_m, col_e = st.columns(4)
        with col_p: st.markdown("##### ⚖️ Pesado")
        with col_h: st.markdown("##### 🧪 Humectación")
        with col_m: st.markdown("##### 🔄 Molienda / CC")
        with col_e: st.markdown("##### 🛍️ Envasado")

        for id_ord, datos in ordenes_activas.items():
            etapa   = datos["Etapa"]
            t_trans = minutos_transcurridos(datos.get(f"Inicio_{etapa}"))
            std_min = datos["Est_CC_Min"] if etapa in ["Pesado","Humectación","Molienda"] else datos["Est_Env_Min"]

            if t_trans > std_min:
                cls   = "code-card code-card-danger"
                badge = f'<span class="badge badge-danger">🔴 RETRASADO ({t_trans - int(std_min)} min exceso)</span>'
            elif t_trans > std_min * 0.8:
                cls   = "code-card code-card-warning"
                badge = '<span class="badge badge-warning">🟡 Cerca del Límite</span>'
            else:
                cls   = "code-card"
                badge = '<span class="badge badge-normal">🟢 A Tiempo</span>'

            # Indicador de aprobación CC en Humectación
            cc_badge = ""
            if etapa == "Humectación":
                if datos.get("CC_Aprobado"):
                    cc_badge = '<br><span class="badge badge-normal">✅ CC Aprobado — Listo para Molienda</span>'
                elif datos.get("Datos_Dispersion"):
                    cc_badge = '<br><span class="badge badge-cc">🔵 Dispersión capturada — En espera de CC</span>'
                else:
                    cc_badge = '<br><span class="badge badge-warning">⏳ Pendiente captura Producción</span>'

            pase_html = ""
            if etapa == "Molienda" and datos.get("Pases"):
                ultimo = datos["Pases"][-1]["Pase"]
                pase_html = f'<br><strong>Pase actual:</strong> <span style="color:#1F497D;font-weight:bold;background:#E8F0FE;padding:2px 6px;border-radius:4px;">#{ultimo}</span>'

            # Operador de la etapa actual
            op_key  = f"Op_{etapa.replace('ó','o').replace('ú','u')}"
            op_disp = datos.get(op_key, datos.get("Op_Pesado","—"))

            html = f"""
            <div class="{cls}">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:5px;">
                    <strong style="font-size:1.1rem;color:#1F497D;">{datos['Código']}</strong>
                    {badge}
                </div>
                <strong>Puesto:</strong> {datos['Puesto']}<br>
                <strong>Lote:</strong> {datos['Lote']}  &nbsp;|&nbsp; <strong>Orden:</strong> {id_ord}<br>
                <strong>Operador:</strong> {op_disp}
                {cc_badge}{pase_html}
                <hr style="margin:8px 0;border:0;border-top:1px solid #ddd;">
                <strong>Tiempo etapa:</strong> {t_trans} / {int(std_min)} min
            </div>
            """
            target = {"Pesado": col_p, "Humectación": col_h, "Molienda": col_m, "Envasado": col_e}.get(etapa)
            if target:
                with target:
                    st.markdown(html, unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("📅 Órdenes Pendientes")
    df_pend = df_programa_ui[df_programa_ui["Estado"] == "Pendiente"]
    if df_pend.empty:
        st.info("🎉 No hay órdenes pendientes. Todo el programa está en proceso o terminado.")
    else:
        st.dataframe(df_pend, use_container_width=True)

    with st.expander("🔍 Ver historial completo de estados"):
        st.dataframe(df_programa_ui, use_container_width=True)


# =========================================================================
# VISTA 2: CONSOLA OPERATIVA (PRODUCCIÓN)
# =========================================================================
elif rol_seleccionado == "⚙️ Consola Operativa (Producción)":
    st.title("🛠️ Panel de Control — Producción")

    pwd = st.text_input("🔑 Contraseña de Producción:", type="password")
    if pwd != CONTRASENA_OPERADOR:
        st.warning("🔒 Introduce la contraseña de producción para continuar.")
    else:
        st.success("🔓 Acceso de Producción autorizado.")

        tab_ini, tab_avanzar, tab_export = st.tabs([
            "🚀 Iniciar Orden", "🔧 Actualizar Etapas", "📊 Histórico y Exportar"
        ])

        # ── TAB 1: INICIAR ORDEN ─────────────────────────────────────────────
        with tab_ini:
            st.subheader("Cargar Nueva Fórmula a Proceso")

            filtro_pend = df_programa_ui[df_programa_ui["Estado"] == "Pendiente"]
            if filtro_pend.empty:
                st.info("No hay órdenes pendientes.")
            else:
                c1, c2 = st.columns(2)
                with c1:
                    id_sel = st.selectbox("Orden Programada:", filtro_pend["ID Orden"].tolist())
                    operador_ini = st.text_input("Operador a cargo (Pesado):", placeholder="Ej. Juan Pérez")
                with c2:
                    # Puesto MANUAL — el usuario lo escribe o elige
                    detalles = filtro_pend[filtro_pend["ID Orden"] == id_sel].iloc[0]
                    codigo_sel = detalles["Código"]
                    st.info(f"**Código:** {codigo_sel}  |  **Lote:** {detalles['Lote']}  |  **Cantidad:** {detalles['Cantidad (Kg)']} Kg")
                    puesto_manual = st.text_input(
                        "Puesto de Trabajo (manual):",
                        placeholder="Ej. PTPSBSMP01",
                        help="Escribe el puesto de trabajo asignado para esta orden."
                    )

                if st.button("🚀 INICIAR PROCESO", type="primary"):
                    if id_sel and operador_ini and puesto_manual:
                        std = DB_ESTANDARES.get(codigo_sel, {
                            "std_cc_hrs": 5.0, "std_env_hrs": 3.0, "std_tot_hrs": 24.0
                        })
                        nueva = {
                            "ID Orden":           id_sel,
                            "Código":             codigo_sel,
                            "Lote":               detalles["Lote"],
                            "Cantidad":           detalles["Cantidad (Kg)"],
                            "Puesto":             puesto_manual.strip().upper(),
                            "Etapa":              "Pesado",
                            "Op_Pesado":          operador_ini,
                            "Op_Humectacion":     "",
                            "Op_Molienda":        "",
                            "Op_Envasado":        "",
                            "Inicio_Pesado":      ahora(),
                            "Inicio_Humectación": None,
                            "Inicio_Molienda":    None,
                            "Inicio_Envasado":    None,
                            "Est_CC_Min":         std["std_cc_hrs"] * 60,
                            "Est_Env_Min":        std["std_env_hrs"] * 60,
                            "Est_Tot_Min":        std["std_tot_hrs"] * 60,
                            "Pases":              [],
                            "Datos_Dispersion":   {},
                            "Datos_CC_Hum":       {},
                            "CC_Aprobado":        False,
                        }
                        guardar_orden_activa_db(id_sel, nueva)
                        actualizar_estado_orden_db(id_sel, "En Proceso")
                        st.success(f"✅ Orden {id_sel} iniciada en puesto {puesto_manual.upper()}.")
                        st.rerun()
                    else:
                        st.error("⚠️ Completa todos los campos: orden, operador y puesto de trabajo.")

        # ── TAB 2: AVANZAR ETAPAS ────────────────────────────────────────────
        with tab_avanzar:
            st.subheader("Actualización de Etapas")

            ordenes_activas = obtener_ordenes_activas_db()
            if not ordenes_activas:
                st.info("No hay procesos activos.")
            else:
                opciones = {
                    f"{d['Código']} | Lote: {d['Lote']} | {d['ID Orden']}": k
                    for k, d in ordenes_activas.items()
                }
                sel_label = st.selectbox("Proceso a actualizar:", list(opciones.keys()))
                id_mod    = opciones[sel_label]
                orden     = ordenes_activas[id_mod]
                etapa     = orden["Etapa"]

                st.info(f"📋 **Código:** {orden['Código']}  |  **Puesto:** {orden['Puesto']}  |  **Etapa:** {etapa}")

                # Cambio de operador en etapa actual
                op_key = f"Op_{etapa.replace('ó','o').replace('ú','u')}"
                nuevo_op = st.text_input("Operador de esta etapa:", value=orden.get(op_key,""), key=f"op_{id_mod}")
                if nuevo_op != orden.get(op_key,""):
                    orden[op_key] = nuevo_op
                    guardar_orden_activa_db(id_mod, orden)

                st.markdown("---")

                # ── PESADO ────────────────────────────────────────────────────
                if etapa == "Pesado":
                    st.markdown("#### ⚖️ Etapa: Pesado")
                    if st.button("✔️ Completar Pesado → Pasar a Humectación"):
                        orden["Etapa"]              = "Humectación"
                        orden["Op_Humectacion"]     = nuevo_op
                        orden["Inicio_Humectación"] = ahora()
                        guardar_orden_activa_db(id_mod, orden)
                        st.success("Pesado completado. Avanzado a Humectación.")
                        st.rerun()

                # ── HUMECTACIÓN (solo captura Dispersión — Producción) ─────────
                elif etapa == "Humectación":
                    st.markdown("#### 🧪 Etapa: Humectación")

                    # ─ Sección Producción: Dispersión ─
                    st.markdown('<div class="box-prod">', unsafe_allow_html=True)
                    st.markdown("**📋 PRODUCCIÓN — Captura de Dispersión / Humectación**")

                    disp = orden.get("Datos_Dispersion", {})
                    col_h1, col_h2 = st.columns(2)
                    with col_h1:
                        pm       = st.text_input("PM Mezclador:",    value=disp.get("PM",""),       key="pm_disp")
                        solidos  = st.number_input("% Sólidos:",      min_value=0.0, max_value=100.0,
                                                   value=float(disp.get("% Solidos", 50.0)),        key="sol_disp")
                    with col_h2:
                        visc     = st.number_input("Viscosidad (cps):", min_value=0,
                                                   value=int(disp.get("Viscosidad", 0)),             key="visc_disp")
                        temp     = st.number_input("Temperatura (°C):", min_value=0,
                                                   value=int(disp.get("Temp", 0)),                   key="temp_disp")

                    if st.button("💾 Guardar Dispersión (Producción)"):
                        orden["Datos_Dispersion"] = {"PM": pm, "% Solidos": solidos,
                                                     "Viscosidad": visc, "Temp": temp}
                        guardar_orden_activa_db(id_mod, orden)
                        st.success("✅ Dispersión guardada. Espera el visto bueno de Calidad.")
                        st.rerun()

                    st.markdown('</div>', unsafe_allow_html=True)

                    # Estado CC
                    if not orden.get("Datos_Dispersion"):
                        st.warning("⏳ Aún no se han guardado los datos de dispersión.")
                    elif not orden.get("CC_Aprobado"):
                        st.info("🔵 Datos de dispersión guardados. Control de Calidad debe dar visto bueno desde la **Consola Calidad**.")
                    else:
                        st.success("✅ Control de Calidad aprobó esta humectación. Ya puedes avanzar a Molienda.")
                        op_mol = st.text_input("Operador para Molienda:", key="op_mol_from_hum")
                        if st.button("▶️ Iniciar Molienda"):
                            if op_mol:
                                orden["Etapa"]           = "Molienda"
                                orden["Op_Molienda"]     = op_mol
                                orden["Inicio_Molienda"] = ahora()
                                guardar_orden_activa_db(id_mod, orden)
                                st.success("Avanzado a Molienda.")
                                st.rerun()
                            else:
                                st.error("Indica el operador de molienda.")

                # ── MOLIENDA ──────────────────────────────────────────────────
                elif etapa == "Molienda":
                    st.markdown("#### 🔄 Etapa: Molienda")
                    c_p1, c_p2, c_p3 = st.columns(3)
                    with c_p1:
                        n_pase = st.number_input("Pase #:", min_value=1, step=1)
                        rpm_m  = st.number_input("RPM Molino:", min_value=0, step=50)
                    with c_p2:
                        temp_m = st.number_input("Temperatura salida (°C):", min_value=0)
                        pres_m = st.number_input("Presión (bar):", min_value=0.0, step=0.1)
                    with c_p3:
                        st.markdown("<br><br>", unsafe_allow_html=True)
                        if st.button("📥 Agregar Pase"):
                            pases = orden.get("Pases", [])
                            pases.append({"Pase": n_pase, "RPM": rpm_m,
                                          "Temp": temp_m, "Presión": pres_m,
                                          "Hora": datetime.now().strftime("%H:%M:%S")})
                            orden["Pases"] = pases
                            guardar_orden_activa_db(id_mod, orden)
                            st.toast("✅ Pase guardado")
                            st.rerun()

                    if orden.get("Pases"):
                        st.markdown("**Pases registrados:**")
                        st.table(pd.DataFrame(orden["Pases"]))

                    st.markdown("---")
                    op_env = st.text_input("Operador para Envasado:", key="op_env_from_mol")
                    if st.button("✔️ Completar Molienda → Pasar a Envasado"):
                        if op_env:
                            orden["Etapa"]          = "Envasado"
                            orden["Op_Envasado"]    = op_env
                            orden["Inicio_Envasado"]= ahora()
                            guardar_orden_activa_db(id_mod, orden)
                            st.success("Molienda completada. Avanzando a Envasado.")
                            st.rerun()
                        else:
                            st.error("Indica el operador de envasado.")

                # ── ENVASADO ──────────────────────────────────────────────────
                elif etapa == "Envasado":
                    st.markdown("#### 🛍️ Etapa: Envasado")
                    c_e1, c_e2 = st.columns(2)
                    with c_e1:
                        cant_real = st.number_input("Cantidad Real Obtenida (Kg):",
                                                    min_value=0.0, value=float(orden["Cantidad"]))
                    with c_e2:
                        obs = st.text_area("Observaciones del Lote:")

                    if st.button("🏁 CONCLUIR PROCESO Y CERRAR ORDEN", type="primary"):
                        fin = ahora()
                        t_p = minutos_transcurridos(orden.get("Inicio_Pesado"))
                        t_h = minutos_transcurridos(orden.get("Inicio_Humectación"))
                        t_m = minutos_transcurridos(orden.get("Inicio_Molienda"))
                        t_e = minutos_transcurridos(orden.get("Inicio_Envasado"))
                        t_r = t_p + t_h + t_m + t_e

                        disp = orden.get("Datos_Dispersion", {})
                        cc   = orden.get("Datos_CC_Hum", {})

                        hist = {
                            "ID Orden":       orden["ID Orden"],
                            "Código":         orden["Código"],
                            "Lote":           orden["Lote"],
                            "Puesto":         orden["Puesto"],
                            "Op_Pesado":      orden.get("Op_Pesado",""),
                            "Op_Humectacion": orden.get("Op_Humectacion",""),
                            "Op_Molienda":    orden.get("Op_Molienda",""),
                            "Op_Envasado":    orden.get("Op_Envasado",""),
                            "Fecha Fin":      fin,
                            "t_pesado":       t_p,
                            "t_hum":          t_h,
                            "t_molienda":     t_m,
                            "t_envasado":     t_e,
                            "t_total_real":   t_r,
                            "std_total":      int(orden["Est_Tot_Min"]),
                            "estatus":        "A Tiempo" if t_r <= orden["Est_Tot_Min"] else "Retrasado",
                            "observaciones":  obs,
                            "disp_pm":        disp.get("PM",""),
                            "disp_solidos":   disp.get("% Solidos", 0),
                            "disp_visc":      disp.get("Viscosidad", 0),
                            "disp_temp":      disp.get("Temp", 0),
                            "cc_analista":    cc.get("Analista",""),
                            "cc_ph":          cc.get("pH", 0),
                            "cc_visc_cc":     cc.get("Viscosidad CC", 0),
                            "cc_observaciones": cc.get("Observaciones",""),
                        }
                        guardar_en_historico_db(hist)
                        actualizar_estado_orden_db(orden["ID Orden"], "Terminado")
                        eliminar_orden_activa_db(id_mod)
                        st.success(f"🎉 Orden {id_mod} finalizada correctamente.")
                        st.rerun()

        # ── TAB 3: EXPORTAR ──────────────────────────────────────────────────
        with tab_export:
            st.subheader("Histórico de Tiempos y Exportación")
            df_h = obtener_historico_db()
            if df_h.empty:
                st.info("No hay registros históricos todavía.")
            else:
                st.dataframe(df_h, use_container_width=True)

            col_dl1, col_dl2 = st.columns(2)
            with col_dl1:
                st.download_button(
                    "📥 Exportar Histórico Completo (Excel 3 hojas)",
                    data=generar_excel_historico(),
                    file_name=f"historico_molienda_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )


# =========================================================================
# VISTA 3: CONSOLA CALIDAD
# =========================================================================
elif rol_seleccionado == "🔬 Consola Calidad":
    st.title("🔬 Panel de Control de Calidad")

    pwd_cc = st.text_input("🔑 Contraseña de Control de Calidad:", type="password")
    if pwd_cc != CONTRASENA_CALIDAD:
        st.warning("🔒 Introduce la contraseña de Control de Calidad para continuar.")
    else:
        st.success("🔓 Acceso de Calidad autorizado.")

        ordenes_activas = obtener_ordenes_activas_db()

        # Filtrar solo las que están en Humectación y tienen dispersión capturada
        hum_con_dispersion = {
            k: v for k, v in ordenes_activas.items()
            if v["Etapa"] == "Humectación" and v.get("Datos_Dispersion")
        }

        if not hum_con_dispersion:
            st.info("💡 No hay órdenes en Humectación con dispersión capturada por Producción.")
            st.markdown("Cuando Producción capture los datos de dispersión, aparecerán aquí para tu visto bueno.")
        else:
            for id_ord, orden in hum_con_dispersion.items():
                st.markdown("---")
                disp = orden.get("Datos_Dispersion", {})
                cc   = orden.get("Datos_CC_Hum", {})

                st.markdown(f"### 📋 {orden['Código']} — Lote: {orden['Lote']} — Orden: {id_ord}")
                st.markdown(f"**Puesto:** {orden['Puesto']}  |  **Operador Humectación:** {orden.get('Op_Humectacion','—')}")

                # Mostrar datos de Producción (solo lectura)
                st.markdown('<div class="box-prod">', unsafe_allow_html=True)
                st.markdown("**📋 Datos de Dispersión (capturados por Producción):**")
                col_v1, col_v2 = st.columns(2)
                with col_v1:
                    st.markdown(f"- **PM Mezclador:** {disp.get('PM','—')}")
                    st.markdown(f"- **% Sólidos:** {disp.get('% Solidos','—')}")
                with col_v2:
                    st.markdown(f"- **Viscosidad:** {disp.get('Viscosidad','—')} cps")
                    st.markdown(f"- **Temperatura:** {disp.get('Temp','—')} °C")
                st.markdown("</div>", unsafe_allow_html=True)

                # Estado actual
                if orden.get("CC_Aprobado"):
                    st.success("✅ Esta humectación ya fue aprobada por Calidad.")
                    if cc:
                        st.markdown('<div class="box-cc">', unsafe_allow_html=True)
                        st.markdown(f"**Analista CC:** {cc.get('Analista','—')}  "
                                    f"| **pH:** {cc.get('pH','—')}  "
                                    f"| **Visc. CC:** {cc.get('Viscosidad CC','—')} cps")
                        if cc.get("Observaciones"):
                            st.markdown(f"**Observaciones:** {cc.get('Observaciones')}")
                        st.markdown("</div>", unsafe_allow_html=True)
                else:
                    # Formulario de aprobación CC
                    st.markdown('<div class="box-cc">', unsafe_allow_html=True)
                    st.markdown("**🔬 CALIDAD — Parámetros de Aprobación de Humectación**")

                    c_cc1, c_cc2 = st.columns(2)
                    with c_cc1:
                        analista = st.text_input("Analista CC:",
                                                 value=cc.get("Analista",""),
                                                 key=f"analista_{id_ord}")
                        ph_val   = st.number_input("pH:",
                                                   min_value=0.0, max_value=14.0,
                                                   value=float(cc.get("pH", 7.0)),
                                                   step=0.1, key=f"ph_{id_ord}")
                    with c_cc2:
                        visc_cc  = st.number_input("Viscosidad CC (cps):",
                                                   min_value=0,
                                                   value=int(cc.get("Viscosidad CC", 0)),
                                                   key=f"visc_cc_{id_ord}")
                        obs_cc   = st.text_area("Observaciones CC:",
                                                value=cc.get("Observaciones",""),
                                                key=f"obs_cc_{id_ord}")

                    col_btn1, col_btn2 = st.columns(2)
                    with col_btn1:
                        if st.button(f"✅ APROBAR — Listo para Molienda", key=f"apr_{id_ord}", type="primary"):
                            if analista:
                                orden["Datos_CC_Hum"] = {
                                    "Analista": analista, "pH": ph_val,
                                    "Viscosidad CC": visc_cc, "Observaciones": obs_cc
                                }
                                orden["CC_Aprobado"] = True
                                guardar_orden_activa_db(id_ord, orden)
                                st.success(f"✅ Humectación aprobada por {analista}. Producción puede avanzar a Molienda.")
                                st.rerun()
                            else:
                                st.error("Indica el nombre del analista de CC.")
                    with col_btn2:
                        if st.button(f"❌ RECHAZAR — Requiere ajuste", key=f"rech_{id_ord}"):
                            orden["Datos_CC_Hum"] = {
                                "Analista": analista, "pH": ph_val,
                                "Viscosidad CC": visc_cc,
                                "Observaciones": f"RECHAZADO: {obs_cc}"
                            }
                            orden["CC_Aprobado"] = False
                            orden["Datos_Dispersion"] = {}  # Limpiar para que Producción vuelva a capturar
                            guardar_orden_activa_db(id_ord, orden)
                            st.warning("⚠️ Humectación rechazada. Producción deberá corregir y volver a capturar los datos.")
                            st.rerun()

                    st.markdown("</div>", unsafe_allow_html=True)
