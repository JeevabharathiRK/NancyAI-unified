import os
import requests
import atexit  # Add this import
from flask import Flask, request, jsonify
from meta_ai_api import MetaAI  # Assuming this is the correct import for MetaAI
from apscheduler.schedulers.background import BackgroundScheduler
from api.nancy import Nancy
import sys
import signal

app = Flask(__name__)

# Your bot's token from environment variables
# BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
BASE_URL = f"https://api.telegram.org/bot7667169314:AAF1nnqQhFs_M1U3nQJ9CDS2UHP6apw7XbY"#{BOT_TOKEN}"

# Set your bot's webhook URL
WEBHOOK_URL = "https://meta-ai-chatbot.onrender.com/webhook"#"https://amateur-augustina-tamil-developer-5493a7ee.koyeb.app/webhook"

# Dictionary to store Nancy instances per user
user_sessions = {}

@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle incoming Telegram updates."""
    data = request.get_json()

    if 'message' in data:
        chat_id = data['message']['chat']['id']
        message_id = data['message']["message_id"]

        # Check if the message is text; if not, respond with an error message
        if 'text' in data['message']:
            message_text = data['message']['text'].lower()

            # Create a new instance of Nancy for each new user
            if chat_id not in user_sessions:
                user_sessions[chat_id] = Nancy()

            # Retrieve the user's Nancy instance
            nancy_instance = user_sessions[chat_id]

            # Get Nancy's response
            response = nancy_instance.prompt(message_text)

            # Send the response as a reply to the specific message
            send_message(chat_id, response, message_id)

        else:
            # If the message is not text (e.g., photo, file), send an error message
            send_message(chat_id, "Sorry, I can only process text messages for now.", message_id)

    return jsonify({"status": "ok"})


def send_message(chat_id, text, reply_to_message_id):
    """Send a message to the chat."""
    parameters = {
        "chat_id": chat_id,
        "text": text,
        "reply_to_message_id": reply_to_message_id  # Reply to the specific message
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


def restart_app():
    """Function to restart the app."""
    print("Restarting the app...")
    os.kill(os.getpid(), signal.SIGTERM)


if __name__ == '__main__':
    # Set webhook when the app starts
    set_webhook()

    # Schedule the app to restart every 30 minutes
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=restart_app, trigger="interval", minutes=30)
    scheduler.start()

    # Start Flask server to listen to incoming webhook events
    port = int(os.environ.get('PORT', 8000))  # Get the port from environment or default to 8000
    app.run(host="0.0.0.0", port=port)

    # Shut down the scheduler when exiting the app
    atexit.register(lambda: scheduler.shutdown())
