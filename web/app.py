import os
from datetime import datetime
from flask import Flask, render_template, request, flash, redirect, url_for

# --------------------------------------------------------------------------
# CONFIGURACIÓN DE LA APLICACIÓN
# --------------------------------------------------------------------------

app = Flask(__name__)

# IMPORTANTE: Se necesita una SECRET_KEY para que los mensajes flash funcionen.
# En producción, usa una cadena de caracteres larga y aleatoria.
app.config['SECRET_KEY'] = 'cambia-esto-por-una-clave-secreta-real'

# Configuración para generar el sitio estático con Flask-Frozen
app.config['FREEZER_DESTINATION'] = 'build'
app.config['FREEZER_RELATIVE_URLS'] = True

# Definición de rutas a los archivos de datos
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PREGENERATED_HTML_PATH = os.path.join(BASE_DIR, 'data', 'contenido_semanal_para_web.html')


# --------------------------------------------------------------------------
# FUNCIONES DE AYUDA (HELPERS)
# --------------------------------------------------------------------------

def get_pregenerated_html():
    """
    Lee de forma segura el contenido del archivo HTML pre-generado.
    Esta función centraliza la lógica para no repetirla en varias rutas.
    Devuelve el contenido HTML como string o un mensaje de error formateado.
    """
    try:
        if os.path.exists(PREGENERATED_HTML_PATH):
            with open(PREGENERATED_HTML_PATH, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            error_msg = f"Error: No se encontró el archivo de contenido en <code>{PREGENERATED_HTML_PATH}</code>."
            return f"<div class='content-card' style='color: red; text-align: center;'><p>{error_msg}</p></div>"
    except Exception as e:
        print(f"ERROR al leer el archivo HTML: {e}")  # Log para el desarrollador
        error_msg = "Ocurrió un problema al cargar el contenido. Por favor, inténtalo más tarde."
        return f"<div class='content-card' style='color: red; text-align: center;'><p><strong>Error:</strong> {error_msg}</p></div>"


# --------------------------------------------------------------------------
# PROCESADOR DE CONTEXTO (VARIABLES GLOBALES PARA PLANTILLAS)
# --------------------------------------------------------------------------

@app.context_processor
def inject_global_vars():
    """
    Inyecta variables en el contexto de todas las plantillas.
    Así no tenemos que pasar 'current_year' en cada 'render_template'.
    """
    return {
        'current_year': datetime.now().year
    }


# --------------------------------------------------------------------------
# RUTAS DE LA APLICACIÓN
# --------------------------------------------------------------------------

@app.route('/')
def index():
    """
    Ruta principal. Ahora solo muestra la página de inicio.
    El contenido del resumen ya no se carga aquí.
    """
    return render_template('index.html')


@app.route('/resumen-semanal.html')
def latest_summary():
    """
    Nueva ruta dedicada a mostrar el resumen semanal completo.
    """
    pagina_completa_html = get_pregenerated_html()
    return render_template('resumen_semanal.html', pagina_completa_html=pagina_completa_html)


@app.route('/sobre-nosotros.html')
def about():
    """Renderiza la página 'Sobre Nosotros'."""
    return render_template('sobre_nosotros.html')


@app.route('/contacto.html', methods=['GET', 'POST'])
def contact():
    """Gestiona la página de contacto y el envío del formulario."""
    return render_template('contacto.html')


# --------------------------------------------------------------------------
# INICIAR SERVIDOR DE DESARROLLO
# --------------------------------------------------------------------------

if __name__ == '__main__':
    app.run(debug=True)