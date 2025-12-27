import requests
import logging

import re

def escape_markdown_v2(text: str) -> str:
    return re.sub(r'([_\[\]()~`>#+\-=|{}.!])', r'\\\1', text)

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
    safe_message = escape_markdown_v2(message)

    payload = {
        "chat_id": chat_id,
        "text": safe_message,
        "parse_mode": "MarkdownV2" # Optional, if we want bold/italic
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
