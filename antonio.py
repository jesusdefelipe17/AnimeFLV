import requests
import json
from bs4 import BeautifulSoup
import os

# Lista de municipios de Ciudad Real (sin ñ)
municipios = [
    "almodovar-del-campo",
    "puertollano",
    "ciudad-real",
    "valdepenas",
    "manzanares",
    "miguelturra",
    "tomelloso",
    "alcazar-de-san-juan",
    "campo-de-criptana",
    "brazatortas",
    # Añadir más municipios según sea necesario
]

# Definimos un diccionario para almacenar los datos
resultados = []

for municipio in municipios:
    url = f"https://presupuestos.gobierto.es/municipios/{municipio}/partida/2022/338/G/functional"
    
    # Hacemos la solicitud a la página
    response = requests.get(url)
    
    if response.status_code == 200:
        # Utilizamos BeautifulSoup para parsear el HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Buscamos el atributo data-bubbles-data en el body
        body = soup.find('body')
        bubbles_data_url = body['data-bubbles-data']
        
        # Hacemos la solicitud a la URL del JSON
        bubbles_response = requests.get(bubbles_data_url)
        
        if bubbles_response.status_code == 200:
            bubbles_data = bubbles_response.json()
            
            # Guardamos el JSON en un archivo
            filename = f"{municipio.replace('-', '_')}_2023.json"  # Formatear el nombre del archivo
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(bubbles_data, f, ensure_ascii=False, indent=4)
            
            print(f"Datos guardados en {filename}")
        else:
            print(f"Error al acceder a {bubbles_data_url} para {municipio}")
    else:
        print(f"Error al acceder a la página de {municipio}")

print("Proceso completado.")
