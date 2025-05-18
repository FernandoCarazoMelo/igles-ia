from crewai import LLM
from dotenv import load_dotenv

from iglesia.agents import create_iglesia_content_crew
from iglesia.utils import obtener_todos_los_textos


def main(debug=True):
    load_dotenv()
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
    df.to_csv("summaries/iglesia.csv", index=False)
    iglesia_content_crew = create_iglesia_content_crew(df, LLM_used)
    _ = iglesia_content_crew.kickoff()


if __name__ == "__main__":
    main()
