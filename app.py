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
df_contactos = load_data_from_sheet("Contactos")

# --- FUNCIONES DE FORMATEO Y SOPORTE ---
def format_boolean_cell(val):
    """Transforma valores booleanos/texto en emojis ✔️ / ❌."""
    if val is True or str(val).strip().lower() in ['true', '1', 'sí', 'si', '✔️']:
        return "✔️"
    return "❌"

def apply_boolean_formatting(df, columns_to_format):
    """Aplica el formato visual a las columnas booleanas indicadas."""
    df_copy = df.copy()
    for col in columns_to_format:
        if col in df_copy.columns:
            df_copy[col] = df_copy[col].apply(format_boolean_cell)
    return df_copy

def highlight_notif_andre_rosa(row):
    """Pinta toda la fila de un tono rosa viejo/malva apagado con letras blancas en modo oscuro."""
    val = row.get("Notif. Andre")
    is_true = val is True or str(val).strip().lower() in ['true', '1', 'sí', 'si', '✔️']
    if is_true:
        # Un color rosa malva profundo y apagado, bien diferenciado del rojo
        return ['background-color: #ff7bff; color: #000000; font-weight: bold;'] * len(row)
    return [''] * len(row)

def selector_fechas_multiples(key_prefix):
    """Genera componentes dinámicos para seleccionar múltiples meses y años."""
    if f"fechas_{key_prefix}" not in st.session_state:
        st.session_state[f"fechas_{key_prefix}"] = [{"mes": datetime.now().month, "año": datetime.now().year}]
    
    st.write("#### 📅 Filtrar por Período:")
    
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
    st.title("📖 Guía de Uso de esta Página Web")
    st.write("¡Hola Andre! Hice este espacio privado para que puedas ver y controlar más fácilmente los ingresos, estados de pagos y alumnos nuevos sumados.")
    st.markdown("""
    ### 🧭 ¿Para qué sirve cada sección del menú?
    1) **📖 Página Principal (Guía):** Es una ayuda fácil con el detalle de qué podes hacer en cada página. Podes ver cómo usarlas más en profundidad en cáda sección en particular.
    2) **💸 Pagos Pendientes:** Te permite ver todas las personas que deben cuotas en los meses elegidos.
    3) **📊 Resumen Mensual:** Calcula cuánta plata ingresó, el total esperado a recadar, lo que falta cobrar y la cantidad de alumnos, totales y nuevos.
    4) **🔍 Historial de Contactos:** Te permite ingresar el nombre o teléfono de cualquier alumno para ver todo su historial de cursos hechos, y sus respectivos estados de pagos y situación.
    """)

    st.markdown("""
    ### ❔Consideraciones
    * 🩷 **Resaltado Rosa**: Si llegas a ver en las tablas alguna fila resaltada de este color, significa que hay algo para que corrobores o que podamos charlar para seguir avanzando.
    * ❤️ **Resaltado Rojo**: Si llegas a ver en las tablas alguna fila resaltada de este color, es solamente para hacerlo más intuitivo visualmente, no hay anda que ver, es solo para vos.
    * 🤍 Recorda que siempre me sirve la crítica constructiva así que cualquier cosa para mejorar o agregar, sabes que me podes decir con completa confianza!
    """)

