import requests
import logging

def send_telegram_notification(token: str, chat_id: str, message: str) -> bool:
    """
    Sends a message to a Telegram chat using the Bot API.
    
    Args:
        token (str): The Telegram Bot API token.
        chat_id (str): The target chat ID or channel username (e.g., "@ChannelName").
        message (str): The text message to send. Supports minimal Markdown/HTML if configured, 
                       but here we default to plain text or simple link preview.
                       
    Returns:
        bool: True if the request was successful (HTTP 200), False otherwise.
    """
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        # "parse_mode": "Markdown" # Optional, if we want bold/italic
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            logging.info(f"Telegram notification sent to {chat_id}")
            return True
        else:
            logging.error(f"Failed to send Telegram notification: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        logging.error(f"Error sending Telegram notification: {e}")
        return False
