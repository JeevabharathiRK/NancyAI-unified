import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# Your bot's token from environment variables
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# Set your bot's webhook URL
WEBHOOK_URL = "https://amateur-augustina-tamil-developer-5493a7ee.koyeb.app/webhook"  # Replace with your actual deployment URL


@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle incoming Telegram updates."""
    data = request.get_json()

    if 'message' in data:
        message_text = data['message'].get('text', '').lower()
        chat_id = data['message']['chat']['id']

        if "hi" in message_text:
            send_message(chat_id, "Hai Jeeva!!")

    return jsonify({"status": "ok"})


def send_message(chat_id, text):
    """Send a message to the chat."""
    parameters = {
        "chat_id": chat_id,
        "text": text
    }
    response = requests.get(BASE_URL + "/sendMessage", params=parameters)
    return response.json()


def set_webhook():
    """Set the webhook for Telegram."""
    url = BASE_URL + "/setWebhook"
    params = {"url": WEBHOOK_URL}
    response = requests.get(url, params=params)
    if response.status_code == 200:
        print("Webhook set successfully!")
    else:
        print("Failed to set webhook:", response.text)


if __name__ == '__main__':
    # Set webhook when the app starts
    set_webhook()
    
    # Start Flask server to listen to incoming webhook events
    port = int(os.environ.get('PORT', 8000))  # Get the port from environment or default to 8000
    app.run(host="0.0.0.0", port=port)
