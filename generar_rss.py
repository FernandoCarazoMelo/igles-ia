import datetime
import json
import os
import xml.etree.ElementTree as ET

# --- Configuración General del Podcast ---
PODCAST_TITLE = "Homilías Papa León XIV"
PODCAST_LINK = "https://igles-ia.es"
PODCAST_DESCRIPTION = "Podcast con los discursos y homilías del Santo Padre íntegras. Leídos con locutor profesional gracias a la IA."
PODCAST_LANGUAGE = "es-ES"
PODCAST_AUTHOR = "igles-ia.es"
PODCAST_OWNER_EMAIL = "igles-ia@igles-ia.es" 

# --- CAMBIO IMPORTANTE AQUÍ ---
# Reemplaza esta URL por la URL pública y real de tu única imagen de portada.
# Puede estar alojada en tu web, en S3, o donde prefieras.
PODCAST_IMAGE = "https://URL-REAL-DE-TU-IMAGEN-DE-PORTADA.jpg" 

# --- Rutas ---
JSON_BASE_DIR = "json-rss/"
OUTPUT_RSS_FILE = "podcast.xml"

# --- Lógica de Carga de Episodios ---
def cargar_todos_los_episodios_metadata():
    """
    Busca en todas las subcarpetas de JSON_BASE_DIR y carga los datos
    de los archivos 'episodes_metadata.json'.
    """
    todos_los_episodios = []
    print(f"Buscando metadatos de episodios en: '{JSON_BASE_DIR}'...")
    
    for root, _, files in os.walk(JSON_BASE_DIR):
        for file in files:
            if file == "episodes_metadata.json":
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        episodios_del_archivo = json.load(f)
                        todos_los_episodios.extend(episodios_del_archivo)
                except (json.JSONDecodeError, KeyError) as e:
                    print(f"Error al leer el archivo {file_path}: {e}")

    todos_los_episodios.sort(
        key=lambda x: tuple(map(int, x.get("numero_episodio", "0.0").split('.'))),
        reverse=True
    )
    
    print(f"Se encontraron y ordenaron {len(todos_los_episodios)} episodios.")
    return todos_los_episodios

# --- Creación de la Estructura RSS ---
ITUNES_NS = "http://www.itunes.com/dtds/podcast-1.0.dtd"
ET.register_namespace("itunes", ITUNES_NS)

rss = ET.Element("rss", {"version": "2.0", "xmlns:itunes": ITUNES_NS})
channel = ET.SubElement(rss, "channel")

# Información general del podcast (Channel)
ET.SubElement(channel, "title").text = PODCAST_TITLE
ET.SubElement(channel, "link").text = PODCAST_LINK
ET.SubElement(channel, "language").text = PODCAST_LANGUAGE
ET.SubElement(channel, "description").text = PODCAST_DESCRIPTION
ET.SubElement(channel, "itunes:author").text = PODCAST_AUTHOR
ET.SubElement(channel, "itunes:image", {"href": PODCAST_IMAGE})
itunes_owner = ET.SubElement(channel, "itunes:owner")
ET.SubElement(itunes_owner, "itunes:name").text = PODCAST_AUTHOR
ET.SubElement(itunes_owner, "itunes:email").text = PODCAST_OWNER_EMAIL

# --- Añadir los Episodios (Items) ---
episodios = cargar_todos_los_episodios_metadata()
for episodio in episodios:
    item = ET.SubElement(channel, "item")

    titulo = episodio["titulo_spotify"]
    descripcion = episodio["descripcion_spotify"]
    audio_url = episodio["url_audio"]
    fecha_pub = episodio["fecha"]
    
    ET.SubElement(item, "title").text = titulo
    description_element = ET.SubElement(item, "description")
    description_element.text = f"<![CDATA[{descripcion}]]>"
    
    pub_date_dt = datetime.datetime.strptime(fecha_pub, "%Y-%m-%d")
    ET.SubElement(item, "pubDate").text = pub_date_dt.strftime("%a, %d %b %Y 12:00:00 GMT")
    
    ET.SubElement(item, "enclosure", {"url": audio_url, "type": "audio/mpeg", "length": "0"})
    ET.SubElement(item, "guid").text = audio_url
    ET.SubElement(item, "itunes:author").text = PODCAST_AUTHOR
    
    # --- CAMBIO AQUÍ ---
    # Usar la misma imagen de portada para todos los episodios
    ET.SubElement(item, "itunes:image", {"href": PODCAST_IMAGE})
    ET.SubElement(item, "itunes:episode").text = episodio["numero_episodio"]

# --- Guardar el Archivo XML ---
tree = ET.ElementTree(rss)
xml_str = ET.tostring(rss, encoding='unicode', method='xml')

import xml.dom.minidom
dom = xml.dom.minidom.parseString(xml_str)
pretty_xml_as_string = dom.toprettyxml(indent="  ")
pretty_xml_as_string = "\n".join([line for line in pretty_xml_as_string.split('\n') if line.strip()])

with open(OUTPUT_RSS_FILE, "w", encoding="utf-8") as f:
    f.write(pretty_xml_as_string)

print(f"✅ RSS generado con éxito: {OUTPUT_RSS_FILE}")
