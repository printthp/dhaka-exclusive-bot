import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN", "")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "dhaka123")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

def get_claude_response(user_message):
    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json={
                "model": "claude-haiku-20240307",
                "max_tokens": 500,
                "system": "তুমি Dhaka Exclusive-এর কাস্টমার সার্ভিস AI। বাংলায় সংক্ষিপ্ত ও বিনয়ী উত্তর দাও।",
                "messages": [{"role": "user", "content": user_message}]
            }
        )
        data = response.json()
        return data["content"][0]["text"]
    except Exception as e:
        print(f"Error: {e}")
        return "দুঃখিত, একটু পরে চেষ্টা করুন।"

def send_message(recipient_id, text):
    requests.post(
        "https://graph.facebook.com/v18.0/me/messages",
        params={"access_token": PAGE_ACCESS_TOKEN},
        json={
            "recipient": {"id": recipient_id},
            "message": {"text": text}
        }
    )

@app.route("/webhook", methods=["GET"])
def verify():
    if request.args.get("hub.verify_token") == VERIFY_TOKEN:
        return request.args.get("hub.challenge"), 200
    return "Error", 403

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    print("DATA:", data)
    try:
        for entry in data.get("entry", []):
            for event in entry.get("messaging", []):
                if "message" in event and "text" in event["message"]:
                    sender_id = event["sender"]["id"]
                    text = event["message"]["text"]
                    reply = get_claude_response(text)
                    send_message(sender_id, reply)
    except Exception as e:
        print(f"Webhook error: {e}")
    return "OK", 200

@app.route("/")
def home():
    return "Dhaka Exclusive Bot Running ✅", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
