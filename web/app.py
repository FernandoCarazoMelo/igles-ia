# ==========================================================================
# 1. IMPORTS
# ==========================================================================
import json
import locale
import os
import re
import shutil
from datetime import datetime

import markdown
import yaml  # Necesitarás PyYAML: pip install PyYAML
from dotenv import load_dotenv
from flask import (
    Flask,
    Response,
    abort,
    redirect,
    render_template,
    send_from_directory,
    url_for,
)
from flask_frozen import Freezer

load_dotenv()

# ==========================================================================
# 2. CONFIGURACIÓN DE LA APLICACIÓN Y FLASK-FROZEN
# ==========================================================================

# Configurar el locale a español para que las fechas se muestren correctamente
try:
    locale.setlocale(locale.LC_TIME, "es_ES.UTF-8")
except locale.Error:
    print(
        "Locale 'es_ES.UTF-8' no encontrado. Usando el locale por defecto del sistema."
    )

# Inicialización de Flask y Freezer
app = Flask(__name__)
app.config["FREEZER_DESTINATION"] = "build"
app.config["FREEZER_RELATIVE_URLS"] = True
freezer = Freezer(app)
# Debajo de la configuración de Freezer
BASE_URL = "https://igles-ia.es"  # URL base de tu sitio web

# Definición de la ruta donde se guardan los datos
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
SUMMARIES_DIR = os.environ.get("SUMMARIES_FOLDER")


@app.route("/callback.html")
def callback():
    # Esta ruta simplemente le dice a Flask-Frozen que este archivo existe.
    # Usamos send_from_directory para servir el archivo estático directamente.
    return app.send_static_file("callback.html")


def slugify(text):
    """
    Convierte un texto en un 'slug' amigable para URLs o IDs.
    Ej: "Un Título Genial!" -> "un-titulo-genial"
    """
    text = text.lower()
    text = re.sub(
        r"[^a-z0-9]+", "-", text
    )  # Reemplaza todo lo que no sea letra o número por un guion
    return text.strip("-")


# ==========================================================================
# 3. LÓGICA DE CARGA DE DATOS
# ==========================================================================


def load_all_summaries():
    all_summaries = []
    if not os.path.exists(SUMMARIES_DIR):
        print(f"ADVERTENCIA: El directorio de resúmenes no existe: {SUMMARIES_DIR}")
        return []

    for week_folder in os.listdir(SUMMARIES_DIR):
        week_path = os.path.join(SUMMARIES_DIR, week_folder)
        if os.path.isdir(week_path):
            try:
                # 1. Leer el resumen principal y su frontmatter YAML
                main_summary_path = os.path.join(
                    week_path, "resumen_semanal_igles-ia.txt"
                )
                metadata = {}
                main_md_content = ""

                if os.path.exists(main_summary_path):
                    with open(main_summary_path, "r", encoding="utf-8") as f:
                        content_full = f.read()
                        # Separar el frontmatter (YAML) del contenido (Markdown)
                        parts = content_full.split("---", 2)
                        if len(parts) >= 3:
                            metadata = yaml.safe_load(parts[1]) or {}
                            main_md_content = parts[2].strip()
                        else:  # Si no hay frontmatter, usar todo el archivo como contenido
                            main_md_content = content_full.strip()

                # 2. Crear el objeto de resumen usando los metadatos del frontmatter
                week_date = datetime.strptime(week_folder, "%Y-%m-%d")
                summary_obj = {
                    "slug": week_folder,
                    "date": week_date,
                    "title": metadata.get("title", f"Resumen del {week_folder}"),
                    "week_of": metadata.get(
                        "week_of", f"Semana del {week_date.strftime('%d de %B de %Y')}"
                    ),
                    "pontificate_week": metadata.get("pontificate_week"),
                    "excerpt": metadata.get("excerpt", "Leer más..."),
                    "main_content": markdown.markdown(main_md_content),
                    "documents": [],
                }

                # 3. Leer los archivos JSON de detalle (sin cambios) sorted_doc_files = sorted(os.listdir(week_path), reverse=True)

                for doc_file in sorted(os.listdir(week_path), reverse=True):
                    if doc_file.endswith(".json"):
                        doc_path = os.path.join(week_path, doc_file)
                        with open(doc_path, "r", encoding="utf-8") as f:
                            doc_data = json.load(f)
                            doc_title = doc_data.get("fuente_documento", doc_file)
                            doc_data["doc_slug"] = f"{week_folder}-{slugify(doc_title)}"
                            doc_data["resumen_general"] = markdown.markdown(
                                doc_data.get("resumen_general", "")
                            )
                            doc_data["ideas_clave"] = [
                                markdown.markdown(idea)
                                for idea in doc_data.get("ideas_clave", [])
                            ]
                            summary_obj["documents"].append(doc_data)

                all_summaries.append(summary_obj)
            except Exception as e:
                print(f"Error procesando la carpeta {week_folder}: {e}")

    all_summaries.sort(key=lambda s: s["date"], reverse=True)
    return all_summaries


# ==========================================================================
# 4. CARGA INICIAL DE DATOS (Se ejecuta una vez al iniciar el script)
# ==========================================================================
ALL_SUMMARIES = load_all_summaries()


# ==========================================================================
# 5. PROCESADOR DE CONTEXTO (Variables globales para las plantillas)
# ==========================================================================
@app.context_processor
def inject_global_vars():
    """Inyecta variables como el año actual en todas las plantillas HTML."""
    return {"current_year": datetime.now().year}


