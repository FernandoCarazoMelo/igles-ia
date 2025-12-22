import json
import os
import re
import unicodedata
from datetime import datetime

import pandas as pd
from crewai import LLM
from tqdm import tqdm

from iglesia.audio_utils import calculate_pontificate_week
from iglesia.clean_text import extract_clean_text
from iglesia.utils import extraer_homilia

tqdm.pandas()

llm_client = LLM(model="gpt-4.1-nano")


def enriquecer_episodios(
    path_all_links: str = "vatican-archiver/documents/links/all_links.csv",
    path_types_list: str = "assets/types_list.csv",
    path_output: str = "vatican-archiver/documents/links_enriched",
    pope: str = "leo-xiv",
    language: str = "es",
):
    os.makedirs(path_output, exist_ok=True)
    output_file = os.path.join(path_output, "all_links_enriched.json") # Define el path del archivo de salida

    # --- [PASO 1: LEER DATOS YA ENRIQUECIDOS] ---
    # Carga el archivo JSON si existe, para saber qué hemos procesado ya.
    if os.path.exists(output_file):
        print(f"Cargando {output_file} existente para evitar duplicados...")
        try:
            df_enriched = pd.read_json(output_file, orient="records")
            # Usamos 'title' (el slug/filename) como clave única
            enriched_slugs = set(df_enriched['title'])
            print(f"Encontrados {len(enriched_slugs)} slugs ya enriquecidos.")
        except ValueError:
            print("El JSON existente parece estar corrupto. Se procesará todo de nuevo.")
            df_enriched = pd.DataFrame(columns=['title']) # DataFrame vacío
            enriched_slugs = set()
    else:
        print(f"No se encontró {output_file}. Se procesará todo.")
        df_enriched = pd.DataFrame(columns=['title']) # DataFrame vacío
        enriched_slugs = set()
    # --- [FIN PASO 1] ---


    def _limpiar_nombre_archivo(nombre):
        # ... (tu función no cambia) ...
        nombre = (
            unicodedata.normalize("NFKD", nombre)
            .encode("ascii", "ignore")
            .decode("ascii")
        )
        nombre = re.sub(
            r"[^\w\s-]", "", nombre
        )
        nombre = re.sub(r"[-\s]+", "_", nombre)
        return nombre.strip("_").lower()[:100]


    def _generar_metadatos_episodio_new(texto_limpio, episodio_info, llm_client):
        # ... (tu función de LLM no cambia) ...
        print("🎙️  Generando título y descripción con IA...")
        try:
            fecha_dt = datetime.strptime(episodio_info["fecha"], "%Y-%m-%d")
            fecha_simple = fecha_dt.strftime("%d/%m")
            numero_formateado = episodio_info["numero_episodio"]

            prompt = f"""
            Eres un experto en comunicación para podcasts religiosos. Todo el texto que generes debe de estar en el idioma: {episodio_info["lang"]}
            Basado en el siguiente texto, genera un título y una descripción optimizados para Spotify.
            El formato de salida DEBE ser un JSON válido con las claves "titulo_spotify", "descripcion_spotify", "titulo_youtube", "mensaje_instagram", "frases_seleccionadas".
            REGLAS DEL TÍTULO SPOTIFY:
            - El formato exacto debe ser: "{numero_formateado} {episodio_info["tipo"]} {fecha_simple} | [TITULO ORIGINAL resumido] | [Tema principal en 3-5 palabras]", si es de tipo "Angelus" no incluyas el [TITULO ORIGINAL resumido] (solo tendrá dos partes).
            - El [TITULO ORIGINAL resumido] tienes que generarlo únicamente con el título original << {episodio_info["titulo"]}>>. no incluyas la fecha en esta parte.
            REGLAS DE LA DESCRIPCIÓN:
            - Debe ser un párrafo de 2-4 frases que resuma el mensaje central del Papa León XIV. Empieza diciendo en este/a {episodio_info["tipo"]} el Papa León XIV... Termina diciendo \n\n'Podcast creado por igles-ia.es'
            REGLAS DEL TÍTULO youtube:
            - El [TITULO ORIGINAL resumido] tienes que generarlo únicamente con el contenido << {episodio_info["texto_limpio"][:1000]}>>.
            - Debe de ser un título clickbait y evergreen.
            MENSAJE DE INSTAGRAM
            - Un mensaje presentando el resumen de la intervención para instagram. Puede usar algunos emojis.
            FRASES SELECCIONADAS
            _ Una lista con 2 o 3 frases LITERALES DEL PAPA. Tienen que ser frases LITERALES DEL TEXTO, no vale que el Papa lea o cite otro texto como el evangelio.
            ----
            TEXTO DEL DOCUMENTO (aunque el prompt esté en español, todo el texto que generes debe de estar en el idioma original: {episodio_info["lang"]}):
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
            print(f"{metadata['titulo_youtube']}")
            return metadata

        except Exception as e:
            print(
                f"❌ Error al generar metadatos con LLM: {e}. Se usarán valores por defecto."
            )
            return {
                "titulo_spotify": f"[{episodio_info['numero_episodio']}] {episodio_info['tipo']} del {episodio_info['fecha']}",
                "descripcion_spotify": texto_limpio[:250] + "...",
            }

    # --- [PASO 2: FILTRAR EL CSV DE ENTRADA] ---
    print(f"Cargando {path_all_links}...")
    homilias = pd.read_csv(path_all_links)
    homilias = homilias[(homilias["pope"] == pope) & (homilias["lang"] == language)]
    homilias = homilias.dropna(subset=["date"]) # Asegura que tengamos fecha
    
    print(f"Total de homilías en CSV (filtradas): {len(homilias)}")

    # ¡LA CLAVE! Filtramos el DataFrame para procesar solo las filas
    # cuyo 'title' (slug) NO esté en el set de slugs ya enriquecidos.
    homilias_a_procesar = homilias[~homilias['title'].isin(enriched_slugs)]

    print(f"Se procesarán {len(homilias_a_procesar)} homilías NUEVAS.")
    
    if homilias_a_procesar.empty:
        print("No hay homilías nuevas que enriquecer. Saliendo.")
        return # Salimos de la función si no hay nada que hacer
    # --- [FIN PASO 2] ---

    
    # --- [PASO 3: Ejecutar el pipeline (solo en homilías nuevas)] ---
    types_list = pd.read_csv(path_types_list).set_index("type")
    
    # Renombramos 'homilias_a_procesar' a 'homilias' para que el resto
    # de tu código funcione sin cambios.
    homilias = homilias_a_procesar.copy() # Usamos .copy() para evitar warnings
    
    homilias["tipo"] = homilias["type"].map(types_list["tipo"])
    homilias = homilias.rename(columns={"title_human": "titulo", "link": "url"})
    all_homilias = []

    print("Iniciando extracción de texto (esto puede tardar)...")
    for i, row in tqdm(homilias.iterrows(), total=len(homilias)):
        homilias_df = extraer_homilia(row)
        all_homilias.append(homilias_df)

    all_homilias = pd.DataFrame(all_homilias)
    all_homilias = pd.concat([homilias.reset_index(), all_homilias["texto"]], axis=1)

    # --- [PASO 4: Procesar y enriquecer (solo homilías nuevas)] ---
    all_homilias["texto_limpio"] = all_homilias["texto"].apply(extract_clean_text)
    
    # Convertimos 'date' a datetime para cálculos (manejando errores)
    all_homilias["date_dt"] = pd.to_datetime(all_homilias["date"], errors='coerce')
    all_homilias = all_homilias.dropna(subset=['date_dt']) # Quitamos las que fallaron
    
    all_homilias["pontificate_week"] = all_homilias["date"].apply(
        calculate_pontificate_week
    )
    all_homilias["texto_limpio_len"] = all_homilias["texto_limpio"].str.len()
    
    # Aseguramos que 'fecha' sea string para el LLM
    all_homilias["fecha"] = all_homilias["date_dt"].dt.strftime("%Y-%m-%d")

    all_homilias = all_homilias.sort_values(["lang", "pontificate_week", "date_dt"])
    all_homilias["week_order"] = (
        all_homilias.groupby(["lang", "pontificate_week"]).cumcount() + 1
    )
    all_homilias["numero_episodio"] = (
        all_homilias["pontificate_week"].astype(str)
        + "."
        + all_homilias["week_order"].astype(str)
    )

    # Devolvemos 'date' a string para el JSON
    all_homilias["date"] = all_homilias["date_dt"].dt.strftime("%Y-%m-%d")
    all_homilias = all_homilias.drop(columns=['date_dt']) # Limpiamos la col temporal

    # --- [PASO 5: Llamada al LLM (solo para homilías nuevas)] ---
    print(f"Iniciando enriquecimiento con LLM para {len(all_homilias)} episodios...")
    metadata = all_homilias.progress_apply(
        lambda row: _generar_metadatos_episodio_new(
            row["texto_limpio"], row, llm_client
        ),
        axis=1,
    )

    all_homilias[
        [
            "titulo_spotify",
            "descripcion_spotify",
            "titulo_youtube",
            "mensaje_instagram",
            "frases_seleccionadas",
        ]
    ] = pd.DataFrame(metadata.to_list())
    all_homilias["filename"] = all_homilias.apply(
        lambda x: f"{x['fecha']}_{x['tipo'].replace(' ', '_').lower()}_{_limpiar_nombre_archivo(x['titulo'])}",
        axis=1,
    )

    # --- [PASO 6: COMBINAR Y GUARDAR] ---
    # Combinamos el DataFrame de homilías ya enriquecidas (del Paso 1)
    # con el DataFrame 'all_homilias' (que contiene las nuevas).
    df_final = pd.concat([df_enriched, all_homilias], ignore_index=True)
    
    # Opcional: limpiar duplicados por si acaso
    df_final = df_final.drop_duplicates(subset=['title'], keep='last')

    print(f"Guardando {len(df_final)} homilías en total ({len(df_enriched)} antiguas + {len(all_homilias)} nuevas) en {output_file}")
    
    # Guardamos el archivo JSON combinado
    df_final.to_json(
        output_file, 
        orient="records"
    )
    # --- [FIN PASO 6] ---


if __name__ == "__main__":
    enriquecer_episodios()