from abc import ABC, abstractmethod

class BaseBot(ABC):

    @abstractmethod
    def send_message(self, recipient_id: str, message: str) -> None:
        """
        Send a message to the specified recipient.

        :param recipient_id: The unique identifier of the recipient.
        :param message: The message text to send.
        """
        pass

    @abstractmethod
    def receive_message(self, sender_id: str, message: str) -> None:
        """
        Process a received message from the specified sender.

        :param sender_id: The unique identifier of the sender.
        :param message: The message text received.
        """
        pass

    @abstractmethod
    def handle_command(self, command: str, *args, **kwargs) -> None:
        """
        Handle a command sent by a user or an admin.

        :param command: The command to be executed.
        :param args: Positional arguments for the command.
        :param kwargs: Keyword arguments for the command.
        """
        pass
