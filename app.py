import streamlit as st
import pandas as pd
from datetime import datetime
import json
import gspread
from google.oauth2.service_account import Credentials

# Configuración de la página
st.set_page_config(page_title="Dashboard Cursos Andre", layout="wide")

# --- CONTROL DE ACCESO (CONTRASEÑA) ---
def check_password():
    """Devuelve True si el usuario ingresó la contraseña correcta."""
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False
        
    if st.session_state.password_correct:
        return True

    st.title("Acceso Privado - Cursos Andre")
    password = st.text_input("Ingresá la contraseña para continuar:", type="password")
    
    if st.button("Ingresar"):
        if password == st.secrets["PASSWORD_SECRETA"]:
            st.session_state.password_correct = True
            st.rerun()
        else:
            st.error("Contraseña incorrecta ❌")
    return False

if not check_password():
    st.stop()

# --- CONEXIÓN Y CARGA DE DATOS ---
@st.cache_data(ttl=300)  # Caché de 5 minutos
def load_data_from_sheet(sheet_name):
    """Se conecta mediante gspread y extrae los datos de una pestaña."""
    try:
        creds_dict = json.loads(st.secrets["google_credentials"]["service_account"])
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_url(st.secrets["SPREADSHEET_URL"])
        sheet = spreadsheet.worksheet(sheet_name)
        data = sheet.get_all_records()
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"No se pudo cargar la hoja '{sheet_name}'. Error: {e}")
        return pd.DataFrame()

# Carga global de datos
df_pagos = load_data_from_sheet("Pagos")
df_cursos = load_data_from_sheet("Cursos")
df_historico = load_data_from_sheet("Historico")

# --- FUNCIONES DE FORMATEO Y SOPORTE ---
def format_boolean_cell(val):
    """Transforma valores booleanos/texto en emojis ✔️ / ❌."""
    if val is True or str(val).strip().lower() in ['true', '1', 'sí', 'si']:
        return "✔️"
    return "❌"

def apply_boolean_formatting(df, columns_to_format):
    """Aplica el formato visual a las columnas booleanas indicadas."""
    df_copy = df.copy()
    for col in columns_to_format:
        if col in df_copy.columns:
            df_copy[col] = df_copy[col].apply(format_boolean_cell)
    return df_copy

def highlight_notif_andre(row):
    """Pinta toda la fila si 'Notif. Andre' es verdadero."""
    val = row.get("Notif. Andre")
    is_true = val is True or str(val).strip().lower() in ['true', '1', 'sí', 'si', '✔️']
    if is_true:
        return ['background-color: rgba(255, 75, 75, 0.2)'] * len(row)
    return [''] * len(row)

def selector_fechas_multiples(key_prefix):
    """Genera componentes dinámicos para seleccionar múltiples meses y años."""
    if f"fechas_{key_prefix}" not in st.session_state:
        st.session_state[f"fechas_{key_prefix}"] = [{"mes": datetime.now().month, "año": datetime.now().year}]
    
    st.write("### 📅 Filtrar por Período:")
    
    # Crear filas dinámicas para cada combinación agregada
    for idx, item in enumerate(st.session_state[f"fechas_{key_prefix}"]):
        col1, col2 = st.columns(2)
        with col1:
            meses_nombres = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
            mes_sel = st.selectbox(f"Mes ({idx+1})", meses_nombres, index=item["mes"]-1, key=f"mes_{key_prefix}_{idx}")
            st.session_state[f"fechas_{key_prefix}"][idx]["mes"] = meses_nombres.index(mes_sel) + 1
        with col2:
            año_sel = st.selectbox(f"Año ({idx+1})", list(range(2020, 2031)), index=list(range(2020, 2031)).index(item["año"]), key=f"año_{key_prefix}_{idx}")
            st.session_state[f"fechas_{key_prefix}"][idx]["año"] = año_sel
            
    if st.button("➕ Agregar otro período", key=f"btn_{key_prefix}"):
        st.session_state[f"fechas_{key_prefix}"].append({"mes": datetime.now().month, "año": datetime.now().year})
        st.rerun()
        
    return st.session_state[f"fechas_{key_prefix}"]

