import logging
import os

import pandas as pd
import requests
from markdownify import markdownify as md

logging.basicConfig(
    level=logging.INFO,  # nivel mínimo de log que quieres ver
    format="%(asctime)s - %(levelname)s - %(message)s",
)
# Carpeta base
OUTPUT_DIR = "pope-archive/documents/vatican_html"
ALL_LINKS_PATH = "pope-archive/documents/links/all_links.csv"

POPES = [
    # "leo-xiv",
    "francesco",
    "benedict-xvi",
    "john-paul-ii",
    "john-paul-i",
    "paul-vi",
    "john-xxiii",
    "pius-xii",
    "pius-xi",
    "benedict-xv",
    "pius-x",
    "leo-xiii",
]

TYPES = ["encyclicals"]


# {
#     "León XIV": "leo-xiv",
#     # "Francisco": "francesco",
#     # "Benedicto XVI": "benedict-xvi",
#     # "Juan Pablo II": "john-paul-ii",
#     # "Juan Pablo I": "john-paul-i",
#     # "Pablo VI": "paul-vi",
#     # "Juan XXIII": "john-xxiii",
#     # "Pío XII": "pius-xii",
#     # "Pío XI": "pius-xi",
#     # "Benedicto XV": "benedict-xv",
#     # "Pío X": "pius-x",
#     # "León XIII": "leo-xiii",
# }

LANGUAGES = ["es"]  # "es", "en", "la", "it"


def download_html(
    url: str,
    pope: str,
    lang: str,
    title: str,
    output_dir: str = OUTPUT_DIR,
    save_markdown: bool = False,
) -> None:
    """
    Download an HTML page from `url` and save it under pope/lang/title.html.
    Optionally, also save a Markdown version.
    """
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        resp.encoding = "utf-8"
        html = resp.text

        # Prepare folder structure
        folder = os.path.join(output_dir, pope, lang)
        os.makedirs(folder, exist_ok=True)

        # Sanitize title for filename
        # safe_title = _sanitize_filename(title)
        safe_title = title
        # Save HTML
        html_path = os.path.join(folder, f"{safe_title}.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)
        logging.info(f"[OK] Saved HTML: {html_path}")

        # Optionally save Markdown
        if save_markdown:
            md_path = os.path.join(folder, f"{safe_title}.md")
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(md(html))
            logging.info(f"[OK] Saved Markdown: {md_path}")

    except Exception as e:
        logging.info(f"[ERROR] Downloading {url}: {e}")


def process_dataframe(df_pivot: pd.DataFrame, save_markdown: bool = False) -> None:
    """Iterate over DataFrame and download available HTML pages."""
    for _, row in df_pivot.iterrows():
        logging.info("Downloading htmls")

        download_html(
            row["link"],
            row["pope"],
            row["lang"],
            row["title"],
            save_markdown=save_markdown,
        )


def main():
    logging.info("hi")
    df = pd.read_csv(ALL_LINKS_PATH)

    df = df[
        (df["pope"].isin(POPES))
        & (df["lang"].isin(LANGUAGES))
        & (df["type"].isin(TYPES))
    ]

    process_dataframe(df, save_markdown=False)


if __name__ == "__main__":
    main()
