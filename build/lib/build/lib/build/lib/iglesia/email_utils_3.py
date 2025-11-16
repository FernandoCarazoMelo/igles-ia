import json
import os
import re
import smtplib
from datetime import datetime
from email.message import EmailMessage
from email.utils import formataddr
import yaml

import markdown
import pandas as pd
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from typing import Union

load_dotenv()

# Define common styles for consistency
DEFAULT_TEXT_FONT_FAMILY = "'Arial', sans-serif"  # A common, safe font for emails
DEFAULT_TEXT_COLOR = "#333"  # A dark grey for general text
HIGHLIGHT_COLOR = "#003366"  # Your desired dark blue for highlights/bold


def aplicar_estilos_html(html_basico):
    soup = BeautifulSoup(html_basico, "html.parser")

    # Estilos para <p>
    for p in soup.find_all("p"):
        estilo_actual = p.get("style", "")
        # Apply font-size, default color, and font-family
        p["style"] = (
            f"{estilo_actual}font-size:15px; color:{DEFAULT_TEXT_COLOR}; font-family:{DEFAULT_TEXT_FONT_FAMILY};".strip()
        )

    # Estilos para <ul> y <li>
    for ul in soup.find_all("ul"):
        estilo_actual = ul.get("style", "")
        # Apply font-size, default color, and font-family to UL
        ul["style"] = (
            f"{estilo_actual}font-size:15px; color:{DEFAULT_TEXT_COLOR}; font-family:{DEFAULT_TEXT_FONT_FAMILY}; list-style-position: inside; padding-left: 20px;".strip()
        )

    for li in soup.find_all("li"):
        estilo_actual = li.get("style", "")
        # Apply margin-bottom and inherit/ensure font-family and color
        li["style"] = (
            f"{estilo_actual}margin-bottom:4px; font-family:{DEFAULT_TEXT_FONT_FAMILY}; color:{DEFAULT_TEXT_COLOR};".strip()
        )

    # Estilos para <a>
    for a in soup.find_all("a"):
        estilo_actual = a.get("style", "")
        # Ensure consistent link color and no underline
        a["style"] = (
            f"{estilo_actual}color:{HIGHLIGHT_COLOR}; text-decoration:none;".strip()
        )
        a["target"] = "_blank"

    # Estilos para <b> (negritas) - Prioritize highlight color
    for strong_tag in soup.find_all(["b", "strong"]):  # Buscar ambos <b> y <strong>
        estilo_actual = strong_tag.get("style", "")
        # Aplica el color de resaltado y asegura la consistencia de la fuente
        # Usa ' !important;' para forzar la precedencia en algunos clientes de email tercos.
        strong_tag["style"] = (
            f"{estilo_actual}color:{HIGHLIGHT_COLOR} !important; font-family:{DEFAULT_TEXT_FONT_FAMILY};".strip()
        )

    # Apply Montserrat to H2, H3, H4 as intended in your original code
    for h2 in soup.find_all("h2"):
        estilo_actual = h2.get("style", "")
        if "font-family" not in estilo_actual:  # Only apply if not already set
            h2["style"] = (
                f"{estilo_actual}color:{HIGHLIGHT_COLOR}; font-family: 'Montserrat', sans-serif;".strip()
            )

    for h3 in soup.find_all("h3"):
        estilo_actual = h3.get("style", "")
        if "font-family" not in estilo_actual:
            h3["style"] = (
                f"{estilo_actual}color:{HIGHLIGHT_COLOR}; font-family: 'Montserrat', sans-serif;".strip()
            )

    for h4 in soup.find_all("h4"):
        estilo_actual = h4.get("style", "")
        if "font-family" not in estilo_actual:
            h4["style"] = (
                f"{estilo_actual}color:{HIGHLIGHT_COLOR}; font-size: 16px; margin-top:15px; margin-bottom:5px; font-family: 'Montserrat', sans-serif;".strip()
            )

    return str(soup)


