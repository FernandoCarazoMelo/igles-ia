import os
from datetime import datetime  # Para el año en el footer

from flask import Flask, render_template

# Inicializar la aplicación Flask
app = Flask(__name__)

# Configuración para Flask-Frozen
app.config['FREEZER_DESTINATION'] = 'build'
app.config['FREEZER_RELATIVE_URLS'] = True

# Ruta al archivo HTML pre-generado
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PREGENERATED_HTML_PATH = os.path.join(BASE_DIR, 'data', 'contenido_semanal_para_web.html')


@app.route('/sobre-nosotros.html')
def about():
    """Renderiza la página 'Sobre Nosotros'."""
    return render_template('sobre_nosotros.html')


@app.route('/')
def index():
    """Ruta principal que muestra el contenido HTML pre-generado."""
    
    pagina_completa_html = "<p>Contenido no disponible. Por favor, genera el archivo <code>contenido_semanal_para_web.html</code>.</p>"
    try:
        if os.path.exists(PREGENERATED_HTML_PATH):
            with open(PREGENERATED_HTML_PATH, 'r', encoding='utf-8') as f:
                pagina_completa_html = f.read()
        else:
            pagina_completa_html = f"<p>Error: No se encontró el archivo de contenido pre-generado en <code>{PREGENERATED_HTML_PATH}</code>.</p>"
    except Exception as e:
        pagina_completa_html = f"<p>Ocurrió un error al leer el contenido pre-generado: {e}</p>"
        # Podrías añadir un logging más detallado aquí para el servidor
        # print(f"Error leyendo HTML pre-generado: {e}")

    current_year = datetime.now().year
    
    return render_template('index.html', 
                           current_year=current_year,
                           pagina_completa_html=pagina_completa_html)

if __name__ == '__main__':
    app.run(debug=True)