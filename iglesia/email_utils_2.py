import json
import os
import re
import smtplib
from datetime import datetime
from email.message import EmailMessage
from email.utils import formataddr

import pandas as pd
from dotenv import load_dotenv

load_dotenv()

# --- Tus funciones de conversión (sin cambios) ---
def convertir_txt_a_html(texto_plano):
    html = ""
    bloques = re.split(r"\n\s*\n", texto_plano.strip())
    for bloque in bloques:
        bloque = bloque.strip()
        bloque = re.sub(
            r'\[(.*?)\]\((https?://[^\s]+)\)',
            r'<a href="\2" style="color:#003366;text-decoration:none;" target="_blank">\1</a>',
            bloque
        )
        if bloque.startswith("- "):
            items = [f"<li>{item[2:].strip()}</li>" for item in bloque.split("\n") if item.startswith("- ")]
            html += f"<ul style='font-size:15px; color:#333;'>{''.join(items)}</ul>\n"
        else:
            bloque = bloque.replace("\n", " ")
            html += f"<p style='font-size:15px; color:#333;'>{bloque}</p>\n"
    return html

def construir_html_desde_jsons(directorio_jsons):
    documentos = []
    if not os.path.exists(directorio_jsons) or not os.path.isdir(directorio_jsons):
        print(f"Advertencia: El directorio de JSONs no existe o no es un directorio: {directorio_jsons}")
        return "" # Devuelve string vacío si no hay directorio

    # Recolectar todos los documentos primero
    for archivo in sorted(os.listdir(directorio_jsons)):
        if archivo.endswith(".json"):
            path = os.path.join(directorio_jsons, archivo)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    datos = json.load(f)
            except Exception as e:
                print(f"Error al leer o parsear el JSON {archivo}: {e}")
                continue # Saltar este archivo

            match = re.search(r"(\d{8})", archivo)
            if match:
                fecha_raw = match.group(1)
                try:
                    fecha_formateada = datetime.strptime(fecha_raw, "%Y%m%d").strftime("%d/%m/%Y")
                except ValueError:
                    fecha_formateada = None
            else:
                fecha_formateada = None

            documentos.append({
                "id": archivo.replace(".json", "").replace(".", "_").replace(" ", "_"),
                "titulo": datos.get("fuente_documento", "Documento sin título"),
                "url": datos.get("url_original", "#"),
                "tipo": datos.get("tipo_documento", "Desconocido"),
                "resumen": datos.get("resumen_general", ""),
                "ideas": datos.get("ideas_clave", []),
                "tags": datos.get("tags_sugeridos", []),
                "fecha": fecha_formateada,
            })
    
    if not documentos:
        return "<p>No se encontraron documentos JSON válidos para mostrar.</p>"
    else:
        documentos.reverse()
    
    html_idx = """
    <h2 style="color:#003366; font-family: 'Montserrat', sans-serif;">📚 Índice de Documentos</h2>
    <ul style="font-size:15px; color:#003366; list-style-type: none; padding-left: 0;">
    """
    for doc in documentos:
        texto_link = f"{doc['tipo']}: {doc['titulo']}" + (f" ({doc['fecha']})" if doc["fecha"] else "")
        html_idx += f"""<li style="margin-bottom: 8px;"><a href="#{doc['id']}" style="color:#003366;text-decoration:none; font-weight:bold;">🔗 {texto_link}</a></li>"""
    html_idx += "</ul><hr style='border:0; height:1px; background-color:#e0e0e0; margin: 40px 0;'>"

    html_docs = ""
    for doc in documentos:
        html_docs += f"""
        <article id="{doc['id']}" style="margin-bottom: 30px;">
          <h3 style="color:#003366; font-family: 'Montserrat', sans-serif;">
            <a href="{doc['url']}" style="color:#003366; text-decoration:none;" target="_blank">📄 {doc['titulo']}</a>
          </h3>
          <p style="font-size:14px; color:#444;">
            <strong>Tipo:</strong> {doc['tipo']} |
            <strong>Texto original:</strong> <a href="{doc['url']}" style="color:#003373; text-decoration:none;" target="_blank">Link</a>
            """
        if doc["fecha"]:
            html_docs += f" | <strong>Fecha:</strong> {doc['fecha']}"
        html_docs += "</p>"
        
        resumen_doc_html = ""
        if doc['resumen']:
            resumen_doc_html = convertir_txt_a_html(doc['resumen'])
        html_docs += resumen_doc_html

        if doc["ideas"]:
            html_docs += """<h4 style="color:#003366; font-size: 16px; margin-top:15px; margin-bottom:5px; font-family: 'Montserrat', sans-serif;">Ideas Clave:</h4>
            <ul style="color:#333; font-size:15px; list-style-position: outside; padding-left: 20px;">"""
            for idea in doc["ideas"]:
                idea_html = convertir_txt_a_html(idea).replace('<p style=\'font-size:15px; color:#333;\'>', '').replace('</p>\n', '')
                html_docs += f"<li>{idea_html}</li>"
            html_docs += "</ul>"

        if doc["tags"]:
            html_docs += "<p style='margin-top:15px;'>"
            for tag in doc["tags"]:
                html_docs += f"""<span style="background-color:#003366;color:white;padding:5px 10px;border-radius:15px;font-size:12px;margin:2px 4px 2px 0;display:inline-block;">#{tag}</span> """
            html_docs += "</p>"
        html_docs += "</article><hr style='border:0; height:1px; background-color:#e0e0e0; margin: 40px 0;'>"
    
    if html_docs.endswith("<hr style='border:0; height:1px; background-color:#e0e0e0; margin: 40px 0;'>"):
        html_docs = html_docs[:-len("<hr style='border:0; height:1px; background-color:#e0e0e0; margin: 40px 0;'>")]
    return html_idx + html_docs
