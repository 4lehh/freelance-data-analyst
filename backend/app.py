from fastapi import FastAPI, File, status, UploadFile, HTTPException
from pydantic import BaseModel
import uvicorn
import pandas as pd
import shutil
import requests
import subprocess
import os
import re
import base64

# App
app = FastAPI()

# Carpeta data
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)        # Se crea si no existe

# Ollama
OLLAMA_URL = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = "qwen2.5-coder"

# Data del modelo
class AnalisisRequest(BaseModel):
    nombre_archivo: str
    prompt_usuario: str

# Funciones utiles

def extraer_codigo_python(respuesta_cruda: str) -> str:
    """
    Usa Expresiones Regulares (Regex) para buscar bloques ```python ... ```
    y extraer únicamente el código, ignorando saludos o texto extra.
    """
    match = re.search(r'```python\s*(.*?)\s*```', respuesta_cruda, re.DOTALL)
    return match.group(1).strip() if match else ""

def obtener_rutar(nombre_archivo: str) -> tuple:
    ruta_csv = os.path.join(DATA_DIR, nombre_archivo)
    ruta_script = os.path.join(DATA_DIR, "temp_script.py")
    ruta_imagen = os.path.join(DATA_DIR, "output_plot.png")

    return ruta_csv, ruta_script, ruta_imagen

def obtener_estadisticos_descriptivos(ruta_csv: str) -> tuple:
    try:
        df = pd.read_csv(ruta_csv)
        resumen_estadistico = df.describe().to_string()
        tipos_datos = df.dtypes.to_string()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error leyendo CSV: {e}")

    return resumen_estadistico, tipos_datos

def crear_prompt(ruta_csv: str, ruta_imagen: str, resumen_estadistico, tipos_datos, prompt_usuario) -> str:
    system_prompt = f"""
        Eres un Analista de Datos Senior. Tienes acceso a un dataset en '{ruta_csv}'.
        
        Aquí tienes el resumen estadístico de los datos:
        {resumen_estadistico}
        
        Y los tipos de datos de las columnas:
        {tipos_datos}
    
        TU TAREA:
        1. Primero, redacta un breve análisis (identifica outliers basándote en los máximos/mínimos del resumen, da recomendaciones o insights).
        2. Luego, escribe un script en Python (dentro de un bloque ```python ```) que responda a la petición del usuario: "{prompt_usuario}".
        
        REGLAS DEL CÓDIGO:
        - Usa pandas y matplotlib/seaborn.
        - INCLUYE SIEMPRE: import matplotlib; matplotlib.use('Agg')
        - NUNCA uses plt.show(). Guarda el gráfico en '{ruta_imagen}' usando plt.savefig().
        - REGLA CRÍTICA: Antes de calcular correlaciones (df.corr()) o aplicar operaciones matemáticas, DEBES aislar solo las columnas numéricas usando: df.select_dtypes(include=['number']).
        """

    return system_prompt

def obtener_salida_errores(codigo_python: str, ruta_script: str) -> tuple:
    stdout = ""
    stderr = ""
    if codigo_python:
        with open(ruta_script, "w", encoding="utf-8") as f:
            f.write(codigo_python)
        
        proceso = subprocess.run(
            ["python", ruta_script],
            capture_output=True, text=True, timeout=30
        )
        stdout = proceso.stdout
        stderr = proceso.stderr

    return stdout, stderr

# --- ENDPOINTS (Rutas de FastAPI) ---

@app.get("/health", status_code=status.HTTP_200_OK)
def health():
    """
    Salud!
    """
    return {"message": "OK"}

