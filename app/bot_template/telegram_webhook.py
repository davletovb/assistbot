from app.core.webhook_handler import BaseWebhookHandler
from telegram import Update, Bot
from telegram.ext import Dispatcher


class TelegramWebhookHandler(BaseWebhookHandler):

    def __init__(self, token: str):
        self.bot = Bot(token)
        self.dispatcher = Dispatcher(self.bot, None, workers=0)

    async def set_webhook(self, webhook_url: str) -> None:
        await self.bot.set_webhook(url=webhook_url)

    async def handle_update(self, update: dict) -> None:
        tg_update = Update.de_json(update, self.bot)
        self.dispatcher.process_update(tg_update)
