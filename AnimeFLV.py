import requests
from bs4 import BeautifulSoup
import json
import re
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import io
import webbrowser

def extraer_datos_de_script(html):
    """Extrae la información de los episodios del script JavaScript en el HTML."""
    soup = BeautifulSoup(html, 'html.parser')
    script = soup.find('script', string=lambda t: t and 'var episodes = ' in t)
    if not script:
        print("No se encontró el script con la información de los episodios.")
        return []
    script_content = script.string
    start_index = script_content.find('var episodes = ') + len('var episodes = ')
    end_index = script_content.find(';', start_index)
    episodes_data = script_content[start_index:end_index].strip()
    try:
        episodes = json.loads(episodes_data)
    except json.JSONDecodeError:
        print("Error al analizar los datos de los episodios.")
        return []
    return episodes

def obtener_nombre_serie(url_serie):
    """Extrae el nombre de la serie desde la URL sin modificar."""
    match = re.search(r'/anime/([^/]+)', url_serie)
    if match:
        return match.group(1)
    else:
        print("No se pudo extraer el nombre de la serie de la URL.")
        return None

def obtener_videos(url_episodio):
    """Extrae la información del video disponible para un episodio desde el script JavaScript."""
    response = requests.get(url_episodio)
    if response.status_code != 200:
        print("Error al acceder a la página del episodio.")
        return []
    soup = BeautifulSoup(response.text, 'html.parser')
    script = soup.find('script', string=lambda t: t and 'var videos = ' in t)
    if not script:
        print("No se encontró el script con la información de los videos.")
        return []
    script_content = script.string
    start_index = script_content.find('var videos = ') + len('var videos = ')
    end_index = script_content.find(';', start_index)
    videos_data = script_content[start_index:end_index].strip()
    try:
        videos = json.loads(videos_data)
    except json.JSONDecodeError:
        print("Error al analizar los datos de los videos.")
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
    response = requests.get(url_serie)
    if response.status_code != 200:
        print("Error al acceder a la página de la serie.")
        return []
    html = response.text
    episodios_data = extraer_datos_de_script(html)
    if not episodios_data:
        print("No se encontraron episodios en el script.")
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
    """Busca una serie en AnimeFLV y devuelve los resultados."""
    url_busqueda = f"https://www3.animeflv.net/browse?q={nombre_serie.replace(' ', '%20')}"
    response = requests.get(url_busqueda)
    if response.status_code != 200:
        print("Error al acceder a la página de búsqueda.")
        return []
    soup = BeautifulSoup(response.content, 'html.parser')
    resultados = soup.find('ul', class_='ListAnimes AX Rows A03 C02 D02')
    if not resultados:
        print("No se encontraron resultados para la búsqueda.")
        return []
    series = []
    for resultado in resultados.find_all('li'):
        enlace = resultado.find('a', href=True)
        titulo = resultado.find('h3', class_='Title')
        if enlace and titulo:
            url = 'https://www3.animeflv.net' + enlace['href']
            series.append({'titulo': titulo.text.strip(), 'url': url})
    return series

def obtener_ultimos_animes():
    """Obtiene los últimos animes de AnimeFLV."""
    url_ultimos_animes = "https://www3.animeflv.net"
    response = requests.get(url_ultimos_animes)
    if response.status_code != 200:
        print("Error al acceder a la página de últimos animes.")
        return []
    soup = BeautifulSoup(response.text, 'html.parser')
    lista_animes = soup.find('ul', class_='ListEpisodios AX Rows A06 C04 D03')
    if not lista_animes:
        print("No se encontraron los últimos animes.")
        return []
    animes = []
    for item in lista_animes.find_all('li'):
        enlace = item.find('a', href=True)
        titulo = item.find('strong', class_='Title')
        episodio = item.find('span', class_='Capi')
        if enlace and titulo and episodio:
            animes.append({
                'titulo': titulo.text.strip(),
                'enlace': 'https://www3.animeflv.net' + enlace['href'],
                'episodio': episodio.text.strip()
            })
    return animes

