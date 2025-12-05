import json
import math
import os

import pandas as pd
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


def select_all_data(table_name: str, select_query: str) -> list:
    """
    Obtiene TODOS los registros de una tabla, manejando automáticamente
    la paginación de 1000 filas de Supabase.
    """
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


def batch_upsert(table_name: str, data: list, on_conflict: str, chunk_size: int = 500):
    """
    Función genérica para hacer upsert de grandes volúmenes de datos en lotes.
    """
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
            # Usamos 'ignore_duplicates=False' para asegurarnos de que el 'on_conflict' se aplica
            # y los datos se actualizan (comportamiento UPSERT)
            supabase.table(table_name).upsert(chunk, on_conflict=on_conflict).execute()
        except Exception as e:
            print(f"❌ Error en el lote {i // chunk_size + 1} para {table_name}: {e}")
            print(f"    Pista: {e}")


# --- Punto de Entrada Principal ---
if __name__ == "__main__":
    JSON_PATH = "vatican-archiver/documents/links_enriched/all_links_enriched.json"  # Tu archivo con los datos de la IA

    print(f"Iniciando enriquecimiento desde: {JSON_PATH}")
    if not os.path.exists(JSON_PATH):
        print(f"Error: No se encuentra el archivo {JSON_PATH}")
        exit()

    try:
        # 1. Cargar los datos enriquecidos
        with open(JSON_PATH, "r", encoding="utf-8") as f:
            data_enriquecida = json.load(f)
        df = pd.DataFrame(data_enriquecida)
        print(f"Se encontraron {len(df)} registros enriquecidos en el JSON.")

        # 2. Limpiar datos y obtener mapa de IDs de la BBDD
        df = df.dropna(subset=["title", "lang"])  # 'title' es el vatican_slug

        print("Obteniendo mapa de IDs de 'homilias' desde la BBDD...")
        homilias_data_db = select_all_data("homilias", "id, vatican_slug")
        homilia_id_map = {row["vatican_slug"]: row["id"] for row in homilias_data_db}

        # 3. Mapear 'homilia_id' a nuestro DataFrame
        df["homilia_id"] = df["title"].map(homilia_id_map)

        # 4. Filtrar filas que no encontramos en la BBDD
        df_invalidas = df[df["homilia_id"].isna()]
        if not df_invalidas.empty:
            print(
                f"⚠️  ADVERTENCIA: {len(df_invalidas)} filas no tienen un 'ancla' en la BBDD."
            )
            print("    (Asegúrate de haber ejecutado el '1_seed_database.py' primero)")

        df_traducciones = df.dropna(subset=["homilia_id"])
        if df_traducciones.empty:
            print("No hay traducciones válidas para actualizar.")
            exit()

        # --- 5. Preparar los datos para el 'upsert' (¡ACTUALIZADO!) ---
        print(f"Filas antes de deduplicar: {len(df_traducciones)}")
        # Mantenemos la ÚLTIMA aparición en caso de duplicados
        df_traducciones_unicas = df_traducciones.drop_duplicates(
            subset=["homilia_id", "lang"], keep="last"
        )
        print(f"Filas únicas a procesar: {len(df_traducciones_unicas)}")

        traducciones_data = df_traducciones_unicas.apply(
            lambda row: {
                "homilia_id": row["homilia_id"],
                "idioma": row.get("lang"),
                "vatican_url": row.get("url"),
                "tipo": row.get("tipo"),
                "numero_episodio": row.get("numero_episodio"),
                "texto_limpio_len": row.get("texto_limpio_len"),
                "texto_original": row.get("texto"),
                "texto_limpio": row.get("texto_limpio"),
                "titulo": row.get("titulo"),
                "titulo_original": row.get("titulo"),
                "titulo_spotify": row.get("titulo_spotify"),
                "titulo_youtube": row.get("titulo_youtube"),
                "resumen": row.get("descripcion_spotify"),
                "descripcion_spotify": row.get("descripcion_spotify"),
                "texto_completo": row.get("texto_limpio"),
                "frases_destacadas": row.get("frases_seleccionadas"),
                "mensaje_instagram": row.get("mensaje_instagram"),
            },
            axis=1,
        ).tolist()

        # 6. Ejecutar la actualización en lotes
        print(
            f"Se van a actualizar/insertar {len(traducciones_data)} traducciones enriquecidas."
        )
        batch_upsert(
            "homilias_traducciones", traducciones_data, on_conflict="homilia_id, idioma"
        )

        print("\n🎉 --- Enriquecimiento de Metadatos Completado --- 🎉")

    except Exception as e:
        print(f"Ocurrió un error general durante el proceso: {e}")
