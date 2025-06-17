import json
import os
import re
import smtplib
from datetime import datetime
from email.message import EmailMessage
from email.utils import formataddr

import markdown
import pandas as pd
from bs4 import BeautifulSoup
from dotenv import load_dotenv

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


def generar_y_guardar_contenido_html_semanal(fecha_resumen, ruta_output_html):
    """
    Genera el cuerpo HTML principal del contenido semanal y lo guarda en un archivo.
    Este contenido se usará tanto para la web Flask como para el cuerpo de los emails.
    """
    SUMMARIES_FOLDER = os.getenv("SUMMARIES_FOLDER")
    if not SUMMARIES_FOLDER:
        print("Error: La variable de entorno SUMMARIES_FOLDER no está configurada.")
        return None

    # Ruta a la carpeta específica de la fecha del resumen
    resumen_path_especifico = os.path.join(SUMMARIES_FOLDER, fecha_resumen)
    resumen_txt_path = os.path.join(
        resumen_path_especifico, "resumen_semanal_igles-ia.txt"
    )

    print(f"Buscando resumen principal en: {resumen_txt_path}")
    print(f"Buscando JSONs en directorio: {resumen_path_especifico}")

    # 1. Contenido principal del TXT
    resumen_principal_html = ""
    if os.path.exists(resumen_txt_path):
        with open(resumen_txt_path, "r", encoding="utf-8") as f:
            resumen_txt = f.read()
            print(f"Resumen principal encontrado: {resumen_txt}")
            # Markdown conversion happens first, then apply inline styles to the resulting HTML
            resumen_txt_converted = markdown.markdown(resumen_txt)
            print(f"Resumen principal convertido a HTML: {resumen_txt_converted}")
            resumen_principal_html = aplicar_estilos_html(resumen_txt_converted)
            print(f"Resumen principal con estilos aplicados: {resumen_principal_html}")
    else:
        print(
            f"Advertencia: No se encontró el archivo de resumen principal: {resumen_txt_path}"
        )
        resumen_principal_html = f"<p style='font-family:{DEFAULT_TEXT_FONT_FAMILY}; color:{DEFAULT_TEXT_COLOR};'>Resumen principal no disponible esta semana.</p>"

    # 2. Contenido extendido desde JSONs
    contenido_extra_html = construir_html_desde_jsons(resumen_path_especifico)

    # 3. Combinar todo
    cuerpo_completo_html = resumen_principal_html + contenido_extra_html

    # 4. Guardar en el archivo de salida
    try:
        os.makedirs(os.path.dirname(ruta_output_html), exist_ok=True)
        with open(ruta_output_html, "w", encoding="utf-8") as f:
            f.write(cuerpo_completo_html)
        print(f"Contenido HTML semanal guardado en: {ruta_output_html}")
        return cuerpo_completo_html
    except Exception as e:
        print(f"Error al guardar el contenido HTML semanal: {e}")
        return None


def _crear_mensaje_email(
    destinatario,
    nombre,
    fecha_resumen,
    cuerpo_html_para_email,
    ruta_plantilla_email,
    ruta_adjunto_wordcloud,
):
    """
    Crea el EmailMessage usando el cuerpo HTML pre-generado.
    """
    EMAIL_USER = os.getenv("EMAIL_USER")

    try:
        with open(ruta_plantilla_email, "r", encoding="utf-8") as f:
            html_email_template = f.read()
    except FileNotFoundError:
        print(f"Error: No se encontró la plantilla de email en {ruta_plantilla_email}")
        return None

    msg = EmailMessage()
    msg["Subject"] = f"Papa León XIV - Resumen semanal - {fecha_resumen}"
    msg["From"] = formataddr(("Igles IA", EMAIL_USER))
    msg["To"] = destinatario

    html_final_email = html_email_template.replace("{{nombre}}", nombre)
    html_final_email = html_final_email.replace("{{body}}", cuerpo_html_para_email)

    msg.add_alternative(html_final_email, subtype="html")

    return msg


def enviar_correos_todos(
    correos_path="emails.csv",
    fecha_resumen="2025-05-20",
    ruta_plantilla_email="plantilla.html",
    ruta_html_generado_para_web="data_web/contenido_semanal.html",
):
    """
    Función principal para generar el contenido una vez y luego enviar todos los correos.
    """
    EMAIL_USER = os.getenv("EMAIL_USER")
    EMAIL_PASS = os.getenv("EMAIL_PASS")
    SUMMARIES_FOLDER = os.getenv("SUMMARIES_FOLDER")

    if not all([EMAIL_USER, EMAIL_PASS, SUMMARIES_FOLDER]):
        print(
            "Error: Faltan variables de entorno necesarias (EMAIL_USER, EMAIL_PASS, SUMMARIES_FOLDER)."
        )
        return

    print("Generando contenido HTML semanal...")
    cuerpo_html_semanal = generar_y_guardar_contenido_html_semanal(
        fecha_resumen, ruta_html_generado_para_web
    )

    if cuerpo_html_semanal is None:
        print(
            "No se pudo generar el contenido HTML semanal. Abortando envío de correos."
        )
        return

    try:
        df = pd.read_csv(correos_path)
    except FileNotFoundError:
        print(f"Error: No se encontró el archivo de correos: {correos_path}")
        return

    ruta_adjunto_wordcloud = os.path.join(
        SUMMARIES_FOLDER, fecha_resumen, "wordcloud.png"
    )

    print(f"\nIniciando envío de correos para la fecha: {fecha_resumen}")
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(EMAIL_USER, EMAIL_PASS)
            for _, row in df.iterrows():
                correo = row["email"]
                nombre = row.get("nombre", "amigo")

                print(f"Preparando email para: {correo} con nombre: {nombre}")
                msg = _crear_mensaje_email(
                    correo,
                    nombre,
                    fecha_resumen,
                    cuerpo_html_semanal,
                    ruta_plantilla_email,
                    ruta_adjunto_wordcloud,
                )

                if msg:
                    smtp.send_message(msg)
                    print(f"Correo enviado a {correo}")
                else:
                    print(f"No se pudo crear el mensaje para {correo}. Saltando.")
        print("\nTodos los correos procesados.")
    except smtplib.SMTPAuthenticationError:
        print("Error de autenticación SMTP. Verifica EMAIL_USER y EMAIL_PASS.")
    except Exception as e:
        print(f"Ocurrió un error durante el envío de correos: {e}")


if __name__ == "__main__":
    FECHA_DEL_RESUMEN = "2025-05-20"

    RUTA_SALIDA_HTML_PARA_FLASK = "web/data/contenido_semanal_para_web.html"
    RUTA_CSV_EMAILS = "emails.csv"
    RUTA_PLANTILLA_EMAIL_HTML = "plantilla.html"

    print("--- Iniciando Proceso Semanal de Igles-IA ---")
    enviar_correos_todos(
        correos_path=RUTA_CSV_EMAILS,
        fecha_resumen=FECHA_DEL_RESUMEN,
        ruta_plantilla_email=RUTA_PLANTILLA_EMAIL_HTML,
        ruta_html_generado_para_web=RUTA_SALIDA_HTML_PARA_FLASK,
    )
    print("--- Proceso Semanal de Igles-IA Terminado ---")
