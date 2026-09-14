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


# --- ENDPOINTS (Rutas de FastAPI) ---

@app.get("/health", status_code=status.HTTP_200_OK)
def health():
    return {"message": "OK"}

@app.post("/analyze", status_code=status.HTTP_200_OK)
async def analizar_datos(request: AnalisisRequest):
    """
    El orquestador principal. Sigue este flujo llamando a las funciones auxiliares:
    
    1. Verifica que el archivo exista en el volumen.
    2. Llama a obtener_columnas_csv().
    3. Llama a construir_prompt_sistema().
    4. Llama a solicitar_codigo_a_ollama().
    5. Llama a extraer_codigo_python().
    6. Llama a ejecutar_codigo_seguro().
    7. Si el código generó una imagen, la lee y la convierte a Base64.
    8. Retorna el código generado, la salida de la consola y la imagen (si hay).
    """
    # Extraemos las rutas
    ruta_csv = os.path.join(DATA_DIR, request.nombre_archivo)
    ruta_script = os.path.join(DATA_DIR, "temp_script.py")
    ruta_imagen = os.path.join(DATA_DIR, "output_plot.png")

    # Si no existe la ruta del .csv
    if not os.path.exists(ruta_csv):
        raise HTTPException(status_code=404, detail="Archivo no encontrado.")

    # Pre-analisis con pandas, df.describe() saca la media, min, max y cuartiles (ideal para outliers)
    try:
        df = pd.read_csv(ruta_csv)
        resumen_estadistico = df.describe().to_string()
        tipos_datos = df.dtypes.to_string()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error leyendo CSV: {e}")

    # Borramos imagen vieja
    if os.path.exists(ruta_imagen):
        os.remove(ruta_imagen)

    # PROMPT DEL SISTEMA ULTRA-ESPECÍFICO
    system_prompt = f"""
    Eres un Analista de Datos Senior. Tienes acceso a un dataset en '{ruta_csv}'.
    
    Aquí tienes el resumen estadístico de los datos:
    {resumen_estadistico}
    
    Y los tipos de datos de las columnas:
    {tipos_datos}

    TU TAREA:
    1. Primero, redacta un breve análisis (identifica outliers basándote en los máximos/mínimos del resumen, da recomendaciones o insights).
    2. Luego, escribe un script en Python (dentro de un bloque ```python ```) que responda a la petición del usuario: "{request.prompt_usuario}".
    
    REGLAS DEL CÓDIGO:
    - Usa pandas y matplotlib/seaborn.
    - INCLUYE SIEMPRE: import matplotlib; matplotlib.use('Agg')
    - NUNCA uses plt.show(). Guarda el gráfico en '{ruta_imagen}' usando plt.savefig().
    """

    # LLAMAR A OLLAMA LOCAL
    try:
        response = requests.post(f"{OLLAMA_URL}/api/generate", json={
            "model": "qwen2.5-coder", 
            "prompt": system_prompt,
            "stream": False
        })
        response.raise_for_status()
        respuesta_completa = response.json()["response"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error contactando a Ollama: {e}")

    # EXTRAER Y EJECUTAR EL CÓDIGO
    codigo_python = extraer_codigo_python(respuesta_completa)
    
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

    # CARGAR LA IMAGEN (si el script funcionó y la creó)
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
    1. Valida que la extensión sea .csv.
    2. Guarda el archivo en el volumen de Docker (ej. /app/data/).
    3. Retorna el nombre del archivo para que el frontend sepa que funcionó.
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
    """Devuelve una lista con los nombres de los archivos CSV guardados."""
    try:
        # Lista los archivos en el volumen que terminen en .csv
        archivos = [f for f in os.listdir(DATA_DIR) if f.endswith('.csv')]
        return {"archivos": archivos}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al leer carpeta: {e}")

@app.delete("/files/{nombre_archivo}", status_code=status.HTTP_200_OK)
async def borrar_archivo(nombre_archivo: str):
    """Elimina un archivo específico del volumen."""
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

