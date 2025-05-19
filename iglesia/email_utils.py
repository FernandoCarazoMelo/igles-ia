import os
import smtplib
from email.message import EmailMessage
from email.utils import formataddr

import pandas as pd
from dotenv import load_dotenv

load_dotenv()
# Función para crear el correo
import json
import re
from datetime import datetime


def convertir_txt_a_html(texto_plano):
    html = ""
    bloques = re.split(r"\n\s*\n", texto_plano.strip())

    for bloque in bloques:
        bloque = bloque.strip()
        
        # Convertir links estilo markdown
        bloque = re.sub(
            r'\[(.*?)\]\((https?://[^\s]+)\)',
            r'<a href="\2" style="color:#003366;text-decoration:none;" target="_blank">\1</a>',
            bloque
        )

        # Detectar listas
        if bloque.startswith("- "):
            items = [f"<li>{item[2:].strip()}</li>" for item in bloque.split("\n") if item.startswith("- ")]
            html += f"<ul style='font-size:15px; color:#333;'>{''.join(items)}</ul>\n"
        else:
            bloque = bloque.replace("\n", " ")  # Unir líneas rotas dentro del párrafo
            html += f"<p style='font-size:15px; color:#333;'>{bloque}</p>\n"

    return html



def construir_html_desde_jsons(directorio):
    documentos = []

    # Recolectar todos los documentos primero
    for archivo in sorted(os.listdir(directorio)):
        if archivo.endswith(".json"):
            path = os.path.join(directorio, archivo)
            with open(path, "r", encoding="utf-8") as f:
                datos = json.load(f)

            # Intentar extraer fecha del nombre del archivo si no está explícita
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
                "id": archivo.replace(".json", ""),  # para usar como ancla
                "titulo": datos.get("fuente_documento", "Documento sin título"),
                "url": datos.get("url_original", "#"),
                "tipo": datos.get("tipo_documento", "Desconocido"),
                "resumen": datos.get("resumen_general", ""),
                "ideas": datos.get("ideas_clave", []),
                "tags": datos.get("tags_sugeridos", []),
                "fecha": fecha_formateada,
            })

    # Construir índice
    html = """
    <h2 style="color:#003366;">📚 Índice de Documentos</h2>
    <ul style="font-size:15px; color:#003366;">
    """
    for doc in documentos:
        texto_link = f"{doc['titulo']}" + (f" ({doc['fecha']})" if doc["fecha"] else "")
        html += f"""<li><a href="#{doc['id']}" style="color:#003366;text-decoration:none;">🔗 {texto_link}</a></li>"""
    html += "</ul><hr style='margin:30px 0;'>"

    # Cuerpo con cada documento
    for doc in documentos:
        html += f"""
        <h3 id="{doc['id']}" style="color:#003366;">
          <a href="{doc['url']}" style="color:#003366; text-decoration:none;" target="_blank">📄 {doc['titulo']}</a>
        </h3>
        <p style="font-size:14px; color:#444;">
          <strong>Tipo:</strong> {doc['tipo']}"""
        if doc["fecha"]:
            html += f" | <strong>Fecha:</strong> {doc['fecha']}"
        html += "</p>"

        html += f"""<p style="font-size:15px; color:#333;">{doc['resumen']}</p>
        <ul style="color:#333; font-size:15px;">"""
        for idea in doc["ideas"]:
            html += f"<li>{idea}</li>"
        html += "</ul>"

        # Tags
        html += "<p>"
        for tag in doc["tags"]:
            html += f"""<span style="background-color:#003366;color:white;padding:5px 10px;border-radius:15px;font-size:12px;margin:2px;display:inline-block;">#{tag}</span> """
        html += "</p><hr style='margin:30px 0;'>"

    return html

def _crear_mensaje(destinatario, nombre, fecha_resumen="2025-05-19"):
    EMAIL_USER = os.getenv("EMAIL_USER")
    EMAIL_PASS = os.getenv("EMAIL_PASS")
    SUMMARIES_FOLDER = os.getenv("SUMMARIES_FOLDER")

    resumen_path = os.path.join(SUMMARIES_FOLDER, fecha_resumen)
    resumen_txt_path = os.path.join(resumen_path, "resumen_semanal_igles-ia.txt")

    with open("plantilla.html", "r", encoding="utf-8") as f:
        html_template = f.read()

    msg = EmailMessage()
    msg["Subject"] = f"Papa León XIV - Resumen semanal - {fecha_resumen}"
    msg["From"] = formataddr(("Igles IA", EMAIL_USER))
    msg["To"] = destinatario

    # Contenido principal
    with open(resumen_txt_path, "r", encoding="utf-8") as f:
        resumen_txt = f.read()
        resumen_principal = convertir_txt_a_html(resumen_txt)


    # Contenido extendido desde JSONs
    contenido_extra = construir_html_desde_jsons(resumen_path)

    # Combinar todo
    cuerpo_completo = resumen_principal + contenido_extra

    html_con_nombre = html_template.replace("{{nombre}}", nombre)
    html_con_nombre = html_con_nombre.replace("{{body}}", cuerpo_completo)

    msg.add_alternative(html_con_nombre, subtype="html")
    return msg


def enviar_correos(correos_path="emails.csv"):
    df = pd.read_csv(correos_path)  # columnas: email,nombre
    EMAIL_USER = os.getenv("EMAIL_USER")
    EMAIL_PASS = os.getenv("EMAIL_PASS")
    # Enviar correos
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL_USER, EMAIL_PASS)
        for _, row in df.iterrows():
            correo = row["email"]
            nombre = row.get("nombre", "amigo")
            msg = _crear_mensaje(correo, nombre)
            smtp.send_message(msg)
            print(f"Correo enviado a {correo}")

if __name__ == "__main__":
    print("hi!")
    enviar_correos()