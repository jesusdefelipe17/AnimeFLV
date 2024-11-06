# Usa una imagen base de Python
FROM python:3.9-slim

# Establece el directorio de trabajo
WORKDIR /app

# Copia el archivo de dependencias y las instala
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copia el resto de los archivos de la aplicación
COPY . .

# Expone el puerto (aunque Railway lo asignará automáticamente)
EXPOSE 8000

# Define el comando para correr la aplicación
CMD ["gunicorn", "AnimeFLVAPI:app", "--bind", "0.0.0.0:$PORT"]
