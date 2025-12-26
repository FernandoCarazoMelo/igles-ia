import math
import os
from datetime import datetime, timedelta

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


# --- ¡NUEVA FUNCIÓN HELPER! ---
def select_all_data(table_name: str, select_query: str) -> list:
    """
    Obtiene TODOS los registros de una tabla, manejando automáticamente
    la paginación de 1000 filas de Supabase.
    """
    all_data = []
    page = 0
    page_size = 1000  # Límite por defecto de Supabase

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
                # Si no hay datos, hemos terminado
                break

            all_data.extend(response.data)

            if len(response.data) < page_size:
                # Si la respuesta tiene menos filas que el tamaño de página,
                # esta era la última página.
                break

            page += 1

        except Exception as e:
            print(f"❌ Error durante la paginación de {table_name}: {e}")
            break

    print(f"✅ Se obtuvieron {len(all_data)} filas en total de '{table_name}'.")
    return all_data


def calcular_lunes(fecha_str: str) -> str:
    """Helper para calcular el lunes de una fecha dada."""
    try:
        homilia_dt = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        dias_para_restar = homilia_dt.weekday()  # Lunes=0, Domingo=6
        fecha_lunes = homilia_dt - timedelta(days=dias_para_restar)
        return fecha_lunes.isoformat()
    except (TypeError, ValueError):
        return None


def batch_upsert(table_name: str, data: list, on_conflict: str, chunk_size: int = 500):
    """
    Función genérica para hacer upsert de grandes volúmenes de datos en lotes.
    """
    if not data:
        print(f"No hay datos para insertar en {table_name}.")
        return

    total_chunks = math.ceil(len(data) / chunk_size)
    print(
        f"Iniciando carga en lotes para '{table_name}'. Total: {len(data)} filas en {total_chunks} lotes."
    )

    for i in tqdm(range(0, len(data), chunk_size), desc=f"Cargando {table_name}"):
        chunk = data[i : i + chunk_size]
        try:
            supabase.table(table_name).upsert(chunk, on_conflict=on_conflict).execute()
        except Exception as e:
            print(f"❌ Error en el lote {i // chunk_size + 1} para {table_name}: {e}")


# --- Punto de Entrada Principal (Lógica de Batching) ---
if __name__ == "__main__":
    CSV_PATH = "vatican-archiver/documents/links/all_links.csv"

    print(f"Iniciando carga masiva desde: {CSV_PATH}")
    if not os.path.exists(CSV_PATH):
        print(f"Error: No se encuentra el archivo {CSV_PATH}")
        exit()

    try:
        df = pd.read_csv(CSV_PATH)
        print(f"Se encontraron {len(df)} enlaces en el CSV.")

        # --- 0. Limpieza y Preparación del DataFrame ---
        df = df.dropna(subset=["date", "title"])

        # --- 1. Procesar y Cargar 'semanas' ---
        print("\n--- Paso 1: Procesando 'semanas' ---")
        df["fecha_lunes"] = df["date"].apply(calcular_lunes)
        semanas_unicas = df["fecha_lunes"].unique()
        semanas_data = [{"fecha_inicio": fecha} for fecha in semanas_unicas if fecha]

        batch_upsert("semanas", semanas_data, on_conflict="fecha_inicio")

        # --- 2. Obtener el mapa de IDs de 'semanas' (MODIFICADO) ---
        print("\n--- Paso 2: Obteniendo mapa de IDs de 'semanas' ---")
        # Usamos la nueva función 'select_all_data'
        semanas_data_db = select_all_data("semanas", "id, fecha_inicio")
        semana_id_map = {row["fecha_inicio"]: row["id"] for row in semanas_data_db}

        df["semana_id"] = df["fecha_lunes"].map(semana_id_map)

        # --- 3. Procesar y Cargar 'homilias' ---
        print("\n--- Paso 3: Procesando 'homilias' ---")
        df_homilias = df.dropna(subset=["semana_id"])
        df_homilias_unicas = df_homilias.drop_duplicates(subset=["title"])

        homilias_data = df_homilias_unicas.apply(
            lambda row: {
                "semana_id": row["semana_id"],
                "pope": row.get("pope"),
                "tipo": row.get("type"),
                "fecha": row.get("date"),
                "vatican_slug": row.get("title"),
            },
            axis=1,
        ).tolist()

        batch_upsert("homilias", homilias_data, on_conflict="vatican_slug")

        # --- 4. Obtener el mapa de IDs de 'homilias' (MODIFICADO) ---
        print("\n--- Paso 4: Obteniendo mapa de IDs de 'homilias' ---")
        # Usamos la nueva función 'select_all_data'
        homilias_data_db = select_all_data("homilias", "id, vatican_slug")
        homilia_id_map = {row["vatican_slug"]: row["id"] for row in homilias_data_db}

        df["homilia_id"] = df["title"].map(homilia_id_map)

        # --- 5. Procesar y Cargar 'homilias_traducciones' ---
        print("\n--- Paso 5: Procesando 'homilias_traducciones' ---")
        df_traducciones = df.dropna(subset=["homilia_id", "lang"])

        print(f"Filas de traducciones antes de deduplicar: {len(df_traducciones)}")
        df_traducciones_unicas = df_traducciones.drop_duplicates(
            subset=["homilia_id", "lang"]
        )
        print(f"Filas de traducciones únicas: {len(df_traducciones_unicas)}")

        traducciones_data = df_traducciones_unicas.apply(
            lambda row: {
                "homilia_id": row["homilia_id"],
                "idioma": row.get("lang"),
                "vatican_url": row.get("link"),
                "titulo": row.get("title_human")
                if pd.notna(row.get("title_human"))
                else row.get("title"),
            },
            axis=1,
        ).tolist()

        batch_upsert(
            "homilias_traducciones", traducciones_data, on_conflict="homilia_id, idioma"
        )

        print("\n🎉 --- Carga Masiva Completada --- 🎉")

    except Exception as e:
        print(f"Ocurrió un error general durante el proceso: {e}")
