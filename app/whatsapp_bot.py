"""
A simple FastAPI app that receives messages from the WhatsApp API and sends a response.
"""
from fastapi import FastAPI, Request
import uvicorn
import logging
import os

from bot_template.whatsapp_bot import WhatsAppBot

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
bot = WhatsAppBot()
VERIFY_TOKEN = os.environ.get('WHATSAPP_VERIFY_TOKEN')

@app.get("/webhook", include_in_schema=False)
async def verify(request: Request):
    if request.query_params.get('hub.mode') == "subscribe" and request.query_params.get("hub.challenge"):
        if not request.query_params.get('hub.verify_token') == VERIFY_TOKEN:
            return "Verification token mismatch", 403
        return int(request.query_params.get('hub.challenge'))
    return "Hello world", 200

@app.post("/webhook", include_in_schema=False)
async def webhook(request: Request):
    data = await request.json()
    logger.info(f"Received webhook data: {data}")

    # process the webhook data
    data = bot.process_webhook(data)
    if data["type"] == "text":
        # send a response
        bot.send_message("Hello world!", data["phone_number"])
    elif data["type"] == "image":
        # send a response
        bot.send_message("Thanks for the image!", data["phone_number"])

    return "ok"

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)