# --- DECLARACIÓN DE LAS PÁGINAS ---
def pagina_intro():
    st.title("📖 Guía de Uso del Dashboard")
    st.write("¡Bienvenida! Este espacio privado está diseñado para controlar los cursos y estados de pagos de manera dinámica.")
    st.markdown("""
    ### 🧭 ¿Cómo usar cada sección del menú?
    * **Página Principal (Guía):** Es esta sección. Aquí podés repasar el funcionamiento del sistema.
    * **💸 Pagos Pendientes:** Te permite ver de forma agrupada (mediante pestañas desplegables) todas las personas que deben cuotas en los meses elegidos. Las alertas importantes destinadas a confirmación visual se resaltan automáticamente en color.
    * **📊 Recaudación Mensual:** Calcula de manera matemática cuánto dinero ingresó de forma efectiva, la proyección total esperada en base a los inscritos, lo que falta cobrar y las métricas de nuevos alumnos.
    * **🔍 Buscador de Contactos:** Te permite ingresar el nombre o teléfono de cualquier alumno (histórico o nuevo) mediante autocompletado inteligente para auditar de inmediato todo su expediente académico y su historial de pagos.
    """)

def pagina_pendientes():
    st.title("💸 Control de Pagos Pendientes por Curso")
    if df_pagos.empty:
        st.warning("No hay datos en la pestaña 'Pagos'.")
        return
        
    periodos = selector_fechas_multiples("pendientes")
    
    # Filtrar el DataFrame original de pagos acumulando las fechas
    df_filtrado_acum = pd.DataFrame()
    for p in periodos:
        df_mes_año = df_pagos[
            (df_pagos['Mes'].astype(str) == str(p["mes"])) & 
            (df_pagos['Año'].astype(str) == str(p["año"]))
        ]
        df_filtrado_acum = pd.concat([df_filtrado_acum, df_mes_año], ignore_index=True)
    
    if df_filtrado_acum.empty:
        st.info("No se encontraron registros de pagos para los meses seleccionados.")
        return

    # Clonamos para trabajar los nombres reales en Contacto Nuevo/Viejo
    df_procesado = df_filtrado_acum.copy()
    if 'Contacto' in df_procesado.columns:
        for col_contacto in ["Contacto Nuevo", "Contacto Viejo"]:
            if col_contacto in df_procesado.columns:
                df_procesado[col_contacto] = df_procesado.apply(
                    lambda r: r['Contacto'] if str(r[col_contacto]).strip().lower() in ['true', '1', 'sí', 'si', 'yes'] else "",
                    axis=1
                )

    # Definimos columnas clave de agrupación
    group_cols = [c for c in ["Nombre", "Nro de Curso", "Día", "Mes", "Año"] if c in df_procesado.columns]
    if not group_cols:
        st.dataframe(df_procesado, width="stretch")
        return
        
    cursos_unicos = df_procesado[group_cols].drop_duplicates()
    
    for idx_curso, curso in cursos_unicos.iterrows():
        # Filtramos todos los alumnos que pertenecen a este curso específico
        condicion_curso = True
        for col in group_cols:
            condicion_curso = condicion_curso & (df_procesado[col] == curso[col])
            
        df_curso_total = df_procesado[condicion_curso].copy()
        total_alumnos_curso = len(df_curso_total)
        
        if total_alumnos_curso == 0:
            continue

        # Evaluamos si existen datos cargados para Cuota 2 y 3
        tiene_cuota2 = False
        if 'Estado Pago 2' in df_curso_total.columns:
            valores_c2 = df_curso_total['Estado Pago 2'].astype(str).str.strip()
            tiene_cuota2 = not valores_c2.isin(['', 'None', 'nan', 'NaN']).all()

        tiene_cuota3 = False
        if 'Estado Pago 3' in df_curso_total.columns:
            valores_c3 = df_curso_total['Estado Pago 3'].astype(str).str.strip()
            tiene_cuota3 = not valores_c3.isin(['', 'None', 'nan', 'NaN']).all()

        # Creamos un bloque visual limpio para los checkboxes de este curso
        st.write(f"⚙️ **Filtros para:** {curso.get('Nombre')} (Nro: {curso.get('Nro de Curso')})")
        col_c1, col_c2 = st.columns(2)
        
        ver_cuota_2 = False
        ver_cuota_3 = False
        
        with col_c1:
            if tiene_cuota2:
                ver_cuota_2 = st.checkbox(f"Incluir Cuota 2", key=f"chk2_{idx_curso}")
        with col_c2:
            if tiene_cuota3 and (ver_cuota_2 or not tiene_cuota2):
                ver_cuota_3 = st.checkbox(f"Incluir Cuota 3", key=f"chk3_{idx_curso}")

        # Identificamos quiénes están pendientes en cada cuota
        es_pendiente_c1 = pd.Series(False, index=df_curso_total.index)
        es_pendiente_c2 = pd.Series(False, index=df_curso_total.index)
        es_pendiente_c3 = pd.Series(False, index=df_curso_total.index)

        if 'Estado' in df_curso_total.columns:
            es_pendiente_c1 = df_curso_total['Estado'].astype(str).str.strip().str.lower() != 'pagado'

        if 'Estado Pago 2' in df_curso_total.columns:
            val_c2 = df_curso_total['Estado Pago 2'].astype(str).str.strip().str.lower()
            es_pendiente_c2 = (val_c2 != 'pagado') & (~val_c2.isin(['', 'none', 'nan']))

        if 'Estado Pago 3' in df_curso_total.columns:
            val_c3 = df_curso_total['Estado Pago 3'].astype(str).str.strip().str.lower()
            es_pendiente_c3 = (val_c3 != 'pagado') & (~val_c3.isin(['', 'none', 'nan']))

        # El filtrado ahora es dinámico y acumulativo según lo que esté chequeado
        if not ver_cuota_2 and not ver_cuota_3:
            condicion_final_pendientes = es_pendiente_c1
            total_pendientes_metrica = es_pendiente_c1.sum()
        elif ver_cuota_2 and not ver_cuota_3:
            condicion_final_pendientes = es_pendiente_c1 | es_pendiente_c2
            total_pendientes_metrica = es_pendiente_c2.sum()
        else:
            condicion_final_pendientes = es_pendiente_c1 | es_pendiente_c2 | es_pendiente_c3
            total_pendientes_metrica = es_pendiente_c3.sum()

        df_curso_pendientes = df_curso_total[condicion_final_pendientes].copy()

        nombre_c = curso.get("Nombre", "Curso")
        nro_c = curso.get("Nro de Curso", "-")
        dia_c = curso.get("Día", "-")
        mes_c = curso.get("Mes", "-")

        # 1) FORMATO EXACTO REQUERIDO: nombre, nro de curso fecha (dia/mes) (X/Y pendientes)
        titulo_toggle = f"📘 {nombre_c} {nro_c} {dia_c}/{mes_c} ({total_pendientes_metrica}/{total_alumnos_curso} pendientes)"

        # Usamos un contenedor controlado para inyectar el expander justo abajo
        with st.expander(titulo_toggle):
            if df_curso_pendientes.empty:
                st.success("🎉 ¡No hay filas pendientes con el criterio seleccionado!")
            else:
                # 2) VISIBILIDAD ACUMULATIVA DE COLUMNAS: Siempre muestra lo anterior
                columnas_base = ["Contacto Nuevo", "Contacto Viejo", "Estado", "Fecha de Pago", "Fecha de Aplazo", "Comentario", "Notif. Andre"]
                
                if ver_cuota_2 or ver_cuota_3:
                    columnas_base += ["Estado Pago 2", "Fecha de Pago 2", "Fecha de Aplazo 2", "Comentario 2"]
                if ver_cuota_3:
                    columnas_base += ["Estado Pago 3", "Fecha de Pago 3", "Fecha de Aplazo 3", "Comentario 3"]

                cols_vista = [c for c in columnas_base if c in df_curso_pendientes.columns]
                df_vista = df_curso_pendientes[cols_vista].copy()
                
                df_vista = apply_boolean_formatting(df_vista, ["Notif. Andre"])
                
                st.dataframe(
                    df_vista.style.apply(highlight_notif_andre, axis=1),
                    width="stretch",
                    hide_index=True
                )
        st.markdown("---") # Separador estético entre cursos

