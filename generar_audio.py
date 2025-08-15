import json
import re
from math import ceil

import boto3

# Configuración AWS (asegúrate de tener credenciales configuradas en tu máquina)
polly = boto3.client("polly", region_name="us-east-1")

# Archivo JSON de entrada
JSON_FILE = "../summaries-local/2025-08-15/iglesia.json"

# Carpeta donde guardar los MP3
OUTPUT_FOLDER = "audio/"

# Leer JSON
with open(JSON_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)


def split_text(text, max_length=3000):
    """
    Divide el texto en fragmentos que no superen el límite de longitud.
    """
    # Calcula el número de fragmentos necesarios
    num_chunks = ceil(len(text) / max_length)
    return [text[i * max_length : (i + 1) * max_length] for i in range(num_chunks)]


def synthesize_speech(text):
    """
    Sintetiza el texto en fragmentos que cumplen con los límites de longitud.
    """
    chunks = split_text(text)
    audio_streams = []

    for chunk in chunks:
        try:
            response = polly.synthesize_speech(
                Text=chunk,
                LanguageCode="es-ES",
                OutputFormat="mp3",
                VoiceId="Raul",
                Engine="long-form",  # mejor calidad
            )
            audio_streams.append(response["AudioStream"].read())
        except polly.exceptions.TextLengthExceededException as e:
            print(f"Error: {e}")
            break

    # Combina los fragmentos de audio en un solo flujo
    audio_data = b"".join(audio_streams)
    return audio_data


for idx in range(len(data["titulo"])):
    titulo = data["titulo"][str(idx)]
    texto = data["texto"][str(idx)]
    filename = data["filename"][str(idx)] + ".mp3"

    # 1) Cortar desde "queridos..."
    match = re.search(r"(queridos.*)", texto, flags=re.IGNORECASE | re.DOTALL)
    if match:
        texto = match.group(1)

    # 2) Eliminar números y paréntesis
    texto = re.sub(r"\([^)]*\)", "", texto)  # elimina contenido entre paréntesis
    texto = re.sub(r"\d+", "", texto)  # elimina dígitos restantes
    texto = texto.strip()
    # 3) Eliminar espacios dobles y limpiar
    texto = re.sub(r"\s+", " ", texto).strip()
    texto = re.split(r"Saludos", texto, flags=re.IGNORECASE)[0]
    texto = re.split(r"Después del Ángelus", texto, flags=re.IGNORECASE)[0]
    texto = re.sub(r"_", "", texto).strip()

    # 4) Generar audio con AWS Polly
    audio_data = synthesize_speech(texto)

    # Guardar el archivo MP3
    with open(OUTPUT_FOLDER + filename, "wb") as f_audio:
        f_audio.write(audio_data)

    print(f"✅ Audio generado: {filename}")
