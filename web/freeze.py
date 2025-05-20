from app import app  # Importa tu instancia de la aplicación Flask desde app.py
from flask_frozen import Freezer

# Configura el Freezer con tu aplicación
freezer = Freezer(app)

if __name__ == '__main__':
    print("Congelando el sitio...")
    freezer.freeze()  # Esta es la función mágica que genera los archivos estáticos
    print(f"Sitio congelado con éxito en la carpeta: {app.config.get('FREEZER_DESTINATION', 'build')}")