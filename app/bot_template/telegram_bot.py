from app.core.base_bot import BaseBot
from telegram import Bot, Update
from telegram.ext import MessageHandler, filters, CallbackContext


class TelegramBot(BaseBot):

    def __init__(self, token: str):
        self.bot = Bot(token)
        self.bot.set_message_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND, self.receive_message))

    def send_message(self, recipient_id: str, message: str) -> None:
        self.bot.send_message(chat_id=recipient_id, text=message)

    def receive_message(self, update: Update, context: CallbackContext) -> None:
        sender_id = update.effective_chat.id
        message = update.effective_message.text
        self.handle_command(sender_id, message)

    def handle_command(self, sender_id: str, command: str, *args, **kwargs) -> None:
        # Implement command handling logic here
        pass
