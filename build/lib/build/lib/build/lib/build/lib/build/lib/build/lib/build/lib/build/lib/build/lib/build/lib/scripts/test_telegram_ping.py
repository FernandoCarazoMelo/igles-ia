
import os
import sys
from dotenv import load_dotenv

load_dotenv()  

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from iglesia.telegram_utils import send_telegram_notification

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = "@HomiliasPapa"

def test_ping():
    print(f"Testing Telegram Bot with Token: {TOKEN[:5]}... and Chat ID: {CHAT_ID}")
    success = send_telegram_notification(TOKEN, CHAT_ID, "🔔 Test notification from EcclesIA Bot pipeline integration.")
    if success:
        print("✅ Message sent successfully!")
    else:
        print("❌ Failed to send message.")

if __name__ == "__main__":
    test_ping()
