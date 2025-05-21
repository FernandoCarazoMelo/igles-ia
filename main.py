import os

import pandas as pd
from crewai import LLM
from dotenv import load_dotenv

from iglesia.agents import create_iglesia_content_crew
from iglesia.email_utils_2 import enviar_correos_todos
from iglesia.utils import obtener_todos_los_textos


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


def main(debug=True, calculate_wordcloud=False):
    load_dotenv()
    print(os.getcwd())
    LLM_used = LLM(
        model="gpt-4.1-nano",
        temperature=0.2,
        max_tokens=2000,
    )
    urls = {
        "Homilia": "https://www.vatican.va/content/leo-xiv/es/homilies/2025.html",
        "Angelus": "https://www.vatican.va/content/leo-xiv/es/angelus/2025.html",
        "Discurso": "https://www.vatican.va/content/leo-xiv/es/speeches/2025/may.index.html",
    }
    fecha_de_hoy = pd.Timestamp.now().strftime("%Y-%m-%d")

    # crear carpeta dentro de summaries con la fecha de hoy
    os.makedirs(f"{os.environ.get('SUMMARIES_FOLDER')}/{fecha_de_hoy}", exist_ok=True)
    print(f"{os.environ.get('SUMMARIES_FOLDER')}/{fecha_de_hoy}")
    df = obtener_todos_los_textos(urls)
    df = df[df["titulo"].str.len() > 10]
    df = df.reset_index(drop=True)
    print(df)
    if debug:
        df = df[:2]
    df["filename"] = df.apply(
        lambda x: f"{x['fecha']}_{x['tipo'].replace(' ', '_').lower()}_{x['titulo'].replace(' ', '_').lower()}",
        axis=1,
    )
    # filtrar los df de la última semana
    print(df)

    run_date = pd.Timestamp("today").normalize()
    df["fecha_dt"] = pd.to_datetime(df["fecha"])
    df = df[
        (df["fecha_dt"] >= (run_date - pd.Timedelta(days=7)))
        & (df["fecha_dt"] < run_date)
    ]

    # por ejemplo, si hoy es lunes 18 de mayo, se filtran los df de lunes 11 de mayo
    # qué dias se incluesn: lunes 11, martes 12, miércoles 13, jueves 14, viernes 15, sábado 16 y domingo 17
    df = df.drop(columns=["fecha_dt"])
    
    if calculate_wordcloud:
        all_text = " ".join(df["texto"])
        save_wordcloud(
            all_text,
            path_save=f"{os.environ.get('SUMMARIES_FOLDER')}/{fecha_de_hoy}/wordcloud.png",
        )
    print(df)
    df.to_csv(
        f"{os.environ.get('SUMMARIES_FOLDER')}/{fecha_de_hoy}/iglesia.csv", index=False
    )
    iglesia_content_crew = create_iglesia_content_crew(df, LLM_used)
    _ = iglesia_content_crew.kickoff()


if __name__ == "__main__":
    main()
    fecha_de_hoy = pd.Timestamp.now().strftime("%Y-%m-%d")
    enviar_correos_todos("emails.csv", fecha_de_hoy)
