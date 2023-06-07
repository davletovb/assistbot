import os
from whatsapp_wrapper import WhatsAppWrapper, WhatsAppAPIError
from typing import List

class WhatsAppBot(WhatsAppWrapper):
    def __init__(self):
        api_token = os.environ.get("WHATSAPP_API_TOKEN")
        number_id = os.environ.get("WHATSAPP_NUMBER_ID")
        super().__init__(api_token, number_id)

    def send_message(self, message: str, phone_number: str) -> int:
        return super().send_message(message, phone_number)

    def send_menu(self, phone_number: str, title: str, options: List[str]) -> int: 
        return super().send_menu(phone_number, title, options)

    def send_buttons(self, phone_number: str, button_text: str, button_titles: List[str]) -> int:
        return super().send_buttons(phone_number, button_text, button_titles)
    
    def send_image(self, phone_number: str, image_url: str, caption: str = None) -> int:
        return super().send_image(phone_number, image_url, caption)
    
    def send_audio(self, phone_number: str, audio_url: str) -> int:
        return super().send_audio(phone_number, audio_url)
    
    def send_video(self, phone_number: str, video_url: str, caption: str = None) -> int:
        return super().send_video(phone_number, video_url, caption)
    
    def send_document(self, phone_number: str, document_url: str, file_name: str) -> int:
        return super().send_document(phone_number, document_url, file_name)
