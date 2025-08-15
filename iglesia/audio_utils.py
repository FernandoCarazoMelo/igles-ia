import json
import os
import re
from collections import defaultdict
from datetime import datetime
from math import ceil

import boto3
from botocore.exceptions import NoCredentialsError

# --- Lógica de cálculo de la semana de pontificado ---
PONTIFICATE_START_DATE = datetime(2025, 5, 8)


def calculate_pontificate_week(run_date_str):
    """Calcula el número de semana del pontificado a partir de una fecha."""
    run_date = datetime.strptime(run_date_str, "%Y-%m-%d")
    delta = run_date - PONTIFICATE_START_DATE
    return (delta.days // 7) + 1


# --- FUNCIÓN 1: Generación de Metadatos con IA ---
def generar_metadatos_episodio(texto_limpio, episodio_info, llm_client):
    """
    Usa un LLM para generar un título dinámico y una descripción para un episodio.
    """
    print("🎙️  Generando título y descripción con IA...")
    try:
        fecha_dt = datetime.strptime(episodio_info["fecha"], "%Y-%m-%d")
        fecha_simple = fecha_dt.strftime("%d/%m")
        numero_formateado = (
            f"[{episodio_info['pontificate_week']}.{episodio_info['sub_index']}]"
        )

        prompt = f"""
        Eres un experto en comunicación para podcasts religiosos. 
        Basado en el siguiente texto, genera un título y una descripción optimizados para Spotify.
        El formato de salida DEBE ser un JSON válido con las claves "titulo_spotify" y "descripcion_spotify".
        REGLAS DEL TÍTULO:
        - El formato exacto debe ser: "{numero_formateado} {episodio_info["tipo"]} {fecha_simple} | [Tema principal en 3-5 palabras]"
        REGLAS DE LA DESCRIPCIÓN:
        - Debe ser un párrafo de 2-4 frases que resuma el mensaje central del Papa León XIV. Empieza diciendo en este/a {episodio_info["tipo"]} el Papa León XIV... Termina diciendo \n\n'Podcast creado por igles-ia.es'
        TEXTO DEL DOCUMENTO:
        ---
        {texto_limpio[:4000]}
        ---
        """
        respuesta_llm = llm_client.call(prompt)
        json_match = re.search(r"\{.*\}", respuesta_llm, re.DOTALL)
        if not json_match:
            raise ValueError("La respuesta del LLM no contenía un JSON válido.")

        metadata = json.loads(json_match.group(0))
        print(f"  -> Título generado: {metadata['titulo_spotify']}")
        return metadata

    except Exception as e:
        print(
            f"❌ Error al generar metadatos con LLM: {e}. Se usarán valores por defecto."
        )
        return {
            "titulo_spotify": f"[{episodio_info['pontificate_week']}.{episodio_info['sub_index']}] {episodio_info['tipo']} del {episodio_info['fecha']}",
            "descripcion_spotify": texto_limpio[:250] + "...",
        }


# --- FUNCIÓN 2: Síntesis y Subida de Audio ---
def sintetizar_y_subir_audio(
    texto_limpio, filename_base, s3_client, polly_client, bucket_name
):
    def synthesize_speech(text):
        def split_text(t, max_length=3000):
            return [
                t[i * max_length : (i + 1) * max_length]
                for i in range(ceil(len(t) / max_length))
            ]

        audio_streams = []
        for chunk in split_text(text):
            try:
                response = polly_client.synthesize_speech(
                    Text=chunk,
                    LanguageCode="es-ES",
                    OutputFormat="mp3",
                    VoiceId="Raul",
                    Engine="long-form",
                )
                audio_streams.append(response["AudioStream"].read())
            except Exception as e:
                print(f"  -> Error con Polly al sintetizar: {e}")
                return None
        return b"".join(audio_streams)

    print("🔊 Generando audio con Polly...")
    audio_data = synthesize_speech(texto_limpio)
    if not audio_data:
        return None
    try:
        filename_mp3 = filename_base + ".mp3"
        print(f"☁️  Subiendo '{filename_mp3}' a S3...")
        s3_client.put_object(
            Bucket=bucket_name,
            Key=filename_mp3,
            Body=audio_data,
            ContentType="audio/mpeg",
        )
        region = (
            s3_client.get_bucket_location(Bucket=bucket_name)["LocationConstraint"]
            or "us-east-1"
        )
        url = f"https://{bucket_name}.s3.{region}.amazonaws.com/{filename_mp3}"
        print(f"  -> Audio disponible en: {url}")
        return url
    except Exception as e:
        print(f"❌ Error al subir a S3: {e}")
        return None


# --- FUNCIÓN PRINCIPAL ORQUESTADORA ---
def procesar_y_generar_episodios(json_file_path, llm_client):
    print("Iniciando proceso de generación de episodios...")
    try:
        S3_BUCKET_NAME = os.environ["S3_BUCKET_NAME"]
        polly = boto3.client("polly", region_name="us-east-1")
        s3 = boto3.client("s3")
    except (KeyError, NoCredentialsError) as e:
        print(f"❌ Error de configuración de AWS: {e}")
        return []

    if not os.path.exists(json_file_path):
        print(f"❌ Error: El archivo JSON no se encuentra en: {json_file_path}")
        return []
    with open(json_file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    episodios_por_semana = defaultdict(list)
    for episodio in data.values():
        pontificate_week = calculate_pontificate_week(episodio["fecha"])
        episodio["pontificate_week"] = pontificate_week
        episodios_por_semana[pontificate_week].append(episodio)

    for semana in episodios_por_semana:
        episodios_por_semana[semana].sort(key=lambda x: x["fecha"])
        for i, episodio in enumerate(episodios_por_semana[semana]):
            episodio["sub_index"] = i + 1

    episodios_procesados = []
    todos_los_episodios = [
        ep for semana in episodios_por_semana.values() for ep in semana
    ]
    todos_los_episodios.sort(key=lambda x: (x["pontificate_week"], x["sub_index"]))

    for episodio in todos_los_episodios:
        print(
            f"\n--- Procesando episodio {episodio['pontificate_week']}.{episodio['sub_index']}: {episodio['filename']} ---"
        )
        texto_original = episodio["texto"]
        match = re.search(
            r"(queridos.*)", texto_original, flags=re.IGNORECASE | re.DOTALL
        )
        texto_limpio = match.group(1) if match else texto_original
        texto_limpio = re.sub(r"\([^)]*\)|_|\s+", " ", texto_limpio).strip()
        texto_limpio = re.split(
            r"Saludos|Después del Ángelus", texto_limpio, flags=re.IGNORECASE
        )[0]

        metadata = generar_metadatos_episodio(texto_limpio, episodio, llm_client)
        url_audio = sintetizar_y_subir_audio(
            texto_limpio, episodio["filename"], s3, polly, S3_BUCKET_NAME
        )

        if url_audio:
            episodios_procesados.append(
                {
                    "titulo_original": episodio["titulo"],
                    "titulo_spotify": metadata["titulo_spotify"],
                    "descripcion_spotify": metadata["descripcion_spotify"],
                    "url_audio": url_audio,
                    "fecha": episodio["fecha"],
                    "filename": episodio["filename"],
                    "tipo": episodio["tipo"],
                    "numero_episodio": f"{episodio['pontificate_week']}.{episodio['sub_index']}",
                }
            )

    print("\nProceso finalizado.")
    return episodios_procesados


# ==========================================================================
# BLOQUE DE TEST
# ==========================================================================
if __name__ == "__main__":
    from crewai import LLM
    from dotenv import find_dotenv, load_dotenv

    print("*" * 50)
    print("EJECUTANDO SCRIPT EN MODO DE TEST REAL")
    print("*" * 50)

    # 1. Cargar variables de entorno (OPENAI_API_KEY, S3_BUCKET_NAME, etc.)
    load_dotenv(find_dotenv())

    # 2. Definir la fecha para la prueba
    FECHA_TEST = "2025-08-16"

    # 3. Construir la ruta al archivo JSON que debería haber generado el pipeline principal
    # Asegúrate de que este archivo exista antes de ejecutar el test.
    json_input_path = f"json-rss/{FECHA_TEST}/episodes.json"

    print(f"Buscando archivo de entrada en: {json_input_path}")

    if not os.path.exists(json_input_path):
        print(f"❌ Error: El archivo de entrada '{json_input_path}' no existe.")
        print(
            "Asegúrate de ejecutar primero el pipeline principal (ej: pipeline-date) para esta fecha."
        )
    else:
        # 4. Inicializar el cliente LLM real
        print("Inicializando cliente LLM real (gpt-4.1-nano)...")
        llm_real = LLM(model="gpt-4.1-nano")

        # 5. Llamar a la función principal con los datos reales
        resultados = procesar_y_generar_episodios(json_input_path, llm_real)

        # 6. Imprimir y guardar los resultados
        if resultados:
            print("\n\n--- RESULTADOS DEL TEST ---")
            print(json.dumps(resultados, indent=4, ensure_ascii=False))
            print("---------------------------")

            # Guardar los metadatos en el archivo correspondiente
            output_metadata_path = f"json-rss/{FECHA_TEST}/episodes_metadata.json"
            print(f"Guardando metadatos en: {output_metadata_path}")
            with open(output_metadata_path, "w", encoding="utf-8") as f:
                json.dump(resultados, f, ensure_ascii=False, indent=4)
            print("✅ Metadatos guardados.")
        else:
            print("\n\n--- EL TEST NO PRODUJO RESULTADOS ---")
