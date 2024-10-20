import os
import requests
import atexit
from flask import Flask, request, jsonify
from api.nancy import Nancy
from apscheduler.schedulers.background import BackgroundScheduler
import signal

app = Flask(__name__)

#Environment variables
TG_BOT_TOKEN = os.environ['TG_BOT_TOKEN']
WEBHOOK_URL = os.environ['WEBHOOK_URL']
BASE_URL = f"https://api.telegram.org/bot{TG_BOT_TOKEN}"
# Your bot's token from environment variables
# BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
BASE_URL = f"https://api.telegram.org/bot7667169314:AAF1nnqQhFs_M1U3nQJ9CDS2UHP6apw7XbY"#{BOT_TOKEN}"

# Set your bot's webhook URL
WEBHOOK_URL = "https://meta-ai-chatbot.onrender.com/webhook"#"https://amateur-augustina-tamil-developer-5493a7ee.koyeb.app/webhook"

# Dictionary to store Nancy instances per user
user_sessions = {}

nancy = Nancy()
@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle incoming Telegram updates."""
    data = request.get_json()
    read_msg(nancy,data)
    return jsonify({"status": "ok"})

def read_msg(nancy, data):
    try:

        if 'message' in data:
            chat_id = data['message']['chat']['id']
            msg_id = data['message']["message_id"]
            username = data["message"]["from"].get("username", "Unknown")

            if "text" in data["message"]:
                msg = data["message"]["text"]

                if msg.startswith("/select"):
                    if msg.strip() == "/select":
                        available_models = ", ".join(nancy.models.keys())
                        send_msg(f"Available models for selection: {available_models}", msg_id, chat_id)
                        return

                    # Extract the model name from the message
                    model_key = msg.split()[1] if len(msg.split()) > 1 else None
                    new_model = nancy.models.get(model_key, None)

                    if not new_model:
                        send_msg("Invalid model selection. Available models: google-gemma, meta-llama.", msg_id, chat_id)
                        return

                    # Change model for the specific chat ID
                    old_model, updated_model = nancy.change_model_for_chat(chat_id, new_model)
                    send_msg(f"Model changed from {old_model} to {updated_model}.", msg_id, chat_id)

                # Check for the /model command to report the current model
                elif msg.startswith("/model"):
                    current_model = nancy.get_model_for_chat(chat_id)
                    send_msg(f"The current model for this chat is {current_model}.", msg_id, chat_id)

                else:
                    # Handle normal text messages
                    send_msg(nancy.prompt(msg, chat_id), msg_id, chat_id)

            elif "photo" in data["message"]:

                file_id = data["message"]["photo"][-1]["file_id"]
                file_url = requests.get(f"{BASE_URL}/getFile?file_id={file_id}").json()["result"]["file_path"]
                image_url = f"https://api.telegram.org/file/bot{TG_BOT_TOKEN}/{file_url}"
                caption = data["message"].get("caption", "")

                # Analyze the image
                analysis_result = nancy.analyze_image(image_url, caption, chat_id)
                send_msg(analysis_result, msg_id, chat_id)

    except Exception as e:
        print(f"Error reading message: {str(e)}")


def send_msg(text, message_id, chat_id):
    """Sends a message back to the user."""
    parameters = {
        "chat_id": chat_id,
        "text": text,
        "reply_to_message_id": message_id
    }
    try:
        resp = requests.get(BASE_URL + "/sendMessage", params=parameters)
        if resp.status_code == 200:
            print(f"Message sent to chat_id {chat_id}: {text}")
        else:
            print(f"Failed to send message to chat_id {chat_id}: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"Error sending message: {str(e)}")


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
    port = int(os.environ.get('PORT', 8000))
    app.run(host="0.0.0.0", port=port)

    # Shut down the scheduler when exiting the app
    atexit.register(lambda: scheduler.shutdown())