def pagina_pendientes():
    st.title("💸 Control de Pagos Pendientes")
    st.write("##### Resumen mensual de deudores por cada curso")
    st.caption("###### 💡 Es clave para hacer un control filtrando por una o más fechas (podes sacarlas haciendo click en la cruz roja del mes correspondiente en la sección 'Períodos Activos'), ordenarlos a gusto, y verlos o minimizarlos todos juntos haciendo click en 'Abrir/Cerrar todas las pestañas de los cursos'. \nCONSIDERACIONES: Si ves que dentro de los cursos aparece una casilla (para chequear/clickear) con 'cuota 2' o '3', podes chequearla para ver esos datos en específico (podes ver 1 cuota a la vez).")
    st.write("---")

    if df_pagos.empty:
        st.warning("No hay datos en la pestaña 'Pagos'.")
        return
        
    if "periodos_seleccionados" not in st.session_state:
        st.session_state.periodos_seleccionados = selector_fechas_multiples("pendientes")
    else:
        nuevos_periodos = selector_fechas_multiples("pendientes")
        if nuevos_periodos != st.session_state.periodos_seleccionados and nuevos_periodos:
            st.session_state.periodos_seleccionados = nuevos_periodos

    periodos = st.session_state.periodos_seleccionados

    if not periodos:
        st.info("Por favor, selecciona al menos un mes/año para consultar.")
        return

    st.write("#### ✅ Períodos Activos:")
    cols_fechas = st.columns(len(periodos) + 1)
    for idx_p, p in enumerate(periodos):
        with cols_fechas[idx_p]:
            if st.button(f"{p['mes']}/{p['año']} ❌", key=f"del_{p['mes']}_{p['año']}_{idx_p}"):
                st.session_state.periodos_seleccionados.remove(p)
                st.rerun()

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

    df_procesado = df_filtrado_acum.copy()
    if 'Contacto' in df_procesado.columns:
        for col_contacto in ["Contacto Nuevo", "Contacto Viejo"]:
            if col_contacto in df_procesado.columns:
                df_procesado[col_contacto] = df_procesado.apply(
                    lambda r: r['Contacto'] if str(r[col_contacto]).strip().lower() in ['true', '1', 'sí', 'si', 'yes'] else "",
                    axis=1
                )

    group_cols = [c for c in ["Curso", "Nro. Curso", "Día", "Mes", "Año"] if c in df_procesado.columns]
    if not group_cols:
        st.dataframe(df_procesado, width="stretch")
        return
        
    cursos_unicos = df_procesado[group_cols].drop_duplicates()

    # --- CONTROL DE EXPANDERS ---
    col_orden, col_expandir = st.columns([2, 1])
    with col_expandir:
        abrir_todos = st.checkbox("🔓 Abrir/Cerrar todas las pestañas de los cursos", key="expandir_pendientes")
    with col_orden:
        st.write("#### 🗂️ Ordenar cursos por:")
        criterio_orden = st.radio(
            "🗂️ Ordenar cursos por:",
            ["Fecha del Curso", "Orden Alfabético"],
            horizontal=True,
            label_visibility="collapsed"
        )
    
    if criterio_orden == "Orden Alfabético":
        cursos_unicos = cursos_unicos.sort_values(by=["Curso", "Nro. Curso"], ascending=[True, True])
    else:
        orden_cols = [c for c in ["Año", "Mes", "Día"] if c in cursos_unicos.columns]
        for col in orden_cols:
            cursos_unicos[col] = pd.to_numeric(cursos_unicos[col], errors='coerce').fillna(0)
        cursos_unicos = cursos_unicos.sort_values(by=orden_cols, ascending=[True, True, True])

    st.write("---")

    for idx_curso, curso in cursos_unicos.iterrows():
        condicion_curso = True
        for col in group_cols:
            condicion_curso = condicion_curso & (df_procesado[col] == curso[col])
            
        df_curso_total = df_procesado[condicion_curso].copy()
        total_alumnos_curso = len(df_curso_total)
        
        if total_alumnos_curso == 0:
            continue

        tiene_cuota2 = False
        if 'Estado Pago 2' in df_curso_total.columns:
            valores_c2 = df_curso_total['Estado Pago 2'].astype(str).str.strip().str.lower()
            tiene_cuota2 = not valores_c2.isin(['', 'none', 'nan', 'na', '<na>']).all()

        tiene_cuota3 = False
        if 'Estado Pago 3' in df_curso_total.columns:
            valores_c3 = df_curso_total['Estado Pago 3'].astype(str).str.strip().str.lower()
            tiene_cuota3 = not valores_c3.isin(['', 'none', 'nan', 'na', '<na>']).all()

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

        key_chk2 = f"chk2_{idx_curso}"
        key_chk3 = f"chk3_{idx_curso}"
        
        ver_cuota_2 = st.session_state.get(key_chk2, False)
        ver_cuota_3 = st.session_state.get(key_chk3, False)

        if not ver_cuota_2 and not ver_cuota_3:
            condicion_final_pendientes = es_pendiente_c1
            total_pendientes_metrica = es_pendiente_c1.sum()
        elif ver_cuota_2 and not ver_cuota_3:
            condicion_final_pendientes = es_pendiente_c2
            total_pendientes_metrica = es_pendiente_c2.sum()
        else:
            condicion_final_pendientes = es_pendiente_c3
            total_pendientes_metrica = es_pendiente_c3.sum()

        df_curso_pendientes = df_curso_total[condicion_final_pendientes].copy()

        nombre_c = curso.get("Curso", "Curso")
        dia_c = int(curso.get("Día", 0))
        mes_c = int(curso.get("Mes", 0))
        nro_c = str(curso.get("Nro. Curso", "")).strip()
        texto_nro = f" {nro_c}" if nro_c and nro_c.lower() not in ["", "nan", "none", "-", "<na>"] else ""
        
        titulo_toggle = f"📘 {nombre_c}{texto_nro} - ({total_pendientes_metrica}/{total_alumnos_curso} pendientes) - [Fecha: {dia_c}/{mes_c}]"

        with st.expander(titulo_toggle, expanded=abrir_todos):
            col_c1, col_c2 = st.columns(2)
            with col_c1:
                if tiene_cuota2:
                    st.checkbox("Ver Cuota 2", key=key_chk2, on_change=st.rerun)
            with col_c2:
                if tiene_cuota3 and (ver_cuota_2 or not tiene_cuota2):
                    st.checkbox("Ver Cuota 3", key=key_chk3, on_change=st.rerun)

            if df_curso_pendientes.empty:
                st.success("🎉 ¡No hay pendientes bajo el criterio seleccionado para este curso!")
            else:
                # --- AQUÍ SE SACARON LAS COLUMNAS DE ESTADO ---
                columnas_base = ["Contacto Nuevo", "Contacto Viejo"]
                
                if not ver_cuota_2 and not ver_cuota_3:
                    columnas_base += ["Fecha de Aplazo", "Comentario"]
                elif ver_cuota_2 and not ver_cuota_3:
                    columnas_base += ["Fecha de Aplazo 2", "Comentario 2"]
                else:
                    columnas_base += ["Fecha de Aplazo 3", "Comentario 3"]
                
                columnas_base += ["Notif. Andre"]

                cols_vista = [c for c in columnas_base if c in df_curso_pendientes.columns]
                df_vista = df_curso_pendientes[cols_vista].copy()
                
                df_vista = apply_boolean_formatting(df_vista, ["Notif. Andre"])
                
                st.dataframe(
                    df_vista.style.apply(highlight_notif_andre_rosa, axis=1),
                    width="stretch",
                    hide_index=True
                )