@app.post("/analyze", status_code=status.HTTP_200_OK)
async def analizar_datos(request: AnalisisRequest):
    """
    Este endpoint carga el prompt del usuario y el dataset entregado para luego llamar a Ollama y obtener lo solicitado.
    """
    # Extraemos las rutas
    ruta_csv, ruta_script, ruta_imagen = obtener_rutar(nombre_archivo=request.nombre_archivo)

    # Si no existe la ruta del .csv
    if not os.path.exists(ruta_csv):
        raise HTTPException(status_code=404, detail="Archivo no encontrado.")

    # Pre-analisis con pandas, df.describe() saca la media, min, max y cuartiles (ideal para outliers)
    resumen_estadistico, tipos_datos = obtener_estadisticos_descriptivos(ruta_csv=ruta_csv)

    # Borramos imagen vieja
    if os.path.exists(ruta_imagen):
        os.remove(ruta_imagen)

    # Creacion prompt
    system_prompt = crear_prompt(ruta_csv=ruta_csv, ruta_imagen=ruta_imagen, resumen_estadistico=resumen_estadistico, tipos_datos=tipos_datos, prompt_usuario=request.prompt_usuario)

    # Llamar a Ollama
    try:
        response = requests.post(f"{OLLAMA_URL}/api/generate", json={
            "model": OLLAMA_MODEL, 
            "prompt": system_prompt,
            "stream": False
        })
        response.raise_for_status()
        respuesta_completa = response.json()["response"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error contactando a Ollama: {e}")

    # Extraer el codigo y ejecutarlo
    codigo_python = extraer_codigo_python(respuesta_completa)

    # Obtener la salida y los errores
    stdout, stderr = obtener_salida_errores(codigo_python=codigo_python, ruta_script=ruta_script)
    

    # Cargar la imagen (si el script funcionó y la creó)
    imagen_base64 = None
    if os.path.exists(ruta_imagen):
        with open(ruta_imagen, "rb") as f:
            imagen_base64 = base64.b64encode(f.read()).decode('utf-8')

    # Devolvemos TODO: El análisis de texto de Gemma, la salida del código y la imagen
    return {
        "analisis_texto": respuesta_completa.replace(f"```python\n{codigo_python}\n```", ""), # El texto sin el código
        "codigo_generado": codigo_python,
        "consola_salida": stdout,
        "consola_errores": stderr,
        "imagen_base64": imagen_base64
    }



@app.post("/upload", status_code=status.HTTP_201_CREATED)
async def subir_csv(file: UploadFile = File(...)):
    """
    Sube un archivo .csv y lo guarda dentro de un contenedor Docker.
    """

    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Formato invalido. Se deben subir archivos .csv")

    # Construir ruta fisica donde se guardará
    file_path = os.path.join(DATA_DIR, file.filename)

    try:
        # Abrimos un archivo en blanco en modo "wb" (write binary)
        with open(file_path, "wb") as buffer:
            # shutil mueve los bytes del archivo temporal de FastAPI al disco duro
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al guardar el archivo: {str(e)}")

    # 4. Respuesta exitosa
    return {
        "mensaje": "Archivo subido correctamente", 
        "nombre_archivo": file.filename
    }

@app.get("/files", status_code=status.HTTP_200_OK)
async def listar_archivos():
    """
    Devuelve una lista con los nombres de los archivos CSV guardados.
    """

    try:
        # Lista los archivos en el volumen que terminen en .csv
        archivos = [f for f in os.listdir(DATA_DIR) if f.endswith('.csv')]
        return {"archivos": archivos}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al leer carpeta: {e}")

@app.delete("/files/{nombre_archivo}", status_code=status.HTTP_200_OK)
async def borrar_archivo(nombre_archivo: str):
    """
    Elimina un archivo específico del volumen. Se debe colocar el nombre del archivo junto a su extensión.
    Ejemplo: dataset.csv
    """
    ruta_archivo = os.path.join(DATA_DIR, nombre_archivo)
    
    if not os.path.exists(ruta_archivo):
        raise HTTPException(status_code=404, detail="Archivo no encontrado.")
    
    try:
        os.remove(ruta_archivo)
        return {"mensaje": f"Archivo {nombre_archivo} eliminado con éxito."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al eliminar: {e}")


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)