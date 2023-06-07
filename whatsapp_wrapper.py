import requests
import json
import os
from typing import List
import logging

WHATSAPP_PRODUCT = "whatsapp"
INDIVIDUAL_RECIPIENT = "individual"

class WhatsAppAPIError(Exception):
    """Exception raised for WhatsApp API errors."""

class WhatsAppWrapper:
    """A wrapper for the WhatsApp Cloud API."""

    API_URL = "https://graph.facebook.com/v17.0/"
    API_TOKEN = os.environ.get("WHATSAPP_API_TOKEN")
    NUMBER_ID = os.environ.get("WHATSAPP_NUMBER_ID")
    
    def __init__(self):
        self.API_URL = f"{self.API_URL}{self.NUMBER_ID}/messages"
        self.headers = {
            "Authorization": f"Bearer {self.API_TOKEN}",
            "Content-Type": "application/json"
        }
    
    def __repr__(self):
        return f"<WhatsAppWrapper NUMBER_ID={self.NUMBER_ID}>"
    
    def send_message(self, message: str, phone_number: str) -> int:
        """Sends a text message to a WhatsApp number."""
        data = {
            "messaging_product": WHATSAPP_PRODUCT,
            "recipient_type": INDIVIDUAL_RECIPIENT,
            "to": phone_number,
            "type": "text",
            "text": {"body": message}
        }
        try: 
            response = requests.post(self.API_URL, headers=self.headers, data=json.dumps(data))
            response.raise_for_status()
        except requests.HTTPError as err:
            raise WhatsAppAPIError(f"Error sending message: {err}")
        return response.status_code
    
    def send_menu(self, phone_number: str, title: str, options: List[str]) -> int: 
        """Sends a menu with options to a WhatsApp number.""" 
        buttons = [
            {
                "type": "postback", 
                "title": option, 
                "payload": option
            } for option in options
        ] 
        
        data = { 
            "messaging_product": WHATSAPP_PRODUCT, 
            "recipient_type": INDIVIDUAL_RECIPIENT, 
            "to": phone_number, 
            "type": "template", 
            "template": 
                { 
                "type": "button", 
                "text": {"body": title},
                "buttons": buttons }
            } 
        try: 
            response = requests.post(self.API_URL, headers=self.headers, data=json.dumps(data)) 
            response.raise_for_status() 
        except requests.HTTPError as err: 
            raise WhatsAppAPIError(f"Error sending menu: {err}") 
        return response.status_code
    
    def send_buttons(self, phone_number: str, button_text: str, button_titles: List[str]) -> int:
        """Sends buttons with reply actions to a WhatsApp number."""
        buttons = [
            {
                "type": "reply",
                "reply": {
                    "id": f"UNIQUE_BUTTON_ID_{i}",
                    "title": title
                }
            } for i, title in enumerate(button_titles, start=1)
        ]

        data = {
            "messaging_product": WHATSAPP_PRODUCT,
            "recipient_type": INDIVIDUAL_RECIPIENT,
            "to": phone_number,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {
                    "text": button_text
                },
                "action": {
                    "buttons": buttons
                }
            }
        }
        try:
            response = requests.post(self.API_URL, headers=self.headers, data=json.dumps(data))
            response.raise_for_status()
        except requests.HTTPError as err:
            raise WhatsAppAPIError(f"Error sending buttons: {err}")
        return response.status_code

    def send_image(self, phone_number: str, image_url: str, caption: str = None) -> int:
        """Sends an image to a WhatsApp number."""
        data = {
            "messaging_product": WHATSAPP_PRODUCT,
            "recipient_type": INDIVIDUAL_RECIPIENT,
            "to": phone_number,
            "type": "image",
            "image": {"url": image_url}
        }
        if caption:
            data["image"]["caption"] = caption

        try:
            response = requests.post(self.API_URL, headers=self.headers, data=json.dumps(data))
            response.raise_for_status()
        except requests.HTTPError as err:
            raise WhatsAppAPIError(f"Error sending image: {err}")
        return response.status_code

    def send_audio(self, phone_number: str, audio_url: str) -> int:
        """Sends an audio message to a WhatsApp number."""
        data = {
            "messaging_product": WHATSAPP_PRODUCT,
            "recipient_type": INDIVIDUAL_RECIPIENT,
            "to": phone_number,
            "type": "audio",
            "audio": {"url": audio_url}
        }
        try:
            response = requests.post(self.API_URL, headers=self.headers, data=json.dumps(data))
            response.raise_for_status()
        except requests.HTTPError as err:
            raise WhatsAppAPIError(f"Error sending audio: {err}")
        return response.status_code

    def send_video(self, phone_number: str, video_url: str, caption: str = None) -> int:
        """Sends a video to a WhatsApp number."""
        data = {
            "messaging_product": WHATSAPP_PRODUCT,
            "recipient_type": INDIVIDUAL_RECIPIENT,
            "to": phone_number,
            "type": "video",
            "video": {"url": video_url}
        }
        if caption:
            data["video"]["caption"] = caption

        try:
            response = requests.post(self.API_URL, headers=self.headers, data=json.dumps(data))
            response.raise_for_status()
        except requests.HTTPError as err:
            raise WhatsAppAPIError(f"Error sending video: {err}")
        return response.status_code

    def send_document(self, phone_number: str, document_url: str, file_name: str) -> int:
        """Sends a document to a WhatsApp number."""
        data = {
            "messaging_product": WHATSAPP_PRODUCT,
            "recipient_type": INDIVIDUAL_RECIPIENT,
            "to": phone_number,
            "type": "document",
            "document": {
                "url": document_url,
                "filename": file_name
            }
        }
        try:
            response = requests.post(self.API_URL, headers=self.headers, data=json.dumps(data))
            response.raise_for_status()
        except requests.HTTPError as err:
            raise WhatsAppAPIError(f"Error sending document: {err}")
        return response.status_code
