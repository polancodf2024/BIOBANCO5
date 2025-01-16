import csv
import paramiko
import os
import pandas as pd
import streamlit as st
import toml
import paramiko
from datetime import datetime
from filelock import FileLock

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

# Conexión al servidor remoto
def connect_to_remote():
    try:
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(REMOTE_HOST, username=REMOTE_USER, password=REMOTE_PASSWORD, port=REMOTE_PORT)
        sftp_client = ssh_client.open_sftp()
        return ssh_client, sftp_client
    except Exception as e:
        st.error(f"Error al conectar al servidor remoto: {e}")
        return None, None

# Descargar archivo remoto
def download_file(sftp_client, remote_file, local_file):
    try:
        sftp_client.get(os.path.join(REMOTE_DIR, remote_file), local_file)
        st.info(f"Archivo {local_file} descargado desde el servidor remoto.")
    except Exception as e:
        st.error(f"Error al descargar archivo {remote_file}: {e}")

# Subir archivo remoto
def upload_file(sftp_client, local_file, remote_file):
    try:
        sftp_client.put(local_file, os.path.join(REMOTE_DIR, remote_file))
        st.success(f"Archivo {local_file} subido exitosamente al servidor remoto.")
    except Exception as e:
        st.error(f"Error al subir archivo {local_file}: {e}")

# Cerrar conexión remota
def close_connection(ssh_client, sftp_client):
    if sftp_client:
        sftp_client.close()
    if ssh_client:
        ssh_client.close()
    st.info("Conexión cerrada exitosamente.")

