import json
import os
import re
from math import ceil

import boto3
from botocore.exceptions import NoCredentialsError


def procesar_json_y_subir_a_s3(json_file_path):
    """
    Lee un archivo JSON, genera los audios correspondientes con Polly y los sube a S3.

    Args:
        json_file_path (str): La ruta al archivo JSON que se va a procesar.

    Returns:
        list: Una lista de las URLs públicas de S3 de los archivos creados.
              Devuelve una lista vacía si ocurre un error.
    """
    # --- 1. Configuración y Clientes de AWS ---
    print("Iniciando proceso de generación y subida de audios...")
    try:
        S3_BUCKET_NAME = os.environ["S3_BUCKET_NAME"]
        polly = boto3.client("polly", region_name="us-east-1")
        s3 = boto3.client("s3")
    except KeyError:
        print("❌ Error: La variable de entorno S3_BUCKET_NAME no está configurada.")
        return []
    except NoCredentialsError:
        print("❌ Error: Credenciales de AWS no encontradas.")
        return []   

    # --- 2. Lectura y Validación del Archivo JSON ---
    if not os.path.exists(json_file_path):
        print(f"❌ Error: El archivo JSON no se encuentra en la ruta: {json_file_path}")
        return []

    with open(json_file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # --- 3. Funciones Ayudantes (Anidadas) ---
    def split_text(text, max_length=3000):
        num_chunks = ceil(len(text) / max_length)
        return [text[i * max_length : (i + 1) * max_length] for i in range(num_chunks)]

    def synthesize_speech(text):
        chunks = split_text(text)
        audio_streams = []
        for chunk in chunks:
            try:
                response = polly.synthesize_speech(
                    Text=chunk,
                    LanguageCode="es-ES",
                    OutputFormat="mp3",
                    VoiceId="Raul",
                    Engine="long-form",
                )
                audio_streams.append(response["AudioStream"].read())
            except Exception as e:
                print(f"Error con Polly al sintetizar un fragmento: {e}")
                return None
        return b"".join(audio_streams)

    # --- 4. Bucle Principal de Procesamiento ---
    urls_generadas = []
    for idx in range(len(data["titulo"])):
        titulo = data["titulo"][str(idx)]
        texto = data["texto"][str(idx)]
        filename = data["filename"][str(idx)] + ".mp3"

        # Limpieza de texto
        match = re.search(r"(queridos.*)", texto, flags=re.IGNORECASE | re.DOTALL)
        if match:
            texto = match.group(1)
        texto = re.sub(r"\([^)]*\)", "", texto)
        texto = texto.strip()
        texto = re.sub(r"\s+", " ", texto).strip()
        texto = re.split(r"Saludos|Después del Ángelus", texto, flags=re.IGNORECASE)[0]
        texto = re.sub(r"_", "", texto).strip()

        # Generar audio
        print(f"\nGenerando audio para: {filename}...")
        audio_data = synthesize_speech(texto)

        # Subir a S3
        if audio_data:
            try:
                print(f"Subiendo '{filename}' al bucket '{S3_BUCKET_NAME}'...")
                s3.put_object(
                    Bucket=S3_BUCKET_NAME,
                    Key=filename,
                    Body=audio_data,
                    ContentType="audio/mpeg",
                )
                region = (
                    s3.get_bucket_location(Bucket=S3_BUCKET_NAME)["LocationConstraint"]
                    or "us-east-1"
                )
                url = f"https://{S3_BUCKET_NAME}.s3.{region}.amazonaws.com/{filename}"
                urls_generadas.append(url)
                print(f"✅ Archivo subido con éxito a: {url}")
            except Exception as e:
                print(f"❌ Error al subir a S3: {e}")
                # Continuar con el siguiente archivo en lugar de detener todo
                continue

    print("\nProceso finalizado.")
    return urls_generadas


# ==========================================================================
# BLOQUE DE EJECUCIÓN
# ==========================================================================
if __name__ == "__main__":
    # Esta parte solo se ejecuta cuando corres el script directamente
    # desde la terminal.

    # 1. Define la ruta al archivo JSON que quieres procesar
    JSON_A_PROCESAR = "./json-rss/2025-08-15/iglesia.json"

    # 2. Llama a la función principal
    lista_de_urls = procesar_json_y_subir_a_s3(JSON_A_PROCESAR)

    # 3. Muestra los resultados
    if lista_de_urls:
        print("\n--- URLs de los audios generados ---")
        for url in lista_de_urls:
            print(url)
        print("------------------------------------")
