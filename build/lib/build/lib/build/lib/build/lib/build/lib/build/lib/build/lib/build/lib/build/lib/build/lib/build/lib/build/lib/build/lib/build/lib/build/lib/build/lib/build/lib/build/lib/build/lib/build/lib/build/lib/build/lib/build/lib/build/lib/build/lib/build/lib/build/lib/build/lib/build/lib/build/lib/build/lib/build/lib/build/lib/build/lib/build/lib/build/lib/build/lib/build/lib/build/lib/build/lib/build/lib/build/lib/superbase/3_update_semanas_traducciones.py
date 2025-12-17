import os
from pathlib import Path

import frontmatter  # La librería que acabas de instalar
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


def update_semana_summary(file_path: Path) -> (bool, str):
    """
    Lee un archivo 'resumen_semanal_igles-ia.txt' y actualiza
    la fila correspondiente en 'semanas_traducciones'.
    """
    try:
        # --- 1. Leer el archivo .txt con frontmatter ---
        with open(file_path, "r", encoding="utf-8") as f:
            post = frontmatter.load(f)

        metadata = post.metadata  # El diccionario del frontmatter (YAML)
        content = post.content  # El texto de resumen (después de '---')

        # --- 2. Obtener la 'fecha_inicio' (la clave) ---
        fecha_inicio = metadata.get("date")
        if not fecha_inicio:
            return False, f"Archivo sin 'date' en el frontmatter: {file_path.name}"

        # --- 3. Encontrar el 'semana_id' (el ancla) ---
        # Buscamos en 'semanas' usando la fecha del lunes
        resultado_ancla = (
            supabase.table("semanas")
            .select("id")
            .eq("fecha_inicio", fecha_inicio)
            .limit(1)
            .execute()
        )

        if not resultado_ancla.data:
            return False, f"No se encontró 'semana' ancla para la fecha: {fecha_inicio}"

        semana_id = resultado_ancla.data[0]["id"]

        # --- 4. Preparar los datos a actualizar ---
        # Usamos el 'excerpt' para el mensaje de WhatsApp
        # y el 'content' (cuerpo) para el resumen semanal
        data_to_update = {
            "semana_id": semana_id,
            "idioma": "es",  # Asumimos 'es' por el nombre de archivo
            "resumen_semanal": content.strip(),
            "mensaje_whatsapp": metadata.get("excerpt"),
        }

        # --- 5. Ejecutar el UPSERT ---
        # Usamos upsert para crear o actualizar la fila de traducción
        (
            supabase.table("semanas_traducciones")
            .upsert(data_to_update, on_conflict="semana_id, idioma")
            .execute()
        )

        return True, f"Actualizado resumen para: {fecha_inicio}"

    except Exception as e:
        return False, f"Error fatal procesando {file_path.name}: {e}"


# --- Punto de Entrada Principal ---
if __name__ == "__main__":
    # Directorio base donde están tus carpetas de fechas (ej. 2025-10-27)
    # Asumimos que el script está en la raíz del proyecto
    BASE_DIR = Path("web/data/summaries")

    print(f"Buscando resúmenes semanales en: {BASE_DIR.resolve()}")

    # 1. Encontrar todos los archivos de resumen
    summary_files = list(BASE_DIR.glob("*/resumen_semanal_igles-ia.txt"))

    if not summary_files:
        print("No se encontraron archivos 'resumen_semanal_igles-ia.txt'.")
        exit()

    print(f"Se encontraron {len(summary_files)} archivos de resumen para procesar.")

    # 2. Iterar y procesar cada archivo
    success_count = 0
    fail_count = 0

    for file in tqdm(summary_files, desc="Actualizando resúmenes semanales"):
        success, message = update_semana_summary(file)

        if success:
            success_count += 1
            # print(message) # Descomenta para ver el log de cada éxito
        else:
            fail_count += 1
            print(f"⚠️  {message}")  # Imprime solo los errores

    print("\n--- Actualización de Resúmenes Completada ---")
    print(f"✅ Filas actualizadas con éxito: {success_count}")
    print(f"🔥 Filas con error: {fail_count}")