# --- Fin de tus funciones de conversión ---


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
    resumen_txt_path = os.path.join(resumen_path_especifico, "resumen_semanal_igles-ia.txt")

    print(f"Buscando resumen principal en: {resumen_txt_path}")
    print(f"Buscando JSONs en directorio: {resumen_path_especifico}")

    # 1. Contenido principal del TXT
    resumen_principal_html = ""
    if os.path.exists(resumen_txt_path):
        with open(resumen_txt_path, "r", encoding="utf-8") as f:
            resumen_txt = f.read()
            resumen_principal_html = convertir_txt_a_html(resumen_txt)
    else:
        print(f"Advertencia: No se encontró el archivo de resumen principal: {resumen_txt_path}")
        resumen_principal_html = "<p>Resumen principal no disponible esta semana.</p>"

    # 2. Contenido extendido desde JSONs
    # La función construir_html_desde_jsons ya usa el directorio resumen_path_especifico
    contenido_extra_html = construir_html_desde_jsons(resumen_path_especifico)

    # 3. Combinar todo

    # 3. Combinar todo
    estilo_negrita = "<style> b { color: #003366; } </style>\n"
    cuerpo_completo_html = estilo_negrita + resumen_principal_html + contenido_extra_html
    
    # 4. Guardar en el archivo de salida
    try:
        # Asegurarse de que el directorio de salida exista
        os.makedirs(os.path.dirname(ruta_output_html), exist_ok=True)
        with open(ruta_output_html, "w", encoding="utf-8") as f:
            f.write(cuerpo_completo_html)
        print(f"Contenido HTML semanal guardado en: {ruta_output_html}")
        return cuerpo_completo_html
    except Exception as e:
        print(f"Error al guardar el contenido HTML semanal: {e}")
        return None


def _crear_mensaje_email(destinatario, nombre, fecha_resumen, cuerpo_html_para_email, ruta_plantilla_email, ruta_adjunto_wordcloud):
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

    # Reemplazar placeholders en la plantilla del email
    html_final_email = html_email_template.replace("{{nombre}}", nombre)
    html_final_email = html_final_email.replace("{{body}}", cuerpo_html_para_email)

    # Adjuntar archivo png (wordcloud)
    # if os.path.exists(ruta_adjunto_wordcloud):
    #     with open(ruta_adjunto_wordcloud, "rb") as f:
    #         img_data = f.read()
    #         msg.add_attachment(img_data, maintype="image", subtype="png", filename="wordcloud.png")
    # else:
    #     print(f"Advertencia: No se encontró el archivo wordcloud.png en {ruta_adjunto_wordcloud}")
        
    msg.add_alternative(html_final_email, subtype="html")
    
    return msg