def pagina_recaudado():
    st.title("📊 Resumen de Recaudación Mensual")
    if df_pagos.empty or df_cursos.empty:
        st.warning("Se requieren los datos de las hojas 'Pagos' y 'Cursos' para computar las métricas financieras.")
        return
        
    periodos = selector_fechas_multiples("recaudacion")
    
    # Filtrar el DataFrame acumulando períodos
    df_filtrado_acum = pd.DataFrame()
    for p in periodos:
        df_mes_año = df_pagos[
            (df_pagos['Mes'].astype(str) == str(p["mes"])) & 
            (df_pagos['Año'].astype(str) == str(p["año"]))
        ]
        df_filtrado_acum = pd.concat([df_filtrado_acum, df_mes_año], ignore_index=True)
        
    if df_filtrado_acum.empty:
        st.info("No se encontraron registros de alumnos para los meses seleccionados.")
        return

    group_cols = [c for c in ["Nombre", "Nro de Curso", "Día", "Mes", "Año"] if c in df_filtrado_acum.columns]
    cursos_unicos = df_filtrado_acum[group_cols].drop_duplicates()
    
    for _, curso in cursos_unicos.iterrows():
        condicion = True
        for col in group_cols:
            condicion = condicion & (df_filtrado_acum[col] == curso[col])
            
        df_curso_alumnos = df_filtrado_acum[condicion]
        
        nombre_c = curso.get("Nombre", "")
        nro_c = curso.get("Nro de Curso", "")
        dia_c = curso.get("Día", "")
        mes_c = curso.get("Mes", "")
        anio_c = curso.get("Año", "")
        
        df_pagados = df_curso_alumnos[df_curso_alumnos['Estado'].astype(str).str.strip().str.lower() == 'pagado']
        recaudado_real = pd.to_numeric(df_pagados['Costo'], errors='coerce').sum()
        
        total_personas = len(df_curso_alumnos)
        
        costo_unitario = 0
        if 'Nombre' in df_cursos.columns and 'Costo' in df_cursos.columns:
            match_curso = df_cursos[df_cursos['Nombre'].astype(str).str.strip().str.lower() == str(nombre_c).strip().lower()]
            if not match_curso.empty:
                costo_unitario = pd.to_numeric(match_curso['Costo'].iloc[0], errors='coerce')
        
        if costo_unitario == 0:
            costo_unitario = pd.to_numeric(df_curso_alumnos['Costo'], errors='coerce').max()
            
        costo_unitario = 0 if pd.isna(costo_unitario) else costo_unitario
        
        esperado_total = costo_unitario * total_personas
        falta_cobrar = esperado_total - recaudado_real
        
        is_nuevo = df_curso_alumnos['Contacto Nuevo'].astype(str).str.strip().str.lower().isin(['true', '1', 'sí', 'si'])
        total_contactos_nuevos = is_nuevo.sum()
        
        titulo_recaudacion = f"📈 Financiero: {nombre_c} (Nro: {nro_c}) — {dia_c}/{mes_c}/{anio_c}"
        
        with st.expander(titulo_recaudacion):
            c1, c2, c3 = st.columns(3)
            c1.metric("💰 Recaudado Efectivo", f"${recaudado_real:,.2f}")
            c2.metric("🎯 Esperado Total", f"${esperado_total:,.2f}")
            c3.metric("🚨 Falta Cobrar", f"${falta_cobrar:,.2f}")
            
            c4, c5 = st.columns(2)
            c4.metric("👥 Total Alumnos", f"{total_personas} registrados")
            c5.metric("✨ Contactos Nuevos", f"{total_contactos_nuevos} nuevos")

