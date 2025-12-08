import boto3
import os

# Inicializar el cliente de SES. Se puede reutilizar en ejecuciones.
ses_client = boto3.client('ses', region_name=os.environ.get('AWS_REGION', 'eu-west-1'))
FROM_EMAIL = 'igles-ia@igles-ia.es'

def lambda_handler(event, context):
    # Extraer los datos del usuario que envía Cognito
    user_email = event['request']['userAttributes']['email']
    # Aunque no lo usemos en el email, es bueno tenerlo por si lo necesitas para logs
    user_name = event['request']['userAttributes'].get('name', 'amigo/a')

    subject = "✨ ¡Bienvenido a Igles-IA! Tu resumen semanal del Papa León XIV"
    
    # 1. Leer el contenido de la plantilla HTML
    try:
        # El archivo html debe estar en la misma carpeta que este script lambda
        with open('welcome.html', 'r', encoding='utf-8') as f:
            body_html = f.read()
    except FileNotFoundError:
        print("Error: No se encontró el archivo welcome.html en el paquete de la Lambda.")
        # Devolvemos el evento para que Cognito no falle, aunque no se envíe el email
        return event

    # 2. Enviar el email usando el contenido del archivo
    try:
        response = ses_client.send_email(
            Source=f"Igles-IA <{FROM_EMAIL}>",
            Destination={'ToAddresses': [user_email]},
            Message={
                'Subject': {'Data': subject},
                'Body': {'Html': {'Data': body_html}}
            }
        )
        print(f"Email de bienvenida enviado a {user_email}. Message ID: {response['MessageId']}")
    except Exception as e:
        print(f"Error al enviar email a {user_email}: {e}")

    # Devolver el evento a Cognito es crucial
    return event