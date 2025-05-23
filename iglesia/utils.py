import re
from datetime import datetime

import pandas as pd
import requests
from bs4 import BeautifulSoup


def obtener_homilias_vaticano(url):
    response = requests.get(url)
    if response.status_code != 200:
        print("Error:", response.status_code)
        return []

    soup = BeautifulSoup(response.content, "html.parser")
    homilias = []

    # Busca dentro de <div class="vaticanindex">
    contenedor = soup.find("div", class_="vaticanindex")
    if not contenedor:
        print("No se encontró el contenedor principal.")
        return []

    # Encuentra todas las entradas <li> dentro del <ul>
    for li in contenedor.find_all("li"):
        enlace = li.find("a")
        if enlace and enlace["href"]:
            titulo = enlace.get_text(strip=True)
            href = enlace["href"]
            if href.startswith("/"):
                href = "https://www.vatican.va" + href
            homilias.append({"titulo": titulo, "url": href})

    return homilias


# Función para extraer y formatear la fecha desde la URL
def extraer_fecha_desde_url(url):
    match = re.search(r"/(\d{8})-", url)
    if match:
        fecha_str = match.group(1)
        fecha_dt = datetime.strptime(fecha_str, "%Y%m%d")
        return fecha_dt.strftime("%d de %B de %Y")  # Por ejemplo: "11 de mayo de 2025"
    return ""


def extraer_homilia(homilia):
    url = homilia["url"]
    titulo_homilia = homilia["titulo"]
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")

    div_testo = soup.find("div", class_="testo")

    # Texto principal de la homilía
    texto_container = div_testo.find_all("div", class_="text")
    texto = "\n".join(
        p.get_text(separator=" ", strip=True)
        for div in texto_container
        for p in div.find_all("p")
    )

    # Fecha desde la URL
    fecha = extraer_fecha_desde_url(url)

    return {
        "url": url,
        "fecha": fecha,
        "titulo_homilia": titulo_homilia,
        "texto": texto,
    }


def obtener_todos_los_textos(urls):
    all_homilias = []
    for tipo, url in urls.items():
        homilias = obtener_homilias_vaticano(url)
        homilias_df = [extraer_homilia(h) for h in homilias]

        # Añadir el tipo de homilía al DataFrame
        for h in homilias_df:
            h["tipo"] = tipo
        # Añadir a la lista total
        all_homilias.extend(homilias_df)

    # Convertir a DataFrame
    all_homilias = pd.DataFrame(all_homilias)
    # Reordenar columnas
    all_homilias = all_homilias[["tipo", "fecha", "titulo_homilia", "url", "texto"]]
    # renombrar titulo_texto
    all_homilias = all_homilias.rename(columns={"titulo_homilia": "titulo"})
    # Ordenar por fecha
    all_homilias["fecha"] = pd.to_datetime(
        all_homilias["fecha"], format="%d de %B de %Y", errors="coerce"
    )
    all_homilias = all_homilias.sort_values(by="fecha", ascending=True)
    all_homilias = all_homilias.reset_index(drop=True)
    # Convertir la fecha a string # Y-m-d
    all_homilias["fecha"] = all_homilias["fecha"].dt.strftime("%Y-%m-%d")

    return all_homilias
