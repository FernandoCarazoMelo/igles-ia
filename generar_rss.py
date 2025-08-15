# Archivo: generar_rss.py
import datetime
import json
import os
import xml.etree.ElementTree as ET

# --- Configuración ---
PODCAST_TITLE = "Homilías Papa León XIV"
PODCAST_LINK = "https://igles-ia.es/podcast"
PODCAST_DESCRIPTION = "Podcast con los discursos y homilías del Santo Padre íntegras. Leídos con locutor profesional gracias a la IA."
PODCAST_LANGUAGE = "es"
PODCAST_IMAGE = "https://igles-ia.es/images/podcast-cover.jpg"
PODCAST_AUTHOR = "igles-ia.es"

# Rutas
SUMMARIES_BASE_DIR = "json-rss/"  # Carpeta principal de los JSON
AUDIO_BASE_URL = "https://igles-ia.es/audio/"
IMAGE_BASE_URL = "https://igles-ia.es/images/episodios/"
OUTPUT_RSS_FILE = "podcast.xml"  # Lo guardará en la raíz del proyecto

# --- Lógica ---


def cargar_todos_los_episodios():
    """Busca en todas las subcarpetas de SUMMARIES_BASE_DIR y carga los datos de los JSON."""
    episodios = []
    for root, _, files in os.walk(SUMMARIES_BASE_DIR):
        for file in files:
            if file.endswith(".json"):
                try:
                    with open(os.path.join(root, file), "r", encoding="utf-8") as f:
                        data = json.load(f)
                        # Aplanar los datos en una lista de diccionarios de episodios
                        for idx in range(len(data["titulo"])):
                            episodio = {
                                "titulo": data["titulo"][str(idx)],
                                "fecha": data["fecha"][str(idx)],
                                "texto": data["texto"][str(idx)],
                                "filename": data["filename"][str(idx)],
                            }
                            episodios.append(episodio)
                except (json.JSONDecodeError, KeyError) as e:
                    print(f"Error al leer el archivo {file}: {e}")
    # Ordenar episodios por fecha, del más nuevo al más antiguo
    episodios.sort(key=lambda x: x["fecha"], reverse=True)
    return episodios


# --- Creación del RSS ---
ITUNES_NS = "http://www.itunes.com/dtds/podcast-1.0.dtd"
ET.register_namespace("itunes", ITUNES_NS)

rss = ET.Element("rss", {"version": "2.0", "xmlns:itunes": ITUNES_NS})
channel = ET.SubElement(rss, "channel")

# Info general del podcast
ET.SubElement(channel, "title").text = PODCAST_TITLE
ET.SubElement(channel, "link").text = PODCAST_LINK
# ... (el resto de la configuración general es igual)
ET.SubElement(channel, "language").text = PODCAST_LANGUAGE
ET.SubElement(channel, "description").text = PODCAST_DESCRIPTION
ET.SubElement(channel, "itunes:author").text = PODCAST_AUTHOR
ET.SubElement(channel, "itunes:image", {"href": PODCAST_IMAGE})


# Añadir todos los episodios
episodios = cargar_todos_los_episodios()
for episodio in episodios:
    item = ET.SubElement(channel, "item")

    # Primera línea como resumen, con un límite de caracteres
    descripcion_corta = episodio["texto"].split("\n")[0][:250] + "..."

    # Enlaces
    audio_url = AUDIO_BASE_URL + episodio["filename"] + ".mp3"
    imagen_url = IMAGE_BASE_URL + episodio["filename"] + ".jpg"

    ET.SubElement(item, "title").text = episodio["titulo"]
    ET.SubElement(item, "description").text = descripcion_corta
    ET.SubElement(item, "pubDate").text = datetime.datetime.strptime(
        episodio["fecha"], "%Y-%m-%d"
    ).strftime("%a, %d %b %Y 12:00:00 GMT")
    ET.SubElement(
        item, "enclosure", {"url": audio_url, "type": "audio/mpeg", "length": "0"}
    )  # length es opcional
    ET.SubElement(item, "itunes:image", {"href": imagen_url})

# Guardar archivo XML
tree = ET.ElementTree(rss)
tree.write(OUTPUT_RSS_FILE, encoding="utf-8", xml_declaration=True)

print(f"✅ RSS generado con {len(episodios)} episodios: {OUTPUT_RSS_FILE}")
