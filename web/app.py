import datetime  # <--- AÑADE ESTA LÍNEA para importar el módulo datetime
import os  # Para manejar rutas de archivos de forma robusta

import markdown  # Para convertir Markdown a HTML
from flask import Flask, render_template

# Inicializar la aplicación Flask
app = Flask(__name__)

# Configuración para Flask-Frozen
app.config['FREEZER_DESTINATION'] = 'build'

@app.route('/')
def index():
    """Ruta principal que muestra el resumen semanal."""
    resumen_html_content = "No se pudo cargar el resumen."
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(base_dir, 'resumen-semanal.md')

        with open(file_path, 'r', encoding='utf-8') as f:
            markdown_content = f.read()
        
        resumen_html_content = markdown.markdown(markdown_content, extensions=['fenced_code', 'tables'])
    
    except FileNotFoundError:
        resumen_html_content = "<p>Error: No se encontró el archivo <code>resumen-semanal.md</code>.</p>"
    except Exception as e:
        resumen_html_content = f"<p>Ocurrió un error al procesar el resumen: {e}</p>"

    # Obtener el año actual
    current_year = datetime.datetime.now().year # <--- AÑADE ESTA LÍNEA

    # Pasa el año actual a la plantilla
    return render_template('index.html', 
                           resumen_html_content=resumen_html_content,
                           current_year=current_year) # <--- MODIFICA ESTA LÍNEA

if __name__ == '__main__':
    app.run(debug=True)