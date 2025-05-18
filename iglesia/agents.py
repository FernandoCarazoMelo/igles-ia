from collections import Counter

import pandas as pd
from crewai import Agent, Crew, Task

# # Create agents
# text_summarizer = Agent(
#     role='Text Summarizer',
#     goal='Create concise and accurate summaries of individual texts',
#     backstory="""You are an expert in text analysis and summarization. 
#     You excel at extracting key information and creating clear summaries.""",
#     verbose=True
# )

# summary_consolidator = Agent(
#     role='Summary Consolidator',
#     goal='Create a comprehensive summary that combines individual summaries while preserving source attribution',
#     backstory="""You are skilled at synthesizing information from multiple sources 
#     and creating coherent consolidated summaries while maintaining source references.""",
#     verbose=True
# )

# def create_crew_summary(df):
#     # Create individual summary tasks
#     summary_tasks = []
#     for idx, row in df.iterrows():
#         task = Task(
#             description=f'Create a summary of the following text: {row["texto"]}. Source: {row["titulo"]}',
#             expected_output='A concise summary of the provided text with its source',
#             agent=text_summarizer
#         )
#         summary_tasks.append(task)
    
#     # Create final consolidation task
#     consolidation_task = Task(
#         description='Create a comprehensive summary of all the previous summaries, including their sources',
#         expected_output='A consolidated summary with source attributions',
#         agent=summary_consolidator,
#         context=summary_tasks  # This provides the results of previous tasks as context
#     )
    
#     # Create and execute the crew
#     crew = Crew(
#         agents=[text_summarizer, summary_consolidator],
#         tasks=summary_tasks + [consolidation_task],
#         verbose=True
#     )
    
    
#     return crew