def pagina_recaudado():
    st.title("📊 Resumen Mensual")
    st.write("##### Reporte de los Ingresos (actuales, esperados, y faltantes) y la cantidad de Contactos Nuevos generados.")
    st.caption("###### 💡 Al estar categorizado por fecha y curso, te permite tener una idea general de lo recaudado hasta el momento, el total esperado a cobrar, su diferencia con lo que falta cobrar, cuántos alumnos hay y cuántos de ellos es su primera vez haciendo un curso tuyo.")
    st.write("---")

    if df_pagos.empty or df_cursos.empty:
        st.warning("Se requieren los datos de las hojas 'Pagos' y 'Cursos' para computar las métricas financieras.")
        return
        
    if "periodos_recaudacion" not in st.session_state:
        st.session_state.periodos_recaudacion = selector_fechas_multiples("recaudacion")
    else:
        nuevos_periodos = selector_fechas_multiples("recaudacion")
        if nuevos_periodos != st.session_state.periodos_recaudacion and nuevos_periodos:
            st.session_state.periodos_recaudacion = nuevos_periodos

    periodos = st.session_state.periodos_recaudacion

    if not periodos:
        st.info("Por favor, selecciona al menos un mes/año para consultar.")
        return

    st.write("#### ✅ Períodos activos:")
    cols_fechas = st.columns(len(periodos) + 1)
    for idx_p, p in enumerate(periodos):
        with cols_fechas[idx_p]:
            if st.button(f"{p['mes']}/{p['año']} ❌", key=f"del_rec_{p['mes']}_{p['año']}_{idx_p}"):
                st.session_state.periodos_recaudacion.remove(p)
                st.rerun()

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

    group_cols = [c for c in ["Curso", "Nro. Curso", "Día", "Mes", "Año"] if c in df_filtrado_acum.columns]
    cursos_unicos = df_filtrado_acum[group_cols].drop_duplicates()
    
    # --- NUEVA SECCIÓN: CONTROL DE EXPANDERS ---
    col_orden, col_expandir = st.columns([2, 1])
    with col_expandir:
        abrir_todos = st.checkbox("🔓 Abrir/Cerrar todas las pestañas de los cursos", key="expandir_recaudacion")
    with col_orden:
        st.write("#### 🗂️ Ordenar cursos por:")
        criterio_orden = st.radio(
            "🗂️ Ordenar cursos por:",
            ["Fecha del Curso", "Orden Alfabético"],
            horizontal=True,
            label_visibility="collapsed"
        )

    st.write("---")
    
    if criterio_orden == "Orden Alfabético":
        cursos_unicos = cursos_unicos.sort_values(by=["Curso", "Nro. Curso"], ascending=[True, True])
    else:
        orden_cols = [c for c in ["Año", "Mes", "Día"] if c in cursos_unicos.columns]
        for col in orden_cols:
            cursos_unicos[col] = pd.to_numeric(cursos_unicos[col], errors='coerce').fillna(0)
        cursos_unicos = cursos_unicos.sort_values(by=orden_cols, ascending=[True, True, True])

    for idx_curso, curso in cursos_unicos.iterrows():
        condicion = True
        for col in group_cols:
            condicion = condicion & (df_filtrado_acum[col] == curso[col])
            
        df_curso_alumnos = df_filtrado_acum[condicion].copy()
        total_personas = len(df_curso_alumnos)
        
        if total_personas == 0:
            continue

        nombre_c = curso.get("Curso", "Curso")
        nro_c = str(curso.get("Nro. Curso", "")).strip()
        dia_c = int(curso.get("Día", 0))
        mes_c = int(curso.get("Mes", 0))
        anio_c = curso.get("Año", "")
        
        tiene_cuota2 = False
        if 'Estado Pago 2' in df_curso_alumnos.columns:
            valores_c2 = df_curso_alumnos['Estado Pago 2'].astype(str).str.strip()
            tiene_cuota2 = not valores_c2.isin(['', 'None', 'nan', 'NaN']).all()

        tiene_cuota3 = False
        if 'Estado Pago 3' in df_curso_alumnos.columns:
            valores_c3 = df_curso_alumnos['Estado Pago 3'].astype(str).str.strip()
            tiene_cuota3 = not valores_c3.isin(['', 'None', 'nan', 'NaN']).all()

        key_chk2 = f"chk2_rec_{idx_curso}"
        key_chk3 = f"chk3_rec_{idx_curso}"
        
        ver_cuota_2 = st.session_state.get(key_chk2, False)
        ver_cuota_3 = st.session_state.get(key_chk3, False)

        col_estado_activa = "Estado"
        col_costo_activa = "Costo"
        
        if ver_cuota_2 and not ver_cuota_3:
            col_estado_activa = "Estado Pago 2"
        elif ver_cuota_3:
            col_estado_activa = "Estado Pago 3"

        costo_unitario = 0
        col_c_nombre = 'Nombre' if 'Nombre' in df_cursos.columns else ('Curso' if 'Curso' in df_cursos.columns else '')
        col_c_nro = 'Nro. Curso' if 'Nro. Curso' in df_cursos.columns else ('Nro de Curso' if 'Nro de Curso' in df_cursos.columns else '')
        
        if col_c_nombre and col_c_nro and 'Día' in df_cursos.columns and 'Mes' in df_cursos.columns and 'Año' in df_cursos.columns:
            match_curso = df_cursos[
                (df_cursos[col_c_nombre].astype(str).str.strip().str.lower() == str(nombre_c).strip().lower()) &
                (df_cursos[col_c_nro].astype(str).str.strip() == str(nro_c)) &
                (df_cursos['Día'].astype(str) == str(dia_c)) &
                (df_cursos['Mes'].astype(str) == str(mes_c)) &
                (df_cursos['Año'].astype(str) == str(anio_c))
            ]
            if not match_curso.empty and 'Costo' in df_cursos.columns:
                costo_unitario = pd.to_numeric(match_curso['Costo'].iloc[0], errors='coerce')

        costo_unitario = 0 if pd.isna(costo_unitario) else costo_unitario
        
        # Filtrar los alumnos pagados para el Recaudado Efectivo
        df_pagados = df_curso_alumnos[df_curso_alumnos[col_estado_activa].astype(str).str.strip().str.lower() == 'pagado']
        recaudado_real = pd.to_numeric(df_pagados[col_costo_activa], errors='coerce').sum()
        
        # CAMBIO: Sumar la columna Costo para TODOS los alumnos del curso (independientemente de su estado)
        esperado_total = pd.to_numeric(df_curso_alumnos[col_costo_activa], errors='coerce').sum()
        
        # Calcular la diferencia de lo que falta cobrar
        falta_cobrar = max(0.0, esperado_total - recaudado_real)
        
        total_contactos_nuevos = 0
        if 'Primer Curso' in df_curso_alumnos.columns:
            is_nuevo = df_curso_alumnos['Primer Curso'].astype(str).str.strip().str.lower().isin(['true', '1', 'sí', 'si', 'yes'])
            total_contactos_nuevos = is_nuevo.sum()

        texto_nro = f" {nro_c}" if nro_c and nro_c.lower() not in ["", "nan", "none", "-", "<na>"] else ""
        titulo_recaudacion = f"📘 {nombre_c}{texto_nro} - [Fecha: {dia_c}/{mes_c}]"
        
        # AGREGADO: expanded=abrir_todos controla si se muestra abierto o cerrado dinámicamente
        with st.expander(titulo_recaudacion, expanded=abrir_todos):
            col_c1, col_c2 = st.columns(2)
            with col_c1:
                if tiene_cuota2:
                    st.checkbox("Ver Cuota 2", key=key_chk2, on_change=st.rerun)
            with col_c2:
                if tiene_cuota3 and (ver_cuota_2 or not tiene_cuota2):
                    st.checkbox("Ver Cuota 3", key=key_chk3, on_change=st.rerun)
            
            st.write("") 
            
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown(f"""
                <div style="background-color: #1e3d2f; padding: 10px; border-radius: 5px; border-left: 5px solid #2e7d32;">
                    <span style="font-size: 13px; color: #a5d6a7; font-weight: bold;">💰 Recaudado Efectivo</span><br>
                    <span style="font-size: 18px; color: #ffffff; font-weight: bold;">${recaudado_real:,.2f}</span>
                </div>
                """, unsafe_allow_html=True)
            with c2:
                st.markdown(f"""
                <div style="background-color: #1a3a4a; padding: 10px; border-radius: 5px; border-left: 5px solid #0288d1;">
                    <span style="font-size: 13px; color: #90caf9; font-weight: bold;">🎯 Esperado Total</span><br>
                    <span style="font-size: 18px; color: #ffffff; font-weight: bold;">${esperado_total:,.2f}</span>
                </div>
                """, unsafe_allow_html=True)
            with c3:
                st.markdown(f"""
                <div style="background-color: #421d22; padding: 10px; border-radius: 5px; border-left: 5px solid #c62828;">
                    <span style="font-size: 13px; color: #ef9a9a; font-weight: bold;">🚨 Falta Cobrar</span><br>
                    <span style="font-size: 18px; color: #ffffff; font-weight: bold;">${falta_cobrar:,.2f}</span>
                </div>
                """, unsafe_allow_html=True)
            
            st.write("") 
            
            c4, c5 = st.columns(2) 
            with c4:
                st.markdown(f"""
                <div style="background-color: #665691; padding: 10px; border-radius: 5px; border-left: 5px solid #9d7aff;">
                    <span style="font-size: 13px; color: #d1c4e9; font-weight: bold;">👥 Total Alumnos</span><br>
                    <span style="font-size: 18px; color: #ffffff; font-weight: bold;">{total_personas} registrados</span>
                </div>
                """, unsafe_allow_html=True)
            with c5:
                st.markdown(f"""
                <div style="background-color: #8a854e; padding: 10px; border-radius: 5px; border-left: 5px solid #ffbd27;">
                    <span style="font-size: 13px; color: #f7ef8b; font-weight: bold;">✨ Contactos Nuevos</span><br>
                    <span style="font-size: 18px; color: #ffffff; font-weight: bold;">{total_contactos_nuevos} nuevos</span>
                </div>
                """, unsafe_allow_html=True)

