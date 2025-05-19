import os

import pandas as pd
from crewai import LLM
from dotenv import load_dotenv

from iglesia.agents import create_iglesia_content_crew
from iglesia.utils import obtener_todos_los_textos


def main(debug=True):
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

    run_date = pd.Timestamp('today').normalize()
    df['fecha_dt'] = pd.to_datetime(df['fecha'])
    df = df[(df['fecha_dt'] >= (run_date - pd.Timedelta(days=7))) & (df['fecha_dt'] < run_date)]
    
    # por ejemplo, si hoy es lunes 18 de mayo, se filtran los df de lunes 11 de mayo
    # qué dias se incluesn: lunes 11, martes 12, miércoles 13, jueves 14, viernes 15, sábado 16 y domingo 17
    df = df.drop(columns=["fecha_dt"])
    print(df)
    df.to_csv(f"{os.environ.get('SUMMARIES_FOLDER')}/{fecha_de_hoy}/iglesia.csv", index=False)
    iglesia_content_crew = create_iglesia_content_crew(df, LLM_used)
    _ = iglesia_content_crew.kickoff()


if __name__ == "__main__":
    main()