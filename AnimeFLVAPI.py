from flask import Flask, request, jsonify, g
import requests
from bs4 import BeautifulSoup
import json
import re
import logging
from requests_html import HTMLSession
from flask_cors import CORS  
import unicodedata
from cachetools import TTLCache
import sqlite3
import random
from datetime import datetime

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})  # Permitir cualquier origen

# Configuración de logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Referer': 'https://www.google.com/'
}


cache = TTLCache(maxsize=1000, ttl=86400)

# Función para obtener la conexión a la base de datos
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect('anime.db')
    return g.db

# Cerrar la conexión a la base de datos al final de la solicitud@app.teardown_appcontext
def close_db(error):
    if hasattr(g, 'db'):
        db = g.pop('db', None)
        if db is not None:
            db.close()

# Crear la tabla si no existe (esto lo puedes hacer al iniciar la app)
with sqlite3.connect('anime.db') as conn:
    cursor = conn.cursor()

    # Crear la tabla 'series' si no existe
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS series (
        id TEXT PRIMARY KEY,
        titulo TEXT,
        url TEXT,
        poster TEXT,
        tipo TEXT,
        puntuacion TEXT,
        descripcion TEXT
    )
    ''')

    # Crear la tabla 'episodios' si no existe
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS episodios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        serie_id TEXT,
        numero TEXT,
        url TEXT,
        videos TEXT,
        FOREIGN KEY (serie_id) REFERENCES series(id)
    )
    ''')

    # Confirmar los cambios en la base de datos
    conn.commit()

