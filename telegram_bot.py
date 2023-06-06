import os
import logging
import re
import time
import threading
from tempfile import NamedTemporaryFile
from pydub import AudioSegment
from telegram import Update, InlineKeyboardButton, KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardMarkup, ParseMode, Bot, LabeledPrice, ChatAction
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, PollAnswerHandler, CallbackQueryHandler, PreCheckoutQueryHandler
from threading import Thread
from cachetools import cached, TTLCache
from datetime import datetime

from prompter import Prompter

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

# Enable logging for debugging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Chat history and buffer size
chat_context = TTLCache(maxsize=10, ttl=14400)

# Start command
def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(
        'Hi! I am your ChatGPT bot. Ask me anything, and I will try to help!')

# Show typing status while waiting for a response
def send_typing_status(update: Update, context: CallbackContext, stop_event: threading.Event):
    while not stop_event.is_set():
        context.bot.send_chat_action(chat_id=update.message.chat_id, action=ChatAction.TYPING)
        time.sleep(5)  # Send typing status every 5 seconds

# Process text message
def process_message(prompter, update, user_message, chat_id):
    url_pattern = r"(https?://\S+)"
    url_match = re.match(url_pattern, user_message)
    if url_match:
        url = url_match.group(1)
        summary = prompter.save_url(url=url)
        response = "Summary of the web page: " + summary
        update.message.reply_text(text=response, quote=True)
        user_message = f"{url} saved to my documents database."
    else:
        response = prompter.generate_response(message=user_message, chat_context=chat_context[chat_id])
        image_url_pattern = r"(https://oaidalleapiprodscus\.blob\..*)"
        image_match = re.match(image_url_pattern, response)
        if image_match:
            image_url = image_match.group(1)
            update.message.reply_photo(image_url)
        else:
            update.message.reply_text(text=response)
    return user_message, response


# Message handler
def message_handler(update: Update, context: CallbackContext) -> None:

    # Get the chat id
    chat_id = update.message.chat_id

    # If the chat context is empty, initialize it
    if chat_id not in chat_context:
        chat_context[chat_id] = []
    
    prompter = Prompter(chat_id=chat_id)
    
    try:
        user_message = None
        # Get the user message
        # Check if the message is a voice message or text message
        if update.message.voice:
            with NamedTemporaryFile(prefix="voice_message_", suffix=".ogg") as voice_file:
                update.message.voice.get_file().download(voice_file.name)
                voice_file.flush()

                with NamedTemporaryFile(prefix="voice_message_", suffix=".mp3") as mp3_file:
                    AudioSegment.from_ogg(voice_file.name).export(mp3_file.name, format="mp3")
                    with open(mp3_file.name, "rb") as f:
                        transcript = prompter.transcribe_voice(file=f)
            user_message = transcript

        elif update.message.audio:
            with NamedTemporaryFile(prefix="audio_message_", suffix=".mp3") as audio_file:
                update.message.audio.get_file().download(audio_file.name)
                audio_file.flush()

                with open(audio_file.name, "rb") as f:
                    transcript = prompter.transcribe_voice(file=f)
            user_message = transcript

        else:
            user_message = update.message.text

        # If the user sends a message, send the message to the chatbot
        if user_message:

            # Show typing status to the user while the assistant is generating a response
            stop_typing_event = threading.Event()
            typing_thread = threading.Thread(target=send_typing_status, args=(update, context, stop_typing_event))
            typing_thread.start()

            user_message, response = process_message(prompter, update, user_message, chat_id)

            chat_context[chat_id].extend([{ "Human": user_message, "AI": response }])

            # Stop the typing status thread
            stop_typing_event.set()
            typing_thread.join()

        else:
            update.message.reply_text("Sorry, I don't understand that. Please try again.")
    
    except Exception as e:
        logger.error(f"Error during message processing: {e}")
        update.message.reply_text("Sorry, I couldn't process your message. Please try again.")


# Document handler
def document_handler(update: Update, context: CallbackContext) -> None:
    # Get the chat id
    chat_id = update.message.chat_id

    logger.info("Document received")

    # If the chat context is empty, initialize it
    if chat_id not in chat_context:
        chat_context[chat_id] = []
    
    prompter = Prompter(chat_id=chat_id)
    
    try:
        # Get the document
        file_name = update.message.document.file_name
        file_id = update.message.document.file_id
        file = context.bot.get_file(file_id)
        file.download(file_name)

        # Show typing status to the user while the assistant is generating a response
        stop_typing_event = threading.Event()
        typing_thread = threading.Thread(target=send_typing_status, args=(update, context, stop_typing_event))
        typing_thread.start()

        # Save the document to the vector database
        summary = prompter.save_document(document=file_name)

        response = "Summary of the document: " + summary

        update.message.reply_text(text=response, quote=True)

        chat_context[chat_id].extend([{ "Human": f"{file_name} saved to my documents database.", "AI": response }])

        # Stop the typing status thread
        stop_typing_event.set()
        typing_thread.join()
        os.remove(file_name)
    
    except Exception as e:
        logger.error(f"Error during document processing: {e}")
        update.message.reply_text("Sorry, I couldn't process your document. Please try again.")


# Clear the document database
def clear_database(update: Update, context: CallbackContext) -> None:
    # Get the chat id
    chat_id = update.message.chat_id

    prompter = Prompter(chat_id=chat_id)

    # if the database is cleared, send a message to the user
    if prompter.clear_database():
        update.message.reply_text(text="Database cleared.")
    else:
        update.message.reply_text(text="Database not cleared.")


# Error handler
def error_handler(update: Update, context: CallbackContext) -> None:
    logger.error(msg="Exception while handling an update:",
                 exc_info=context.error)
    update.message.reply_text(
        'An error occurred while processing your message. Please try again.')


def main() -> None:
    # Set up the updater and dispatcher
    updater = Updater(TELEGRAM_BOT_TOKEN)
    dispatcher = updater.dispatcher

    # Add handlers
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("clear_database", clear_database))
    dispatcher.add_handler(MessageHandler(
        Filters.text | Filters.voice | Filters.audio & ~Filters.command, message_handler))
    dispatcher.add_handler(MessageHandler(
        Filters.document.mime_type("application/pdf") | Filters.document.mime_type("text/plain") | Filters.document.mime_type("application/msword") | Filters.document.mime_type("application/vnd.openxmlformats-officedocument.wordprocessingml.document") | Filters.document.mime_type("text/html") | Filters.document.mime_type("text/csv") | Filters.document.mime_type("text/tab-separated-values") | Filters.document.mime_type("text/richtext"),
        document_handler))
    dispatcher.add_error_handler(error_handler)
    # Start the bot
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