def pagina_buscador():
    st.title("🔍 Historial de Contactos")
    st.markdown("##### Buscador de Cursos asistidos de un alumnos y sus respectivos Estados de Pago.")
    st.caption("###### 💡 Es muy útil principalmente a la hora de chequear si alguien nos consulta por qué cursos realizó y cuáles ya pago o adeuda.")
    st.write("---")
    
    nombres_historico = df_historico['Contacto Viejo'].dropna().unique().tolist() if 'Contacto Viejo' in df_historico.columns else []
    nombres_contactos = df_contactos['Contacto Nuevo'].dropna().unique().tolist() if 'Contacto Nuevo' in df_contactos.columns else []
    lista_contactos_completa = sorted(list(set(nombres_historico + nombres_contactos)))
    
    telefonos_historico = df_historico['Tel. Cel.'].dropna().astype(str).unique().tolist() if 'Tel. Cel.' in df_historico.columns else []
    telefonos_contactos = df_contactos['Tel. Cel.'].dropna().astype(str).unique().tolist() if 'Tel. Cel.' in df_contactos.columns else []
    lista_telefonos_completa = sorted(list(set(telefonos_historico + telefonos_contactos)))
    
    c1, col_vacia, c2 = st.columns([10, 1, 10])
    
    contacto_seleccionado = None
    telefono_seleccionado = None

    
    with c1:
        st.write("### Nombre de Contacto")
        contacto_seleccionado = st.selectbox("Escribí o seleccioná el nombre:", [""] + lista_contactos_completa, key="sb_contacto")
        
    with c2:
        st.write("### Número de Teléfono")
        telefono_seleccionado = st.selectbox("Escribí o seleccioná el teléfono:", [""] + lista_telefonos_completa, key="sb_telefono")

    df_resultados = pd.DataFrame()
    termino_busqueda = ""
    nombre_resuelto_por_telefono = ""
    
    if contacto_seleccionado and contacto_seleccionado != "":
        termino_busqueda = contacto_seleccionado
        if not df_pagos.empty:
            cond_viejo = df_pagos['Contacto Viejo'].astype(str) == contacto_seleccionado if 'Contacto Viejo' in df_pagos.columns else False
            cond_nuevo = df_pagos['Contacto Nuevo'].astype(str) == contacto_seleccionado if 'Contacto Nuevo' in df_pagos.columns else False
            df_resultados = df_pagos[cond_viejo | cond_nuevo]
            
    elif telefono_seleccionado and telefono_seleccionado != "":
        termino_busqueda = telefono_seleccionado
        nombres_asociados = []
        if 'Contacto Viejo' in df_historico.columns and 'Tel. Cel.' in df_historico.columns:
            nombres_asociados += df_historico[df_historico['Tel. Cel.'].astype(str) == telefono_seleccionado]['Contacto Viejo'].tolist()
        if 'Contacto Nuevo' in df_contactos.columns and 'Tel. Cel.' in df_contactos.columns:
            nombres_asociados += df_contactos[df_contactos['Tel. Cel.'].astype(str) == telefono_seleccionado]['Contacto Nuevo'].tolist()
            
        nombres_asociados = list(set([n for n in nombres_asociados if n and str(n).strip() != ""]))
        
        if nombres_asociados:
            nombre_resuelto_por_telefono = nombres_asociados[0]
        
        if not df_pagos.empty and nombres_asociados:
            cond_viejo = df_pagos['Contacto Viejo'].isin(nombres_asociados) if 'Contacto Viejo' in df_pagos.columns else False
            cond_nuevo = df_pagos['Contacto Nuevo'].isin(nombres_asociados) if 'Contacto Nuevo' in df_pagos.columns else False
            df_resultados = df_pagos[cond_viejo | cond_nuevo]
            
    if termino_busqueda == "":
        st.info("Por favor, seleccioná un criterio arriba (escribiendo o desplegando) para trazar el estado de pagos.")
        return
        
    if df_resultados.empty:
        st.warning(f"No se encontraron registros de cursadas activas asociados a: '{termino_busqueda}'.")
        return
        
    # Mostrar el nombre real asociado si buscó por teléfono
    if nombre_resuelto_por_telefono:
        st.success(f"📌 Expediente encontrado para el Teléfono {termino_busqueda} ➔ Contacto: **{nombre_resuelto_por_telefono}**")
    else:
        st.success(f"📌 Expediente de Cursos Encontrados para: {termino_busqueda}")
    
    mostrar_opcion_c2 = False
    if 'Estado Pago 2' in df_resultados.columns:
        mostrar_opcion_c2 = not df_resultados['Estado Pago 2'].astype(str).str.strip().str.lower().isin(['', 'none', 'nan', 'na', '<na>']).all()

    mostrar_opcion_c3 = False
    if 'Estado Pago 3' in df_resultados.columns:
        mostrar_opcion_c3 = not df_resultados['Estado Pago 3'].astype(str).str.strip().str.lower().isin(['', 'none', 'nan', 'na', '<na>']).all()

    ver_c2 = False
    ver_c3 = False
    if mostrar_opcion_c2 or mostrar_opcion_c3:
        st.write("#### ⚙️​​ Cuotas Opcionales a Agregar:")
        st.caption("(Se agregan, no se reemplaza una por otra)")
        col_chk1, col_chk2 = st.columns(2)
        with col_chk1:
            if mostrar_opcion_c2:
                ver_c2 = st.checkbox("Agregar columnas de Cuota 2", key="busc_ver_c2")
        with col_chk2:
            if mostrar_opcion_c3:
                ver_c3 = st.checkbox("Agregar columnas de Cuota 3", key="busc_ver_c3")
        
    columnas_buscador = ["Curso", "Nro. Curso", "Día", "Mes", "Año", "Costo", "Estado", "Fecha de Pago", "Fecha de Aplazo", "Comentario"]
    
    if ver_c2:
        columnas_buscador += ["Estado Pago 2", "Fecha de Pago 2", "Fecha de Aplazo 2", "Comentario 2"]
    if ver_c3:
        columnas_buscador += ["Estado Pago 3", "Fecha de Pago 3", "Fecha de Aplazo 3", "Comentario 3"]
        
    columnas_buscador += ["Notif. Andre", "Mensaje Recordatorio Pagos"]
    
    cols_existentes = [c for c in columnas_buscador if c in df_resultados.columns]
    df_buscador_vista = df_resultados[cols_existentes].copy()
    
    if "Notif. Andre" in df_buscador_vista.columns:
        df_buscador_vista = apply_boolean_formatting(df_buscador_vista, ["Notif. Andre"])
    if "Mensaje Recordatorio Pagos" in df_buscador_vista.columns:
        df_buscador_vista = apply_boolean_formatting(df_buscador_vista, ["Mensaje Recordatorio Pagos"])
        
    # --- MODIFICACIÓN DE COLORES A TONOS MÁS APAGADOS Y PASTEL ---
    def colorear_expediente_oscuro(fila):
        estilos = [''] * len(fila)
        
        notif_val = str(fila.get('Notif. Andre', '')).strip()
        es_notif = notif_val == '✔️'
        
        estado_val = 'pagado'
        if ver_c3 and 'Estado Pago 3' in fila:
            estado_val = str(fila.get('Estado Pago 3', '')).strip().lower()
        elif ver_c2 and 'Estado Pago 2' in fila:
            estado_val = str(fila.get('Estado Pago 2', '')).strip().lower()
        elif 'Estado' in fila:
            estado_val = str(fila.get('Estado', '')).strip().lower()
            
        es_pendiente = estado_val == 'pendiente'
        
        if es_notif:
            # Rosa/Vino apagado y pastel para modo oscuro
            estilos = ['background-color: #ff7bff; color: #000000; font-weight: bold;'] * len(fila)
        elif es_pendiente:
            # Rojo ladrillo/óxido apagado (no chillón)
            estilos = ['background-color: #d93535; color: #ffffff; font-weight: bold;'] * len(fila)
            
        return estilos

    st.dataframe(
        df_buscador_vista.style.apply(colorear_expediente_oscuro, axis=1),
        width="stretch", 
        hide_index=True
    )

# --- MAPEO DEL MENÚ LATERAL DE NAVEGACIÓN ---
paginas = {
    "📖 Página Principal (Guía)": pagina_intro,
    "💸 Pagos Pendientes": pagina_pendientes,
    "📊 Resumen Mensual": pagina_recaudado,
    "🔍 Historial de Contactos": pagina_buscador
}

st.sidebar.title("🧭 Navegación")
seleccion = st.sidebar.radio("Ir a la sección:", list(paginas.keys()))

paginas[seleccion]()
