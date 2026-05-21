FROM python:3.12-slim

WORKDIR /app

# Instalar dependencias primero para aprovechar la caché de capas de Docker.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código de la aplicación.
COPY app.py .

EXPOSE 3000

# Arrancar la API con uvicorn en el puerto 3000.
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "3000"]
