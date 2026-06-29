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

        # Evaluamos disponibilidad de Cuota 2 y Cuota 3
        tiene_cuota2 = False
        if 'Estado Pago 2' in df_curso_total.columns:
            valores_c2 = df_curso_total['Estado Pago 2'].astype(str).str.strip()
            tiene_cuota2 = not valores_c2.isin(['', 'None', 'nan', 'NaN']).all()

        tiene_cuota3 = False
        if 'Estado Pago 3' in df_curso_total.columns:
            valores_c3 = df_curso_total['Estado Pago 3'].astype(str).str.strip()
            tiene_cuota3 = not valores_c3.isin(['', 'None', 'nan', 'NaN']).all()

        # Checkboxes de control en columnas limpias
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

        # Identificamos quiénes están pendientes en cada cuota individualmente
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

        # Filtrado dinámico y acumulativo para los datos y las métricas de la cabecera
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

        # 1) CORRECCIÓN CLAVE: Título limpio con estructura exacta: nombre nro_curso dia/mes (pendientes/total)
        titulo_toggle = f"📘 {nombre_c} {nro_c} {dia_c}/{mes_c} ({total_pendientes_metrica}/{total_alumnos_curso} pendientes)"

        with st.expander(titulo_toggle):
            if df_curso_pendientes.empty:
                st.success("🎉 ¡No hay filas pendientes con el criterio seleccionado!")
            else:
                # 2) VISIBILIDAD ACUMULATIVA: Muestra siempre los bloques anteriores correspondientes
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
        st.markdown("---")