# ==========================================================================
# 6. RUTAS DE LA APLICACIÓN (Las "páginas" de tu web)
# ==========================================================================


@app.route("/")
def index():
    """Página de inicio."""
    return render_template("index.html")


@app.route("/resumenes.html")
def archive():
    """Página del archivo histórico con la lista de todos los resúmenes."""
    return render_template("archivo.html", summaries=ALL_SUMMARIES)


@app.route("/resumen/<slug>.html")
def summary_detail(slug):
    """Página de detalle para un resumen semanal específico."""
    summary = next((s for s in ALL_SUMMARIES if s["slug"] == slug), None)
    if summary is None:
        abort(404)
    return render_template("resumen_individual.html", summary=summary)


@app.route("/resumen-semanal.html")
def latest_summary():
    """Ruta de conveniencia que redirige al último resumen disponible."""
    if not ALL_SUMMARIES:
        abort(404)
    latest_slug = ALL_SUMMARIES[0]["slug"]
    return redirect(url_for("summary_detail", slug=latest_slug))


@app.route("/sobre-nosotros.html")
def about():
    """Página 'Sobre Nosotros'."""
    return render_template("sobre_nosotros.html")


@app.route("/contacto.html")
def contact():
    """Página de contacto."""
    return render_template("contacto.html")


@app.route("/leon-xiv-jubileo-de-los-jovenes-2025.html")
def jubileo():
    """Página de jubileo."""
    return render_template("jubileo.html")


@app.route("/robots.txt")
def robots_txt():
    """Sirve el archivo robots.txt desde la carpeta estática."""
    return app.send_static_file("robots.txt")


@app.route("/politica-de-privacidad.html")
def privacy_policy():
    """Página de Política de Privacidad."""
    return render_template("politica_de-privacidad.html")


# En la sección 6. RUTAS DE LA APLICACIÓN


@app.route("/sitemap.xml")
def sitemap():
    """Genera el sitemap.xml dinámicamente con todas las URLs del sitio."""
    pages = []

    # Añadir URLs estáticas
    static_urls = [
        {
            "loc": url_for("index", _external=True),
            "priority": "1.0",
            "changefreq": "weekly",
        },
        {
            "loc": url_for("archive", _external=True),
            "priority": "0.9",
            "changefreq": "weekly",
        },
        {
            "loc": url_for("about", _external=True),
            "priority": "0.5",
            "changefreq": "monthly",
        },
        {
            "loc": url_for("contact", _external=True),
            "priority": "0.5",
            "changefreq": "yearly",
        },
    ]
    for url_info in static_urls:
        url_info["loc"] = url_info["loc"].replace("http://localhost", BASE_URL)
        pages.append(url_info)

    # Añadir URLs dinámicas de los resúmenes
    for summary in ALL_SUMMARIES:
        url_info = {
            "loc": url_for("summary_detail", slug=summary["slug"], _external=True),
            "lastmod": summary["date"].strftime("%Y-%m-%d"),
            "changefreq": "yearly",
            "priority": "0.8",
        }
        url_info["loc"] = url_info["loc"].replace("http://localhost", BASE_URL)
        pages.append(url_info)

    sitemap_xml = render_template("sitemap.xml", pages=pages)
    return Response(sitemap_xml, mimetype="application/xml")


# --- AÑADE ESTA RUTA ---
@app.route("/podcast.xml")
def podcast_feed():
    """
    Sirve el archivo podcast.xml desde la carpeta raíz del proyecto.
    """
    # Esto soluciona el error durante el 'freeze'
    return send_from_directory(PROJECT_ROOT, "podcast.xml")


# ==========================================================================
# 7. GENERADOR DE URLS PARA FLASK-FROZEN
# ==========================================================================


@freezer.register_generator
def summary_detail():
    """Indica a Flask-Frozen cómo generar una página estática por cada resumen."""
    for summary in ALL_SUMMARIES:
        yield {"slug": summary["slug"]}


# ==========================================================================
# 8. BLOQUE DE EJECUCIÓN PRINCIPAL
# ==========================================================================
if __name__ == "__main__":
    print("Congelando el sitio...")
    freezer.freeze()
    build_dir = app.config.get("FREEZER_DESTINATION", "build")
    print(f"Sitio estático generado con éxito en: {build_dir}")

    print("\nIniciando proceso de post-build...")

    # --- CORRECCIÓN ---
    # Asegurarse de que la carpeta 'build' existe antes de intentar copiar en ella.
    os.makedirs(build_dir, exist_ok=True)

    rss_origen = os.path.join(PROJECT_ROOT, "podcast.xml")
    rss_destino = os.path.join(build_dir, "podcast.xml")

    if os.path.exists(rss_origen):
        print(f"Copiando '{rss_origen}' a '{rss_destino}'...")
        shutil.copy2(rss_origen, rss_destino)
        print("✅ RSS copiado con éxito.")
    else:
        print(f"⚠️  ADVERTENCIA: No se encontró 'podcast.xml' en '{PROJECT_ROOT}'.")
    redirects_origen = Path(PROJECT_ROOT) / "_redirects"
    redirects_destino = Path(build_dir) / "_redirects"
    if redirects_origen.exists():
        print(f"📂 Copiando '{redirects_origen}' → '{redirects_destino}'...")
        shutil.copy2(redirects_origen, redirects_destino)
        print("✅ Archivo _redirects copiado con éxito.")
    else:
        print(f"⚠️  No se encontró '{redirects_origen}
