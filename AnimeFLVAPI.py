from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
import json
import re
import logging
from requests_html import HTMLSession
from flask_cors import CORS  # <-- Importa flask-cors
import unicodedata

app = Flask(__name__)
CORS(app)

# Configuración de logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def quitar_acentos(texto):
    """Elimina los acentos de un texto."""
    texto_normalizado = unicodedata.normalize('NFD', texto)
    texto_sin_acentos = ''.join(char for char in texto_normalizado if unicodedata.category(char) != 'Mn')
    return texto_sin_acentos

def extraer_datos_de_script(html):
    """Extrae la información de los episodios del script JavaScript en el HTML."""
    soup = BeautifulSoup(html, 'html.parser')
    script = soup.find('script', string=lambda t: t and 'var episodes = ' in t)
    if not script:
        logger.warning("No se encontró el script con los datos de episodios.")
        return []
    script_content = script.string
    start_index = script_content.find('var episodes = ') + len('var episodes = ')
    end_index = script_content.find(';', start_index)
    episodes_data = script_content[start_index:end_index].strip()
    try:
        episodes = json.loads(episodes_data)
    except json.JSONDecodeError:
        logger.error("Error al decodificar los datos JSON del script de episodios.")
        return []
    return episodes

import requests
from bs4 import BeautifulSoup
import logging