def obtener_imagen_y_descripcion(url_serie):
    """Obtiene la imagen y la descripción de una serie desde su URL."""
    # Reemplazar '/ver' por '/anime' en la URL
    url_serie = url_serie.replace('/ver/', '/anime/')
    url_serie = re.sub(r'-\d+$', '', url_serie)  # Eliminar el número final de la URL
    response = requests.get(url_serie)
    if response.status_code != 200:
        print("Error al acceder a la página de la serie.")
        return None, None
    
    soup = BeautifulSoup(response.text, 'html.parser')
    imagen = soup.find('div', class_='AnimeCover')
    descripcion = soup.find('div', class_='Description')
    if imagen and descripcion:
        imagen_tag = imagen.find('img')
        imagen_url = 'https://www3.animeflv.net' + imagen_tag['src']
        descripcion_texto = descripcion.find('p').text.strip()
        return imagen_url, descripcion_texto
    else:
        print("No se encontró la imagen o descripción.")
        return None, None

class AnimeFLVApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Buscador de Series AnimeFLV")
        self.root.geometry("1700x800")  # Ajustado el tamaño de la ventana principal

        # Crear el notebook para las pestañas
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Pestaña de búsqueda de series
        self.tab_busqueda = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_busqueda, text="Buscar Serie")

        # Pestaña de últimos animes
        self.tab_ultimos = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_ultimos, text="Últimos Animes")

        self.crear_interfaz_busqueda(self.tab_busqueda)
        self.crear_interfaz_ultimos(self.tab_ultimos)

        # Cargar los últimos animes al iniciar
        self.cargar_ultimos_animes()

    def crear_interfaz_busqueda(self, frame):
        """Crea la interfaz de búsqueda de series en la pestaña correspondiente."""
        self.frame_busqueda = ttk.Frame(frame, padding="10")
        self.frame_busqueda.pack(fill=tk.BOTH, expand=True)

        self.lbl_nombre = ttk.Label(self.frame_busqueda, text="Nombre de la serie:")
        self.lbl_nombre.grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)

        self.entry_nombre = ttk.Entry(self.frame_busqueda, width=100)
        self.entry_nombre.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        self.entry_nombre.bind("<Return>", self.buscar_serie)  # Buscar al presionar Enter

        self.btn_buscar = ttk.Button(self.frame_busqueda, text="Buscar", command=self.buscar_serie)
        self.btn_buscar.grid(row=0, column=2, sticky=tk.W, padx=5, pady=5)

        # Configuración de las tablas
        self.tree_series = ttk.Treeview(self.frame_busqueda, columns=("Serie", "URL"), show="headings", height=10)
        self.tree_series.heading("Serie", text="Serie")
        self.tree_series.heading("URL", text="URL")
        self.tree_series.column("Serie", width=200)
        self.tree_series.column("URL", width=200)
        self.tree_series.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), padx=5, pady=5)
        self.tree_series.bind("<ButtonRelease-1>", self.cargar_episodios)

        self.tree_episodios = ttk.Treeview(self.frame_busqueda, columns=("Episodio", "URL"), show="headings", height=10)
        self.tree_episodios.heading("Episodio", text="Episodio")
        self.tree_episodios.heading("URL", text="URL")
        self.tree_episodios.column("Episodio", width=200)
        self.tree_episodios.column("URL", width=200)
        self.tree_episodios.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), padx=5, pady=5)
        self.tree_episodios.bind("<ButtonRelease-1>", self.cargar_videos)

        self.tree_videos = ttk.Treeview(self.frame_busqueda, columns=("Título", "Enlace"), show="headings", height=10)
        self.tree_videos.heading("Título", text="Título")
        self.tree_videos.heading("Enlace", text="Enlace")
        self.tree_videos.column("Título", width=200)
        self.tree_videos.column("Enlace", width=200)
        self.tree_videos.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), padx=5, pady=5)
        self.tree_videos.bind("<Double-1>", self.abrir_enlace)

        self.loading_label = ttk.Label(self.frame_busqueda, text="Verificando enlaces...", foreground="blue")
        self.loading_label.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), padx=5, pady=5)
        self.loading_label.grid_forget()

        


    def crear_interfaz_ultimos(self, frame):
        """Crea la interfaz para mostrar los últimos animes en la pestaña correspondiente."""
        self.frame_ultimos = ttk.Frame(frame, padding="10")
        self.frame_ultimos.pack(fill=tk.BOTH, expand=True)

        # Frame para la tabla de últimos animes con scroll
        self.frame_tabla_ultimos = ttk.Frame(self.frame_ultimos)
        self.frame_tabla_ultimos.pack(fill=tk.BOTH, expand=True)

        self.tree_ultimos = ttk.Treeview(self.frame_tabla_ultimos, columns=("Título", "Episodio", "URL"), show="headings", height=10)
        self.tree_ultimos.heading("Título", text="Título")
        self.tree_ultimos.heading("Episodio", text="Episodio")
        self.tree_ultimos.heading("URL", text="URL")
        self.tree_ultimos.column("Título", width=300)
        self.tree_ultimos.column("Episodio", width=150)
        self.tree_ultimos.column("URL", width=500)
        self.tree_ultimos.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.tree_ultimos.bind("<ButtonRelease-1>", self.mostrar_detalle_anime)

        # Añadir scrollbars
        self.scrollbar_vers = ttk.Scrollbar(self.frame_tabla_ultimos, orient=tk.VERTICAL, command=self.tree_ultimos.yview)
        self.scrollbar_vers.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree_ultimos.configure(yscrollcommand=self.scrollbar_vers.set)

        self.scrollbar_hor = ttk.Scrollbar(self.frame_tabla_ultimos, orient=tk.HORIZONTAL, command=self.tree_ultimos.xview)
        self.scrollbar_hor.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree_ultimos.configure(xscrollcommand=self.scrollbar_hor.set)

        # Área para mostrar la imagen y la descripción del anime seleccionado
        self.frame_detalle = ttk.Frame(self.frame_ultimos, padding="10")
        self.frame_detalle.pack(fill=tk.BOTH, expand=True)

        self.img_label = ttk.Label(self.frame_detalle)
        self.img_label.pack(side=tk.LEFT, padx=10)

        self.desc_label = ttk.Label(self.frame_detalle, wraplength=400, justify=tk.LEFT)
        self.desc_label.pack(side=tk.LEFT, padx=10, fill=tk.BOTH, expand=True)

        # Crear la tabla de capítulos
        self.tree_capitulos = ttk.Treeview(self.frame_detalle, columns=("Capítulo", "Enlace"), show="headings", height=10)
        self.tree_capitulos.heading("Capítulo", text="Capítulo")
        self.tree_capitulos.heading("Enlace", text="Enlace")
        self.tree_capitulos.column("Capítulo", width=150)
        self.tree_capitulos.column("Enlace", width=250)
        self.tree_capitulos.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        # self.tree_capitulos.bind("<Button-1>", self.abrir_enlace)

        # Configurar el peso de las filas y columnas
        self.frame_ultimos.grid_rowconfigure(0, weight=1)
        self.frame_ultimos.grid_columnconfigure(0, weight=1)
        self.frame_ultimos.grid_columnconfigure(1, weight=2)


      # Crear un frame adicional para los botones
        self.frame_botones = ttk.Frame(self.frame_busqueda)
        self.frame_botones.grid(row=4, column=0, columnspan=3, pady=5, sticky=tk.EW)

        self.frame_botones.columnconfigure(0, weight=1)
        self.frame_botones.columnconfigure(1, weight=1)
        self.frame_botones.columnconfigure(2, weight=1)

        self.btn_viendo = ttk.Button(self.frame_botones, text="Estoy viendo", command=self.marcar_como_viendo)
        self.btn_viendo.grid(row=0, column=0, padx=5, pady=5, sticky=tk.EW)

        self.btn_pendiente = ttk.Button(self.frame_botones, text="Pendiente", command=self.marcar_como_pendiente)
        self.btn_pendiente.grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)

        self.btn_terminado = ttk.Button(self.frame_botones, text="Terminado", command=self.marcar_como_terminado)
        self.btn_terminado.grid(row=0, column=2, padx=5, pady=5, sticky=tk.EW)

    def buscar_serie(self, event=None):
        nombre_serie = self.entry_nombre.get()
        series = buscar_serie(nombre_serie)
        if not series:
            messagebox.showinfo("Resultado", "No se encontraron series con el nombre dado.")
            return
        self.tree_series.delete(*self.tree_series.get_children())
        self.tree_episodios.delete(*self.tree_episodios.get_children())
        self.tree_videos.delete(*self.tree_videos.get_children())
        for serie in series:
            self.tree_series.insert("", "end", iid=serie['titulo'], values=(serie['titulo'], serie['url']))
        self.series = series

    def cargar_episodios(self, event):
        selected_item = self.tree_series.selection()
        if not selected_item:
            return
        url_serie = self.tree_series.item(selected_item[0])['values'][1]
        episodios = obtener_episodios(url_serie)
        if not episodios:
            messagebox.showinfo("Resultado", "No se encontraron episodios para esta serie.")
            return
        self.tree_episodios.delete(*self.tree_episodios.get_children())
        self.tree_videos.delete(*self.tree_videos.get_children())
        for episodio in episodios:
            self.tree_episodios.insert("", "end", values=(episodio['episodio'], episodio['enlace']))

    def cargar_videos(self, event):
        selected_item = self.tree_episodios.selection()
        if not selected_item:
            return
        url_episodio = self.tree_episodios.item(selected_item[0])['values'][1]
        videos = obtener_videos(url_episodio)
        if not videos:
            messagebox.showinfo("Resultado", "No se encontraron videos para este episodio.")
            return
        self.tree_videos.delete(*self.tree_videos.get_children())
        for video in videos:
            video_url = video['url'] if video['url'] else video['code']
            self.tree_videos.insert("", "end", values=(video['titulo'], video_url))

    def cargar_ultimos_animes(self):
        """Carga los últimos animes en la pestaña correspondiente."""
        ultimos_animes = obtener_ultimos_animes()
        if not ultimos_animes:
            messagebox.showinfo("Resultado", "No se encontraron los últimos animes.")
            return
        self.tree_ultimos.delete(*self.tree_ultimos.get_children())
        for anime in ultimos_animes:
            self.tree_ultimos.insert("", "end", values=(anime['titulo'], anime['episodio'], anime['enlace']))

    def mostrar_detalle_anime(self, event):
        item = self.tree_ultimos.selection()
        if not item:
            return
        url = self.tree_ultimos.item(item[0], "values")[2]  # Obtener la URL correcta
        imagen_url, descripcion = obtener_imagen_y_descripcion(url)
        if imagen_url and descripcion:
            # Cargar y mostrar la imagen
            image_data = requests.get(imagen_url).content
            image = Image.open(io.BytesIO(image_data))
            image = image.resize((300, 400), Image.LANCZOS)  # Redimensionar imagen con mejor calidad
            self.img_label.img = ImageTk.PhotoImage(image)
            self.img_label.config(image=self.img_label.img)
            # Actualizar la descripción
            self.desc_label.config(text=descripcion)
            
            # Cargar y mostrar los episodios de la serie
            episodios = obtener_episodios(url)
            self.tree_capitulos.delete(*self.tree_capitulos.get_children())
            for episodio in episodios:
                self.tree_capitulos.insert("", "end", values=(episodio['episodio'], episodio['enlace']))
        else:
            self.img_label.config(image='')  # Borra la imagen
            self.desc_label.config(text="No se encontró descripción.")  # Mensaje de error
            self.tree_capitulos.delete(*self.tree_capitulos.get_children())  # Borra los capítulos

    def abrir_enlace(self, event):
        item = self.tree_videos.selection()
        if not item:
            return
        url = self.tree_videos.item(item[0], "values")[1]
        if url:
            webbrowser.open(url)

    def marcar_como_viendo(self):
        selected_item = self.tree_series.selection()
        if not selected_item:
            messagebox.showinfo("Información", "Por favor, selecciona una serie.")
            return
        serie = self.tree_series.item(selected_item[0])['values'][0]
        messagebox.showinfo("Información", f"La serie '{serie}' se ha marcado como 'Estoy viendo'.")

    def marcar_como_pendiente(self):
        selected_item = self.tree_series.selection()
        if not selected_item:
            messagebox.showinfo("Información", "Por favor, selecciona una serie.")
            return
        serie = self.tree_series.item(selected_item[0])['values'][0]
        messagebox.showinfo("Información", f"La serie '{serie}' se ha marcado como 'Pendiente'.")

    def marcar_como_terminado(self):
        selected_item = self.tree_series.selection()
        if not selected_item:
            messagebox.showinfo("Información", "Por favor, selecciona una serie.")
            return
        serie = self.tree_series.item(selected_item[0])['values'][0]
        messagebox.showinfo("Información", f"La serie '{serie}' se ha marcado como 'Terminado'.")

if __name__ == "__main__":
    root = tk.Tk()
    app = AnimeFLVApp(root)
    root.mainloop()
