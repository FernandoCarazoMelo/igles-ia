import json
import logging
import os
import random
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from config import LANGUAGES, POPE_MAP
from tqdm import tqdm

logging.basicConfig(
    level=logging.INFO,  # nivel mínimo de log que quieres ver
    format="%(asctime)s - %(levelname)s - %(message)s"
)

BASE_URL = "https://www.vatican.va/"   # ajusta si es distinto
CACHE_DIR = "cache"


# ------------------------
# Helpers: cache + requests
# ------------------------

def safe_filename(url: str) -> str:
    """Convert a URL into a safe filename for local cache."""
    return url.replace("https://", "").replace("http://", "").replace("/", "_")


def get_cached_page(url: str, pope_slug: str, language: str, force_refresh: bool = False) -> str | None:
    """
    Retrieve a page from cache if available, otherwise download with rate limiting.
    """
    pope_cache_dir = os.path.join(CACHE_DIR, pope_slug, language)
    os.makedirs(pope_cache_dir, exist_ok=True)

    filename = os.path.join(pope_cache_dir, safe_filename(url) + ".html")

    # Cached version available
    if not force_refresh and os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            return f.read()

    # Rate limiting
    time.sleep(random.uniform(1, 3))

    headers = {
        "User-Agent": "AcademicResearchBot/1.0 (contact: your_email@example.com)"
    }

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        logging.error(f"Failed to fetch {url}: {e}")
        return None

    # Save in cache
    with open(filename, "w", encoding="utf-8") as f:
        f.write(resp.text)

    return resp.text


def get_soup(url: str, pope_slug: str, language: str, force_refresh: bool = False) -> BeautifulSoup | None:
    """Wrapper to return BeautifulSoup object from cached page or download."""
    html = get_cached_page(url, pope_slug, language, force_refresh)
    if not html:
        return None
    return BeautifulSoup(html, "html.parser")


# ------------------------
# Scraper logic
# ------------------------

def get_pope_main_page_url(pope_slug: str, language: str = "es") -> str:
    """Build the main page URL for a given pope and language."""
    return urljoin(BASE_URL, f"content/{pope_slug}/{language}.html")


def process_pope_index_pages(pope_name: str, pope_slug: str, language: str) -> set[str]:
    """Retrieve all index or category pages for a given pope."""
    logging.info(f"--- Processing main page for Pope {pope_name} ---")

    pope_main_page_url = get_pope_main_page_url(pope_slug, language)
    soup = get_soup(pope_main_page_url, pope_slug, language)

    if not soup:
        logging.error(f"Could not access the main page for {pope_name}. Skipping.")
        return set()

    urls_to_visit: set[str] = set()

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


def extract_document_links(index_url: str, pope_slug: str, language: str) -> set[str]:
    """Extract all document links from a specific index page."""
    full_slug = f"{pope_slug}/{language}"
    pope_main_page_url = get_pope_main_page_url(full_slug, language)

    soup = get_soup(index_url, pope_slug, language)
    if not soup:
        logging.error(f"Could not access page {index_url}. Skipping.")
        return set()

    urls_to_visit: set[str] = set()

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
    except Exception as E:
        urls_to_visit = []
        logging.warning(f"error: {E}")


    return urls_to_visit


def get_all_pope_documents(pope_name: str, pope_slug: str, language: str) -> list[str]:
    """Retrieve all available document links for a given pope and language."""
    all_document_urls: set[str] = set()

    index_urls = process_pope_index_pages(pope_name, pope_slug, language)
    if not index_urls:
        logging.warning(f"No index pages found for {pope_name}")
        return []

    for url in tqdm(index_urls):
        document_urls = extract_document_links(url, pope_slug, language)
        all_document_urls.update(document_urls)

    logging.info(
        f"Total documents found for {pope_name} [{language}]: {len(all_document_urls)}"
    )
    return sorted(all_document_urls)


def save_links(pope_name: str, pope_slug: str, languages: list[str], output_dir: str = "links"):
    """Generate and save all document links for a pope in multiple languages."""
    pope_dir = os.path.join(output_dir, pope_slug)
    os.makedirs(pope_dir, exist_ok=True)

    all_links = {}
    for lang in languages:
        logging.info(f"Fetching links for {pope_name} [{lang}]...")
        links = get_all_pope_documents(pope_name, pope_slug, lang)
        all_links[lang] = links

        output_path = os.path.join(pope_dir, f"{lang}.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(links, f, indent=2, ensure_ascii=False)

        logging.info(f"Saved {len(links)} links for {pope_name} [{lang}] -> {output_path}")

    # combined_path = os.path.join(pope_dir, "all.json")
    # with open(combined_path, "w", encoding="utf-8") as f:
    #     json.dump(all_links, f, indent=2, ensure_ascii=False)

    # logging.info(f"Saved combined links -> {combined_path}")
    return all_links


if __name__ == "__main__":
    for pope_name, pope_slug in POPE_MAP.items():
        save_links(pope_name,pope_slug, LANGUAGES)