def construir_html_desde_jsons(directorio_jsons):
    documentos = []
    if not os.path.exists(directorio_jsons) or not os.path.isdir(directorio_jsons):
        print(
            f"Advertencia: El directorio de JSONs no existe o no es un directorio: {directorio_jsons}"
        )
        return ""  # Devuelve string vacío si no hay directorio

    # Recolectar todos los documentos primero
    for archivo in sorted(os.listdir(directorio_jsons)):
        if archivo.endswith(".json"):
            path = os.path.join(directorio_jsons, archivo)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    datos = json.load(f)
            except Exception as e:
                print(f"Error al leer o parsear el JSON {archivo}: {e}")
                continue  # Saltar este archivo

            match = re.search(r"(\d{8})", archivo)
            if match:
                fecha_raw = match.group(1)
                try:
                    fecha_formateada = datetime.strptime(fecha_raw, "%Y%m%d").strftime(
                        "%d/%m/%Y"
                    )
                except ValueError:
                    fecha_formateada = None
            else:
                fecha_formateada = None

            documentos.append(
                {
                    "id": archivo.replace(".json", "")
                    .replace(".", "_")
                    .replace(" ", "_"),
                    "titulo": datos.get("fuente_documento", "Documento sin título"),
                    "url": datos.get("url_original", "#"),
                    "tipo": datos.get("tipo_documento", "Desconocido"),
                    "resumen": datos.get("resumen_general", ""),
                    "ideas": datos.get("ideas_clave", []),
                    "tags": datos.get("tags_sugeridos", []),
                    "fecha": fecha_formateada,
                }
            )

    if not documentos:
        return "<p>No se encontraron documentos JSON válidos para mostrar.</p>"
    else:
        documentos.reverse()

    html_idx = f"""
    <h2 style="color:{HIGHLIGHT_COLOR}; font-family: 'Montserrat', sans-serif;">📚 Índice de Documentos</h2>
    <ul style="font-size:15px; color:{DEFAULT_TEXT_COLOR}; font-family:{DEFAULT_TEXT_FONT_FAMILY}; list-style-type: none; padding-left: 0;">
    """
    for doc in documentos:
        texto_link = f"{doc['tipo']}: {doc['titulo']}" + (
            f" ({doc['fecha']})" if doc["fecha"] else ""
        )
        html_idx += f"""<li style="margin-bottom: 8px;"><a href="#{doc["id"]}" style="color:{HIGHLIGHT_COLOR};text-decoration:none; font-weight:bold;">🔗 {texto_link}</a></li>"""
    html_idx += (
        "<hr style='border:0; height:1px; background-color:#e0e0e0; margin: 40px 0;'>"
    )

    html_docs = ""
    for doc in documentos:
        html_docs += f"""
        <article id="{doc["id"]}" style="margin-bottom: 30px;">
          <h3 style="color:{HIGHLIGHT_COLOR}; font-family: 'Montserrat', sans-serif;">
            <a href="{doc["url"]}" style="color:{HIGHLIGHT_COLOR}; text-decoration:none;" target="_blank">📄 {doc["titulo"]}</a>
          </h3>
          <p style="font-size:14px; color:{DEFAULT_TEXT_COLOR}; font-family:{DEFAULT_TEXT_FONT_FAMILY};">
            <strong>Tipo:</strong> {doc["tipo"]} |
            <strong>Texto original:</strong> <a href="{doc["url"]}" style="color:{HIGHLIGHT_COLOR}; text-decoration:none;" target="_blank">Link</a>
            """
        if doc["fecha"]:
            html_docs += f" | <strong>Fecha:</strong> {doc['fecha']}"
        html_docs += "</p>"

        resumen_doc_html = ""
        if doc["resumen"]:
            # markdown.markdown output needs to be passed through aplicar_estilos_html
            # to ensure inline styles are applied correctly to paragraphs and bold text within the markdown
            resumen_doc_html = aplicar_estilos_html(markdown.markdown(doc["resumen"]))
        html_docs += resumen_doc_html

        if doc["ideas"]:
            html_docs += f"""<h4 style="color:{HIGHLIGHT_COLOR}; font-size: 16px; margin-top:15px; margin-bottom:5px; font-family: 'Montserrat', sans-serif;">Ideas Clave:</h4>
            <ul style="color:{DEFAULT_TEXT_COLOR}; font-size:15px; font-family:{DEFAULT_TEXT_FONT_FAMILY}; list-style-position: outside; padding-left: 20px;">"""
            for idea in doc["ideas"]:
                # Ensure ideas also get inline styles, especially for any bold text within them
                idea_html = aplicar_estilos_html(idea)
                # Remove outer <p> tags if applying to LI directly, as they might be added by markdown conversion
                idea_html = idea_html.replace(
                    f'<p style="font-size:15px; color:{DEFAULT_TEXT_COLOR}; font-family:{DEFAULT_TEXT_FONT_FAMILY};">',
                    "",
                ).replace("</p>\n", "")
                html_docs += f"<li>{idea_html}</li>"
            html_docs += "</ul>"

        if doc["tags"]:
            html_docs += "<p style='margin-top:15px;'>"
            for tag in doc["tags"]:
                html_docs += f"""<span style="background-color:{HIGHLIGHT_COLOR};color:white;padding:5px 10px;border-radius:15px;font-size:12px;margin:2px 4px 2px 0;display:inline-block; font-family:{DEFAULT_TEXT_FONT_FAMILY};">#{tag}</span> """
            html_docs += "</p>"
        html_docs += "</article><hr style='border:0; height:1px; background-color:#e0e0e0; margin: 40px 0;'>"

    if html_docs.endswith(
        "<hr style='border:0; height:1px; background-color:#e0e0e0; margin: 40px 0;'>"
    ):
        html_docs = html_docs[
            : -len(
                "<hr style='border:1px; height:1px; background-color:#e0e0e0; margin: 40px 0;'>"
            )
        ]
    return html_idx + html_docs


