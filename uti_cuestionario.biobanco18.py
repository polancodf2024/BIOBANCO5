import streamlit as st
import pandas as pd
import paramiko
from pathlib import Path
import toml

# Leer configuraciones locales desde config.toml
config = toml.load(".streamlit/config.toml")

# Configuraciones remotas desde secrets.toml
REMOTE_HOST = st.secrets["remote"]["host"]
REMOTE_USER = st.secrets["remote"]["user"]
REMOTE_PASSWORD = st.secrets["remote"]["password"]
REMOTE_PORT = st.secrets["remote"]["port"]
REMOTE_DIR = st.secrets["remote"]["dir"]
REMOTE_FILE_XLSX = st.secrets["files"]["remote_file_xlsx"]
REMOTE_FILE_CSV = st.secrets["files"]["remote_file_csv"]

LOCAL_FILE_XLSX = st.secrets["files"]["local_file_xlsx"]
LOCAL_FILE_CSV = st.secrets["files"]["local_file_csv"]
LOCK_FILE = st.secrets["files"]["lock_file"]

# Función para descargar archivos del servidor remoto
def recibir_archivo_remoto(remote_file, local_file):
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(REMOTE_HOST, port=REMOTE_PORT, username=REMOTE_USER, password=REMOTE_PASSWORD)
        sftp = ssh.open_sftp()
        sftp.get(f"{REMOTE_DIR}/{remote_file}", local_file)
        sftp.close()
        ssh.close()
        st.info(f"Archivo {local_file} descargado del servidor remoto.")
    except Exception as e:
        st.error(f"Error al descargar el archivo {remote_file} del servidor remoto.")
        st.error(str(e))

# Función para subir archivos al servidor remoto
def enviar_archivo_remoto(local_file, remote_file):
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(REMOTE_HOST, port=REMOTE_PORT, username=REMOTE_USER, password=REMOTE_PASSWORD)
        sftp = ssh.open_sftp()
        sftp.put(local_file, f"{REMOTE_DIR}/{remote_file}")
        sftp.close()
        ssh.close()
        st.success(f"Archivo {local_file} subido al servidor remoto.")
    except Exception as e:
        st.error(f"Error al subir el archivo {local_file} al servidor remoto.")
        st.error(str(e))

# Función principal
def main():
    # Solicitar contraseña al inicio (usando REMOTE_PASSWORD)
    input_password = st.text_input("Ingresa la contraseña para acceder:", type="password")
    if input_password != REMOTE_PASSWORD:
        st.error("Contraseña incorrecta. Por favor ingrese la contraseña válida.")
        st.stop()

    # Sincronización automática al iniciar
    try:
        st.info("Sincronizando archivos con el servidor remoto...")
        recibir_archivo_remoto(REMOTE_FILE_XLSX, LOCAL_FILE_XLSX)
        recibir_archivo_remoto(REMOTE_FILE_CSV, LOCAL_FILE_CSV)
    except Exception as e:
        st.warning("No se pudo sincronizar los archivos automáticamente.")
        st.warning(str(e))

    # Mostrar el logo y título
    st.image("escudo_COLOR.jpg", width=150)
    st.title("Subir archivos: respuestas_cuestionario_acumulado.xlsx e identificaciones.csv")

    # Subida de archivo XLSX
    uploaded_xlsx = st.file_uploader("Selecciona el archivo .xlsx para subir y reemplazar el existente", type=["xlsx"])
    if uploaded_xlsx is not None:
        try:
            with open(LOCAL_FILE_XLSX, "wb") as f:
                f.write(uploaded_xlsx.getbuffer())

            # Subir al servidor remoto
            enviar_archivo_remoto(LOCAL_FILE_XLSX, REMOTE_FILE_XLSX)

            st.success("Archivo XLSX subido correctamente.")
        except Exception as e:
            st.error("Error al procesar el archivo XLSX.")
            st.error(str(e))

    # Subida de archivo CSV
    uploaded_csv = st.file_uploader("Selecciona el archivo .csv para subir y reemplazar el existente", type=["csv"])
    if uploaded_csv is not None:
        try:
            with open(LOCAL_FILE_CSV, "wb") as f:
                f.write(uploaded_csv.getbuffer())

            # Subir al servidor remoto
            enviar_archivo_remoto(LOCAL_FILE_CSV, REMOTE_FILE_CSV)

            st.success("Archivo CSV subido correctamente.")
        except Exception as e:
            st.error("Error al procesar el archivo CSV.")
            st.error(str(e))

    # Título para la sección de descarga
    st.title("Descargar archivos: respuestas_cuestionario_acumulado.xlsx e identificaciones.csv")

    # Botón para descargar el archivo XLSX
    if Path(LOCAL_FILE_XLSX).exists():
        with open(LOCAL_FILE_XLSX, "rb") as file:
            st.download_button(
                label="Descargar respuestas_cuestionario_acumulado.xlsx",
                data=file,
                file_name="respuestas_cuestionario_acumulado.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        st.success("Archivo XLSX listo para descargar.")
    else:
        st.warning("El archivo XLSX local no existe. Sincroniza primero con el servidor.")

    # Botón para descargar el archivo CSV
    if Path(LOCAL_FILE_CSV).exists():
        with open(LOCAL_FILE_CSV, "rb") as file:
            st.download_button(
                label="Descargar identificaciones.csv",
                data=file,
                file_name="identificaciones.csv",
                mime="text/csv"
            )
        st.success("Archivo CSV listo para descargar.")
    else:
        st.warning("El archivo CSV local no existe. Sincroniza primero con el servidor.")

if __name__ == "__main__":
    main()
