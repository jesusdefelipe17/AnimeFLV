import csv

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from webdriver_manager.chrome import ChromeDriverManager

# Configura el navegador Chrome
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))

try:
    # Navegar a la página principal
    driver.get('https://www.hacienda.gob.es/es-es/cdi/paginas/informacionpresupuestaria/informacioncclls/presupuestos_eell.aspx')

    # Hacer clic en el enlace "Año 2022 y posteriores"
    WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, 'a[title="Abre nueva ventana"]'))
    ).click()

    # Cambiar el contexto al nuevo popup
    driver.switch_to.window(driver.window_handles[1])

    # Hacer clic en el botón "Acceso al Ejercicio"
    WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[type="submit"]'))
    ).click()

    # Esperar a que la página de búsqueda se cargue
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.ID, 'Comunidad'))
    )

    # Seleccionar la Comunidad Autónoma con valor 08 (Castilla-La Mancha)
    select_comunidad = Select(driver.find_element(By.ID, 'Comunidad'))
    select_comunidad.select_by_value('08')

    # Esperar a que el combo de Provincia se cargue
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.ID, 'Provincia'))
    )

    # Seleccionar la Provincia (Ciudad Real; valor 13)
    select_provincia = Select(driver.find_element(By.ID, 'Provincia'))
    select_provincia.select_by_value('13')

    # Seleccionar el Tipo de Entidad
    select_tipo_entidad = Select(driver.find_element(By.ID, 'CodigoTipoCorporacion'))
    select_tipo_entidad.select_by_value('A5')  # Ayuntamientos >= 5.000 hab.

    # Hacer clic en el botón de búsqueda
    buscar_button = driver.find_element(By.ID, 'btnBuscar')
    buscar_button.click()

    # Esperar a que la tabla esté visible
    WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, 'table.table.table-sm.table-bordered.table-hover'))
    )

    # Encontrar el enlace de "Alcázar de San Juan" y hacer clic en él
    alcazar_link = driver.find_element(By.XPATH, "//a[text()='Almagro']")
    alcazar_link.click()

    # Esperar a que la nueva tabla esté completamente cargada
    WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, 'table.table.table-sm.table-bordered.table-hover'))
    )

    # Hacer clic en el enlace de "Alcázar de San Juan"
    alcazar_link = driver.find_element(By.XPATH, "//a[contains(@href, '/AccesoFormulariosEntidad/11326') and text()='Almagro']")
    alcazar_link.click()

    # Esperar a que la nueva página cargue y el enlace "F.1.1.6 Clasificación por Programas" esté disponible
    WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.XPATH, "//a[@id='lnkFormulario' and contains(text(), 'Clasificación por Programas')]"))
    )

    # Hacer clic en el enlace dentro del <tr> con idformulario="202143"
    row = driver.find_element(By.XPATH, "//tr[@idformulario='202143']//a[@id='lnkFormulario']")
    row.click()

    # Esperar a que cargue la tabla con ID "table20436"
    WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.ID, 'table20436'))
    )

    # Extraer los datos de la tabla
    table = driver.find_element(By.ID, 'table20436')
    
    # Extraer encabezados
    headers = []
    header_rows = table.find_elements(By.CSS_SELECTOR, 'thead tr')
    for header_row in header_rows:
        header_cells = header_row.find_elements(By.TAG_NAME, 'th')
        headers = [header.text.strip() for header in header_cells]
    
    # Extraer datos
    data_rows = table.find_elements(By.CSS_SELECTOR, 'tbody tr')
    data = []
    for row in data_rows:
        columns = row.find_elements(By.TAG_NAME, 'td')
        row_data = [column.text.strip() for column in columns]
        data.append(row_data)
    
    # Guardar los datos en un archivo CSV
    with open('tabla_datos.csv', 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        if headers:
            writer.writerow(headers)  # Escribir encabezados
        writer.writerows(data)  # Escribir los datos

    print("Datos extraídos y guardados en 'tabla_datos.csv'.")

finally:
    driver.quit()
