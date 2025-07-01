import os

import pandas as pd
from crewai import LLM
from dotenv import load_dotenv, find_dotenv
from typer import Typer

from iglesia.agents import create_iglesia_content_crew
from iglesia.email_utils_2 import enviar_correos_todos
from iglesia.utils import obtener_todos_los_textos
from iglesia.cognito_utils import cognito_get_verified_emails

app = Typer()

load_dotenv(find_dotenv())

def save_wordcloud(text, path_save="wordcloud.png"):
    from collections import Counter

    import matplotlib.pyplot as plt
    from nltk.corpus import stopwords
    from wordcloud import WordCloud

    # Preprocess the text
    stop_words = set(stopwords.words("spanish"))
    words = [word for word in text.split() if word.lower() not in stop_words]
    word_counts = Counter(words)

    # Create a word cloud
    wordcloud = WordCloud(
        width=800, height=400, background_color="white"
    ).generate_from_frequencies(word_counts)

    # Save the word cloud to a file
    wordcloud.to_file(path_save)


def run_agents(debug=False, calculate_wordcloud=False, run_domingo: bool = False, run_date: str = None):
    print(os.getcwd())
    LLM_used = LLM(
        model="gpt-4.1-nano",
        temperature=0.2,
        max_tokens=2000,
    )
    urls = {
        "Homilia": ["https://www.vatican.va/content/leo-xiv/es/homilies/2025.html"],
        "Ángelus": ["https://www.vatican.va/content/leo-xiv/es/angelus/2025.html"],
        "Discurso": [
            "https://www.vatican.va/content/leo-xiv/es/speeches/2025/may.index.html",
            "https://www.vatican.va/content/leo-xiv/es/speeches/2025/june.index.html",
        ],
        "Audiencia": [
            "https://www.vatican.va/content/leo-xiv/es/audiences/2025.index.html"
        ],
        "Carta": ["https://www.vatican.va/content/leo-xiv/es/letters/2025.index.html"],
    }
    if run_date:
        run_date = pd.to_datetime(run_date)
        run_date = run_date.strftime("%Y-%m-%d")
    else:
        run_date = pd.Timestamp.now().strftime("%Y-%m-%d")

    # crear carpeta dentro de summaries con la fecha de hoy
    os.makedirs(f"{os.environ.get('SUMMARIES_FOLDER')}/{run_date}", exist_ok=True)
    print(f"{os.environ.get('SUMMARIES_FOLDER')}/{run_date}")
    df = obtener_todos_los_textos(urls)
    df = df[df["titulo"].str.len() > 10]
    df = df.reset_index(drop=True)
    print(df)
    if debug:
        df = df[:2]

    import re
    import unicodedata

    def limpiar_nombre_archivo(nombre):
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

    df["filename"] = df.apply(
        lambda x: f"{x['fecha']}_{x['tipo'].replace(' ', '_').lower()}_{limpiar_nombre_archivo(x['titulo'])}",
        axis=1,
    )

    # filtrar los df de la última semana
    print(df)

    df["fecha_dt"] = pd.to_datetime(df["fecha"])

    run_date_dt = pd.to_datetime(run_date)
    if run_domingo:
        # incluir los textos del mismo día
        df = df[(df["fecha_dt"] >= (run_date_dt - pd.Timedelta(days=6))) & (df["fecha_dt"] <= run_date_dt)]
        # incluir los textos del domingo
    
    else:
        df = df[
            (df["fecha_dt"] >= (run_date_dt - pd.Timedelta(days=7)))
            & (df["fecha_dt"] < run_date_dt)
        ]

    df = df.drop(columns=["fecha_dt"])

    if calculate_wordcloud:
        all_text = " ".join(df["texto"])
        save_wordcloud(
            all_text,
            path_save=f"{os.environ.get('SUMMARIES_FOLDER')}/{run_date}/wordcloud.png",
        )
    print(df)
    df.to_csv(
        f"{os.environ.get('SUMMARIES_FOLDER')}/{run_date}/iglesia.csv", index=False
    )
    iglesia_content_crew = create_iglesia_content_crew(df, LLM_used, run_date)
    _ = iglesia_content_crew.kickoff()


@app.command()
def pipeline_semanal(debug: bool = True, envio_fecha_ayer: bool = False):
    """
    Enviar correos semanales a todos los usuarios.
    """
    fecha_de_hoy = pd.Timestamp.now().strftime("%Y-%m-%d")

    # fecha de ayer
    fecha_de_ayer = pd.Timestamp.now() - pd.Timedelta(days=1)
    fecha_de_ayer = fecha_de_ayer.strftime("%Y-%m-%d")

    if envio_fecha_ayer:
        print(f"Enviando correos con fecha de ayer: {fecha_de_ayer}")
        fecha_de_hoy = fecha_de_ayer

    contacts = cognito_get_verified_emails()
    # contacts.to_csv("brevo_contacts.csv", index=False)
    print(f"Total de contactos obtenidos: {len(contacts)}")
    if debug:
        print("Solo para pruebas, usar el último contacto\n")
        print(contacts)
        contacts = contacts[contacts["email"].str.contains("carazom@gmail")]

    enviar_correos_todos(contacts, fecha_de_hoy)


@app.command()
def pipeline_diaria(debug: bool = False, calculate_wordcloud: bool = False, run_domingo: bool = False):
    """
    Ejecutar el pipeline diario de la iglesia.
    """
    fecha_de_hoy = pd.Timestamp.now().strftime("%Y-%m-%d")
    run_agents(debug=debug, calculate_wordcloud=calculate_wordcloud, run_domingo=run_domingo)

    contacts = cognito_get_verified_emails()
    # contacts.to_csv("brevo_contacts.csv", index=False)
    print(f"COGNITO. Total de contactos obtenidos: {len(contacts)}")
    print("Solo para pruebas, usar el último contacto\n")
    print(contacts)
    contacts = contacts[contacts["email"].str.contains("nando.carazom@gmai")]

    enviar_correos_todos(contacts, fecha_de_hoy)

@app.command()
def pipeline_date(
    run_date: str = None,
    debug: bool = False,
    calculate_wordcloud: bool = False,
    run_domingo: bool = False,
):
    """
    Ejecutar el pipeline para una fecha específica.
    """
    if run_date is None:
        run_date = pd.Timestamp.now().strftime("%Y-%m-%d")
    print(f"Ejecutando pipeline para la fecha: {run_date}")
    run_agents(debug=debug, calculate_wordcloud=calculate_wordcloud, run_domingo=run_domingo, run_date=run_date)
    enviar_correos_todos("", run_date, send_emails=False)


if __name__ == "__main__":
    app()
