import re

from openai import OpenAI
from pydantic import BaseModel

client = OpenAI()


class DiscursoBoundaries(BaseModel):
    """
    Define la primera frase exacta con la que comienza el discurso.
    """

    frase_inicio_discurso: str


# --- PALABRAS CLAVE PARA EL CORTE FINAL ---


def extract_clean_text(texto_original: str, max_tokens_chars: int = 4000) -> str:
    """
    Extrae el texto principal limpio de un discurso papal.
    1. Usa LLM para encontrar el inicio.
    2. Usa Regex (STOP_WORDS) para cortar el final.
    """

    # -----------------------
    # 1️⃣ Recortar el texto de entrada para el LLM
    # -----------------------
    if len(texto_original) > max_tokens_chars:
        mitad = max_tokens_chars // 2
        texto_input = (
            texto_original[:mitad]
            + "\n...\n[TEXTO RECORTADO]\n...\n"
            + texto_original[-mitad:]
        )
    else:
        texto_input = texto_original

    # -----------------------
    # 2️⃣ Prompt para LLM (Simplificado: solo busca el inicio)
    # -----------------------
    prompt_messages = [
        {
            "role": "system",
            "content": (
                "Eres un asistente experto en analizar discursos papales. "
                "Tu tarea es identificar la primera frase exacta con la que el Papa (u orador) comienza a hablar."
            ),
        },
        {
            "role": "user",
            "content": f"""
Analiza el siguiente texto de un discurso. Debes identificar una sola frase clave:

1.  **`frase_inicio_discurso`**: La primera frase o saludo exacto con la que el Papa (u orador) comienza a hablar.
    (ej. "Queridos hermanos y hermanas", "Queridos amigos", "En el Evangelio de hoy...", "En el nombre del Padre y del Hijo")

Devuelve únicamente el JSON con la frase detectada. No inventes frases, debe ser exacta al texto.

Formato JSON esperado:
{{
  "frase_inicio_discurso": "..."
}}

Texto de entrada:
---
{texto_input}
---
""",
        },
    ]

    # -----------------------
    # 3️⃣ Llamada al LLM con Pydantic
    # -----------------------
    try:
        response = client.responses.parse(
            model="gpt-4o",  # Usando un modelo válido
            input=prompt_messages,
            text_format=DiscursoBoundaries,
        )
        boundaries = response.output_parsed

        # -----------------------
        # 4️⃣ Lógica de Corte (Inicio con LLM)
        # -----------------------
        if boundaries.frase_inicio_discurso:
            # 1. Obtenemos la frase del LLM
            phrase = boundaries.frase_inicio_discurso

            # 2. Escapamos caracteres especiales de Regex (ej. "¡" o ".")
            pattern_escaped = re.escape(phrase)

            # 3. Reemplazamos los espacios por \s+
            #    \s+ significa "uno o más espacios, INCLUYENDO saltos de línea (\n) o tabs (\t)"
            pattern_flexible = re.sub(r"\\ ", r"\\s+", pattern_escaped)

            # 4. Buscamos el patrón (ignorando mayúsculas/minúsculas)
            match = re.search(pattern_flexible, texto_original, flags=re.IGNORECASE)

            if match:
                # 5. Encontrado. Cortamos desde el inicio del 'match'.
                start_index = match.start()
                texto_limpio = texto_original[start_index:]

            else:
                # Fallback si la frase no se encuentra
                print(
                    "ADVERTENCIA: Frase de inicio no encontrada. Usando texto original."
                )
                texto_limpio = texto_original
        else:
            texto_limpio = texto_original

    except Exception as e:
        print(f"Error llamando a la API o procesando: {e}")
        texto_limpio = texto_original

    # -----------------------
    # 5️⃣ Lógica de Corte (Final con Regex) - ¡NUEVA ESTRATEGIA!
    # -----------------------

    # re.split() devuelve una lista. [0] es el texto ANTES del separador.
    # max=1 asegura que solo corte en la PRIMERA aparición.
    # flags=re.IGNORECASE hace que no distinga mayúsculas/minúsculas.
    texto_limpio = re.split(
        r"Saludos|Después del Ángelus|_______", texto_limpio, flags=re.IGNORECASE
    )[0]
    # -----------------------
    # 6️⃣ Limpieza final (Regex corregido para preservar párrafos)
    # -----------------------

    # Eliminar paréntesis y guiones bajos
    texto_limpio = re.sub(r"\([^)]*\)|_", " ", texto_limpio)

    # Normalizar espacios y tabulaciones (PERO NO saltos de línea)
    texto_limpio = re.sub(r"[ \t]+", " ", texto_limpio)

    # Conservar párrafos: Normalizar 3 o más saltos de línea a solo 2
    texto_limpio = re.sub(r"\n{3,}", "\n\n", texto_limpio)

    texto_limpio = texto_limpio.replace("[...]", "")

    return texto_limpio.strip()
