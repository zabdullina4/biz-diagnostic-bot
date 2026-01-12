import os
import logging
from dotenv import load_dotenv

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

from .db import ENGINE
from .models import Base, Message
from .nlp import classify_text, transcribe_ogg
from .db import get_session

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

def init_db():
    Base.metadata.create_all(bind=ENGINE)

OWNER_CHAT_ID = int(os.environ.get("OWNER_CHAT_ID", "0") or "0")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Пришли текст или голос — я сохраню, расшифрую и добавлю в диагностику.\n"
        "Ежедневный отчёт приходит автоматически."
    )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if not text:
        return

    data = classify_text(text)

    msg = Message(
        tg_user_id=update.effective_user.id,
        tg_chat_id=update.effective_chat.id,
        source="text",
        raw_text=text,
        normalized_text=data.get("normalized_text", text),
        category=data.get("category", "unknown"),
        topic=data.get("topic", "unknown"),
        urgency=data.get("urgency", "low"),
        sentiment=data.get("sentiment", "neutral"),
        delegate_candidate=bool(data.get("delegate_candidate", False)),
        automate_candidate=bool(data.get("automate_candidate", False)),
        hire_candidate=bool(data.get("hire_candidate", False)),
        summary=data.get("summary", ""),
    )

    with get_session() as s:
        s.add(msg)
        s.commit()

    await update.message.reply_text("✅ Принято. Сохранила и классифицировала.")

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    voice = update.message.voice
    if not voice:
        return

    file = await context.bot.get_file(voice.file_id)
    file_bytes = await file.download_as_bytearray()

    transcript = transcribe_ogg(bytes(file_bytes))
    transcript = (transcript or "").strip()
    if not transcript:
        await update.message.reply_text("Не получилось распознать голос. Попробуй ещё раз, чуть четче.")
        return

    data = classify_text(transcript)

    msg = Message(
        tg_user_id=update.effective_user.id,
        tg_chat_id=update.effective_chat.id,
        source="voice",
        raw_text=transcript,
        normalized_text=data.get("normalized_text", transcript),
        category=data.get("category", "unknown"),
        topic=data.get("topic", "unknown"),
        urgency=data.get("urgency", "low"),
        sentiment=data.get("sentiment", "neutral"),
        delegate_candidate=bool(data.get("delegate_candidate", False)),
        automate_candidate=bool(data.get("automate_candidate", False)),
        hire_candidate=bool(data.get("hire_candidate", False)),
        summary=data.get("summary", ""),
    )

    with get_session() as s:
        s.add(msg)
        s.commit()

    await update.message.reply_text("🎙️✅ Голос распознан, сохранён и классифицирован.")

def main():
    init_db()
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))

    logging.info("Bot started (polling)...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