def pagina_buscador():
    st.title("🔍 Historial y Auditoría de Contactos")
    
    nombres_historico = df_historico['Contacto'].dropna().unique().tolist() if 'Contacto' in df_historico.columns else []
    nombres_pagos = df_pagos['Contacto'].dropna().unique().tolist() if 'Contacto' in df_pagos.columns else []
    lista_contactos_completa = sorted(list(set(nombres_historico + nombres_pagos)))
    
    telefonos_historico = df_historico['Teléfono'].dropna().astype(str).unique().tolist() if 'Teléfono' in df_historico.columns else []
    telefonos_pagos = df_pagos['Teléfono'].dropna().astype(str).unique().tolist() if 'Teléfono' in df_pagos.columns else []
    lista_telefonos_completa = sorted(list(set(telefonos_historico + telefonos_pagos)))
    
    c1, col_vacia, c2 = st.columns([10, 1, 10])
    
    contacto_seleccionado = None
    telefono_seleccionado = None
    
    with c1:
        st.write("### Buscar por Nombre de Contacto")
        contacto_seleccionado = st.selectbox("Escribí o seleccioná el nombre:", [""] + lista_contactos_completa)
        
    with c2:
        st.write("### Buscar por Número de Teléfono")
        telefono_seleccionado = st.selectbox("Escribí o seleccioná el teléfono:", [""] + lista_telefonos_completa)

    df_resultados = pd.DataFrame()
    termino_busqueda = ""
    
    if contacto_seleccionado:
        termino_busqueda = contacto_seleccionado
        if not df_pagos.empty and 'Contacto' in df_pagos.columns:
            df_resultados = df_pagos[df_pagos['Contacto'].astype(str) == contacto_seleccionado]
    elif telefono_seleccionado:
        termino_busqueda = telefono_seleccionado
        if not df_pagos.empty and 'Teléfono' in df_pagos.columns:
            df_resultados = df_pagos[df_pagos['Teléfono'].astype(str) == telefono_seleccionado]
            
    if termino_busqueda == "":
        st.info("Por favor, seleccioná un criterio arriba para trazar el estado de pagos.")
        return
        
    if df_resultados.empty:
        st.warning(f"No se encontraron registros de cursadas activas asociados a: '{termino_busqueda}'.")
        return
        
    st.success(f"📌 Expediente de Cursos Encontrados para: {termino_busqueda}")
    
    columnas_buscador = [
        "Nombre", "Nro de Curso", "Día", "Mes", "Año", "Estado", "Fecha de Pago", "Fecha de Aplazo", "Comentario",
        "Estado Pago 2", "Fecha de Pago 2", "Fecha de Aplazo 2", "Comentario 2",
        "Estado Pago 3", "Fecha de Pago 3", "Fecha de Aplazo 3", "Comentario 3",
        "msj recordatorio"
    ]
    
    cols_existentes = [c for c in columnas_buscador if c in df_resultados.columns]
    df_buscador_vista = df_resultados[cols_existentes].copy()
    
    df_buscador_vista = apply_boolean_formatting(df_buscador_vista, ["msj recordatorio"])
    
    st.dataframe(df_buscador_vista, width="stretch", hide_index=True)

# --- MAPEO DEL MENÚ LATERAL DE NAVEGACIÓN ---
paginas = {
    "📖 Página Principal (Guía)": pagina_intro,
    "💸 Pagos Pendientes": pagina_pendientes,
    "📊 Recaudación Mensual": pagina_recaudado,
    "🔍 Buscador de Contactos": pagina_buscador
}

st.sidebar.title("🧭 Navegación")
seleccion = st.sidebar.radio("Ir a la sección:", list(paginas.keys()))

# Ejecución dinámica
paginas[seleccion]()
