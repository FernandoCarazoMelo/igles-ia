import json
import os
import re
from pathlib import Path

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

# Compilamos regex para extraer el 'slug' y el 'idioma' de la URL
# Ejemplo: .../leo-xiv/es/audiences/2025/documents/20251022-udienza-generale.html
# Captura 1: (es)
# Captura 2: (20251022-udienza-generale.html)
URL_REGEX = re.compile(r"/([a-z]{2})/.*/documents/([^/]+)$")


def update_homilia_metadata(file_path: Path) -> (bool, str):
    """
    Lee un archivo JSON de metadatos y actualiza la fila
    correspondiente en 'homilias_traducciones'.
    """
    try:
        # --- 1. Leer y parsear el JSON ---
        with open(file_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        url_original = metadata.get("url_original")
        if not url_original:
            return False, f"JSON sin 'url_original': {file_path.name}"

        # --- 2. Extraer 'slug' e 'idioma' de la URL ---
        match = URL_REGEX.search(url_original)
        if not match:
            return False, f"URL no coincide con el patrón: {url_original}"

        idioma = match.group(1)
        vatican_slug = match.group(2)

        # --- 3. Encontrar la 'homilia_id' (el ancla) ---
        # Buscamos en la tabla 'homilias' usando el slug
        resultado_ancla = (
            supabase.table("homilias")
            .select("id")
            .eq("vatican_slug", vatican_slug)
            .limit(1)
            .execute()
        )

        if not resultado_ancla.data:
            return False, f"No se encontró homilía 'ancla' para el slug: {vatican_slug}"

        homilia_id = resultado_ancla.data[0]["id"]

        # --- 4. Preparar los datos a actualizar ---
        data_to_update = {
            "resumen": metadata.get("resumen_general"),
            "ideas_clave": metadata.get("ideas_clave"),
            "tags_sugeridos": metadata.get("tags_sugeridos"),
        }

        # Eliminar claves 'None' para no sobrescribir datos existentes con NULL
        data_to_update = {k: v for k, v in data_to_update.items() if v is not None}

        if not data_to_update:
            return False, f"No hay datos nuevos que actualizar en {file_path.name}"

        # --- 5. Ejecutar el UPDATE ---
        # Actualizamos 'homilias_traducciones' donde coincidan
        # tanto el 'homilia_id' como el 'idioma'.
        (
            supabase.table("homilias_traducciones")
            .update(data_to_update)
            .eq("homilia_id", homilia_id)
            .eq("idioma", idioma)
            .execute()
        )

        return True, f"Actualizado: {vatican_slug} [{idioma}]"

    except json.JSONDecodeError:
        return False, f"Error de JSON en: {file_path.name}"
    except Exception as e:
        return False, f"Error fatal procesando {file_path.name}: {e}"


# --- Punto de Entrada Principal ---
if __name__ == "__main__":
    # Directorio base donde están tus carpetas de fechas (ej. 2025-10-27)
    # Cambia esto a la ruta correcta.
    BASE_DIR = Path("web/data/summaries")

    print(f"Buscando archivos JSON de metadatos en: {BASE_DIR.resolve()}")

    # 1. Encontrar todos los archivos JSON (excepto los de 'episodes')
    # Esta expresión busca en todas las subcarpetas de BASE_DIR
    json_files = list(BASE_DIR.glob("*/*.json"))

    if not json_files:
        print("No se encontraron archivos JSON.")
        exit()

    print(f"Se encontraron {len(json_files)} archivos JSON para procesar.")

    # 2. Iterar y procesar cada archivo
    success_count = 0
    fail_count = 0

    for file in tqdm(json_files, desc="Actualizando metadatos"):
        success, message = update_homilia_metadata(file)

        if success:
            success_count += 1
            # print(message) # Descomenta para ver el log de cada éxito
        else:
            fail_count += 1
            print(f"⚠️  {message}")  # Imprime solo los errores

    print("\n--- Actualización de Metadatos Completada ---")
    print(f"✅ Filas actualizadas con éxito: {success_count}")
    print(f"🔥 Filas con error: {fail_count}")
