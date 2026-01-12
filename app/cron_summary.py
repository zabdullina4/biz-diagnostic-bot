import os
from dotenv import load_dotenv
from telegram import Bot
from .reports import build_21_30_day_summary

load_dotenv()

def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    owner_chat_id = int(os.environ.get("OWNER_CHAT_ID", "0") or "0")
    days = int(os.environ.get("SUMMARY_DAYS", "21") or "21")
    if not token or not owner_chat_id:
        raise RuntimeError("TELEGRAM_BOT_TOKEN / OWNER_CHAT_ID is not set")

    text = build_21_30_day_summary(days=days)
    Bot(token=token).send_message(chat_id=owner_chat_id, text=text)

if __name__ == "__main__":
    main()
