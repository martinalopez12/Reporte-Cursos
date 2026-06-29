import streamlit as st
import pandas as pd
from datetime import datetime
import json
import gspread
from google.oauth2.service_account import Credentials

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
        # Buscamos la clave en los secretos guardados de forma segura en Streamlit
        if password == st.secrets["PASSWORD_SECRETA"]:
            st.session_state.password_correct = True
            st.rerun()
        else:
            st.error("Contraseña incorrecta ❌")
    return False

# Si la contraseña no es correcta, detenemos la ejecución de la app aquí
if not check_password():
    st.stop()

# --- A PARTIR DE AQUÍ EL CÓDIGO SE EJECUTA SOLO SI LA CONTRASEÑA ES CORRECTA ---

@st.cache_data(ttl=600)  # Guarda la información en caché por 10 minutos para que cargue rápido
def load_data_from_sheet(sheet_name):
    """Se conecta de forma segura mediante gspread y extrae los datos de una pestaña."""
    try:
        # Cargamos el JSON de la cuenta de servicio directamente desde los Secrets de Streamlit
        creds_dict = json.loads(st.secrets["google_credentials"]["service_account"])
        
        # Definimos los alcances de la API necesarios para leer las hojas de cálculo y Drive
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        
        # Autenticación directa con las credenciales mapeadas
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        
        # Abrimos la planilla usando la URL limpia guardada en tus Secrets
        spreadsheet = client.open_by_url(st.secrets["SPREADSHEET_URL"])
        sheet = spreadsheet.worksheet(sheet_name)
        
        # Extraemos los datos y los convertimos en un DataFrame de Pandas
        data = sheet.get_all_records()
        return pd.DataFrame(data)
        
    except Exception as e:
        st.error(f"No se pudo cargar la hoja '{sheet_name}'. Error: {e}")
        return pd.DataFrame()

# Carga de datos limpia de las 3 pestañas principales
df_pagos = load_data_from_sheet("Pagos")
df_cursos = load_data_from_sheet("Cursos")
df_historico = load_data_from_sheet("Historico")

# --- DISEÑO DE LA INTERFAZ DEL DASHBOARD ---

st.title("📌 Control de Pagos Pendientes - Mes Actual")

# Verificar si los DataFrames se cargaron correctamente antes de renderizar
if not df_pagos.empty:
    st.subheader("Pestaña de Pagos")
    st.dataframe(df_pagos, use_container_width=True)
else:
    st.warning("Aún no hay datos disponibles para la pestaña 'Pagos'.")

if not df_cursos.empty:
    st.subheader("Lista de Cursos")
    st.dataframe(df_cursos, use_container_width=True)

if not df_historico.empty:
    st.subheader("Histórico General")
    st.dataframe(df_historico, use_container_width=True)
