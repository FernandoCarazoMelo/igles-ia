import json
import logging
import os
import random
import re
import time
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin

import pandas as pd
import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from tqdm import tqdm

# --- Configuración del Logging ---
# Puedes ajustar el nivel de log si lo deseas (e.g., logging.DEBUG)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class VaticanArchiver:
    """
    Una clase para archivar documentos del Vaticano.

    Esta clase encapsula la lógica para:
    1. Encontrar todos los enlaces de documentos de un Papa (find_and_save_links).
    2. Fusionar esos enlaces en un DataFrame de pandas (merge_links_to_csv).
    3. Descargar el contenido HTML de esos enlaces (download_documents).
    """

    def __init__(
        self,
        base_url: str = "https://www.vatican.va/",
        cache_dir: str = "cache",
        links_dir: str = "pope-archive/documents/links",
        csv_dir: str = "pope-archive/documents/links",
        docs_dir: str = "documents",
        rate_limit_delay: Tuple[float, float] = (1.0, 3.0),
        force_refresh: bool = False,
    ):
        """
        Inicializa el archivador.

        Args:
            base_url (str): La URL base del sitio del Vaticano.
            cache_dir (str): Directorio para guardar las páginas HTML cacheadas (índices).
            links_dir (str): Directorio para guardar los archivos JSON de enlaces.
            csv_dir (str): Directorio para guardar los informes CSV fusionados.
            docs_dir (str): Directorio para guardar el contenido HTML final de los documentos.
            rate_limit_delay (Tuple[float, float]): Rango (min, max) de espera entre peticiones.
            force_refresh (bool): Si es True, ignora la caché y vuelve a descargar todo.
        """
        self.base_url = base_url
        self.cache_dir = cache_dir
        self.links_dir = links_dir
        self.csv_dir = csv_dir
        self.docs_dir = docs_dir
        self.rate_limit_delay = rate_limit_delay
        self.force_refresh = force_refresh

        # Configura una sesión de Requests robusta con reintentos
        self.session = self._setup_session()

        # Asegura que los directorios de salida existan
        os.makedirs(self.cache_dir, exist_ok=True)
        os.makedirs(self.links_dir, exist_ok=True)
        os.makedirs(self.csv_dir, exist_ok=True)
        os.makedirs(self.docs_dir, exist_ok=True)
        logging.info(
            f"Archivador inicializado. Caché: '{self.cache_dir}', Salida de Links: '{self.links_dir}'"
        )

    def _setup_session(self) -> requests.Session:
        """Configura una sesión de requests con reintentos."""
        session = requests.Session()
        retries = Retry(
            total=5,
            backoff_factor=1,
            status_forcelist=[500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retries)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        session.headers.update(
            {"User-Agent": "VaticanArchiverBot/1.0 (python-requests)"}
        )
        return session

    def _safe_filename(self, url: str) -> str:
        """Convierte una URL en un nombre de archivo seguro para la caché."""
        return url.replace("https://", "").replace("http://", "").replace("/", "_")

    def _get_cached_page(
        self, url: str, pope_slug: str, language: str
    ) -> Optional[str]:
        """
        Recupera una página de la caché si está disponible, si no, la descarga
        con limitación de tasa (rate limiting).
        """
        pope_cache_dir = os.path.join(self.cache_dir, pope_slug, language)
        os.makedirs(pope_cache_dir, exist_ok=True)
        filename = os.path.join(pope_cache_dir, self._safe_filename(url) + ".html")

        if not self.force_refresh and os.path.exists(filename):
            try:
                with open(filename, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception as e:
                logging.warning(f"No se pudo leer el archivo de caché {filename}: {e}")

        # Limitación de tasa
        time.sleep(random.uniform(self.rate_limit_delay[0], self.rate_limit_delay[1]))

        try:
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()
            resp.encoding = resp.apparent_encoding  # Intenta detectar la codificación

            with open(filename, "w", encoding=resp.encoding) as f:
                f.write(resp.text)
            return resp.text

        except requests.RequestException as e:
            logging.error(f"Fallo al descargar {url}: {e}")
            return None

    def _get_soup(
        self, url: str, pope_slug: str, language: str
    ) -> Optional[BeautifulSoup]:
        """Wrapper para devolver un objeto BeautifulSoup de una página cacheada."""
        html = self._get_cached_page(url, pope_slug, language)
        if not html:
            return None
        return BeautifulSoup(html, "html.parser")

    def _get_pope_main_page_url(self, pope_slug: str, language: str) -> str:
        """Construye la URL de la página principal para un Papa e idioma."""
        return urljoin(self.base_url, f"content/{pope_slug}/{language}.html")

    def _process_pope_index_pages(
        self, pope_name: str, pope_slug: str, language: str
    ) -> Set[str]:
        """Recupera todas las páginas de índice o categorías para un Papa."""
        logging.info(
            f"--- Procesando página principal del Papa {pope_name} [{language}] ---"
        )
        pope_main_page_url = self._get_pope_main_page_url(pope_slug, language)
        soup = self._get_soup(pope_main_page_url, pope_slug, language)

        if not soup:
            logging.error(
                f"No se pudo acceder a la página principal de {pope_name}. Saltando."
            )
            return set()

        urls_to_visit: Set[str] = set()
        content_area = (
            soup.find("div", class_="document-container")
            or soup.find("div", id="main-container")
            or soup.body
        )

        for link in content_area.find_all("a", href=True):
            href = link["href"]
            if (
                pope_slug in href
                and ".html" in href
                and not href.startswith(("http", "#", "javascript"))
            ):
                full_url = urljoin(pope_main_page_url, href)
                urls_to_visit.add(full_url)
        return urls_to_visit

    def _extract_document_links(
        self, index_url: str, pope_slug: str, language: str
    ) -> Set[str]:
        """Extrae todos los enlaces a documentos de una página de índice específica."""
        full_slug = f"{pope_slug}/{language}"
        pope_main_page_url = self._get_pope_main_page_url(pope_slug, language)

        soup = self._get_soup(index_url, pope_slug, language)
        if not soup:
            logging.error(f"No se pudo acceder a la página {index_url}. Saltando.")
            return set()

        urls_to_visit: Set[str] = set()
        # Lógica de scraping para encontrar enlaces a documentos
        url_without_index = index_url.replace(".index.html", "") + "/documents"
        try:
            url_without_index = url_without_index.split(full_slug)[1]
            content_area = (
                soup.find("div", class_="document-container")
                or soup.find("div", id="main-container")
                or soup.body
            )
            for link in content_area.find_all("a", href=True):
                href = link["href"]
                if (
                    full_slug in href
                    and url_without_index in href
                    and ".html" in href
                    and not href.startswith(("http", "#", "javascript"))
                ):
                    full_url = urljoin(pope_main_page_url, href)
                    urls_to_visit.add(full_url)
        except Exception as e:
            urls_to_visit = set()
            logging.warning(f"Error procesando {index_url}: {e}")

        return urls_to_visit

    def _get_all_pope_documents(
        self, pope_name: str, pope_slug: str, language: str
    ) -> List[str]:
        """Recupera todos los enlaces de documentos disponibles para un Papa e idioma."""
        all_document_urls: Set[str] = set()
        index_urls = self._process_pope_index_pages(pope_name, pope_slug, language)

        if not index_urls:
            logging.warning(
                f"No se encontraron páginas de índice para {pope_name} [{language}]"
            )
            return []

        logging.info(
            f"Escaneando {len(index_urls)} páginas de índice para {pope_name} [{language}]..."
        )
        for url in tqdm(index_urls, desc=f"Scraping {pope_name} [{language}]"):
            document_urls = self._extract_document_links(url, pope_slug, language)
            all_document_urls.update(document_urls)

        logging.info(
            f"Total de documentos encontrados para {pope_name} [{language}]: {len(all_document_urls)}"
        )
        return sorted(list(all_document_urls))

    def find_and_save_links(
        self, pope_map: Dict[str, str], languages: List[str]
    ) -> Dict[str, dict]:
        """
        Paso 1: Genera y guarda todos los enlaces de documentos para los Papas e idiomas dados.
        """
        logging.info("--- INICIANDO PASO 1: Encontrar y Guardar Enlaces ---")
        all_links_found = {}
        for pope_name, pope_slug in pope_map.items():
            pope_dir = os.path.join(self.links_dir, pope_slug)
            os.makedirs(pope_dir, exist_ok=True)
            all_links_found[pope_slug] = {}

            for lang in languages:
                logging.info(f"Buscando enlaces para {pope_name} [{lang}]...")
                links = self._get_all_pope_documents(pope_name, pope_slug, lang)
                all_links_found[pope_slug][lang] = links

                output_path = os.path.join(pope_dir, f"{lang}.json")
                try:
                    with open(output_path, "w", encoding="utf-8") as f:
                        json.dump(links, f, indent=2, ensure_ascii=False)
                    logging.info(
                        f"Guardados {len(links)} enlaces para {pope_name} [{lang}] -> {output_path}"
                    )
                except Exception as e:
                    logging.error(f"No se pudo guardar el JSON en {output_path}: {e}")

        return all_links_found

    def _extract_date_from_title(self, title: str) -> Optional[str]:
        """Extrae la fecha de un título (formato YYYYMMDD o DDMMYYYY)."""
        match = re.search(r"(\d{8})", title)
        if not match:
            return None
        digits = match.group(1)

        if digits[:4].startswith(("19", "20")):
            dt = pd.to_datetime(digits, format="%Y%m%d", errors="coerce")
        elif digits[-4:].startswith(("19", "20")):
            dt = pd.to_datetime(digits, format="%d%m%Y", errors="coerce")
        else:
            return None
        return dt.strftime("%Y-%m-%d") if pd.notna(dt) else None

    def merge_links_to_csv(self) -> Optional[pd.DataFrame]:
        """
        Paso 2: Carga los archivos JSON de enlaces, los fusiona, procesa y guarda como CSV.
        """
        logging.info("--- INICIANDO PASO 2: Fusionar Enlaces a CSV ---")
        rows = []
        for pope_slug in os.listdir(self.links_dir):
            pope_path = os.path.join(self.links_dir, pope_slug)
            if not os.path.isdir(pope_path):
                continue
            for file in os.listdir(pope_path):
                if file.endswith(".json"):
                    lang = file.replace(".json", "")
                    file_path = os.path.join(pope_path, file)
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            links = json.load(f)
                            for link in links:
                                rows.append(
                                    {"pope": pope_slug, "lang": lang, "link": link}
                                )
                    except Exception as e:
                        logging.error(f"No se pudo cargar {file_path}: {e}")

        if not rows:
            logging.warning(
                "No se encontraron enlaces en JSON para fusionar. Saltando Paso 2."
            )
            return None

        df = pd.DataFrame(rows)

        # Procesar DataFrame
        df["parts"] = df["link"].str.split("/")
        df["title"] = df["parts"].apply(lambda parts: max(parts, key=len))
        df["type"] = df["parts"].apply(
            lambda parts: parts[6] if len(parts) > 6 else None
        )
        df["date"] = df["title"].apply(self._extract_date_from_title)
        df = df.drop(columns=["parts"])

        # Guardar CSV completo
        all_links_path = os.path.join(self.csv_dir, "all_links.csv")
        df.to_csv(all_links_path, index=False, encoding="utf-8")
        logging.info(f"Guardado CSV fusionado en {all_links_path}")

        # Pivotar DataFrame
        df_pivot = df.pivot_table(
            index=["pope", "type", "title", "date"],
            columns="lang",
            values="link",
            aggfunc="first",
        ).reset_index()

        # sort by date
        df_pivot = df_pivot.sort_values(by="date", ascending=True)
        # Data to str

        # Guardar CSV pivotado
        pivot_path = os.path.join(self.csv_dir, "pivot_links.csv")
        df_pivot.to_csv(pivot_path, index=False, encoding="utf-8")
        logging.info(f"Guardado CSV pivotado en {pivot_path}")

        logging.info(f"Resumen: {len(df)} enlaces totales procesados.")
        logging.info("\nEnlaces por Papa:\n" + str(df.groupby("pope")["link"].count()))
        logging.info(
            "\nEnlaces por Idioma:\n" + str(df.groupby("lang")["link"].count())
        )

        return df

    def _download_single_html(
        self, url: str, pope: str, lang: str, title: str, save_markdown: bool = False
    ) -> None:
        """Descarga y guarda el contenido HTML de un documento final."""
        try:
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()
            resp.encoding = "utf-8"  # Vaticano usa utf-8 para documentos
            html = resp.text

            folder = os.path.join(self.docs_dir, pope, lang)
            os.makedirs(folder, exist_ok=True)

            safe_title = title  # El título de la URL ya es un nombre de archivo seguro
            html_path = os.path.join(folder, f"{safe_title}.html")

            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html)
            logging.info(f"[OK] Guardado HTML: {html_path}")

            if save_markdown:
                md_path = os.path.join(folder, f"{safe_title}.md")
                with open(md_path, "w", encoding="utf-8") as f:
                    f.write(md(html, heading_style="ATX"))
                logging.info(f"[OK] Guardado Markdown: {md_path}")

        except Exception as e:
            logging.error(f"[ERROR] Descargando {url}: {e}")

    def download_documents(
        self,
        links_df: pd.DataFrame,
        popes_filter: Optional[List[str]] = None,
        languages_filter: Optional[List[str]] = None,
        types_filter: Optional[List[str]] = None,
        save_markdown: bool = False,
    ) -> None:
        """
        Paso 3: Descarga el contenido HTML de los enlaces en el DataFrame,
        aplicando los filtros proporcionados.
        """
        logging.info("--- INICIANDO PASO 3: Descargar Documentos HTML ---")

        if links_df is None or links_df.empty:
            logging.warning(
                "El DataFrame de enlaces está vacío. No se puede descargar. ¿Ejecutaste merge_links_to_csv()?"
            )
            return

        # Aplicar filtros
        df_filtered = links_df.copy()
        if popes_filter:
            df_filtered = df_filtered[df_filtered["pope"].isin(popes_filter)]
            logging.info(f"Filtrando por Papas: {popes_filter}")
        if languages_filter:
            df_filtered = df_filtered[df_filtered["lang"].isin(languages_filter)]
            logging.info(f"Filtrando por Idiomas: {languages_filter}")
        if types_filter:
            df_filtered = df_filtered[df_filtered["type"].isin(types_filter)]
            logging.info(f"Filtrando por Tipos: {types_filter}")

        if df_filtered.empty:
            logging.warning(
                "Ningún documento coincide con los filtros. No se descargará nada."
            )
            return

        logging.info(f"Se descargarán {len(df_filtered)} documentos...")
        for _, row in tqdm(
            df_filtered.iterrows(),
            total=df_filtered.shape[0],
            desc="Descargando documentos",
        ):
            self._download_single_html(
                row["link"],
                row["pope"],
                row["lang"],
                row["title"],
                save_markdown=save_markdown,
            )
        logging.info("--- Descarga de documentos completada ---")

    def run_full_archive(
        self,
        pope_map: Dict[str, str],
        languages: List[str],
        download: bool = False,
        download_filters: Optional[dict] = None,
        save_markdown: bool = False,
    ) -> None:
        """
        Ejecuta el pipeline completo: Encontrar, Fusionar y (opcionalmente) Descargar.
        """
        logging.info("====== INICIANDO ARCHIVO COMPLETO DEL VATICANO ======")

        # Paso 1: Encontrar y guardar enlaces
        self.find_and_save_links(pope_map, languages)

        # Paso 2: Fusionar enlaces a CSV
        links_df = self.merge_links_to_csv()

        # Paso 3: Descargar documentos (opcional)
        if download:
            if links_df is not None:
                filters = download_filters or {}
                self.download_documents(
                    links_df,
                    popes_filter=filters.get("popes_filter"),
                    languages_filter=filters.get("languages_filter"),
                    types_filter=filters.get("types_filter"),
                    save_markdown=save_markdown,
                )
            else:
                logging.error(
                    "No se pudo ejecutar el Paso 3 (Descarga) porque el Paso 2 (Fusión) falló."
                )

        logging.info("====== ARCHIVO COMPLETO FINALIZADO ======")


# --- Bloque de Ejecución Principal ---

if __name__ == "__main__":
    # 1. Configuración para la ejecución completa del script

    # El POPE_MAP se define aquí, como solicitaste.
    POPE_MAP_FULL = {
        "León XIV": "leo-xiv",
        # "Francisco": "francesco",
        # "Benedicto XVI": "benedict-xvi",
        # "Juan Pablo II": "john-paul-ii",
        # "Juan Pablo I": "john-paul-i",
        # "Pablo VI": "paul-vi",
        # "Juan XXIII": "john-xxiii",
        # "Pío XII": "pius-xii",
        # "Pío XI": "pius-xi",
        # "Benedicto XV": "benedict-xv",
        # "Pío X": "pius-x",
        # "León XIII": "leo-xiii",
    }

    LANGUAGES_FULL = ["es", "en", "la", "it"]

    # Filtros para el paso de descarga (opcional)
    # Si quieres descargar, cambia download=True abajo.
    DOWNLOAD_FILTERS = {
        "popes_filter": ["leo-xiv"],  # Solo descarga estos
        # "languages_filter": ["es", "it"],       # Solo estos idiomas
        # "types_filter": ["encyclicals", "homilies", "angelus"] # Solo estos tipos
    }

    # 2. Inicializar y ejecutar el archivador

    # force_refresh=True volverá a descargar todos los índices
    archiver = VaticanArchiver(force_refresh=True)

    # Ejecuta el pipeline completo:
    # 1. Encuentra enlaces
    # 2. Fusiona a CSV
    # 3. Descarga (si download=True)
    archiver.run_full_archive(
        pope_map=POPE_MAP_FULL,
        languages=LANGUAGES_FULL,
        download=False,  # Cambia a True para descargar los HTML
        download_filters=DOWNLOAD_FILTERS,
        save_markdown=True,  # Opcional: guardar versión Markdown
    )

    # 3. Ejemplo de cómo lo llamarías desde tu main.py (para León XIV)

    logging.info("\n--- EJEMPLO DE USO COMO MÓDULO ---")

    # Esto es lo que harías en tu otro script (main.py):
    #
    # from vatican_archiver import VaticanArchiver
    #
    # leo_xiv_map = {"León XIV": "leo-xiv"}
    # leo_xiv_langs = ["es"] # O los idiomas que necesites
    #
    # # force_refresh=True es útil para tu script diario/semanal
    # daily_scanner = VaticanArchiver(force_refresh=True)
    #
    # # Paso 1: Encuentra los enlaces más recientes
    # daily_scanner.find_and_save_links(pope_map=leo_xiv_map, languages=leo_xiv_langs)
    #
    # # Paso 2: Fusiona solo los enlaces de León XIV
    # # (El script fusionará lo que haya en la carpeta 'links/',
    # # que en este caso solo será lo de León XIV si la carpeta está limpia)
    # links_df = daily_scanner.merge_links_to_csv()
    #
    # # Ahora podrías usar 'links_df' en tu pipeline de audios
    # if links_df is not None:
    #     logging.info(f"Encontrados {len(links_df)} enlaces para León XIV para procesar.")
    #     # ... tu lógica para 'obtener_todos_los_textos' ...
    #
