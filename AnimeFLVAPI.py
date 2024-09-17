from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
import json
import re
import logging
from requests_html import HTMLSession

app = Flask(__name__)

# Configuración de logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

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
    session = HTMLSession()
    try:
        logger.info(f"Realizando solicitud GET a {url_episodio}")
        response = session.get(url_episodio,headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()
        logger.info(f"Solicitud exitosa. Código de estado: {response.status_code}")
        response.html.render(timeout=20)  # Renderizar JavaScript
        soup = BeautifulSoup(response.content, 'html.parser')
        script = soup.find('script', string=lambda t: t and 'var videos = ' in t)
        if not script:
            logger.warning("No se encontró el script con los datos de videos.")
            return []
        script_content = script.string
        start_index = script_content.find('var videos = ') + len('var videos = ')
        end_index = script_content.find(';', start_index)
        videos_data = script_content[start_index:end_index].strip()
        try:
            videos = json.loads(videos_data)
        except json.JSONDecodeError:
            logger.error("Error al decodificar los datos JSON del script de videos.")
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
    except requests.RequestException as e:
        logger.error(f"Error en la solicitud HTTP: {e}")
        return []
    except Exception as e:
        logger.error(f"Error inesperado: {e}")
        return []
    finally:
        session.close()

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
                if enlace and titulo and episodio:
                    animes.append({
                        'titulo': titulo.text.strip(),
                        'enlace': 'https://www3.animeflv.net' + enlace['href'],
                        'episodio': episodio.text.strip()
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

@app.route('/api/test', methods=['GET'])
def test():
    return jsonify({'status': 'OK', 'message': 'API funcionando correctamente'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
