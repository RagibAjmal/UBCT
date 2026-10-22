# grants/utils.py
import requests
from django.conf import settings

def send_whatsapp_message(to_number, message_text):
    if not settings.WHATSAPP_ACCESS_TOKEN:
        return  # Fail silently if credentials aren't set up yet
        
    url = f"https://graph.facebook.com/v17.0/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    # Note: For production, you will likely need to use "template" types instead of "text"
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {"body": message_text}
    }
    
    requests.post(url, json=payload, headers=headers)