import json
import os
import re

import pandas as pd


# -------------------------
# Helpers
# -------------------------
def _load_links(base_path: str) -> pd.DataFrame:
    """Load JSON links from the directory structure into a DataFrame."""
    rows = []
    for pope in os.listdir(base_path):
        pope_path = os.path.join(base_path, pope)
        if not os.path.isdir(pope_path):
            continue
        for file in os.listdir(pope_path):
            if file.endswith(".json"):
                lang = file.replace(".json", "")
                file_path = os.path.join(pope_path, file)
                with open(file_path, "r", encoding="utf-8") as f:
                    links = json.load(f)
                    for link in links:
                        rows.append({"pope": pope, "lang": lang, "link": link})
    return pd.DataFrame(rows)


def _extract_date_from_title(title: str) -> str | None:
    """Extract date from a title using regex (format YYYYMMDD or DDMMYYYY)."""
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


def _process_links(df: pd.DataFrame) -> pd.DataFrame:
    """Process DataFrame to extract parts, title, type, and date."""
    df = df.copy()
    df["parts"] = df["link"].str.split("/")
    df["title"] = df["parts"].apply(lambda parts: max(parts, key=len))
    df["type"] = df["parts"].apply(lambda parts: parts[6] if len(parts) > 6 else None)
    df["date"] = df["title"].apply(_extract_date_from_title)
    return df.drop(columns=["parts"])


def _pivot_links(df: pd.DataFrame) -> pd.DataFrame:
    """Pivot DataFrame to compare translations and detect missing ones."""
    df_pivot = df.pivot_table(
        index=["pope", "type", "title", "date"],
        columns="lang",
        values="link",
        aggfunc="first"
    ).reset_index()
    if "es" in df_pivot.columns:
        df_pivot["missing_es"] = df_pivot["es"].isna()
    return df_pivot


def _print_summary(df: pd.DataFrame) -> None:
    """Print summary statistics about links."""
    print("\nTotal links:", len(df))
    print("\nLinks by pope:")
    print(df.groupby("pope")["link"].count())
    print("\nLinks by language:")
    print(df.groupby("lang")["link"].count())


# -------------------------
# Main function
# -------------------------
def main(base_path: str = "pope-archive/links/") -> None:
    df = _load_links(base_path)
    df = _process_links(df)
    _print_summary(df)
    df.to_csv(base_path + "all_links.csv")
    df_pivot = _pivot_links(df)
    df_pivot.to_csv(base_path + "df_pivot_links.csv")


    # Mostrar primeras filas
    print("\nProcessed DataFrame:")
    print(df.head())

    print("\nPivoted DataFrame:")
    print(df_pivot.head())


if __name__ == "__main__":
    main()
