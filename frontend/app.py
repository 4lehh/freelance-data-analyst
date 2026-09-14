import streamlit as st
import requests
import base64
import os

# Configuración inicial de la página
st.set_page_config(page_title="Analista de Datos Local", layout="wide")

# Usamos la variable de entorno para Docker, con localhost como respaldo
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.title("🤖 Tu Analista de Datos Local")
st.markdown("Sube tu dataset, hazle una pregunta y el LLM escribirá y ejecutará el código para darte la respuesta.")

# --- MANEJO DEL ESTADO ---
# Usamos session_state para que Streamlit no olvide el nombre del archivo si interactuamos con otros botones
if "nombre_archivo" not in st.session_state:
    st.session_state.nombre_archivo = None

# --- BARRA LATERAL: GESTIÓN DE ARCHIVOS ---
with st.sidebar:
    st.header("1. Carga de Datos")
    
    # --- SUBIR ARCHIVOS NUEVOS ---
    archivo_subido = st.file_uploader("Sube tu archivo CSV", type=["csv"])
    if archivo_subido is not None:
        if st.button("Subir al servidor", use_container_width=True):
            with st.spinner("Subiendo..."):
                archivos = {"file": (archivo_subido.name, archivo_subido.getvalue(), "text/csv")}
                try:
                    respuesta = requests.post(f"{BACKEND_URL}/upload", files=archivos)
                    if respuesta.status_code == 201:
                        st.success("¡Archivo guardado!")
                        st.session_state.nombre_archivo = archivo_subido.name
                        # Forzamos una recarga para que la lista de abajo se actualice
                        st.rerun() 
                    else:
                        st.error("Error al subir el archivo.")
                except Exception as e:
                    st.error(f"Error de conexión: {e}")
    
    st.divider()

    # --- LISTAR Y GESTIONAR ARCHIVOS EXISTENTES ---
    st.header("📁 Archivos Disponibles")
    
    try:
        res_archivos = requests.get(f"{BACKEND_URL}/files")
        if res_archivos.status_code == 200:
            lista_archivos = res_archivos.json().get("archivos", [])
            
            if lista_archivos:
                # Menú desplegable para elegir qué archivo queremos analizar
                archivo_seleccionado = st.selectbox(
                    "Selecciona un dataset para analizar:", 
                    options=lista_archivos,
                    # Si ya hay uno en memoria, lo ponemos por defecto
                    index=lista_archivos.index(st.session_state.nombre_archivo) if st.session_state.nombre_archivo in lista_archivos else 0
                )
                
                # Actualizamos el estado de la sesión con el archivo elegido
                st.session_state.nombre_archivo = archivo_seleccionado
                
                # Botón de eliminar (le damos un color rojo sutil)
                if st.button("🗑️ Eliminar archivo actual", type="secondary", use_container_width=True):
                    res_delete = requests.delete(f"{BACKEND_URL}/files/{archivo_seleccionado}")
                    if res_delete.status_code == 200:
                        st.success("Archivo eliminado.")
                        # Si borramos el archivo activo, limpiamos la variable
                        if st.session_state.nombre_archivo == archivo_seleccionado:
                            st.session_state.nombre_archivo = None
                        st.rerun()
            else:
                st.info("No hay archivos en el servidor. Sube uno arriba.")
                st.session_state.nombre_archivo = None
    except Exception as e:
        st.error("No se pudo conectar con el backend para listar archivos.")

# --- SECCIÓN PRINCIPAL: ANÁLISIS ---
if st.session_state.nombre_archivo:
    st.header("2. Zona de Análisis")
    st.info(f"Dataset activo: **{st.session_state.nombre_archivo}**")
    
    prompt = st.text_area(
        "¿Qué quieres investigar?", 
        placeholder="Ej: Haz un boxplot de los salarios por departamento y dime si hay outliers."
    )
    
    if st.button("Ejecutar Análisis"):
        if not prompt.strip():
            st.warning("Por favor, escribe una instrucción.")
        else:
            with st.spinner("Generando y ejecutando código... Esto puede tomar unos segundos."):
                payload = {
                    "nombre_archivo": st.session_state.nombre_archivo,
                    "prompt_usuario": prompt
                }
                
                try:
                    respuesta = requests.post(f"{BACKEND_URL}/analyze", json=payload)
                    
                    if respuesta.status_code == 200:
                        datos = respuesta.json()
                        
                        # 1. Mostrar el análisis redactado por el modelo
                        st.subheader("📝 Análisis")
                        st.write(datos.get("analisis_texto", "No se generó texto descriptivo."))
                        
                        # 2. Visualizar la imagen generada
                        if datos.get("imagen_base64"):
                            st.subheader("📊 Gráfico")
                            # Decodificamos el Base64 que nos mandó FastAPI de vuelta a bytes
                            image_bytes = base64.b64decode(datos["imagen_base64"])
                            st.image(image_bytes, use_container_width=True)
                        
                        # 3. Sección expandible para el código y los botones de descarga
                        with st.expander("Ver Código y Detalles de Consola"):
                            codigo = datos.get("codigo_generado", "")
                            if codigo:
                                st.code(codigo, language="python")
                                
                                # Botón nativo de Streamlit para descargar archivos
                                st.download_button(
                                    label="Descargar Script (.py)",
                                    data=codigo,
                                    file_name="script_analisis.py",
                                    mime="text/x-python"
                                )
                            
                            # Mostrar si hubo errores de ejecución (stderr)
                            if datos.get("consola_errores"):
                                st.error("El script arrojó el siguiente error:")
                                st.code(datos["consola_errores"])
                                
                    else:
                        st.error(f"Error del servidor: {respuesta.status_code}")
                except Exception as e:
                    st.error(f"Error de conexión con FastAPI: {e}")
else:
    st.warning("👈 Por favor, sube un archivo desde el menú lateral para comenzar.")