import requests
import json
from bs4 import BeautifulSoup

# Lista de municipios de Ciudad Real (sin ñ)
municipios = [
    "almodovar-del-campo",
    # Añadir más municipios según sea necesario
]

# Función para guardar datos
def guardar_datos(municipio, anio):
    # URL para la solicitud principal
    url = f"https://presupuestos.gobierto.es/municipios/{municipio}/partida/{anio}/338/G/functional"
    
    # Hacemos la solicitud a la página
    response = requests.get(url)
    
    if response.status_code == 200:
        # Utilizamos BeautifulSoup para parsear el HTML
        soup = BeautifulSoup(response.content, 'html.parser')

        # Buscamos el atributo data-bubbles-data en el body
        body = soup.find('body')
        if body:
            bubbles_data_url = body['data-bubbles-data']
            # Hacemos la solicitud a la URL del JSON de bubbles
            bubbles_response = requests.get(bubbles_data_url)
            if bubbles_response.status_code == 200:
                bubbles_data = bubbles_response.json()
                # Guardamos el JSON de bubbles en un archivo
                bubbles_filename = f"{municipio.replace('-', '_')}_{anio}.json"  # Formatear el nombre del archivo
                with open(bubbles_filename, 'w', encoding='utf-8') as f:
                    json.dump(bubbles_data, f, ensure_ascii=False, indent=4)
                print(f"Datos Bubbles guardados en {bubbles_filename}")
            else:
                print(f"Error al acceder a la URL de Bubbles para {municipio} en {anio}")

        # Hacemos la solicitud a la URL del JSON para obtener los datos de línea directamente
        line_response = requests.get(f"https://presupuestos.gobierto.es/api/data/lines/budget_line/{municipio}/{anio}/total_budget/G/338/functional.json?places_collection=ine")
        
        if line_response.status_code == 200:
            line_data = line_response.json()
            # Guardamos el JSON de la línea en un archivo
            line_filename = f"{municipio.replace('-', '_')}_{anio}_fiestas_populares_y_festejos.json"  # Formatear el nombre del archivo
            with open(line_filename, 'w', encoding='utf-8') as f:
                json.dump(line_data, f, ensure_ascii=False, indent=4)
            print(f"Datos Line guardados en {line_filename}")
        else:
            print(f"Error al acceder a la URL del JSON de la línea para {municipio} en {anio}")
    else:
        print(f"Error al acceder a la página de {municipio} para el año {anio}")

# Ejemplo de uso
anio = input("Introduce el año que quieres consultar (por defecto 2023): ") or "2023"
for municipio in municipios:
    guardar_datos(municipio, anio)

print("Proceso completado.")