# Configura el logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def obtener_recién_añadidos():
    """Obtiene los animes más recientes de AnimeFLV según la fecha de adición."""
    url_recien_anadidos = "https://www3.animeflv.net/browse?order=updated"

    try:
        logger.info(f"Realizando solicitud GET a {url_recien_anadidos}")
        response = requests.get(url_recien_anadidos, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()
        logger.info(f"Solicitud exitosa. Código de estado: {response.status_code}")
        soup = BeautifulSoup(response.text, 'html.parser')
        logger.info("Buscando la lista de animes recientes en la página")
        lista_animes = soup.find('ul', class_='ListAnimes AX Rows A03 C02 D02')
        if not lista_animes:
            logger.warning("No se encontró la lista de animes recientes")
            return []
        recientes = []
        for item in lista_animes.find_all('li'):
            try:
                imagen_div = item.find('div', class_='Image')
                titulo_h3 = item.find('h3', class_='Title')
                descripcion_div = item.find('div', class_='Description')
                
                # Selecciona los elementos necesarios
                imagen_tag = imagen_div.find('img') if imagen_div else None
                portada = imagen_tag['src'] if imagen_tag else 'N/A'
                titulo = titulo_h3.text.strip() if titulo_h3 else 'N/A'
                
                # Extrae el segundo <p> para la descripción
                descripcion_p_tags = descripcion_div.find_all('p') if descripcion_div else []
                descripcion = descripcion_p_tags[1].text.strip() if len(descripcion_p_tags) > 1 else 'N/A'
                
                # Extrae la calificación
                calificacion_span = descripcion_div.find('span', class_='Vts fa-star')
                calificacion = calificacion_span.text.strip() if calificacion_span else 'N/A'
                
               # Extrae el tipo y seguidores
                tipo_span = descripcion_div.find('span', class_='Type') if descripcion_div else None
                tipo = tipo_span.text.strip() if tipo_span else 'N/A'

                # Elimina acentos del tipo
                tipo = quitar_acentos(tipo)

                # Obtener el href del enlace
                enlace = item.find('a')['href']
                # Extraer el ID del anime del href, quitando el prefijo "/anime/"
                id_anime = enlace.replace('/anime/', '').strip()
                    

                recientes.append({
                    'id': id_anime,
                    'titulo': titulo,
                    'portada': portada,
                    'calificacion': calificacion,
                    'descripcion': descripcion,
                    'tipo': tipo,
                })
            except Exception as e:
                logger.error(f"Error al procesar un elemento reciente: {e}")
        logger.info(f"Animes recientes encontrados: {len(recientes)}")
        return recientes
    except requests.RequestException as e:
        logger.error(f"Error en la solicitud HTTP: {e}")
        return []
    except Exception as e:
        logger.error(f"Error inesperado: {e}")
        return []


def obtener_populares():
    """Obtiene los animes más populares de AnimeFLV según la clasificación."""
    url_populares = "https://www3.animeflv.net/browse?order=rating"
  
    try:
        logger.info(f"Realizando solicitud GET a {url_populares}")
        response = requests.get(url_populares, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()
        logger.info(f"Solicitud exitosa. Código de estado: {response.status_code}")
        soup = BeautifulSoup(response.text, 'html.parser')
        logger.info("Buscando la lista de animes populares en la página")
        lista_animes = soup.find('ul', class_='ListAnimes AX Rows A03 C02 D02')
        if not lista_animes:
            logger.warning("No se encontró la lista de animes populares")
            return []
        populares = []
        for item in lista_animes.find_all('li'):
            try:
                imagen_div = item.find('div', class_='Image')
                titulo_h3 = item.find('h3', class_='Title')
                calificacion_span = item.find('span', class_='Vts fa-star')
                
                if imagen_div and titulo_h3 and calificacion_span:
                    imagen_tag = imagen_div.find('img')
                    portada = imagen_tag['src']
                    titulo = titulo_h3.text.strip()
                    calificacion = calificacion_span.text.strip()
                     # Obtener el href del enlace
                    enlace = item.find('a')['href']
                    # Extraer el ID del anime del href, quitando el prefijo "/anime/"
                    id_anime = enlace.replace('/anime/', '').strip()
                    
                    populares.append({
                        'id': id_anime,
                        'titulo': titulo,
                        'portada': portada,
                        'calificacion': calificacion  # Agregar calificación
                    })
            except Exception as e:
                logger.error(f"Error al procesar un elemento popular: {e}")
        logger.info(f"Animes populares encontrados: {len(populares)}")
        return populares
    except requests.RequestException as e:
        logger.error(f"Error en la solicitud HTTP: {e}")
        return []
    except Exception as e:
        logger.error(f"Error inesperado: {e}")
        return []

def obtener_nombre_serie(url_serie):
    """Extrae el nombre de la serie desde la URL sin modificar."""
    match = re.search(r'/anime/([^/]+)', url_serie)
    if match:
        return match.group(1)
    else:
        logger.warning("No se pudo extraer el nombre de la serie de la URL.")
        return None

def obtener_videos(url_episodio):
    """Extrae la información del video disponible para un episodio desde el script JavaScript."""
    response = requests.get(url_episodio)
    if response.status_code != 200:
        return []
    soup = BeautifulSoup(response.text, 'html.parser')
    script = soup.find('script', string=lambda t: t and 'var videos = ' in t)
    if not script:
        return []
    script_content = script.string
    start_index = script_content.find('var videos = ') + len('var videos = ')
    end_index = script_content.find(';', start_index)
    videos_data = script_content[start_index:end_index].strip()
    try:
        videos = json.loads(videos_data)
    except json.JSONDecodeError:
        return []
    video_info = []
    for video_type, video_list in videos.items():
        for video in video_list:
            video_info.append({
                'titulo': video.get('title', 'No disponible'),
                'url': video.get('url', ''),
                'server': video.get('server', ''),
                'code': video.get('code', '')
            })
    return video_info

def obtener_episodios(url_serie):
    """Obtiene todos los episodios disponibles para la serie."""
    url_serie = url_serie.replace('/ver/', '/anime/')
    url_serie = re.sub(r'-\d+$', '', url_serie)  # Eliminar el número final de la URL
    try:
        logger.info(f"Realizando solicitud GET a {url_serie}")
        response = requests.get(url_serie,headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()
        logger.info(f"Solicitud exitosa. Código de estado: {response.status_code}")
        html = response.text
        episodios_data = extraer_datos_de_script(html)
        if not episodios_data:
            logger.warning("No se encontraron datos de episodios.")
            return []
        nombre_serie = obtener_nombre_serie(url_serie)
        if not nombre_serie:
            logger.warning("No se pudo extraer el nombre de la serie.")
            return []
        episodios = []
        for episodio_num, episodio_id in episodios_data:
            url = f'https://www3.animeflv.net/ver/{nombre_serie}-{episodio_num}'
            episodios.append({'enlace': url, 'episodio': f"Episodio {episodio_num}"})
        episodios.sort(key=lambda x: int(re.search(r'(\d+)$', x['episodio']).group(1)))
        return episodios
    except requests.RequestException as e:
        logger.error(f"Error en la solicitud HTTP: {e}")
        return []
    except Exception as e:
        logger.error(f"Error inesperado: {e}")
        return []

def buscar_serie(nombre_serie):
    """Busca una serie en AnimeFLV y devuelve los resultados."""
    url_busqueda = f"https://www3.animeflv.net/browse?q={nombre_serie.replace(' ', '%20')}"
    try:
        logger.info(f"Realizando solicitud GET a {url_busqueda}")
        response = requests.get(url_busqueda, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()
        logger.info(f"Solicitud exitosa. Código de estado: {response.status_code}")
        soup = BeautifulSoup(response.content, 'html.parser')
        resultados = soup.find('ul', class_='ListAnimes AX Rows A03 C02 D02')
        if not resultados:
            logger.warning("No se encontraron resultados de búsqueda.")
            return []
        series = []
        for resultado in resultados.find_all('li'):
            enlace = resultado.find('a', href=True)
            titulo = resultado.find('h3', class_='Title')
            if enlace and titulo:
                url = 'https://www3.animeflv.net' + enlace['href']
                series.append({'titulo': titulo.text.strip(), 'url': url})
        return series
    except requests.RequestException as e:
        logger.error(f"Error en la solicitud HTTP: {e}")
        return []
    except Exception as e:
        logger.error(f"Error inesperado: {e}")
        return []

def obtener_ultimos_animes():
    """Obtiene los últimos animes de AnimeFLV."""
    url_ultimos_animes = "https://www3.animeflv.net"
  
    try:
        logger.info(f"Realizando solicitud GET a {url_ultimos_animes}")
        response = requests.get(url_ultimos_animes,headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()
        logger.info(f"Solicitud exitosa. Código de estado: {response.status_code}")
        soup = BeautifulSoup(response.text, 'html.parser')
        logger.info("Buscando la lista de animes en la página")
        lista_animes = soup.find('ul', class_='ListEpisodios AX Rows A06 C04 D03')
        if not lista_animes:
            logger.warning("No se encontró la lista de animes")
            return []
        animes = []
        for item in lista_animes.find_all('li'):
            try:
                enlace = item.find('a', href=True)
                titulo = item.find('strong', class_='Title')
                episodio = item.find('span', class_='Capi')
                portada = item.find('span', class_='Image')
                img_tag = portada.find('img')
                match = re.search(r'/([^/]+)-\d+$', enlace['href'])  # Captura la parte antes del número final
                if match:
                    id = match.group(1)  # Capturamos el nombre sin el número
                else:
                    id = enlace['href'].split('/')[-1]  # Si no coincide, usamos el valor completo
                if enlace and titulo and episodio:
                    animes.append({
                        'id':id,
                        'titulo': titulo.text.strip(),
                        'enlace': 'https://www3.animeflv.net' + enlace['href'],
                        'episodio': episodio.text.strip(),
                        'portada':'https://www3.animeflv.net' + img_tag['src']
                    })
                else:
                    logger.warning(f"Elemento faltante en uno de los ítems: {item}")
            except Exception as e:
                logger.error(f"Error al procesar un elemento: {e}")
        logger.info(f"Animes encontrados: {len(animes)}")
        return animes
    except requests.RequestException as e:
        logger.error(f"Error en la solicitud HTTP: {e}")
        return []
    except Exception as e:
        logger.error(f"Error inesperado: {e}")
        return []

def obtener_imagen_y_descripcion(url_serie):
    """Obtiene la imagen y la descripción de una serie desde su URL."""
    url_serie = url_serie.replace('/ver/', '/anime/')
    url_serie = re.sub(r'-\d+$', '', url_serie)  # Eliminar el número final de la URL
    try:
        logger.info(f"Realizando solicitud GET a {url_serie}")
        response = requests.get(url_serie,headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()
        logger.info(f"Solicitud exitosa. Código de estado: {response.status_code}")
        soup = BeautifulSoup(response.text, 'html.parser')
        imagen = soup.find('div', class_='AnimeCover')
        descripcion = soup.find('div', class_='Description')
        if imagen and descripcion:
            imagen_tag = imagen.find('img')
            imagen_url = 'https://www3.animeflv.net' + imagen_tag['src']
            descripcion_texto = descripcion.find('p').text.strip()
            return imagen_url, descripcion_texto
        else:
            logger.warning("No se encontró la imagen o descripción.")
            return None, None
    except requests.RequestException as e:
        logger.error(f"Error en la solicitud HTTP: {e}")
        return None, None
    except Exception as e:
        logger.error(f"Error inesperado: {e}")
        return None, None

@app.route('/api/getAnime', methods=['GET'])
def api_buscar_serie():
    nombre_serie = request.args.get('anime')
    if not nombre_serie:
        return jsonify({'error': 'El parámetro "anime" es obligatorio.'}), 400
    series = buscar_serie(nombre_serie)
    return jsonify(series)

@app.route('/api/episodios', methods=['GET'])
def api_obtener_episodios():
    url_serie = request.args.get('url_serie')
    if not url_serie:
        return jsonify({'error': 'El parámetro "url_serie" es obligatorio.'}), 400
    episodios = obtener_episodios(url_serie)
    return jsonify(episodios)

@app.route('/api/videos', methods=['GET'])
def api_obtener_videos():
    url_episodio = request.args.get('url_episodio')
    if not url_episodio:
        return jsonify({'error': 'El parámetro "url_episodio" es obligatorio.'}), 400
    videos = obtener_videos(url_episodio)
    return jsonify(videos)

@app.route('/api/ultimosAnimes', methods=['GET'])
def api_obtener_ultimos_animes():
    animes = obtener_ultimos_animes()
    return jsonify(animes)

@app.route('/api/imagen_y_descripcion', methods=['GET'])
def api_obtener_imagen_y_descripcion():
    url_serie = request.args.get('url_serie')
    if not url_serie:
        return jsonify({'error': 'El parámetro "url_serie" es obligatorio.'}), 400
    imagen_url, descripcion = obtener_imagen_y_descripcion(url_serie)
    if imagen_url and descripcion:
        return jsonify({'imagen_url': imagen_url, 'descripcion': descripcion})
    else:
        return jsonify({'error': 'No se pudo obtener la imagen o descripción.'}), 404

@app.route('/api/getPopulares', methods=['GET'])
def api_obtener_populares():
    populares = obtener_populares()
    return jsonify(populares)

@app.route('/api/getRecienAnadidos', methods=['GET'])
def api_obtener_recién_añadidos():
    recientes = obtener_recién_añadidos()
    return jsonify(recientes)

@app.route('/api/test', methods=['GET'])
def test():
    return jsonify({'status': 'OK', 'message': 'API funcionando correctamente'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