# ==========================================================================
# 2. NUEVA LÓGICA PARA GENERAR EL CONTENIDO DEL EMAIL
# ==========================================================================
def generar_html_semanal_completo(fecha_resumen):
    """
    Lee la carpeta de una semana, procesa el .txt con frontmatter y los JSONs,
    y devuelve el cuerpo HTML final para el email y los metadatos.
    """
    SUMMARIES_FOLDER = os.getenv("SUMMARIES_FOLDER")
    ruta_semana = os.path.join(SUMMARIES_FOLDER, fecha_resumen)

    # Parte 1: Leer el resumen principal desde el .txt con YAML
    ruta_resumen_txt = os.path.join(ruta_semana, 'resumen_semanal_igles-ia.txt')
    metadata = {}
    main_md_content = "Resumen principal no disponible esta semana."

    if os.path.exists(ruta_resumen_txt):
        with open(ruta_resumen_txt, 'r', encoding='utf-8') as f:
            content_full = f.read()
            parts = content_full.split('---', 2)
            if len(parts) >= 3:
                metadata = yaml.safe_load(parts[1]) or {}
                main_md_content = parts[2].strip()
    
    # Parte 2: Construir el HTML
    titulo_principal = metadata.get('title', 'Resumen Semanal de Igles-IA')
    html_resumen_principal = f"<h3>{titulo_principal}</h3>" + markdown.markdown(main_md_content)
    html_documentos_detalle = construir_html_desde_jsons(ruta_semana)
    
    html_completo = html_resumen_principal
    if html_documentos_detalle: # Solo añade la sección de detalles si existe
        html_completo += "<hr style='border:0; height:1px; background-color:#e0e0e0; margin: 40px 0;'>" + html_documentos_detalle

    # Parte 3: Aplicar estilos en línea a todo el contenido
    html_final_con_estilos = aplicar_estilos_html(html_completo)
    
    return html_final_con_estilos, metadata

# Tu función _crear_mensaje_email puede quedar igual o simplificarse
def _crear_mensaje_email(destinatario, nombre, asunto, cuerpo_html, plantilla_path):
    EMAIL_USER = os.getenv("EMAIL_USER")
    msg = EmailMessage()
    msg["Subject"] = asunto
    msg["From"] = formataddr(("Igles-IA", EMAIL_USER))
    msg["To"] = destinatario
    
    with open(plantilla_path, "r", encoding="utf-8") as f:
        html_template = f.read()
    
    html_final = html_template.replace("{{nombre}}", nombre)
    html_final = html_final.replace("{{body}}", cuerpo_html)
    msg.add_alternative(html_final, subtype="html")
    return msg

