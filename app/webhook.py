import os
import logging
from dotenv import load_dotenv

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

from .db import ENGINE
from .models import Base, Message
from .nlp import classify_text, transcribe_ogg
from .db import get_session
from .reports import get_daily_stats, build_daily_report, build_21_30_day_summary

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

def init_db():
    Base.metadata.create_all(bind=ENGINE)

OWNER_CHAT_ID = int(os.environ.get("OWNER_CHAT_ID", "0") or "0")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "").strip()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Пришли текст или голос — я сохраню, расшифрую и добавлю в диагностику."
    )

async def daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rows = get_daily_stats(hours=24)
    text = build_daily_report(rows)
    await update.message.reply_text(text)

async def summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    days = int(os.environ.get("SUMMARY_DAYS", "21") or "21")
    text = build_21_30_day_summary(days=days)
    await update.message.reply_text(text)

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

    await update.message.reply_text("✅ Принято.")

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    voice = update.message.voice
    if not voice:
        return

    file = await context.bot.get_file(voice.file_id)
    file_bytes = await file.download_as_bytearray()

    transcript = transcribe_ogg(bytes(file_bytes))
    transcript = (transcript or "").strip()
    if not transcript:
        await update.message.reply_text("Не получилось распознать голос. Попробуй ещё раз.")
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

    await update.message.reply_text("🎙️✅ Голос распознан и сохранён.")

async def cron_daily_http(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # вызываться будет HTTP GET /cron/daily?secret=...
    # тут просто шлём отчёт владельцу
    if OWNER_CHAT_ID:
        rows = get_daily_stats(hours=24)
        text = build_daily_report(rows)
        await context.bot.send_message(chat_id=OWNER_CHAT_ID, text=text)

def main():
    init_db()
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")

    port = int(os.environ.get("PORT", "10000"))
    public_url = os.environ.get("RENDER_EXTERNAL_URL", "").strip()

    if not public_url:
        raise RuntimeError("RENDER_EXTERNAL_URL is not set (Render sets it automatically for Web Services)")

    # путь вебхука — секретный
    webhook_path = f"/telegram/{token}"

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("daily", daily))
    app.add_handler(CommandHandler("summary", summary))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))

    # ВАЖНО: webhook_url должен быть публичным
    webhook_url = f"{public_url}{webhook_path}"

    logging.info(f"Webhook url: {webhook_url}")

    app.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=webhook_path.lstrip("/"),
        webhook_url=webhook_url,
        drop_pending_updates=True,
    )

if __name__ == "__main__":
    main()
