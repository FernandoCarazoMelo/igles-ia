import os
from collections import Counter

import pandas as pd
from crewai import Agent, Crew, Task

from datetime import datetime, timedelta

# La fecha de inicio del pontificado que nos servirá de referencia
PONTIFICATE_START_DATE = datetime(2025, 5, 8)

def calculate_pontificate_week(run_date_str):
    """Calcula el número de semana del pontificado basado en la fecha de ejecución."""
    run_date = datetime.strptime(run_date_str, "%Y-%m-%d")
    delta = run_date - PONTIFICATE_START_DATE
    # Sumamos 1 porque la primera semana (días 0-6) es la semana 1.
    return (delta.days // 7) + 1

def get_week_of_string(run_date_str):
    """Genera la cadena de texto 'Semana del DD/MM al DD/MM de YYYY'."""
    run_date = datetime.strptime(run_date_str, "%Y-%m-%d")
    end_of_week = run_date - timedelta(days=1)  # Domingo anterior
    start_of_week = end_of_week - timedelta(days=6)  # Lunes anterior

    if start_of_week.year == end_of_week.year:
        result = f"Semana del {start_of_week.strftime('%d/%m')} al {end_of_week.strftime('%d/%m de %Y')}"
    else:
        result = f"Semana del {start_of_week.strftime('%d/%m/%Y')} al {end_of_week.strftime('%d/%m/%Y')}"

    return result


def create_iglesia_content_crew(df, llm_instance, run_date=None):
    """
    Crea un Crew para analizar textos eclesiásticos individualmente (incluyendo tipo y URL)
    y luego generar un resumen semanal consolidado para el portal "igles-ia"
    con una introducción dinámica sobre los tipos de documentos y enlaces a los originales.

    Args:
        df (pd.DataFrame): DataFrame con columnas "texto", "titulo", "tipo", "url".
        llm_instance: Instancia del modelo de lenguaje (LLM).

    Returns:
        Crew: El objeto Crew configurado.
    """

    # Agente 1: Analista de Textos Individuales
    periodista_catolico = Agent(
        role="Periodista católico, experto en analizar y estructurar textos del Papa y de la Iglesia",
        goal="Analizar meticulosamente textos eclesiásticos, extrayendo su esencia: resumen, ideas clave impactantes, tags relevantes, tipo de documento y URL original.",
        backstory="Eres un periodista católico con profunda formación doctrinal y ojo crítico. Tu especialidad es desglosar textos del Papa (homilías, discursos, etc.) en componentes estructurados (JSON) que incluyan metadatos esenciales como tipo y fuente URL, para facilitar su posterior divulgación y referencia.",
        llm=llm_instance,
        verbose=True,
        allow_delegation=False,
    )

    if run_date is None:
        run_date = pd.Timestamp.now().strftime("%Y-%m-%d")
        


    print(f"Agents: {os.environ.get('SUMMARIES_FOLDER')}/{run_date}")
    # Fase 1: Tareas de Análisis Individual
    analysis_tasks = []
    for idx, row in df.iterrows():
        texto_input = row["texto"]
        titulo_doc = row["titulo"]
        tipo_doc = row["tipo"]
        url_doc = row["url"]
        filename = row["filename"]

        output_filename_individual = (
            f"{os.environ.get('SUMMARIES_FOLDER')}/{run_date}/{filename}.json"
        )

        task_individual = Task(
            description=f"""Analiza en profundidad el siguiente texto eclesiástico.
            Título: "{titulo_doc}"
            Tipo de Documento: "{tipo_doc}"
            URL Original: "{url_doc}"
            Texto: "{texto_input}"

            Tu análisis debe enfocarse en extraer la información clave y estructurarla.
            Formatea tu respuesta exclusivamente como un objeto JSON. No incluyas ninguna explicación o texto introductorio fuera del JSON.
            Asegúrate de incluir todos los campos solicitados en el JSON.""",
            expected_output=f"""Un objeto JSON con las siguientes claves:
            1. "fuente_documento": "{titulo_doc}" (El título del documento).
            2. "tipo_documento": "{tipo_doc}" (El tipo de documento, ej: Homilía, Discurso, Ángelus).
            3. "url_original": "{url_doc}" (La URL completa del documento original).
            4. "resumen_general": Un string con el resumen conciso (40-70 palabras).
            5. "ideas_clave": Una lista de 3-5 strings, donde cada string es una idea clave pastoralmente relevante (15-30 palabras por idea).
            6. "tags_sugeridos": Una lista de 3-5 strings (tags) que describan el contenido y temas principales.
            
            Ejemplo de formato JSON esperado:
            {{
              "fuente_documento": "Discurso sobre la Esperanza",
              "tipo_documento": "Discurso",
              "url_original": "https://www.vatican.va/content/francesco/es/speeches/2025/may/sample-speech.html",
              "resumen_general": "El Santo Padre nos recuerda que la esperanza cristiana no defrauda y es motor de transformación personal y social, anclada en Cristo resucitado.",
              "ideas_clave": [
                "La esperanza cristiana es una certeza activa, no una espera pasiva.",
                "Cristo resucitado es el fundamento último de nuestra esperanza.",
                "Esta esperanza debe traducirse en obras de caridad y justicia.",
                "Cultivar la esperanza en la oración y los sacramentos."
              ],
              "tags_sugeridos": ["esperanza", "vida cristiana", "resurrección", "familia", "eucaristía"] 
            }}
            """,
            agent=periodista_catolico,
            output_file=output_filename_individual,
        )
        analysis_tasks.append(task_individual)

    # Preparar la introducción dinámica para el resumen semanal
    doc_type_counts = Counter(df["tipo"])
    if not doc_type_counts:
        intro_counts_sentence = "Esta semana, reflexionamos sobre importantes mensajes de la Iglesia."  # Fallback
    else:
        parts = []
        for doc_type, count in doc_type_counts.items():
            plural = "s" if count > 1 else ""
            # Ajustar el nombre del tipo para que suene natural en plural si es necesario (ej. Ángelus no cambia)
            tipo_display = doc_type
            if (
                doc_type.lower() == "ángelus" and count > 1
            ):  # Ángelus es invariable en plural
                plural = ""
            elif (
                doc_type.lower().endswith("z") and count > 1
            ):  # Ej. voz -> voces (no aplica mucho aquí, pero como ejemplo)
                tipo_display = doc_type[:-1] + "ces"
                plural = ""  # ya está en plural
            elif not doc_type.lower().endswith(
                "s"
            ):  # Para la mayoría: homilía -> homilías
                plural = "s" if count > 1 else ""
                tipo_display = doc_type + plural if count > 1 else doc_type

            parts.append(
                f"{count} {tipo_display.lower() if count > 1 else tipo_display.lower()}"
            )  # ej. "3 homilías", "1 ángelus"

        if len(parts) > 1:
            intro_counts_sentence = f"Esta semana, el Papa León XIV nos ha ofrecido reflexiones a través de {', '.join(parts[:-1])} y {parts[-1]}."
        elif parts:
            intro_counts_sentence = f"Esta semana, el Papa León XIV nos ha ofrecido reflexiones a través de {parts[0]}."
        else:  # Si el df estuviera vacío o sin tipos válidos
            intro_counts_sentence = (
                "Esta semana, no ha habido discursos u homilías del Papa."
            )
    pontificate_week_number = calculate_pontificate_week(run_date)
    week_of_string = get_week_of_string(run_date)

    # ... (tu código anterior para preparar 'intro_counts_sentence') ...

    # --- TAREA SEMANAL CON PROMPT MEJORADO ---
    weekly_summary_task = Task(
        description=f"""Tu tarea es generar el contenido COMPLETO para el archivo de resumen semanal.
        El archivo debe tener DOS partes: un encabezado YAML Frontmatter y el cuerpo del resumen en Markdown.

        Usa la siguiente información para rellenar el encabezado YAML:
        - Para 'date', usa esta fecha: {run_date}
        - Para 'week_of', usa este texto: "{week_of_string}"
        - Para 'pontificate_week', usa este número: {pontificate_week_number}

        Basándote en el contexto de los documentos analizados esta semana, debes:
        1. Inventar un 'title' atractivo y descriptivo para el resumen de esta semana. No incluyas generalizaded como 'Reflexiones del Papa León XIV'. Solo aspectos diferenciales de la semana en cuestión. no inlcuyas el año, ni la fecha en el title.
        2. Escribir un 'excerpt' (resumen corto de 1-2 frases) que invite a la lectura. No incluyas generalidades como 'Una semana marcada por discursos, homilías y encuentros'. En su lugar, enfócate en un aspecto específico del mensaje del Papa esta semana, como 'El Papa León XIV nos invita a cultivar la paciencia y la esperanza, virtudes que contrastan con el deseo de resultados rápidos de la cultura moderna, recordándonos que el Reino de Dios crece a su propio ritmo.'.
        3. Crear un 'slug' para la URL usando el formato: 'semana-N-palabra-clave'. Reemplaza N con el número de semana y usa 2-3 palabras clave del título.

        Después del encabezado YAML, escribe el cuerpo del resumen en Markdown siguiendo estas reglas:
        - Empieza con el saludo: "Esta semana, el Papa León XIV nos ha ofrecido reflexiones a través de..." (usa la frase que ya hemos calculado: '{intro_counts_sentence}').
        - Escribe un resumen pastoral integrado de unas 150 palabras.
        - Usa **negrita** para destacar 2-3 frases o conceptos clave.
        - Incluye una sección final titulada "#### Temas Clave Analizados:" con una lista de 3-4 puntos importantes.
        """,
        expected_output=f"""Un archivo de texto plano que contenga un encabezado YAML válido seguido del contenido en Markdown. No incluyas explicaciones, solo el contenido del archivo.

        EJEMPLO PERFECTO DEL FORMATO DE SALIDA ESPERADO:
        ---
        title: "La Esperanza Cristiana Frente a la Cultura de la Inmediatez"
        week_of: "{week_of_string}"
        date: "{run_date}"
        pontificate_week: {pontificate_week_number}
        excerpt: "El Papa León XIV nos invita a cultivar la paciencia y la esperanza, virtudes que contrastan con el deseo de resultados rápidos de la cultura moderna, recordándonos que el Reino de Dios crece a su propio ritmo."
        slug: "semana-{pontificate_week_number}-esperanza-paciencia"
        ---
        
        {intro_counts_sentence}

        Esta semana, el Papa León XIV nos ha ofrecido una reflexión profunda a partir de la **parábola del sembrador**, una imagen sencilla pero poderosa. Nos ha recordado que el **Reino de Dios crece en silencio**, a menudo lejos de nuestra vista y comprensión. Aunque no siempre veamos frutos inmediatos, la semilla ya está actuando en lo oculto.

        Su mensaje es una invitación a vivir con **paciencia y confianza**, sabiendo que lo que hoy parece pequeño o invisible puede transformarse en algo fecundo con el tiempo.

        #### Temas Clave Analizados:
        * **La paciencia de Dios:** El crecimiento espiritual no es automático ni espectacular. Dios respeta nuestros ritmos y nos acompaña con paciencia, sin imponer.
        * **La semilla de la fe:** Se nos llama a **cultivar la Palabra** en nuestra vida diaria, con gestos concretos de amor, oración y apertura al prójimo.
        * **Esperanza frente a la inmediatez:** En una cultura que exige resultados instantáneos, el Papa nos invita a **redescubrir la fuerza de lo lento**, lo humilde, lo que crece en silencio.

        Es un mensaje sencillo, pero muy necesario: confiar, sembrar con fe… y dejar que Dios haga crecer.

        """,
        agent=periodista_catolico,
        context=analysis_tasks,
        output_file=f"{os.environ.get('SUMMARIES_FOLDER')}/{run_date}/resumen_semanal_igles-ia.txt",
    )
    
    iglesia_content_crew = Crew(
        agents=[periodista_catolico],
        tasks=analysis_tasks + [weekly_summary_task],
        verbose=True,
    )

    return iglesia_content_crew