# ==========================================================================
# 3. TU FUNCIÓN ORIGINAL, PERO CON LA NUEVA LÓGICA
# Mismo nombre, mismos parámetros, mismo comportamiento esperado.
# ==========================================================================

def enviar_correos_todos(
    correos_path: Union[str, pd.DataFrame] = "emails.csv",
    fecha_resumen="2025-05-20",
    ruta_plantilla_email="plantilla.html",
    ruta_html_generado_para_web="data_web/contenido_semanal.html", # Mantenemos el parámetro
    send_emails=True,
):
    """
    Función principal para generar el contenido una vez y luego enviar todos los correos.
    Ahora compatible con la nueva estructura de datos.
    """
    EMAIL_USER = os.getenv("EMAIL_USER")
    EMAIL_PASS = os.getenv("EMAIL_PASS")

    if not all([EMAIL_USER, EMAIL_PASS, os.getenv("SUMMARIES_FOLDER")]):
        print("Error: Faltan variables de entorno necesarias.")
        return

    print(f"Generando contenido HTML para la semana: {fecha_resumen}")
    cuerpo_html_semanal, metadata = generar_html_semanal_completo(fecha_resumen)

    if cuerpo_html_semanal is None:
        print("No se pudo generar el contenido HTML semanal. Abortando.")
        return

    # Guardamos el HTML generado, como hacía tu función original
    try:
        os.makedirs(os.path.dirname(ruta_html_generado_para_web), exist_ok=True)
        with open(ruta_html_generado_para_web, "w", encoding="utf-8") as f:
            f.write(cuerpo_html_semanal)
        print(f"Contenido HTML para la web guardado en: {ruta_html_generado_para_web}")
    except Exception as e:
        print(f"No se pudo guardar el archivo HTML para la web: {e}")

    if not send_emails:
        print("Modo de prueba: No se enviarán correos. El contenido HTML se ha generado.")
        return

    # --- Lógica de envío (tu código original, casi sin cambios) ---
    if isinstance(correos_path, pd.DataFrame):
        df = correos_path
    else:
        df = pd.read_csv(correos_path)

    # Construir el asunto del correo usando los nuevos metadatos
    week_num = metadata.get('pontificate_week')
    asunto = f"✨Igles-IA #{week_num} | León XIV: {metadata.get('title', 'Resumen semanal')}"

    print(f"\nIniciando envío de correos con asunto: {asunto}")
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(EMAIL_USER, EMAIL_PASS)
            for _, row in df.iterrows():
                correo = row["email"]
                nombre = row.get("nombre", "amigo")

                msg = _crear_mensaje_email(
                    correo, nombre, asunto, cuerpo_html_semanal, ruta_plantilla_email
                )
                if msg:
                    smtp.send_message(msg)
                    print(f"Correo enviado a {correo}")
        print("\nTodos los correos procesados.")
    except Exception as e:
        print(f"Ocurrió un error durante el envío de correos: {e}")

# ==========================================================================
# 4. BLOQUE DE EJECUCIÓN (COMO EL TUYO)
# ==========================================================================
if __name__ == "__main__":
    # Esta lógica puede venir de tu script principal
    FECHA_DEL_RESUMEN = "2025-07-01" # Cambia esto a la fecha/carpeta que quieras procesar

    # Rutas que tu script original utilizaba
    RUTA_SALIDA_HTML_PARA_FLASK = "web/data/contenido_semanal_para_web.html"
    RUTA_CSV_EMAILS = "emails.csv"
    RUTA_PLANTILLA_EMAIL_HTML = "plantilla.html"

    print("--- Iniciando Proceso Semanal de Igles-IA ---")
    enviar_correos_todos(
        correos_path=RUTA_CSV_EMAILS,
        fecha_resumen=FECHA_DEL_RESUMEN,
        ruta_plantilla_email=RUTA_PLANTILLA_EMAIL_HTML,
        ruta_html_generado_para_web=RUTA_SALIDA_HTML_PARA_FLASK,
        send_emails=True # Poner en False para solo generar el HTML sin enviar
    )
    print("--- Proceso Semanal de Igles-IA Terminado ---")