def guardar_serie_en_bbdd(serie_data):
    """Guarda los datos de una serie en la base de datos."""
    try:
        db = get_db()
        cursor = db.cursor()

        id_serie = serie_data.get('id')
        titulo = serie_data.get('titulo')
        url = serie_data.get('url')
        poster = serie_data.get('poster')
        tipo = serie_data.get('tipo')
        puntuacion = serie_data.get('puntuacion')
        descripcion = serie_data.get('descripcion')

        # Insertar los datos en la base de datos
        cursor.execute('''
            INSERT OR REPLACE INTO series (id, titulo, url, poster, tipo, puntuacion, descripcion)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (id_serie, titulo, url, poster, tipo, puntuacion, descripcion))

        # Guardar los cambios
        db.commit()

        print(f"Datos de la serie '{titulo}' guardados correctamente.")

    except sqlite3.Error as e:
        print(f"Error al guardar los datos en la base de datos: {str(e)}")


def convertir_fecha_a_formato_espanol(fecha):
    """Convierte una fecha del formato 'YYYY/MM/DD HH:MM:SS AM/PM' al formato español 'DD/MM/YYYY HH:MM:SS' en 24 horas."""
    try:
        # Convertimos la cadena de fecha al objeto datetime
        fecha_dt = datetime.strptime(fecha, '%Y/%m/%d %I:%M:%S %p')
        # Formateamos la fecha al formato deseado (DD/MM/YYYY HH:MM:SS en 24 horas)
        fecha_espanol = fecha_dt.strftime('%d/%m/%Y %H:%M:%S')
        return fecha_espanol
    except ValueError:
        return 'Fecha no disponible'

def clean_string(s):
    """Elimina caracteres Unicode no deseados y devuelve un string limpio."""
    # Decodifica caracteres Unicode y reemplaza caracteres indeseables
    return s.encode('utf-8').decode('unicode_escape').replace("\u200b", '').replace("\u00a0", ' ').strip()


def quitar_acentos(texto):
    """Elimina los acentos de un texto."""
    texto_normalizado = unicodedata.normalize('NFD', texto)
    texto_sin_acentos = ''.join(char for char in texto_normalizado if unicodedata.category(char) != 'Mn')
    return texto_sin_acentos

def quitar_acentos_y_caracteres_raros(texto):
    """Elimina los acentos, comillas y caracteres especiales de un texto."""
    # Normalizar texto para eliminar acentos
    texto_normalizado = unicodedata.normalize('NFD', texto)
    texto_sin_acentos = ''.join(char for char in texto_normalizado if unicodedata.category(char) != 'Mn')
    
    # Eliminar caracteres no alfanuméricos (excepto espacios)
    texto_limpio = re.sub(r'[^a-zA-Z0-9\s]', '', texto_sin_acentos).replace("\r","").replace("\n"," ")

    return texto_limpio

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
        response = requests.get(url_recien_anadidos, headers=headers)
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
        response = requests.get(url_populares, headers=headers)
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
    
    # Revisamos si el episodio ya está en la caché
    if url_episodio in cache:
        logger.info(f"Obteniendo datos cacheados para el episodio {url_episodio}")
        return cache[url_episodio]
    
    try:
        # Añadimos el timeout de 1 segundo a la solicitud
        response = requests.get(url_episodio, timeout=1, headers=headers)
        if response.status_code != 200:
            logger.warning(f"Error al obtener el episodio {url_episodio}: {response.status_code}")
            return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        script = soup.find('script', string=lambda t: t and 'var videos = ' in t)
        if not script:
            logger.warning(f"No se encontró el script de videos en {url_episodio}")
            return []

        # Extraer la parte del script que contiene la información de videos
        script_content = script.string
        start_index = script_content.find('var videos = ') + len('var videos = ')
        end_index = script_content.find(';', start_index)
        videos_data = script_content[start_index:end_index].strip()

        # Convertir los datos de videos a un objeto JSON
        videos = json.loads(videos_data)

        # Recopilar información de los videos
        video_info = []
        for video_type, video_list in videos.items():
            for video in video_list:
                video_info.append({
                    'titulo': video.get('title', 'No disponible'),
                    'url': video.get('url', ''),
                    'server': video.get('server', ''),
                    'code': video.get('code', '')
                })

        # Guardar el resultado en la caché
        cache[url_episodio] = video_info

        return video_info
    except requests.RequestException as e:
        logger.error(f"Error en la solicitud HTTP para el episodio {url_episodio}: {e}")
        return []
    except json.JSONDecodeError:
        logger.error(f"Error al decodificar JSON en {url_episodio}")
        return []

def guardar_episodio_en_bbdd(serie_id, numero, url, videos):
    """Guarda un episodio en la base de datos."""
    db = get_db()
    cursor = db.cursor()
    
    # Insertar el episodio en la tabla episodios
    cursor.execute("""
        INSERT INTO episodios (serie_id, numero, url, videos) 
        VALUES (?, ?, ?, ?)
    """, (serie_id, numero, url, json.dumps(videos)))  # Guardar los videos como JSON
    
    db.commit()

def actualizar_episodio_en_bbdd(serie_id, numero, videos):
    """Actualiza los videos de un episodio en la base de datos."""
    db = get_db()
    cursor = db.cursor()
    
    # Actualizar los videos en la tabla episodios
    cursor.execute(""" 
        UPDATE episodios 
        SET videos = ? 
        WHERE serie_id = ? AND numero = ?
    """, (json.dumps(videos), serie_id, numero))
    
    db.commit()

def obtener_episodios(url_serie, pagina=0, limite=12):
    """Obtiene los episodios disponibles para la serie y su información de videos con paginación."""
    url_serie = url_serie.replace('/ver/', '/anime/')
    url_serie = re.sub(r'-\d+$', '', url_serie)  # Eliminar el número final de la URL

    # Extraer el `serie_id` del final de la URL
    serie_id = url_serie.split('/')[-1]

    # Conectar a la base de datos
    with sqlite3.connect('anime.db') as conn:
        cursor = conn.cursor()

        # Consultar episodios existentes en la base de datos con límite y desplazamiento (paginación)
        cursor.execute('SELECT numero FROM episodios WHERE serie_id = ? LIMIT ? OFFSET ?', 
                       (serie_id, limite, pagina * limite))
        episodios_en_bbdd = cursor.fetchall()
        episodios_en_bbdd = [int(episodio[0].split(' ')[-1]) for episodio in episodios_en_bbdd]  # Extraer números de episodios

        episodios = []  # Para almacenar los episodios encontrados

        # Si se encuentran episodios en la base de datos, se almacenan y se verifican
        if episodios_en_bbdd:
            logger.info(f"Episodios encontrados en la base de datos para la serie {serie_id}: {episodios_en_bbdd}")
        else:
            logger.info(f"No se encontraron episodios en la base de datos para la serie {serie_id}")

    # Si no se encontraron episodios en la base de datos o queremos verificar nuevos episodios, hacemos la solicitud a la web
    try:
        # Añadimos el timeout de 1 segundo a la solicitud
        logger.info(f"Realizando solicitud GET a {url_serie}")
        response = requests.get(url_serie, headers=headers, timeout=1)
        response.raise_for_status()
        logger.info(f"Solicitud exitosa. Código de estado: {response.status_code}")
        html = response.text

        # Extraer los datos de los episodios desde el script
        episodios_data = extraer_datos_de_script(html)
        if not episodios_data:
            logger.warning(f"No se encontraron datos de episodios en {url_serie}")
            return []

        episodios = []  # Para almacenar los episodios obtenidos de la web
        nuevos_episodios = []  # Para almacenar los episodios nuevos que no están en la base de datos

        # Aplicar la paginación a los episodios obtenidos desde la web
        inicio = pagina * limite
        fin = inicio + limite
        episodios_data_paginados = episodios_data[inicio:fin]  # Solo obtenemos los episodios de esta página

        for episodio_num, episodio_id in episodios_data_paginados:
            episodio_num_int = int(episodio_num)

            # Si el episodio no está en la base de datos, lo añadimos
            if episodio_num_int not in episodios_en_bbdd:
                url_episodio = f'https://www3.animeflv.net/ver/{serie_id}-{episodio_num}'
                
                # Llamar a la función obtener_videos para obtener los enlaces de videos
                videos = obtener_videos(url_episodio)
                
                nuevos_episodios.append({
                    'enlace': url_episodio,
                    'episodio': f"Episodio {episodio_num}",
                    'videos': videos  # Incluir la información de los videos para cada episodio
                })

                # Guardar los episodios nuevos en la base de datos
                guardar_episodio_en_bbdd(serie_id, f"Episodio {episodio_num}", url_episodio, videos)

            # Añadir los episodios existentes o nuevos a la lista de episodios
            episodios.append({
                'enlace': f'https://www3.animeflv.net/ver/{serie_id}-{episodio_num}',
                'episodio': f"Episodio {episodio_num}",
                'videos': [] if episodio_num_int in episodios_en_bbdd else videos
            })

        # Informar sobre los nuevos episodios añadidos
        if nuevos_episodios:
            logger.info(f"Se añadieron {len(nuevos_episodios)} episodios nuevos a la base de datos")
        else:
            logger.info(f"No se encontraron episodios nuevos para añadir.")

        return episodios

    except requests.RequestException as e:
        logger.error(f"Error en la solicitud HTTP: {e}")
        return []
    except Exception as e:
        logger.error(f"Error inesperado: {e}")
        return []


def buscar_serie_en_bbdd(nombre_serie):
    """Busca una serie en la base de datos por su título."""
    db = get_db()
    cursor = db.cursor()
    query = "SELECT id, titulo, url, poster, tipo, puntuacion, descripcion FROM series WHERE titulo LIKE ?"
    cursor.execute(query, (f"%{nombre_serie}%",))
    rows = cursor.fetchall()

    series = []
    if rows:
        for row in rows:
            serie_data = {
                'id': row[0],
                'titulo': row[1],
                'url': row[2],
                'poster': row[3],
                'tipo': row[4],
                'puntuacion': row[5],
                'descripcion': row[6],
            }
            series.append(serie_data)

    return series

def buscar_serie(nombre_serie):
    """Busca una serie en AnimeFLV y guarda los resultados en la base de datos."""
    
    # Primero, intentamos encontrar la serie en la base de datos
    series_bbdd = buscar_serie_en_bbdd(nombre_serie)
    
    # Si encontramos la serie en la base de datos, la devolvemos directamente
    if series_bbdd:
        print(f"Serie '{nombre_serie}' encontrada en la base de datos.")
        return series_bbdd
    
    # Si no encontramos la serie en la base de datos, hacemos la solicitud a AnimeFLV
    print(f"Serie '{nombre_serie}' no encontrada en la base de datos. Realizando la búsqueda online.")
    url_busqueda = f"https://www3.animeflv.net/browse?q={nombre_serie.replace(' ', '%20')}"
    
    try:
        response = requests.get(url_busqueda, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        resultados = soup.find('ul', class_='ListAnimes AX Rows A03 C02 D02')
        
        if not resultados:
            return []
        
        series = []
        for resultado in resultados.find_all('li'):
            # Extraer el enlace a la serie
            enlace = resultado.find('a', href=True)
            titulo = resultado.find('h3', class_='Title')
            poster_img = resultado.find('figure').find('img')  # Extraer el póster (imagen)
            descripcion_div = resultado.find('div', class_='Description')  # Extraer la descripción completa
            
            # Asegurarse de que todos los elementos existen
            if enlace and titulo and poster_img and descripcion_div:
                url = 'https://www3.animeflv.net' + enlace['href']
                poster_url = poster_img['src']
                
                # Extraer tipo, puntuación y descripción
                tipo_span = descripcion_div.find('span', class_='Type')
                puntuacion_span = descripcion_div.find('span', class_='Vts')
                descripcion_p = descripcion_div.find_all('p')[1]  # El segundo <p> contiene la descripción
                
                tipo = tipo_span.text.strip() if tipo_span else 'Desconocido'
                puntuacion = puntuacion_span.text.strip() if puntuacion_span else 'N/A'
                descripcion = descripcion_p.text.strip() if descripcion_p else 'Sin descripción disponible'
                
                # Extraer el id (lo que viene después del último '/')
                id_serie = url.split('/')[-1]
                
                # Agregar los datos extraídos a la lista
                serie_data = {
                    'titulo': titulo.text.strip(),
                    'url': url,
                    'poster': poster_url,
                    'tipo': tipo,
                    'puntuacion': puntuacion,
                    'descripcion': descripcion,
                    'id': id_serie
                }
                
                # Guardar la serie en la base de datos
                guardar_serie_en_bbdd(serie_data)

                # Añadir la serie a la lista de resultados
                series.append(serie_data)
        
        return series

    except requests.RequestException as e:
        return {'error': f"Error en la solicitud HTTP: {e}"}
    except Exception as e:
        return {'error': f"Error inesperado: {e}"}

def buscar_serie_manga(nombre_serie):
    """Busca una serie de manga en InManga y guarda los resultados en la base de datos."""

    # Reemplazamos espacios por %20 para la búsqueda
    url_busqueda = f"https://inmanga.com/manga/GetQuickSearch?name={nombre_serie.replace(' ', '%20')}"
    
    try:
        response = requests.get(url_busqueda, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()
        
        # Parseamos el JSON devuelto
        json_data = json.loads(response.json()["data"])
        
        if not json_data.get("success", False):
            return {'error': "Búsqueda fallida en InManga."}

        # Extraer el resultado de la búsqueda
        resultados = json_data.get("result", [])
        if not resultados:
            return []

        series = []
        for resultado in resultados:
            # Extraemos los datos necesarios
            titulo = resultado.get('Name', 'Sin título')
            poster_url = resultado.get('ThumbnailPath', '')  # Poster
            descripcion = resultado.get('Sinopsis', 'Sin descripción disponible')
            id_serie = resultado.get('Identification', 'Sin ID')
            
          
            partes_poster = poster_url.split('/')  # Dividir la URL por '/'
            nombre_serie_poster = partes_poster[-2]  # El nombre de la serie está justo antes del ID
            poster_id = partes_poster[-1]  # El ID del manga está al final

            # Para la URL del manga, usamos el nombre de la serie y el ID extraído
            url = f"https://inmanga.com/ver/manga/{nombre_serie_poster}/{poster_id}"

            # Los siguientes campos no están disponibles en InManga, así que los inventamos o ponemos valores predeterminados
            tipo = resultado.get('BroadcastStatusDescription', r'N\A')  # Usando cadena cruda
            puntuacion = round(random.uniform(3.5, 5.0), 1)
            
            # Crear el diccionario serie_data con los campos requeridos
            serie_data = {
                'titulo': titulo,
                'url': url,
                'poster': poster_url,
                'tipo': quitar_acentos_y_caracteres_raros(tipo),
                'puntuacion': puntuacion,
                'descripcion': quitar_acentos_y_caracteres_raros(descripcion),
                'id': id_serie
            }
            
            # Guardamos la serie en la base de datos
           
            
            # Añadimos la serie a la lista de resultados
            series.append(serie_data)

        return series

    except requests.RequestException as e:
        return {'error': f"Error en la solicitud HTTP: {e}"}
    except Exception as e:
        return {'error': f"Error inesperado: {e}"}
    

def obtener_ultimos_animes():
    """Obtiene los últimos animes de AnimeFLV."""
    url_ultimos_animes = "https://www3.animeflv.net"
  
    try:
        logger.info(f"Realizando solicitud GET a {url_ultimos_animes}")
        response = requests.get(url_ultimos_animes,headers=headers)
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
        response = requests.get(url_serie,headers=headers)
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
def normalizar_texto(texto):
    # Normalizar el texto eliminando acentos y caracteres especiales
    texto = ''.join(
        c for c in unicodedata.normalize('NFKD', texto)
        if unicodedata.category(c) != 'Mn'
    )
    # Eliminar las comillas dobles, comillas simples
    texto = texto.replace('"', '').replace("'", "")

    # Reemplazar caracteres unicode especiales
    texto = texto.replace('\u00a1', '').replace('\u00bf', '').replace('\u2026', '')

    # Eliminar saltos de línea y espacios extra
    texto = texto.replace("\r\n", " ").replace("\n", " ").strip()

    # Eliminar espacios adicionales
    return ' '.join(texto.split())

# Función para obtener los datos del anime desde AnimeFLV
def obtener_anime_perfil(nombre_anime):
    """Busca un anime en AnimeFLV y devuelve los datos del perfil."""
    nombre_anime = normalizar_texto(nombre_anime)  # Normalizar nombre de la serie
    url = f"https://www3.animeflv.net/anime/{nombre_anime}"

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        # Parsear el contenido HTML con BeautifulSoup
        soup = BeautifulSoup(response.content, 'html.parser')

        # Extraer el título
        titulo_h1 = soup.find('h1', class_='Title')
        titulo = normalizar_texto(titulo_h1.text) if titulo_h1 else "Titulo no encontrado"

        # Extraer la imagen del póster
        poster_div = soup.find('div', class_='AnimeCover').find('img')
        poster_url = "https://www3.animeflv.net" + poster_div['src'] if poster_div else None

        # Extraer los géneros
        generos = []
        nav_genres = soup.find('nav', class_='Nvgnrs')
        if nav_genres:
            generos = [normalizar_texto(a.text) for a in nav_genres.find_all('a')]

        # Extraer la sinopsis
        sinopsis_div = soup.find('div', class_='Description')
        sinopsis = normalizar_texto(sinopsis_div.find('p').text) if sinopsis_div else None

        # Extraer la calificación
        votos_div = soup.find('div', class_='Votes')
        calificacion = votos_div.find('span', id='votes_prmd').text if votos_div else "Calificacion no disponible"
        votos_totales = votos_div.find('span', id='votes_nmbr').text if votos_div else "Votos no disponibles"


        # Armar la respuesta
        anime_data = {
            'id': nombre_anime,
            'titulo': titulo,
            'poster': poster_url,
            'generos': generos,
            'descripcion': sinopsis,
            'calificacion': calificacion,
            'votos_totales': votos_totales
        }

        return anime_data

    except requests.RequestException as e:
        return {'error': f"Error en la solicitud HTTP: {str(e)}"}
    except Exception as e:
        return {'error': f"Error inesperado: {str(e)}"}

def obtener_animes_por_genero(generos):
    """
    Obtiene animes de AnimeFLV según los géneros proporcionados.
    
    Args:
        generos (list): Lista de géneros para buscar animes.
        
    Returns:
        list: Lista de animes que coinciden con los géneros.
    """
    # Base URL para la búsqueda
    base_url = "https://www3.animeflv.net/browse?"
    
    # Construir la URL con los géneros
    genero_query = "&".join([f"genre%5B%5D={genero}" for genero in generos])
    url_busqueda = f"{base_url}{genero_query}&order=rating"

    try:
        # Realizar la solicitud GET a la URL construida
        response = requests.get(url_busqueda, headers=headers)
        response.raise_for_status()
        
        # Parsear el contenido HTML con BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Buscar la lista de animes en la página
        lista_animes = soup.find('ul', class_='ListAnimes AX Rows A03 C02 D02')
        if not lista_animes:
            return []

        animes = []
        for item in lista_animes.find_all('li'):
            try:
                imagen_div = item.find('div', class_='Image')
                titulo_h3 = item.find('h3', class_='Title')
                enlace = item.find('a')['href']
                id_anime = enlace.replace('/anime/', '').strip()
                calificacion_span = item.find('span', class_='Vts fa-star')
                
                if imagen_div and titulo_h3 and calificacion_span:
                    imagen_tag = imagen_div.find('img')
                    portada = imagen_tag['src']
                    titulo = titulo_h3.text.strip()
                    calificacion = calificacion_span.text.strip()
                    
                    animes.append({
                        'id': id_anime,
                        'titulo': titulo,
                        'portada': portada,
                        'calificacion': calificacion
                    })
            except Exception as e:
                # Loguear cualquier error durante el procesamiento de los animes
                print(f"Error al procesar un anime: {e}")
        
        return animes

    except requests.RequestException as e:
        print(f"Error en la solicitud HTTP: {e}")
        return []
    
def obtener_mangas_mas_vistos():
    """Obtiene los mangas más vistos desde la página de InManga."""
    url_mangas_vistos = "https://inmanga.com/manga/getMostViewedMangas"
    
    try:
        response = requests.get(url_mangas_vistos,headers=headers)
        response.raise_for_status()

        # Parseamos el HTML usando BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')

        mangas_vistos = []

        # Buscamos todos los elementos de manga dentro de los enlaces
        for item in soup.find_all('a', class_='list-group-item'):
            try:
                # Obtenemos el título del manga
                titulo_tag = item.find('strong', class_='media-box-heading')
                titulo = titulo_tag.text.strip() if titulo_tag else 'Sin título'

                # Obtenemos el enlace del manga
                enlace = item['href']
                enlace_completo = f"https://inmanga.com{enlace}"

                # Obtenemos la portada (imagen)
                img_tag = item.find('img', class_='ImageContainer')
                portada = img_tag['src'] if img_tag else None

                # Generamos una calificación aleatoria entre 3 y 5
                calificacion = round(random.uniform(3, 5), 2)

                # Obtenemos el ID del manga (es el nombre en la URL de la imagen)
                if portada:
                    id_manga = portada.split('/')[-2]

                # Añadimos el manga a la lista
                mangas_vistos.append({
                    'titulo': titulo,
                    'portada': portada,
                    'calificacion': calificacion,
                    'enlace': enlace_completo,
                    'id': id_manga
                })

            except Exception as e:
                print(f"Error al procesar un manga: {e}")
        
        print(f"Mangas más vistos encontrados: {len(mangas_vistos)}")
        return mangas_vistos

    except requests.RequestException as e:
        print(f"Error en la solicitud HTTP: {e}")
        return []
    except Exception as e:
        print(f"Error inesperado: {e}")
        return []
    
def obtener_mangas_ultimos_capitulos():
    """Obtiene los capítulos más recientes desde la página de InManga."""
    url_ultimos_capitulos = "https://inmanga.com/chapter/getRecentChapters"
    
    try:
        response = requests.get(url_ultimos_capitulos, headers=headers)
        response.raise_for_status()

        # Parseamos el HTML usando BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')

        mangas_capitulos = []

        # Buscamos los elementos de los capítulos recientes
        for item in soup.find_all('a', class_='list-group-item'):
            try:
                # Obtenemos el título del manga
                titulo_tag = item.find('strong', class_='media-box-heading')
                titulo = titulo_tag.text.strip() if titulo_tag else 'Sin título'

                # Obtenemos el enlace del capítulo
                enlace = item['href']
                enlace_completo = enlace.rsplit('/', 1)[-1]

                # Obtenemos la portada (imagen)
                img_tag = item.find('img', class_='ImageContainer')
                portada = img_tag['src'] if img_tag else None

                # Obtenemos el ID del manga desde la URL de la portada
                id_manga = None
                if portada:
                    id_manga = portada.split('/')[-1]  # Tomamos la última parte de la URL

                 # Obtenemos el número del capítulo
                capitulo_tag = item.find('div', class_='recent-chapter-container-footer')
                capitulo = capitulo_tag.find('strong').text.strip() if capitulo_tag else 'Capítulo no disponible'


                fecha_tag = item.find('span', class_='chapterRegistrationDateContainer')
                fecha_registro = fecha_tag['data-registrationdate'] if fecha_tag else 'Fecha no disponible'

                # Convertimos la fecha al formato español si está disponible
                if fecha_registro != 'Fecha no disponible':
                    fecha_registro = convertir_fecha_a_formato_espanol(fecha_registro)

                # Añadimos el capítulo a la lista
                mangas_capitulos.append({
                    'titulo': titulo,
                    'portada': portada,
                    'capitulo': capitulo,  
                    'enlace': enlace_completo,
                    'id': id_manga,
                    'fecha_registro':fecha_registro
                })

            except Exception as e:
                print(f"Error al procesar un capítulo: {e}")
        
        print(f"Capítulos más recientes encontrados: {len(mangas_capitulos)}")
        return mangas_capitulos

    except requests.RequestException as e:
        print(f"Error en la solicitud HTTP: {e}")
        return []
    except Exception as e:
        print(f"Error inesperado: {e}")
        return []



def obtener_manga_perfil(url_manga):
    """Obtiene los detalles del perfil de un manga desde la página de InManga."""
    
    try:
        print(f"Realizando solicitud GET a {url_manga}")
        
        # Establecer encabezados para la solicitud
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }
        
        response = requests.get(url_manga, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')

        # Obtener el contenedor principal donde están el título y la descripción
        contenedor_manga = soup.select_one('div.col-md-9.col-sm-8.col-xs-12')

        if not contenedor_manga:
            print("No se encontró el contenedor del manga.")
            return {'error': 'No se encontró el contenedor del manga.'}

        # Obtener el título del manga desde el div con clase 'panel-heading visible-xs'
        titulo_tag = soup.find('div', class_='panel-heading visible-xs')
        titulo = titulo_tag.text.strip() if titulo_tag else 'Desconocido'

        # Generar el id con el título en minúsculas y reemplazar espacios por guiones
        id_manga = re.sub(r'\s+', '-', titulo.lower()) if titulo else 'sin-id'

        # Obtener el póster (imagen)
        poster_tag = soup.find('div', class_='text-center bg-center custom-bg-center').find('img')
        poster = poster_tag['src'] if poster_tag else 'Sin imagen'
        poster = 'https://inmanga.com' + poster if poster != 'Sin imagen' else poster

        # Obtener la lista de elementos de estado, publicación, periodicidad, etc.
        elementos_info = soup.find('div', class_='list-group')
        estado, publicacion, periodicidad, proximo_capitulo = 'Desconocido', 'Desconocida', 'Desconocida', 'No disponible'

        # Iterar sobre cada 'a' con la clase 'list-group-item'
        for item in elementos_info.find_all('a', class_='list-group-item'):
            # Obtener el texto del enlace (descripción)
            descripcion_item = item.get_text(strip=True)
            # Obtener el valor dentro del span
            span = item.find('span')
            valor_span = span.text.strip() if span else None

            if 'Estado' in descripcion_item:
                estado = valor_span if valor_span else 'Desconocido'
            elif 'Publicación' in descripcion_item:
                publicacion = valor_span if valor_span else 'Desconocida'
            elif 'Periodicidad' in descripcion_item:
                periodicidad = valor_span if valor_span else 'Desconocida'

        # Caso especial: Obtener próximo capítulo desde la clase nextChapterPublicationContainer
        proximo_capitulo_tag = elementos_info.find('a', class_='nextChapterPublicationContainer')
        if proximo_capitulo_tag:
            proximo_capitulo_span = proximo_capitulo_tag.find('span', class_='nextChapterPublicationInput')
            proximo_capitulo = proximo_capitulo_span.text.strip() if proximo_capitulo_span and proximo_capitulo_span.text else 'No disponible'

        # Obtener y limpiar descripción desde el panel-body correcto
        descripcion_tag = contenedor_manga.find('div', class_='panel-body')
        descripcion = descripcion_tag.text.strip() if descripcion_tag else 'Sin descripción'
        descripcion_limpia = re.sub(r'\s+', ' ', descripcion).strip()

        # Obtener el identificador de manga del URL
        identificador_manga = url_manga.split('/')[-1].split('?')[0]  # Extrae el identificador al final del URL
        url_capitulos = f"https://inmanga.com/chapter/getall?mangaIdentification={identificador_manga}"
        
        # Obtener capítulos desde la API
        print(f"Obteniendo capítulos desde {url_capitulos}")
        response_capitulos = requests.get(url_capitulos, headers=headers)
        response_capitulos.raise_for_status()
        
        capitulos_data = json.loads(response_capitulos.text)  # Decodificar la respuesta JSON

       # Procesar los capítulos
        capitulos = {}  # Cambiado de lista a diccionario
        # La respuesta puede estar en un string, así que debemos volver a cargarla
        capitulos_json = json.loads(capitulos_data['data'])

        for capitulo in capitulos_json['result']:
            # Solo recoger la identificación para la llamada de siguiente nivel
            identificacion = capitulo['Identification']
            capitulos[capitulo['FriendlyChapterNumberUrl']] = {  # Utilizamos index + 1 como clave para empezar desde 1
                'chapter_id': identificacion
            }
           
        # Devolver los capítulos en un diccionario
        return {
            'id': id_manga,
            'titulo': titulo,
            'poster': poster,
            'estado': quitar_acentos_y_caracteres_raros(estado),
            'publicacion': publicacion,
            'periodicidad': periodicidad,
            'proximo_capitulo': proximo_capitulo,
            'descripcion': quitar_acentos_y_caracteres_raros(descripcion_limpia),
            'capitulos': capitulos  # Añadir el diccionario de capítulos
        }

    except Exception as e:
        print(f"Error al obtener el perfil del manga {url_manga}: {e}")
        return {'error': f"No se pudo obtener el perfil del manga {url_manga}."}

def obtener_imagenes_manga(url_capitulo):
    """Obtiene las imágenes de un capítulo del manga desde la URL proporcionada."""
    
    try:
        # Crear la URL del capítulo detallado
        url_capitulo_detalle = f"https://inmanga.com/chapter/chapterIndexControls?identification={url_capitulo}"

        # Hacer una solicitud para obtener los datos de las páginas
        response_capitulo_detalle = requests.get(url_capitulo_detalle,headers=headers)
        response_capitulo_detalle.raise_for_status()

        # Extraer datos de los inputs hidden
        soup_detalle = BeautifulSoup(response_capitulo_detalle.text, 'html.parser')
        chapter_number = soup_detalle.find('input', {'id': 'ChapterNumber'})['value']
        friendly_manga_name = soup_detalle.find('input', {'id': 'FriendlyMangaName'})['value']

        # Recoger imágenes de las páginas
        paginas = soup_detalle.find_all('a', class_='NextPage')  # Obtiene todas las páginas
        imagenes = []  # Lista para almacenar las URLs de las imágenes

        for pagina in paginas:
            # Encuentra la URL de la página de imagen
            img_tag = pagina.find('img', class_='ImageContainer')
            if img_tag:
                # Construir la URL de la imagen
                imagen_url = f"https://pack-yak.intomanga.com/images/manga/{friendly_manga_name}/chapter/{chapter_number}/page/{img_tag['data-pagenumber']}/{img_tag['id']}"

                # Aquí simplemente agregamos la URL de la imagen a la lista
                imagenes.append(imagen_url)  # Agregar la URL de la imagen a la lista

        return imagenes  # Retornar la lista de imágenes

    except Exception as e:
        print(f"Error al obtener imágenes del capítulo: {e}")
        return {'error': str(e)}  # Manejar el error

@app.route('/api/getAnimesByGenre', methods=['GET'])
def api_obtener_animes_por_genero():
    """
    API para obtener animes según uno o varios géneros.
    """
    generos = request.args.getlist('genre')
    if not generos:
        return jsonify({'error': 'El parámetro "genre" es obligatorio.'}), 400
    
    animes = obtener_animes_por_genero(generos)
    return jsonify(animes)

@app.route('/api/getAnimePerfil', methods=['GET'])
def api_get_anime_perfil():
    nombre_anime = request.args.get('anime')
    
    if not nombre_anime:
        return jsonify({'error': 'El parámetro "anime" es obligatorio.'}), 400

    anime_perfil = obtener_anime_perfil(nombre_anime)
    
    if 'error' in anime_perfil:
        return jsonify(anime_perfil), 500
    
    return jsonify(anime_perfil)


@app.route('/api/getAnime', methods=['GET'])
def api_buscar_serie():
    nombre_serie = request.args.get('anime')
    if not nombre_serie:
        return jsonify({'error': 'El parámetro "anime" es obligatorio.'}), 400
    series = buscar_serie(nombre_serie)
    return jsonify(series)


@app.route('/api/getManga', methods=['GET'])
def api_buscar_serie_manga():
    nombre_serie = request.args.get('manga')
    if not nombre_serie:
        return jsonify({'error': 'El parámetro "manga" es obligatorio.'}), 400
    series = buscar_serie_manga(nombre_serie)
    return jsonify(series)


@app.route('/api/episodios', methods=['GET'])
def api_obtener_episodios():
    url_serie = request.args.get('url_serie')
    if not url_serie:
        return jsonify({'error': 'El parámetro "url_serie" es obligatorio.'}), 400

    # Obtiene los parámetros de paginación
    pagina = request.args.get('pagina', default=0, type=int)  # Página por defecto es 0
    limite = request.args.get('limite', default=12, type=int)  # Límite por defecto es 12

    episodios = obtener_episodios(url_serie, pagina=pagina, limite=limite)
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


@app.route('/api/MangasPopulares', methods=['GET'])
def api_obtener_mangas_populares():
    mangas_populares = obtener_mangas_mas_vistos()
    return jsonify(mangas_populares)


@app.route('/api/getMangaPerfil', methods=['GET'])
def api_get_manga_perfil():
    url_manga = request.args.get('manga')
    
    if not url_manga:
        return jsonify({'error': 'El parámetro "manga" es obligatorio.'}), 400

    # Obtener datos del perfil del manga desde el scraping
    manga_perfil = obtener_manga_perfil(url_manga)
    
    if 'error' in manga_perfil:
        return jsonify(manga_perfil), 500
    
    return jsonify(manga_perfil)

@app.route('/api/getMangaImages', methods=['GET'])
def api_get_manga_images():
    # Obtener la URL del capítulo del manga
    url_capitulo = request.args.get('url')
    
    if not url_capitulo:
        return jsonify({'error': 'El parámetro "url" es obligatorio.'}), 400

    # Obtener las imágenes del capítulo del manga
    imagenes = obtener_imagenes_manga(url_capitulo)
    
    if 'error' in imagenes:
        return jsonify(imagenes), 500
    
    return jsonify(imagenes)


@app.route('/api/MangaUltimosCapitulos', methods=['GET'])
def api_obtener_ultimos_capitulos():
    mangas_ultimos_capitulos = obtener_mangas_ultimos_capitulos()
    return jsonify(mangas_ultimos_capitulos)



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
