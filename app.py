from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
import json
import re

app = Flask(__name__)

def extraer_datos_de_script(html):
    soup = BeautifulSoup(html, 'html.parser')
    script = soup.find('script', string=lambda t: t and 'var episodes = ' in t)
    if not script:
        return []
    script_content = script.string
    start_index = script_content.find('var episodes = ') + len('var episodes = ')
    end_index = script_content.find(';', start_index)
    episodes_data = script_content[start_index:end_index].strip()
    try:
        episodes = json.loads(episodes_data)
    except json.JSONDecodeError:
        return []
    return episodes

def obtener_nombre_serie(url_serie):
    match = re.search(r'/anime/([^/]+)', url_serie)
    if match:
        return match.group(1)
    else:
        return None

def obtener_videos(url_episodio):
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
    response = requests.get(url_serie)
    if response.status_code != 200:
        return []
    html = response.text
    episodios_data = extraer_datos_de_script(html)
    if not episodios_data:
        return []
    nombre_serie = obtener_nombre_serie(url_serie)
    if not nombre_serie:
        return []
    episodios = []
    for episodio_num, episodio_id in episodios_data:
        url = f'https://www3.animeflv.net/ver/{nombre_serie}-{episodio_num}'
        episodios.append({'enlace': url, 'episodio': f"Episodio {episodio_num}"})
    episodios.sort(key=lambda x: int(re.search(r'(\d+)$', x['episodio']).group(1)))
    return episodios

def buscar_serie(nombre_serie):
    url_busqueda = f"https://www3.animeflv.net/browse?q={nombre_serie.replace(' ', '%20')}"
    response = requests.get(url_busqueda)
    if response.status_code != 200:
        return []
    soup = BeautifulSoup(response.content, 'html.parser')
    resultados = soup.find('ul', class_='ListAnimes AX Rows A03 C02 D02')
    if not resultados:
        return []
    series = []
    for resultado in resultados.find_all('li'):
        enlace = resultado.find('a', href=True)
        titulo = resultado.find('h3', class_='Title')
        if enlace and titulo:
            url = 'https://www3.animeflv.net' + enlace['href']
            series.append({'titulo': titulo.text.strip(), 'url': url})
    return series

@app.route('/buscar_serie', methods=['GET'])
def buscar_serie_route():
    nombre_serie = request.args.get('nombre_serie')
    if not nombre_serie:
        return jsonify({'error': 'No se proporcionó el nombre de la serie.'}), 400
    series = buscar_serie(nombre_serie)
    return jsonify(series)
    

if __name__ == '__main__':
    app.run(port=5500, debug=True)
