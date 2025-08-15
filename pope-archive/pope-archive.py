import logging
import os
import time
from urllib.parse import urljoin, urlparse

import html2text
import requests
from bs4 import BeautifulSoup

# --- Configuración ---

BASE_URL = "https://www.vatican.va/"
START_PAGE_URL = "https://www.vatican.va/content/vatican/es/holy-father.html"  # URL actualizada, la original daba problemas
OUTPUT_DIR = "archivo_papal"
LOG_FILE = "archiver.log"
REQUEST_DELAY_SECONDS = 1
REQUEST_TIMEOUT_SECONDS = 30

# Mapeo de nombres de Papas a sus slugs en la URL
POPE_MAP = {
    "León XIV": "leo-xiv",
    "Francisco": "francesco",
    "Benedicto XVI": "benedict-xvi",
    "Juan Pablo II": "john-paul-ii",
    "Juan Pablo I": "john-paul-i",
    "Pablo VI": "paul-vi",
    "Juan XXIII": "john-xxiii",
    "Pío XII": "pius-xii",
    "Pío XI": "pius-xi",
    "Benedicto XV": "benedict-xv",
    "Pío X": "pius-x",
    "León XIII": "leo-xiii",
}

# Configuración del logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# --- Funciones de Red y Extracción ---


def get_soup(url):
    """
    Realiza una solicitud GET a una URL, maneja errores y devuelve un objeto BeautifulSoup.
    """
    try:
        time.sleep(REQUEST_DELAY_SECONDS)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()  # Lanza una excepción para códigos de error HTTP
        # Usar 'html.parser' para compatibilidad, aunque 'lxml' es más rápido
        return BeautifulSoup(response.content, "html.parser")
    except requests.exceptions.RequestException as e:
        logging.error(f"Error al acceder a la URL {url}: {e}")
        return None


def get_pope_main_page_url(pope_slug):
    """Construye la URL de la página principal de un Papa."""
    return urljoin(BASE_URL, f"content/{pope_slug}/es.html")


def scrape_document(doc_url):
    """
    Extrae el título y el contenido de una página de documento y lo convierte a Markdown.
    """
    logging.info(f"Procesando documento: {doc_url}")
    soup = get_soup(doc_url)
    if not soup:
        return None

    title_tag = soup.find("h3", class_="title")
    title = title_tag.get_text(strip=True) if title_tag else "Sin Título"

    content_div = soup.find("div", class_="text")
    if not content_div:
        logging.warning(
            f"No se encontró el div 'text' en {doc_url}. Saltando documento."
        )
        return None

    # Convertir el contenido HTML a Markdown
    converter = html2text.HTML2Text()
    converter.ignore_links = False
    markdown_content = converter.handle(str(content_div))

    # Combinar título y contenido
    full_markdown = f"# {title}\n\n{markdown_content}"
    return full_markdown


def save_as_markdown(pope_name, doc_url, markdown_content):
    """
    Guarda el contenido de un documento como un archivo Markdown, preservando la estructura de carpetas.
    """
    try:
        # Parseamos la URL para obtener la ruta y crear la estructura de carpetas
        url_parts = urlparse(doc_url)
        path_parts = url_parts.path.strip("/").split("/")

        # Estructura: 'es/nombre-del-papa/categoria/nombre_archivo.md'
        # El código de idioma es path_parts[1], el slug del papa es path_parts[2], la categoría es path_parts[3]
        lang_code = path_parts[1]
        pope_slug = path_parts[2]  # El slug se usa para la carpeta del papa
        category = path_parts[3]

        # Crear la ruta del directorio
        dir_path = os.path.join(lang_code, pope_slug, category)
        os.makedirs(dir_path, exist_ok=True)

        # Crear el nombre del archivo, corrigiendo el error
        # CORRECCIÓN AQUÍ: Accedemos al primer elemento (índice [0]) de la tupla.
        file_name = os.path.splitext(path_parts[-1])[0] + ".md"

        file_path = os.path.join(dir_path, file_name)

        # Guardar el contenido en el archivo
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)

        # Opcional: registrar el éxito del guardado
        # logging.info(f"Guardado exitosamente: {file_path}")

    except Exception as e:
        logging.error(f"No se pudo guardar el documento {doc_url}: {e}")


def process_pope(pope_name, pope_slug):
    """
    Procesa todos los documentos de un Papa específico.
    """
    logging.info(f"--- Iniciando procesamiento para el Papa: {pope_name} ---")
    pope_main_page_url = get_pope_main_page_url(pope_slug)

    soup = get_soup(pope_main_page_url)
    if not soup:
        logging.error(
            f"No se pudo acceder a la página principal de {pope_name}. Saltando."
        )
        return

    # Usar un conjunto para evitar procesar URLs duplicadas
    urls_to_visit = set()
    document_urls = set()

    # Encontrar enlaces a categorías de documentos en la página principal del Papa
    # La estructura puede variar, buscamos enlaces dentro del contenido principal
    content_area = (
        soup.find("div", class_="document-container")
        or soup.find("div", id="main-container")
        or soup.body
    )
    for link in content_area.find_all("a", href=True):
        href = link["href"]
        # Filtrar enlaces que parecen ser categorías o índices
        if (
            pope_slug in href
            and ".html" in href
            and not href.startswith(("http", "#", "javascript"))
        ):
            full_url = urljoin(pope_main_page_url, href)
            urls_to_visit.add(full_url)

    # Proceso de descubrimiento recursivo o por cola
    processed_urls = set()
    while urls_to_visit:
        current_url = urls_to_visit.pop()
        if current_url in processed_urls:
            continue

        processed_urls.add(current_url)
        logging.info(f"Explorando índice: {current_url}")

        index_soup = get_soup(current_url)
        if not index_soup:
            continue

        # Buscar enlaces en la página de índice
        index_content_area = (
            index_soup.find("div", class_="document-container") or index_soup.body
        )
        for link in index_content_area.find_all("a", href=True):
            href = link["href"]
            full_url = urljoin(current_url, href)

            if pope_slug not in full_url:
                continue

            # Decidir si es un documento final o otro índice
            if "/documents/" in full_url:
                document_urls.add(full_url)
            elif "index.html" in full_url and full_url not in processed_urls:
                urls_to_visit.add(full_url)

    logging.info(f"Se encontraron {len(document_urls)} documentos para {pope_name}.")
    
    # Descargar y guardar cada documento
    for doc_url in document_urls:
        markdown_content = scrape_document(doc_url)
        if markdown_content:
            save_as_markdown(pope_name, doc_url, markdown_content)


# --- Función Principal ---


def main():
    """
    Función principal que orquesta el proceso de archivado.
    """
    logging.info("Iniciando el Archivador Papal.")
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        logging.info(f"Directorio de salida creado: {OUTPUT_DIR}")

    for pope_name, pope_slug in POPE_MAP.items():
        process_pope(pope_name, pope_slug)

    logging.info("Proceso de archivado completado.")


if __name__ == "__main__":
    main()