def create_iglesia_content_crew(df, llm_instance):
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
        allow_delegation=False
    )

    # Agente 2: Redactor del Resumen Semanal
    redactor_jefe_iglesia = Agent(
        role="Redactor Jefe del portal Igles-IA, con especial habilidad para la síntesis pastoral",
        goal="Elaborar un resumen semanal inspirador y pastoral para los subscriptores de Igles-IA, integrando los análisis de los textos de la semana, comenzando con un recuento de los tipos de documentos y enlazando a las fuentes originales.",
        backstory="""Como corazón editorial de Igles-IA, tu pluma transforma análisis doctrinales en mensajes semanales que nutren la fe. 
        Eres experto en tejer una narrativa coherente a partir de múltiples fuentes, destacando los mensajes clave de la Iglesia de forma accesible, motivadora y digitalmente atractiva, incluyendo referencias claras a los textos completos para quien desee profundizar.""",
        llm=llm_instance,
        verbose=True,
        allow_delegation=False
    )

    # Fase 1: Tareas de Análisis Individual
    analysis_tasks = []
    for idx, row in df.iterrows():
        texto_input = row["texto"]
        titulo_doc = row["titulo"]
        tipo_doc = row["tipo"]
        url_doc = row["url"]
        filename = row["filename"]
        
        # Generar un nombre de archivo único para cada análisis semana_fecha_tipo_titulo
        output_filename_individual = f"summaries/{filename}.json"

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
    doc_type_counts = Counter(df['tipo'])
    if not doc_type_counts:
        intro_counts_sentence = "Esta semana, reflexionamos sobre importantes mensajes de la Iglesia." # Fallback
    else:
        parts = []
        # Ordenar por conteo o alfabéticamente para consistencia si se desea
        # sorted_types = sorted(doc_type_counts.items(), key=lambda item: item[1], reverse=True) 
        for doc_type, count in doc_type_counts.items():
            plural = "s" if count > 1 else ""
            # Ajustar el nombre del tipo para que suene natural en plural si es necesario (ej. Ángelus no cambia)
            tipo_display = doc_type
            if doc_type.lower() == "ángelus" and count > 1: # Ángelus es invariable en plural
                plural = ""
            elif doc_type.lower().endswith("z") and count > 1: # Ej. voz -> voces (no aplica mucho aquí, pero como ejemplo)
                 tipo_display = doc_type[:-1] + "ces"
                 plural = "" # ya está en plural
            elif not doc_type.lower().endswith("s"): # Para la mayoría: homilía -> homilías
                 plural = "s" if count > 1 else ""
                 tipo_display = doc_type + plural if count > 1 else doc_type


            parts.append(f"{count} {tipo_display.lower() if count > 1 else tipo_display.lower()}") # ej. "3 homilías", "1 ángelus"

        if len(parts) > 1:
            intro_counts_sentence = f"Esta semana, el Papa (o la Iglesia, según corresponda) nos ha ofrecido reflexiones a través de {', '.join(parts[:-1])} y {parts[-1]}."
        elif parts:
            intro_counts_sentence = f"Esta semana, el Papa (o la Iglesia, según corresponda) nos ha ofrecido reflexiones a través de {parts[0]}."
        else: # Si el df estuviera vacío o sin tipos válidos
            intro_counts_sentence = "Esta semana, reflexionamos sobre importantes mensajes de la Iglesia."


    # Fase 2: Tarea de Consolidación Semanal
    weekly_summary_task = Task(
        description= "Resumen de los resumenes recibidos",
        expected_output= "Un txt con un mensaje breve y directo para el 'Resumen Semanal de Igles-IA'. Resume los resumenes que has recibido. Al final añade los links a TODAS las urls originales.",
        # # Descripción MUY SIMPLIFICADA para weekly_summary_task
        # description = f"""Tu tarea es crear un 'Resumen Semanal de Igles-IA' muy sencillo.
        # Recibirás análisis JSON de varios textos. Cada JSON tiene "fuente_documento", "tipo_documento", "url_original", y "resumen_general".

        # **Introducción Obligatoria (debes usarla textualmente después del saludo):**
        # "{intro_counts_sentence}"

        # Instrucciones Claras y Simples:
        # 1.  Comienza con el saludo: "Querido subscriptor de Igles-IA,"
        # 2.  En la línea siguiente, escribe la "Introducción Obligatoria".
        # 3.  Luego, para cada análisis JSON que recibas del contexto:
        #     a.  Menciona el tipo y título del documento. Ejemplo: "Sobre el tipo_documento 'fuente_documento'..."
        #     b.  Presenta el "resumen_general" de ese texto.
        #     c.  Añade el enlace al texto completo. Ejemplo: "(Texto completo aquí: url_original)".
        # 4.  Puedes usar frases de transición muy simples como "Además...", "También se trató...", o simplemente presentar cada uno en un nuevo párrafo.
        # 5.  Mantén un tono pastoral y directo.
        # 6.  Concluye con: "Que estas ideas principales nos guíen durante la semana. Con afecto, El equipo de Igles-IA."

        # El objetivo es un boletín breve, claro y fácil de leer. La respuesta final debe ser únicamente el texto del resumen.
        # """,

        # # Expected_output MUY SIMPLIFICADO para weekly_summary_task
        # expected_output = """Un texto breve y directo para el 'Resumen Semanal de Igles-IA'.
        # Debe seguir esta estructura básica:
        # - Saludo.
        # - Introducción obligatoria (frase sobre tipos de documentos).
        # - Para cada texto analizado: mención de su tipo/título, el resumen general del mismo, y el enlace al texto completo.
        # - Conclusión simple.

        # Ejemplo de estructura (el contenido variará según los JSON de entrada):
        # Querido subscriptor de Igles-IA,

        # {intro_counts_sentence}

        # Sobre el Discurso 'La Importancia de la Comunidad', el mensaje central fue la necesidad de apoyarnos mutuamente en la fe. (Texto completo aquí: [URL_DEL_DISCURSO]).

        # Además, en la Homilía 'Vivir la Palabra', se nos animó a llevar el Evangelio a nuestra vida diaria. (Texto completo aquí: [URL_DE_LA_HOMILIA]).

        # Que estas ideas principales nos guíen durante la semana.
        # Con afecto,
        # El equipo de Igles-IA.
        # """,
        agent=periodista_catolico,
        context=analysis_tasks,
        output_file="summaries/resumen_semanal_igles-ia.txt"
    )
    
    iglesia_content_crew = Crew(
        agents=[periodista_catolico],
        tasks=analysis_tasks + [weekly_summary_task],
        verbose=True
    )
    
    return iglesia_content_crew