def enviar_correos_todos(correos_path="emails.csv", fecha_resumen="2025-05-20",
                         ruta_plantilla_email="plantilla.html", 
                         ruta_html_generado_para_web="data_web/contenido_semanal.html"):
    """
    Función principal para generar el contenido una vez y luego enviar todos los correos.
    """
    EMAIL_USER = os.getenv("EMAIL_USER")
    EMAIL_PASS = os.getenv("EMAIL_PASS")
    SUMMARIES_FOLDER = os.getenv("SUMMARIES_FOLDER")

    if not all([EMAIL_USER, EMAIL_PASS, SUMMARIES_FOLDER]):
        print("Error: Faltan variables de entorno necesarias (EMAIL_USER, EMAIL_PASS, SUMMARIES_FOLDER).")
        return

    # Paso 1: Generar y guardar el contenido HTML una vez
    print("Generando contenido HTML semanal...")
    cuerpo_html_semanal = generar_y_guardar_contenido_html_semanal(fecha_resumen, ruta_html_generado_para_web)

    if cuerpo_html_semanal is None:
        print("No se pudo generar el contenido HTML semanal. Abortando envío de correos.")
        return

    # Paso 2: Preparar para enviar correos
    try:
        df = pd.read_csv(correos_path)  # columnas: email,nombre
    except FileNotFoundError:
        print(f"Error: No se encontró el archivo de correos: {correos_path}")
        return

    ruta_adjunto_wordcloud = os.path.join(SUMMARIES_FOLDER, fecha_resumen, "wordcloud.png")

    print(f"\nIniciando envío de correos para la fecha: {fecha_resumen}")
    # Enviar correos
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(EMAIL_USER, EMAIL_PASS)
            for _, row in df.iterrows():
                correo = row["email"]
                nombre = row.get("nombre", "amigo") # Usa "amigo" si no hay nombre
                
                print(f"Preparando email para: {correo} con nombre: {nombre}")
                msg = _crear_mensaje_email(correo, nombre, fecha_resumen, cuerpo_html_semanal, ruta_plantilla_email, ruta_adjunto_wordcloud)
                
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
    # --- Configuración ---
    # Asegúrate de que estas rutas sean correctas para tu estructura
    FECHA_DEL_RESUMEN = "2025-05-20" # Cambia esto cada semana o pásalo como argumento
    
    # Ruta donde se guardará el HTML que también usará Flask.
    # Ejemplo: si este script está en 'scripts_email/' y Flask en 'igles-ia-flask/',
    # podría ser '../igles-ia-flask/data/contenido_semanal_para_web.html'
    RUTA_SALIDA_HTML_PARA_FLASK = "web/data/contenido_semanal_para_web.html" # Ajusta esta ruta

    # Ruta al archivo CSV con los emails
    RUTA_CSV_EMAILS = "emails.csv" # Asegúrate que este archivo exista

    # Ruta a tu plantilla HTML para el email (la que tiene {{nombre}} y {{body}})
    RUTA_PLANTILLA_EMAIL_HTML = "plantilla.html" # Asegúrate que este archivo exista
    # --- Fin Configuración ---

    print("--- Iniciando Proceso Semanal de Igles-IA ---")
    enviar_correos_todos(
        correos_path=RUTA_CSV_EMAILS,
        fecha_resumen=FECHA_DEL_RESUMEN,
        ruta_plantilla_email=RUTA_PLANTILLA_EMAIL_HTML,
        ruta_html_generado_para_web=RUTA_SALIDA_HTML_PARA_FLASK
    )
    print("--- Proceso Semanal de Igles-IA Terminado ---")
