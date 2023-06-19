from abc import ABC, abstractmethod


class BaseWebhookHandler(ABC):

    @abstractmethod
    async def set_webhook(self, webhook_url: str) -> None:
        """
        Set the webhook URL for the messaging platform.

        :param webhook_url: The URL to which the messaging platform should send updates.
        """
        pass

    @abstractmethod
    async def handle_update(self, update: dict) -> None:
        """
        Process an incoming update from the messaging platform.

        :param update: The update data received from the messaging platform.
        """
        pass
