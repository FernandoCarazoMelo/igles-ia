import json
import math
import os
import re
from pathlib import Path

import pandas as pd  # Usaremos pandas para manejar los datos fácilmente
from dotenv import load_dotenv
from supabase import Client, create_client
from tqdm import tqdm

load_dotenv()

# --- Configuración de Supabase ---
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    print("Error: Faltan las variables de entorno SUPABASE_URL o SUPABASE_SERVICE_KEY.")
    exit()

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
# ---------------------------------

# Regex para extraer el 'slug' (ej. 20251026...) y el 'idioma' (ej. 'es') de la URL
URL_REGEX = re.compile(r"/([a-z]{2})/.*/documents/([^/]+)$")


def select_all_data(table_name: str, select_query: str) -> list:
    """Obtiene TODOS los registros de una tabla, manejando paginación."""
    all_data = []
    page = 0
    page_size = 1000
    print(f"Iniciando descarga completa de '{table_name}'...")
    while True:
        try:
            start_index = page * page_size
            end_index = (page + 1) * page_size - 1
            response = (
                supabase.table(table_name)
                .select(select_query)
                .range(start_index, end_index)
                .execute()
            )
            if not response.data:
                break
            all_data.extend(response.data)
            if len(response.data) < page_size:
                break
            page += 1
        except Exception as e:
            print(f"❌ Error durante la paginación de {table_name}: {e}")
            break
    print(f"✅ Se obtuvieron {len(all_data)} filas en total de '{table_name}'.")
    return all_data


def extract_slug_lang_from_url(url: str) -> tuple[str | None, str | None]:
    """Extrae el vatican_slug y el idioma de la URL usando regex."""
    if not url or not isinstance(url, str):
        return None, None
    match = URL_REGEX.search(url)
    if match:
        idioma = match.group(1)
        vatican_slug = match.group(2)
        return vatican_slug, idioma
    else:
        print(f"⚠️ URL no coincide con el patrón esperado: {url}")
        return None, None


def batch_upsert(table_name: str, data: list, on_conflict: str, chunk_size: int = 500):
    """Función genérica para hacer upsert en lotes."""
    if not data:
        print(f"No hay datos para insertar/actualizar en {table_name}.")
        return
    total_chunks = math.ceil(len(data) / chunk_size)
    print(
        f"Iniciando carga en lotes para '{table_name}'. Total: {len(data)} filas en {total_chunks} lotes."
    )
    for i in tqdm(range(0, len(data), chunk_size), desc=f"Actualizando {table_name}"):
        chunk = data[i : i + chunk_size]
        try:
            supabase.table(table_name).upsert(chunk, on_conflict=on_conflict).execute()
        except Exception as e:
            print(f"❌ Error en el lote {i // chunk_size + 1} para {table_name}: {e}")
            print(f"    Pista: {e}")


# --- Punto de Entrada Principal ---
if __name__ == "__main__":
    BASE_DIR = Path("json-rss")
    print(
        f"Buscando archivos 'episodes_metadata.json' en subcarpetas de: {BASE_DIR.resolve()}"
    )

    # 1. Encontrar y leer todos los JSON
    all_episodes = []
    json_files = list(BASE_DIR.glob("**/episodes_metadata.json"))

    if not json_files:
        print("No se encontraron archivos 'episodes_metadata.json'.")
        exit()

    print(f"Se encontraron {len(json_files)} archivos JSON.")
    for file_path in json_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    all_episodes.extend(data)
                elif isinstance(data, dict):
                    all_episodes.append(data)
        except Exception as e:
            print(f"⚠️ Error leyendo {file_path}: {e}")

    if not all_episodes:
        print("No se pudo leer ningún dato de los archivos JSON.")
        exit()

    df = pd.DataFrame(all_episodes)
    print(f"Se leyeron {len(df)} registros de episodios en total.")

    # 2. Extraer 'vatican_slug' e 'idioma' de la URL (¡NUEVO!)
    df[["vatican_slug_extracted", "idioma_extracted"]] = df["vatican_url"].apply(
        lambda x: pd.Series(extract_slug_lang_from_url(x))
    )

    # Limpiar filas donde no pudimos extraer datos o falta la URL del audio
    df = df.dropna(subset=["vatican_slug_extracted", "idioma_extracted", "url_audio"])

    if df.empty:
        print(
            "No hay episodios válidos con URL, slug extraído, idioma y url_audio para procesar."
        )
        exit()

    # 3. Obtener mapa de IDs de 'homilias'
    print("Obteniendo mapa de IDs de 'homilias' desde la BBDD...")
    homilias_data_db = select_all_data("homilias", "id, vatican_slug")
    homilia_id_map = {row["vatican_slug"]: row["id"] for row in homilias_data_db}

    # 4. Mapear 'homilia_id'
    df["homilia_id"] = df["vatican_slug_extracted"].map(homilia_id_map)

    # 5. Filtrar filas sin ancla y deduplicar
    df_validas = df.dropna(subset=["homilia_id"])
    df_invalidas = df[df["homilia_id"].isna()]
    if not df_invalidas.empty:
        print(
            f"⚠️ ADVERTENCIA: {len(df_invalidas)} episodios no encontraron 'ancla' en BBDD."
        )
        print("   (Asegúrate de haber ejecutado '1_seed_database.py')")
        print(
            "   Slugs extraídos de la URL no encontrados:",
            df_invalidas["vatican_slug_extracted"].unique(),
        )

    if df_validas.empty:
        print("No hay episodios válidos para actualizar.")
        exit()

    # Deduplicamos por la clave única de la BBDD
    df_unicas = df_validas.drop_duplicates(subset=["homilia_id", "idioma_extracted"])

    # 6. Preparar datos para 'upsert' (SOLO la URL del audio)
    audio_data_to_upsert = df_unicas.apply(
        lambda row: {
            "homilia_id": row["homilia_id"],
            "idioma": row["idioma_extracted"],
            "audio_url": row.get("url_audio"),
            "titulo": row.get(
                "titulo_original", row.get("vatican_slug_extracted", "Título pendiente")
            ),
        },
        axis=1,
    ).tolist()

    # 7. Ejecutar la actualización en lotes
    print(f"Se van a actualizar/insertar {len(audio_data_to_upsert)} URLs de audio.")
    batch_upsert(
        "homilias_traducciones", audio_data_to_upsert, on_conflict="homilia_id, idioma"
    )

    print("\n🎉 --- Actualización de URLs de Audio Completada --- 🎉")
