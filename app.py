import streamlit as st
import pandas as pd
from datetime import datetime
# 1. Importación explícita de la conexión
from streamlit_gsheets import GSheetsConnection

# Configuración de la página
st.set_page_config(page_title="Dashboard Cursos Andre", layout="wide")

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

if check_password():
    # 🔐 Conexión privada y segura a Google Sheets
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    @st.cache_data(ttl=60)  # Se actualiza cada 1 minuto
    def load_data(sheet_name):
        try:
            return conn.read(worksheet=sheet_name)
        except Exception as e:
            st.error(f"No se pudo cargar la hoja '{sheet_name}'. Error: {e}")
            return pd.DataFrame()

    # Cargamos las pestañas del Google Sheet
    df_pagos = load_data("Pagos")
    df_cursos = load_data("Cursos")
    df_historico = load_data("Historico")

    # Limpieza y formateo de la pestaña Pagos
    if not df_pagos.empty:
        df_pagos = df_pagos.copy()
        if "Contacto Nuevo" in df_pagos.columns:
            df_pagos["Contacto Nuevo"] = df_pagos["Contacto Nuevo"].fillna("").astype(str).str.strip()
        if "Contacto Viejo" in df_pagos.columns:
            df_pagos["Contacto Viejo"] = df_pagos["Contacto Viejo"].fillna("").astype(str).str.strip()
        if "Costo" in df_pagos.columns:
            df_pagos["Costo"] = pd.to_numeric(df_pagos["Costo"], errors='coerce').fillna(0)

    # Limpieza de la pestaña Historico (Adaptado: SOLO procesa Contacto Viejo si existe)
    if not df_historico.empty:
        df_historico = df_historico.copy()
        if "Contacto Viejo" in df_historico.columns:
            df_historico["Contacto Viejo"] = df_historico["Contacto Viejo"].fillna("").astype(str).str.strip()

    # Menú lateral
    opcion = st.sidebar.radio(
        "Seleccioná una sección:",
        ["1. Pendientes del Mes", "2. Recaudación Mensual", "3. Buscador de Alumnos"]
    )

    # -------------------------------------------------------------------------
    # PAGINA 1: TOGGLES DE CURSOS DEL MES ACTUAL
    # -------------------------------------------------------------------------
    if opcion == "1. Pendientes del Mes":
        st.header("📌 Control de Pagos Pendientes - Mes Actual")
        
        mes_actual = datetime.now().month
        ano_actual = datetime.now().year
        
        if not df_pagos.empty and "Mes" in df_pagos.columns and "Año" in df_pagos.columns:
            # Filtrado tolerante a mezclas de tipos numéricos/strings
            df_pagos["Mes"] = pd.to_numeric(df_pagos["Mes"], errors='coerce')
            df_pagos["Año"] = pd.to_numeric(df_pagos["Año"], errors='coerce')
            
            df_mes = df_pagos[(df_pagos["Mes"] == mes_actual) & (df_pagos["Año"] == ano_actual)]
            df_pendientes = df_mes[df_mes["Estado"] != "Pagado"]

            cursos_del_mes = df_pendientes["Curso"].dropna().unique()

            if len(cursos_del_mes) == 0:
                st.success("¡No hay pagos pendientes registrados para este mes! 🎉")
            else:
                st.write("Los cursos con el indicador 🔵 tienen alertas o filas marcadas para que revises.")
                
                for curso in list(cursos_del_mes):
                    df_curso_pend = df_pendientes[df_pendientes["Curso"] == curso]
                    
                    tiene_novedad = False
                    if "Notif. Andre" in df_curso_pend.columns:
                        tiene_novedad = df_curso_pend["Notif. Andre"].any()
                    
                    puntito = "🔵 " if tiene_novedad else ""
                    cantidad_pendientes = len(df_curso_pend)
                    titulo_toggle = f"{puntito}📘 {curso} ({cantidad_pendientes} pendientes)"
                    
                    with st.expander(titulo_toggle):
                        df_mostrar = df_curso_pend.copy()
                        
                        # Definición segura del Nombre del Alumno controlando que falte Contacto Nuevo
                        def obtener_nombre(r):
                            c_nuevo = str(r.get("Contacto Nuevo", "")).strip()
                            if c_nuevo != "" and c_nuevo != "nan":
                                return c_nuevo
                            return r.get("Contacto Viejo", "")

                        df_mostrar["Nombre Alumno"] = df_mostrar.apply(obtener_nombre, axis=1)
                        
                        columnas_finales = ["Nombre Alumno", "Fecha de Aplazo", "Comentario", "Mensaje Recordatorio Pagos", "Notif. Andre"]
                        columnas_existentes = [c for c in columnas_finales if c in df_mostrar.columns]
                        df_final = df_mostrar[columnas_existentes].reset_index(drop=True)
                        
                        def resaltar_notif(row):
                            if "Notif. Andre" in row and (row["Notif. Andre"] is True or str(row["Notif. Andre"]).lower() == 'true'):
                                return ['background-color: #d1ecf1; color: #0c5460; font-weight: bold;'] * len(row)
                            return [''] * len(row)
                        
                        st.dataframe(df_final.style.apply(resaltar_notif, axis=1), use_container_width=True)
        else:
            st.error("No se pudo procesar la estructura de la pestaña 'Pagos'. Revisa las columnas.")

    # -------------------------------------------------------------------------
    # PAGINA 2: RECAUDACIÓN MENSUAL
    # -------------------------------------------------------------------------
    elif opcion == "2. Recaudación Mensual":
        st.header("📊 Resumen de Recaudación Mensual")
        
        meses_nombres = {1:"Enero", 2:"Febrero", 3:"Marzo", 4:"Abril", 5:"Mayo", 6:"Junio", 
                         7:"Julio", 8:"Agosto", 9:"Septiembre", 10:"Octubre", 11:"Noviembre", 12:"Diciembre"}
        
        mes_act = datetime.now().month
        ano_act = datetime.now().year
        
        col1, col2 = st.columns(2)
        with col1:
            mes_sel = st.selectbox("Seleccioná el Mes:", list(meses_nombres.keys()), index=list(meses_nombres.keys()).index(mes_act), format_func=lambda x: meses_nombres[x])
        with col2:
            ano_sel = st.selectbox("Seleccioná el Año:", [ano_act - 1, ano_act, ano_act + 1], index=1)

        if not df_pagos.empty and "Mes" in df_pagos.columns and "Año" in df_pagos.columns:
            df_pagos["Mes"] = pd.to_numeric(df_pagos["Mes"], errors='coerce')
            df_pagos["Año"] = pd.to_numeric(df_pagos["Año"], errors='coerce')
            
            df_rec = df_pagos[(df_pagos["Mes"] == mes_sel) & (df_pagos["Año"] == ano_sel)].copy()
            
            if df_rec.empty:
                st.warning("No hay registros de cursos para el mes seleccionado.")
            else:
                resumen_data = []
                for curso, group in df_rec.groupby("Curso"):
                    acumulado = group[group["Estado"] == "Pagado"]["Costo"].sum()
                    esperado = group["Costo"].sum()
                    por_cobrar = group[group["Estado"] != "Pagado"]["Costo"].sum()
                    total_personas = len(group)
                    
                    resumen_data.append({
                        "Curso": curso,
                        "Ingresos Acumulados": f"${acumulado:,.2f}",
                        "Ingresos Esperados": f"${esperado:,.2f}",
                        "Por Cobrar": f"${por_cobrar:,.2f}",
                        "Total Personas": total_personas
                    })
                    
                df_resumen_mensual = pd.DataFrame(resumen_data)
                st.dataframe(df_resumen_mensual, use_container_width=True)

    # -------------------------------------------------------------------------
    # PAGINA 3: BUSCADOR UNIFICADO DE PERSONAS (HISTORIAL)
    # -------------------------------------------------------------------------
    elif opcion == "3. Buscador de Alumnos":
        st.header("🔍 Historial e Info de Alumnos")
        
        nombre_buscado = st.text_input("Ingresá el nombre de la persona a buscar:").strip().lower()
        
        if nombre_buscado and not df_pagos.empty:
            # Búsqueda segura verificando la existencia de las columnas primero
            condiciones = []
            if "Contacto Nuevo" in df_pagos.columns:
                condiciones.append(df_pagos["Contacto Nuevo"].str.lower().str.contains(nombre_buscado, na=False))
            if "Contacto Viejo" in df_pagos.columns:
                condiciones.append(df_pagos["Contacto Viejo"].str.lower().str.contains(nombre_buscado, na=False))
            
            if condiciones:
                query_final = condiciones[0]
                for cond in condiciones[1:]:
                    query_final = query_final | cond
                resultados_pagos = df_pagos[query_final].copy()
            else:
                resultados_pagos = pd.DataFrame()
            
            st.subheader(f"Resultados encontrados para: '{nombre_buscado}'")
            
            if resultados_pagos.empty:
                st.info("No se encontraron registros en la base de datos con ese nombre.")
            else:
                df_res = resultados_pagos.copy()
                
                def obtener_nombre_res(r):
                    c_nuevo = str(r.get("Contacto Nuevo", "")).strip()
                    if c_nuevo != "" and c_nuevo != "nan":
                        return c_nuevo
                    return r.get("Contacto Viejo", "")

                df_res["Nombre Encontrado"] = df_res.apply(obtener_nombre_res, axis=1)
                
                # Armado de la fecha con manejo de nulos
                df_res["Fecha Curso"] = df_res.apply(lambda r: f"{int(r['Día'])}/{int(r['Mes'])}/{int(r['Año'])}" if pd.notnull(r.get('Día')) and pd.notnull(r.get('Mes')) else "Sin fecha", axis=1)
                
                columnas_busqueda = ["Nombre Encontrado", "Curso", "Fecha Curso", "Estado", "Fecha de Pago", "Fecha de Aplazo", "Comentario", "Mensaje Recordatorio Pagos"]
                columnas_validas = [c for c in columnas_busqueda if c in df_res.columns]
                
                st.dataframe(df_res[columnas_validas].reset_index(drop=True), use_container_width=True)
