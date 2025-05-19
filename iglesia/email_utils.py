import os
import smtplib
from email.message import EmailMessage
from email.utils import formataddr

import pandas as pd
from dotenv import load_dotenv

load_dotenv()
# Función para crear el correo
import json


def construir_html_desde_jsons(directorio):
    html = ""
    for archivo in os.listdir(directorio):
        if archivo.endswith(".json"):
            path = os.path.join(directorio, archivo)
            with open(path, "r", encoding="utf-8") as f:
                datos = json.load(f)
            html += f"""
            <hr style="margin:30px 0;">
            <h3 style="color:#003366;">📄 {datos['fuente_documento']}</h3>
            <p style="font-size:15px; color:#444;"><strong>Tipo:</strong> {datos['tipo_documento']}</p>
            <p style="font-size:15px; color:#333;">{datos['resumen_general']}</p>
            <ul style="color:#333; font-size:15px;">
            """
            for idea in datos["ideas_clave"]:
                html += f"<li>{idea}</li>"
            html += "</ul><p>"
            for tag in datos["tags_sugeridos"]:
                html += f"""<span style="background-color:#003366;color:white;padding:5px 10px;border-radius:15px;font-size:12px;margin:2px;display:inline-block;">#{tag}</span> """
            html += "</p>"
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
        resumen_principal = f"<p style='font-size:16px; color:#333;'>{f.read().replace('\\n\\n', '</p><p style=\"font-size:16px; color:#333;\">')}</p>"

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