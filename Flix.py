from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import chromedriver_autoinstaller
import time
import requests
from bs4 import BeautifulSoup
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import io
import webbrowser


def obtener_iframe_src(url_pelicula):
    """Obtiene el src del iframe después de cambiar el servidor."""
    
    # Configuración de Selenium
    chrome_options = Options()
    chrome_options.add_argument('--headless')  # Ejecuta el navegador en modo headless
    chrome_options.add_argument('--disable-gpu')  # Deshabilita la GPU (opcional)

    # Descargar e instalar chromedriver automáticamente
    chromedriver_autoinstaller.install()

    # Inicializa el driver de Selenium
    driver = webdriver.Chrome(options=chrome_options)

    try:
        # Accede a la URL de la película
        driver.get(url_pelicula)

        # Espera hasta que el botón esté presente y haz clic en él
        boton_servidor = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CLASS_NAME, 'bstd.Button'))
        )
        boton_servidor.click()

        # Espera un tiempo para que el iframe se cargue
        time.sleep(3)

        # Obtén el iframe
        iframe = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, 'iframe'))
        )

        # Extrae el src del iframe
        iframe_src = iframe.get_attribute('src')
    finally:
        # Cierra el navegador
        driver.quit()

    return iframe_src

def buscar_pelicula(nombre_pelicula):
    """Busca una película en PelisflixHD y devuelve los resultados."""
    url_busqueda = f"https://pelisflixhd.net/?s={nombre_pelicula.replace(' ', '+')}"
    response = requests.get(url_busqueda)
    if response.status_code != 200:
        print("Error al acceder a la página de búsqueda.")
        return []
    
    soup = BeautifulSoup(response.content, 'html.parser')
    resultados = soup.find('ul', class_='MovieList Rows AX A04 B03 C20 D03 E20 Alt')
    
    if not resultados:
        print("No se encontraron resultados para la búsqueda.")
        return []
    
    peliculas = []
    for resultado in resultados.find_all('li', class_='TPostMv'):
        enlace = resultado.find('a', href=True)
        titulo = resultado.find('h2', class_='Title')
        if enlace and titulo:
            url = enlace['href']
            peliculas.append({'titulo': titulo.text.strip(), 'url': url})
    
    return peliculas

class Flix:
    def __init__(self, root):
        self.root = root
        self.root.title("Buscador de Peliculas")
        self.root.geometry("1700x800")  # Ajustado el tamaño de la ventana principal

        # Crear el notebook para las pestañas
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Pestaña de búsqueda de series
        self.tab_busqueda = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_busqueda, text="Buscar Película")

        self.crear_interfaz_busqueda(self.tab_busqueda)

    def crear_interfaz_busqueda(self, frame):
        """Crea la interfaz de búsqueda de series en la pestaña correspondiente."""
        self.frame_busqueda = ttk.Frame(frame, padding="10")
        self.frame_busqueda.pack(fill=tk.BOTH, expand=True)

        self.lbl_nombre = ttk.Label(self.frame_busqueda, text="Nombre de la película:")
        self.lbl_nombre.grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)

        self.entry_nombre = ttk.Entry(self.frame_busqueda, width=100)
        self.entry_nombre.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        self.entry_nombre.bind("<Return>", self.buscar_pelicula)  # Buscar al presionar Enter

        self.btn_buscar = ttk.Button(self.frame_busqueda, text="Buscar", command=self.buscar_pelicula)
        self.btn_buscar.grid(row=0, column=2, sticky=tk.W, padx=5, pady=5)

        # Configuración de las tablas
        self.tree_series = ttk.Treeview(self.frame_busqueda, columns=("Película", "URL"), show="headings", height=10)
        self.tree_series.heading("Película", text="Película")
        self.tree_series.heading("URL", text="URL")
        self.tree_series.column("Película", width=200)
        self.tree_series.column("URL", width=200)
        self.tree_series.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), padx=5, pady=5)
        self.tree_series.bind("<ButtonRelease-1>", self.cargar_iframe)

        self.tree_iframe = ttk.Treeview(self.frame_busqueda, columns=("Enlace del Iframe",), show="headings", height=10)
        self.tree_iframe.heading("Enlace del Iframe", text="Enlace del Iframe")
        self.tree_iframe.column("Enlace del Iframe", width=500)
        self.tree_iframe.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), padx=5, pady=5)
        self.tree_iframe.bind("<Double-1>", self.abrir_enlace)

        self.loading_label = ttk.Label(self.frame_busqueda, text="Verificando enlaces...", foreground="blue")
        self.loading_label.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), padx=5, pady=5)
        self.loading_label.grid_forget()

    def buscar_pelicula(self, event=None):
        nombre_pelicula = self.entry_nombre.get()
        peliculas = buscar_pelicula(nombre_pelicula)
        if not peliculas:
            messagebox.showinfo("Resultado", "No se encontraron películas con el nombre dado.")
            return
        self.tree_series.delete(*self.tree_series.get_children())
        self.tree_iframe.delete(*self.tree_iframe.get_children())
        for pelicula in peliculas:
            self.tree_series.insert("", "end", iid=pelicula['titulo'], values=(pelicula['titulo'], pelicula['url']))
        self.peliculas = peliculas

    def cargar_iframe(self, event):
        selected_item = self.tree_series.selection()
        if not selected_item:
            return
        url_pelicula = self.tree_series.item(selected_item[0])['values'][1]
        iframe_src = obtener_iframe_src(url_pelicula)
        if not iframe_src:
            messagebox.showinfo("Resultado", "No se encontró el iframe para esta película.")
            return
        self.tree_iframe.delete(*self.tree_iframe.get_children())
        self.tree_iframe.insert("", "end", values=(iframe_src,))

    def abrir_enlace(self, event):
        item = self.tree_iframe.selection()
        if not item:
            return
        url = self.tree_iframe.item(item[0], "values")[0]
        if url:
            webbrowser.open(url)

if __name__ == "__main__":
    root = tk.Tk()
    app = Flix(root)
    root.mainloop()
