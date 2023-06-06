"""
ChatGPT Telegram Bot is a Telegram bot that uses the ChatGPT model to generate responses to user messages.
It also connects to a number of tools that can be used to answer questions, generate images and more.
"""

import os
import logging
import re
import openai
from pydub import AudioSegment
from telegram import Update, InlineKeyboardButton, KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardMarkup, ParseMode, Bot, LabeledPrice, ChatAction
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, PollAnswerHandler, CallbackQueryHandler, PreCheckoutQueryHandler
from threading import Thread
from cachetools import cached, TTLCache
from datetime import datetime

from langchain.chat_models import ChatOpenAI
from langchain.chains import LLMChain, ConversationChain
from langchain.prompts import PromptTemplate
from langchain.agents import load_tools, initialize_agent, Tool, AgentType
from langchain.memory import ConversationBufferMemory
from langchain.tools import DuckDuckGoSearchRun
from langchain.utilities import GoogleSearchAPIWrapper
from langchain.utilities.wolfram_alpha import WolframAlphaAPIWrapper
from langchain.callbacks.streaming_stdout_final_only import FinalStreamingStdOutCallbackHandler

from .vectordb import VectorDB

# Set OpenAI API key
# openai_api_key = None
openai.api_key = os.environ.get("OPENAI_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
GOOGLE_CSE_ID = os.environ.get("GOOGLE_CSE_ID")
WOLFRAM_ALPHA_APPID=os.environ.get("WOLFRAM_ALPHA_APPID")
STRIPE_TOKEN = os.environ.get("STRIPE_TOKEN")

# Enable logging for debugging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Chat history and buffer size
chat_context = {}
buffer_size = 10

# Start command
def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(
        'Hi! I am your ChatGPT bot. Ask me anything, and I will try to help!')
    #update.message.reply_text('Please enter your OpenAI API Key:')


# Ask for OpenAI API key
def set_api_key(update: Update, context: CallbackContext) -> None:
    global openai_api_key
    openai_api_key = update.message.text
    openai.api_key = openai_api_key
    update.message.reply_text(
        'API Key set successfully. You can now ask me anything, and I will try to help!')

# Generate image
def generate_image(prompt):

    logger.info("Generating image...")

    response = openai.Image.create(
        prompt=prompt,
        n=1,
        size="256x256"
    )

    return response['data'][0]['url']


# Transcribe voice
def transcribe_voice(file):
    
    logger.info("Transcribing voice...")

    transcript = openai.Audio.transcribe("whisper-1", file)
    
    return transcript["text"]


# Save file to the vector database
def save_to_database(file, chat_user_id):
    # check if the chat_user_id is string
    if not isinstance(chat_user_id, str):
        chat_user_id = str(chat_user_id)

    db = VectorDB(chat_user_id, openai.api_key)

    summary = db.add_document(file)

    return summary


# Get url and summarize text
def summarize_url(url, chat_user_id):
    # check if the chat_user_id is string
    if not isinstance(chat_user_id, str):
        chat_user_id = str(chat_user_id)

    db = VectorDB(chat_user_id, openai.api_key)

    summary = db.add_url(url)

    return summary


# Prompt the LLM to generate a response
def generate_response(messages, chat_context, chat_id):

    # Format the chat history as a string
    formatted_chat_history = "\n".join([f"{k}: {v}" for entry in chat_context for k, v in entry.items()])

    # Create a prompt template
    template = f"""
    Chat History:
    {formatted_chat_history}

    Human: {messages}
    AI:"""

    # Create a prompt template
    #prompt_template = PromptTemplate(template=template, validate_template=False)

    # A conversation buffer (memory) & import llm of choice
    #memory = ConversationBufferMemory(memory_key="chat_history", input_key="input")

    # Create a model, chain and tool for the language model
    llm = ChatOpenAI(temperature=0, 
                     streaming=True, 
                     callbacks=[FinalStreamingStdOutCallbackHandler()], 
                     max_retries=3,
                     openai_api_key=openai.api_key)

    #llm_chain = ConversationChain(llm=llm, prompt=prompt_template)
    
    # create an image model tool
    image_tool = Tool(
        name="Image Model",
        func=generate_image,
        description="use this tool to generate images from text",
        return_direct=True)
    
    # create a tool for searching the web
    search = GoogleSearchAPIWrapper(google_api_key=GOOGLE_API_KEY, google_cse_id=GOOGLE_CSE_ID, k=5)

    search_tool = Tool(
        name="Search",
        func=search.run,
        description="""Use this tool to search the web.
                    Useful for when you need to answer questions about current events.
                    Use this more if the question is about technical topics, errors or fixes.""")
    
    # create a tool for wolfram alpha
    wolfram_alpha = WolframAlphaAPIWrapper(wolfram_alpha_appid=WOLFRAM_ALPHA_APPID)

    wolfram_alpha_tool = Tool(
        name="Wolfram Alpha",
        func=wolfram_alpha.run,
        description="""Use this tool to search Wolfram Alpha.
                    Useful for when you need to answer questions about Science, Engineering, Technology, Culture, Society and Everyday Life.""")
    
    # create a tool for the vector database
    # check if the chat_user_id is string
    chat_user_id = str(chat_id)
    db = VectorDB(chat_user_id, openai.api_key)

    vector_db_tool = Tool(
        name="Search User Documents",
        func=db.query,
        description="""Use this tool to search the user documents database.
                    Useful for when you need to answer questions about user's documents.
                    Documents such as PDFs, Word Documents, HTML files, text files, CSV files, etc.""")
    
    # Provide access to a list of tools that the agents will use
    tools = load_tools(['wikipedia',
                        'open-meteo-api',
                        'llm-math'],
                        llm=llm)

    tools.append(image_tool)
    tools.append(search_tool)
    tools.append(wolfram_alpha_tool)
    tools.append(vector_db_tool)
    

    # initialise the agents & make all the tools and llm available to it
    agent = initialize_agent(tools=tools,
                             llm=llm, 
                             agent=AgentType.CONVERSATIONAL_REACT_DESCRIPTION, 
                             verbose=True,
                             handle_parsing_errors="Check your output and make sure it conforms!")

    # Ask questions
    answer = agent.run(input=template, chat_history=formatted_chat_history, return_only_outputs=True)

    return answer


# Message handler
def message_handler(update: Update, context: CallbackContext) -> None:

    # Get the chat id
    chat_id = update.message.chat_id

    # If the chat context is empty, initialize it
    if chat_id not in chat_context:
        chat_context[chat_id] = []

    # Get the user message
    # Check if the message is a voice message
    if update.message.voice:
        # Download the voice message
        file_id = update.message.voice.file_id
        voice_file = context.bot.get_file(file_id)
        voice_file.download("voice_message.ogg")

        # Convert the .ogg file to .mp3
        ogg_audio = AudioSegment.from_ogg("voice_message.ogg")
        ogg_audio.export("voice_message.mp3", format="mp3")

        # Transcribe the voice message
        with open("voice_message.mp3", "rb") as f:
            transcript = transcribe_voice(f)
        user_message = transcript
    elif update.message.audio:
        # Download the audio message
        file_id = update.message.audio.file_id
        audio_file = context.bot.get_file(file_id)
        audio_file.download("audio_message.mp3")

        # Transcribe the audio message
        with open("audio_message.mp3", "rb") as f:
            transcript = transcribe_voice(f)
        user_message = transcript
    else:
        user_message = update.message.text
    
    # Show typing status to the user while the assistant is generating a response
    context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

    # If the user sends a message, send the message to the chatbot
    if user_message:

        # Check if the message is url
        url_pattern = r"(https?://\S+)"
        url_match = re.match(url_pattern, user_message)
        if url_match:
            # If the message is a url, summarize the content
            url = url_match.group(1)
            summary = summarize_url(url, chat_id)
            response = "Summary of the web page: " + summary
            update.message.reply_text(text=response, quote=True)
            user_message = f"{url} saved to my documents database."
        else:
            response = generate_response(user_message, chat_context[chat_id], chat_id)

            # check if the answer has an image url
            image_url_pattern = r"(https://oaidalleapiprodscus\.blob\..*)"
            image_match = re.match(image_url_pattern, response)

            # if the answer has an image url, send the image
            if image_match:
                image_url = image_match.group(1)
                update.message.reply_photo(image_url)
            else:
                # if no image url, send the text
                update.message.reply_text(response)
    else:
        update.message.reply_text("Sorry, I don't understand that. Please try again.")
    
     # Add the user message to the chat context
    chat_context[chat_id].append(
        {"Human": user_message})

    # If the chat context is too long, remove the oldest message
    if len(chat_context[chat_id]) > buffer_size:
        chat_context[chat_id].pop(0)

    # Add the response to the chat context
    chat_context[chat_id].append(
        {"AI": response})

    # If the chat context is too long, remove the oldest message
    if len(chat_context[chat_id]) > buffer_size:
        chat_context[chat_id].pop(0)

    logger.info("Chat history updated")


# Document handler
def document_handler(update: Update, context: CallbackContext) -> None:
    # Get the chat id
    chat_id = update.message.chat_id

    logger.info("Document received")

    # If the chat context is empty, initialize it
    if chat_id not in chat_context:
        chat_context[chat_id] = []

    # Get the document
    file_name = update.message.document.file_name
    file_id = update.message.document.file_id
    file = context.bot.get_file(file_id)
    file.download(file_name)

    logger.info("Document downloaded")

    # Save the document to the vector database
    summary = save_to_database(file_name, chat_id)

    response = "Summary of the document: " + summary

    update.message.reply_text(quote=True, text=response)

    # Add the document to the chat context
    chat_context[chat_id].append(
        {"Human": f"{file_name} saved to my documents database."})

    # If the chat context is too long, remove the oldest message
    if len(chat_context[chat_id]) > buffer_size:
        chat_context[chat_id].pop(0)
    
    # Add the response to the chat context
    chat_context[chat_id].append(
        {"AI": response})
    
    # If the chat context is too long, remove the oldest message
    if len(chat_context[chat_id]) > buffer_size:
        chat_context[chat_id].pop(0)
    
    logger.info("Chat history updated")


# Clear the document database
def clear_database(update: Update, context: CallbackContext) -> None:
    # Get the chat id
    chat_id = update.message.chat_id

    # check if the chat_user_id is string
    if not isinstance(chat_id, str):
        chat_user_id = str(chat_id)

    db = VectorDB(chat_user_id, openai.api_key)

    # Clear the database
    db.clear_database()

    update.message.reply_text(text="Database cleared.")


# Donation
def donate(update: Update, context: CallbackContext) -> None:
    out = context.bot.send_invoice(
        chat_id=update.message.chat_id,
        title="Test donation",
        description="Donate money here.",
        payload="test",
        provider_token=STRIPE_TOKEN,
        currency="USD",
        prices=[LabeledPrice("Give", 2000)],
        need_name=False,
    )


# Pre-checkout handler
def pre_checkout_handler(update: Update, context: CallbackContext) -> None:
    """https://core.telegram.org/bots/api#answerprecheckoutquery"""
    query = update.pre_checkout_query
    query.answer(ok=True)


# Successful payment
def successful_payment_callback(update: Update, context: CallbackContext) -> None:
    update.message.reply_text("Thank you for your purchase!")


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
    #dispatcher.add_handler(CommandHandler("setapikey", set_api_key))
    dispatcher.add_handler(CommandHandler("donate", donate))
    dispatcher.add_handler(CommandHandler("clear_database", clear_database))
    dispatcher.add_handler(PreCheckoutQueryHandler(pre_checkout_handler))
    dispatcher.add_handler(MessageHandler(
        Filters.successful_payment, successful_payment_callback))
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