# Inicializar archivo CSV si no existe
def initialize_csv():
    if not os.path.exists(LOCAL_FILE_CSV):
        with open(LOCAL_FILE_CSV, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(["id", "prefijo"])

# Generar identificación consecutiva
def generar_identificacion(prefijo):
    initialize_csv()
    with open(LOCAL_FILE_CSV, mode='r', newline='', encoding='utf-8') as file:
        reader = csv.reader(file)
        rows = list(reader)
        last_id = int(rows[-1][0]) if len(rows) > 1 else 0

    nuevo_id = last_id + 1
    with open(LOCAL_FILE_CSV, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow([nuevo_id, prefijo])

    identificacion = f"{prefijo}{nuevo_id:06d}"
    return identificacion

# Generar el cuestionario completo
def generar_cuestionario():
    st.title('Cuestionario Paciente - BioBanco')

    responses = {}
    with st.form(key='cuestionario_form'):
        responses['Fecha de entrevista'] = st.date_input('Fecha de entrevista', value=datetime.now()).strftime('%d/%m/%Y')
        responses['Procedencia del paciente'] = st.selectbox(
            'Procedencia del paciente',
            ['Cardiopatía isquémica', 
            'Cirugía electiva', 
            'Clínica arritmias', 
            'Clínica coagulación',
            'Clínica hipertensión', 
            'Clínica insuficiencia cardiaca', 
            'Clínica valvulares', 
            'Complejo  aórtico', 
            'Consulta externa lado A', 
            'Consulta externa lado B', 
            'Donador control', 
            'Factores de riesgo', 
            'Hipertensión arterial sistémica', 
            'Miocardiopatía', 
            'Síndrome disantonómico',
            'Transplante'],
            key='procedencia'
        )

        if not responses['Procedencia del paciente']:
            st.error("Debe seleccionar la procedencia del paciente.")

        num_registro = st.text_input('Núm. registro INCICh')
        if not num_registro.isdigit():
            st.error('Núm. registro INCICh campo numérico entre 6 y 10 dígitos')
        else:
            responses['Núm. registro INCICh'] = int(num_registro)

        responses['Nombre del paciente'] = st.text_input('Nombre del paciente')
        fecha_nacimiento = st.date_input('Fecha de nacimiento', min_value=datetime(1944, 1, 1), max_value=datetime.now())
        responses['Fecha de nacimiento'] = fecha_nacimiento.strftime('%d/%m/%Y')

        hoy = datetime.now()
        edad = hoy.year - fecha_nacimiento.year - ((hoy.month, hoy.day) < (fecha_nacimiento.month, fecha_nacimiento.day))
        responses['Edad actual (años)'] = edad

        responses['Género'] = st.selectbox('Género', ['Masculino', 'Femenino', 'Otro'])

        responses['Peso (Kg)'] = st.number_input('Peso (Kg)', min_value=35.0, max_value=150.0, step=0.1)
        responses['Estatura (m)'] = st.number_input('Estatura (m)', min_value=1.20, max_value=2.00, step=0.01)

        if responses['Estatura (m)'] > 0:
            imc = round(responses['Peso (Kg)'] / (responses['Estatura (m)'] ** 2), 1)
        else:
            imc = 0.0
        responses['Índice de masa corporal (IMC)'] = imc

        responses['Tensión arterial Sistólica (mmHg)'] = st.number_input('Tensión arterial Sistólica (mmHg)', min_value=50, max_value=220)
        responses['Tensión arterial Diastólica (mmHg)'] = st.number_input('Tensión arterial Diastólica (mmHg)', min_value=40, max_value=130)
        responses['Frecuencia cardiaca (lpm)'] = st.number_input('Frecuencia cardiaca (lpm)', min_value=40, max_value=120)

        st.text("¿Dónde nació usted y sus familiares?")
        estados_mexico = [
            'Otro', 'Aguascalientes', 'Baja California', 'Baja California Sur', 'Campeche', 'Chiapas', 'Chihuahua',
            'Ciudad de Mexico', 'Coahuila', 'Colima', 'Durango', 'Estado de Mexico', 'Guanajuato', 'Guerrero',
            'Hidalgo', 'Jalisco', 'Michoacan', 'Morelos', 'Nayarit', 'Nuevo Leon', 'Oaxaca', 'Puebla', 'Queretaro',
            'Quintana Roo', 'San Luis Potosi', 'Sinaloa', 'Sonora', 'Tabasco', 'Tamaulipas', 'Tlaxcala', 'Veracruz',
            'Yucatan', 'Zacatecas'
        ]

        responses['¿Dónde nació su abuelo materno?'] = st.selectbox('¿Dónde nació su abuelo materno?', estados_mexico)
        responses['¿Dónde nació su abuela materna?'] = st.selectbox('¿Dónde nació su abuela materna?', estados_mexico)
        responses['¿Dónde nació su abuelo paterno?'] = st.selectbox('¿Dónde nació su abuelo paterno?', estados_mexico)
        responses['¿Dónde nació su abuela paterna?'] = st.selectbox('¿Dónde nació su abuela paterna?', estados_mexico)
        responses['¿Dónde nació su padre?'] = st.selectbox('¿Dónde nació su padre?', estados_mexico)
        responses['¿Dónde nació su madre?'] = st.selectbox('¿Dónde nació su madre?', estados_mexico)
        responses['¿Dónde nació usted?'] = st.selectbox('¿Dónde nació usted?', estados_mexico)

        # Pregunta general
        st.text("¿Tuvo o tiene familiares con alguna enfermedad del corazón?")

        # Opciones de respuesta
        opciones = [' ', 'Sí', 'No', 'No sabe']
        respuesta_general = st.radio("Seleccione una opción:", opciones, key="enfermedades_familiares")


        st.text("¿Tuvo o tiene familiar(es) con?")

        enfermedades = [
            'Hipertensión', 'Dislipidemia',
            'Diabetes', 'Sobrepreso/Obesidad'
        ]

        opciones = [' ', 'Sí', 'No', 'No sabe']

        enfermedades_respuestas = {
            enfermedad: None for enfermedad in enfermedades
        }

        for enfermedad in enfermedades:
            enfermedades_respuestas[enfermedad] = st.radio(f"**{enfermedad}**", opciones, key=f"{enfermedad}")

        responses['Familiares con enfermedades específicas'] = enfermedades_respuestas

        preguntas = [
            "¿Fuma usted actualmente?",
            "¿En los últimos 3 meses ha tomado alcohol?",
            "¿Tiene exceso de peso?",
            "¿Tiene diabetes?",
            "¿Le han indicado medicamento para la diabetes?",
            "¿Tiene dislipidemia?",
            "¿Le han indicado medicamento para la dislipidemia?",
            "¿Tiene hipertensión?",
            "¿Le han indicado medicamento para la hipertensión?"
        ]

        opciones_preguntas = [' ', 'Sí', 'No', 'No sabe']

        preguntas_respuestas = {}
        for pregunta in preguntas:
            preguntas_respuestas[pregunta] = st.radio(pregunta, opciones_preguntas, key=pregunta)

        responses['Preguntas adicionales'] = preguntas_respuestas

        responses['¿El paciente firmó el consentimiento informado para participar como donador del Biobanco del INCICh?'] = st.selectbox(
            '¿Firmó el paciente el consentimiento informado?', ['Sí', 'No'], key='firma_consentimiento'
        )

        prefijo = 'CB' if responses.get('Procedencia del paciente') == 'Donador control' else st.selectbox('ID Muestra: "PB = Paciente Biobanco", "CB = Control Biobanco"', ['PB', 'CB'])

        whatsapp = st.text_input('Proporcione el WhatsApp del donante:')
        if not whatsapp.isdigit() or len(whatsapp) != 10:
            st.error('El número de WhatsApp debe contener exactamente 10 dígitos.')
        else:
            responses['WhatsApp'] = whatsapp

        email = st.text_input('Proporcione el correo electrónico del donante:', value="No proporcionó email")
        responses['Correo electrónico'] = email

        submit_button = st.form_submit_button(label='Guardar Respuestas')
        cancel_button = st.form_submit_button(label='Salir sin Guardar')

    if submit_button:
        if 'identificacion' not in st.session_state:
            st.session_state.identificacion = generar_identificacion(prefijo)

        responses['Identificación de la muestra'] = st.session_state.identificacion
        st.write("Identificación de la muestra generada:", st.session_state.identificacion)
        return responses

    return None

# Guardar respuestas localmente
def guardar_respuestas(responses):
    df_respuestas = pd.DataFrame([responses])

    with FileLock(LOCK_FILE):
        if os.path.exists(LOCAL_FILE_XLSX):
            df_existente = pd.read_excel(LOCAL_FILE_XLSX)

            if 'ID' not in df_existente.columns:
                df_existente['ID'] = range(1, len(df_existente) + 1)

            nuevo_id = df_existente['ID'].max() + 1
            df_respuestas['ID'] = nuevo_id

            df_final = pd.concat([df_existente, df_respuestas], ignore_index=True)
        else:
            df_respuestas['ID'] = 1
            df_final = df_respuestas

    df_final.to_excel(LOCAL_FILE_XLSX, index=False, engine='openpyxl')

# Función principal
def main():
    ssh_client, sftp_client = connect_to_remote()
    st.image("escudo_COLOR.jpg", width=150)
    if ssh_client and sftp_client:
        try:
            download_file(sftp_client, REMOTE_FILE_XLSX, LOCAL_FILE_XLSX)
            download_file(sftp_client, REMOTE_FILE_CSV, LOCAL_FILE_CSV)
            responses = generar_cuestionario()
            if responses:
                guardar_respuestas(responses)
                upload_file(sftp_client, LOCAL_FILE_XLSX, REMOTE_FILE_XLSX)
                upload_file(sftp_client, LOCAL_FILE_CSV, REMOTE_FILE_CSV)
        finally:
            close_connection(ssh_client, sftp_client)
    else:
        st.error("No se pudo conectar al servidor remoto.")

if __name__ == "__main__":
    main()

