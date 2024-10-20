import os
import requests
from flask import Flask, request, jsonify
from api.nancy import Nancy

app = Flask(__name__)

# Environment variables
TG_BOT_TOKEN = os.environ['TG_BOT_TOKEN']
WEBHOOK_URL = os.environ['WEBHOOK_URL']
BASE_URL = f"https://api.telegram.org/bot{TG_BOT_TOKEN}"

nancy = Nancy()

@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle incoming Telegram updates."""
    data = request.get_json()
    read_msg(nancy, data)
    return jsonify({"status": "ok"})

def read_msg(nancy, data):
    if 'message' in data:
        chat_id = data['message']['chat']['id']
        msg_id = data['message']["message_id"]

        # Check for text messages
        if "text" in data["message"]:
            msg = data["message"]["text"]
            if msg.startswith("/select"):
                handle_select_command(nancy, msg, msg_id, chat_id)
            elif msg.startswith("/model"):
                current_model = nancy.get_model_for_chat(chat_id)
                send_msg(f"Current model: {current_model}", msg_id, chat_id)
            else:
                send_msg(nancy.prompt(msg, chat_id), msg_id, chat_id)

        # Check for images (photos)
        elif "photo" in data["message"]:
            file_id = data["message"]["photo"][-1]["file_id"]
            file_url = requests.get(f"{BASE_URL}/getFile?file_id={file_id}").json()["result"]["file_path"]
            image_url = f"https://api.telegram.org/file/bot{TG_BOT_TOKEN}/{file_url}"
            caption = data["message"].get("caption", "")

            # Analyze the image using Nancy
            analysis_result = nancy.analyze_image(image_url, caption, chat_id)
            send_msg(analysis_result, msg_id, chat_id)

def handle_select_command(nancy, msg, msg_id, chat_id):
    if msg.strip() == "/select":
        available_models = ", ".join(nancy.models.keys())
        send_msg(f"Available models: {available_models}", msg_id, chat_id)
        return

    model_key = msg.split()[1] if len(msg.split()) > 1 else None
    new_model = nancy.models.get(model_key)

    if new_model:
        old_model, updated_model = nancy.change_model_for_chat(chat_id, new_model)
        send_msg(f"Model changed from {old_model} to {updated_model}.", msg_id, chat_id)
    else:
        send_msg("Invalid model. Use /select to see available models.", msg_id, chat_id)

def send_msg(text, message_id, chat_id):
    """Sends a message to the user."""
    params = {"chat_id": chat_id, "text": text, "reply_to_message_id": message_id}
    requests.get(BASE_URL + "/sendMessage", params=params)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 8000)))
