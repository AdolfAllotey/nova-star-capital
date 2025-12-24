import os
import sys
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from src.v2.utils.telegram_utils import send_telegram_message
from src.v2.intelligence.chat_interface import ask_bot

load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
AUTHORIZED_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "5308497197")  # Ton chat_id

async def ask_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_chat_id = str(update.effective_chat.id)
    if user_chat_id != AUTHORIZED_CHAT_ID:
        await update.message.reply_text("⛔ Non autorisé.")
        return

    question = " ".join(context.args)
    if not question:
        await update.message.reply_text("❓ Pose une question après /ask")
        return

    await update.message.reply_text("🤖 Réflexion en cours…")
    response = ask_bot(question)
    await update.message.reply_text(response)

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("ask", ask_command))
    app.run_polling()

if __name__ == "__main__":
    main()