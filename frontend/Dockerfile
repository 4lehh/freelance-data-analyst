FROM python:3.11-slim

# Establecemos el directorio de trabajo
WORKDIR /app

# Copiamos primero SOLO el requirements (esto optimiza la caché de Docker)
COPY requirements.txt .

# Instalamos las dependencias
RUN pip install --no-cache-dir -r requirements.txt 

# Copiamos el resto del código (tu app.py)
COPY . .

# Indicamos qué puerto usa el contenedor para Streamlit
EXPOSE 8501

# Ejecutamos Streamlit
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]