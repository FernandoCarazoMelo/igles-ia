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

    def _limpiar_nombre_archivo(nombre):
        nombre = (
            unicodedata.normalize("NFKD", nombre)
            .encode("ascii", "ignore")
            .decode("ascii")
        )
        nombre = re.sub(
            r"[^\w\s-]", "", nombre
        )  # Quita cualquier carácter que no sea letra/número/guion/bajo
        nombre = re.sub(r"[-\s]+", "_", nombre)  # Reemplaza espacios y guiones por "_"
        return nombre.strip("_").lower()[:100]

    def _generar_metadatos_episodio_new(texto_limpio, episodio_info, llm_client):
        """
        Usa un LLM para generar un título dinámico y una descripción para un episodio.
        """
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

    homilias = pd.read_csv(path_all_links)
    homilias = homilias[(homilias["pope"] == pope) & (homilias["lang"] == language)]
    types_list = pd.read_csv(path_types_list).set_index("type")
    homilias["tipo"] = homilias["type"].map(types_list["tipo"])
    homilias = homilias.rename(columns={"title_human": "titulo", "link": "url"})
    homilias = homilias.dropna(subset=["date"])
    all_homilias = []

    for i, row in tqdm(homilias.iterrows(), total=len(homilias)):
        homilias_df = extraer_homilia(row)
        # Añadir el tipo de homilía al DataFrame
        all_homilias.append(homilias_df)

    all_homilias = pd.DataFrame(all_homilias)
    all_homilias = pd.concat([homilias.reset_index(), all_homilias["texto"]], axis=1)

    all_homilias["texto_limpio"] = all_homilias["texto"].apply(extract_clean_text)
    all_homilias["pontificate_week"] = all_homilias["date"].apply(
        calculate_pontificate_week
    )
    all_homilias["texto_limpio_len"] = all_homilias["texto_limpio"].str.len()
    all_homilias["fecha"] = all_homilias["date"]

    all_homilias["date"] = pd.to_datetime(all_homilias["date"])

    # Ordenamos los datos por idioma, semana y fecha
    all_homilias = all_homilias.sort_values(["lang", "pontificate_week", "date"])

    # Calculamos el número secuencial dentro de cada idioma y semana
    all_homilias["week_order"] = (
        all_homilias.groupby(["lang", "pontificate_week"]).cumcount() + 1
    )

    # Creamos la etiqueta final del episodio, por ejemplo "1.1", "1.2", etc.
    all_homilias["numero_episodio"] = (
        all_homilias["pontificate_week"].astype(str)
        + "."
        + all_homilias["week_order"].astype(str)
    )

    all_homilias["date"] = all_homilias["date"].dt.strftime("%Y-%m-%d")
    all_homilias["fecha"] = all_homilias["date"]

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
    all_homilias.to_json(
        os.path.join(path_output, "all_links_enriched.json"), orient="records"
    )


if __name__ == "__main__":
    enriquecer_episodios()
