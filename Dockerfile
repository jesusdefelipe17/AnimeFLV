# Usa una imagen base de Python
FROM python:3.9-slim

# Establece el directorio de trabajo
WORKDIR /app

# Copia el archivo de dependencias y las instala
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copia el resto de los archivos de la aplicación
COPY . .

# Expone el puerto 8000, aunque Railway debería asignar `PORT`
EXPOSE 8000

# Define el puerto en las variables de entorno de Docker
ENV PORT=8000

# Comando para ejecutar la aplicación
CMD ["python", "AnimeFLVAPI.py"]
