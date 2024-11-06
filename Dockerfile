# Usa una imagen base de Python
FROM python:3.9-slim

# Establece el directorio de trabajo
WORKDIR /app

# Copia el archivo de dependencias (requirements.txt) y lo instala
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copia el resto de los archivos de la aplicación
COPY . .

# Expone el puerto, Railway usará la variable de entorno PORT
EXPOSE 8000

# Comando para ejecutar la aplicación (cambia a AnimeFLVAPI.py)
CMD ["python", "AnimeFLVAPI.py"]
