from app.core.webhook_handler import BaseWebhookHandler
from whatsapp import WhatsAppClient


class WhatsAppWebhookHandler(BaseWebhookHandler):

    def __init__(self, token: str):
        self.client = WhatsAppClient(token)

    async def set_webhook(self, webhook_url: str) -> None:
        await self.client.set_webhook(url=webhook_url)

    async def handle_update(self, update: dict) -> None:
        # Process the incoming update from WhatsApp.
        # You'll need to implement this based on the library you choose.
