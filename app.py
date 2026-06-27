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
                "model": "claude-haiku-4-5",
                "max_tokens": 500,
                "system": "তুমি Dhaka Exclusive-এর কাস্টমার সার্ভিস AI। বাংলায় সংক্ষিপ্ত ও বিনয়ী উত্তর দাও।",
                "messages": [{"role": "user", "content": user_message}]
            }
        )
        data = response.json()
        print(f"Claude full response: {data}")
        if "content" in data:
            return data["content"][0]["text"]
        else:
            print(f"Claude error details: {data}")
            return "দুঃখিত, একটু পরে চেষ্টা করুন।"
    except Exception as e:
        print(f"Exception: {e}")
        return "দুঃখিত, একটু পরে চেষ্টা করুন।"

def send_message(recipient_id, text):
    response = requests.post(
        "https://graph.facebook.com/v18.0/me/messages",
        params={"access_token": PAGE_ACCESS_TOKEN},
        json={
            "recipient": {"id": recipient_id},
            "message": {"text": text}
        }
    )
    print(f"Send message result: {response.json()}")

@app.route("/webhook", methods=["GET"])
def verify():
    if request.args.get("hub.verify_token") == VERIFY_TOKEN:
        return request.args.get("hub.challenge"), 200
    return "Error", 403

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    print(f"DATA: {data}")
    try:
        for entry in data.get("entry", []):
            for event in entry.get("messaging", []):
                if "message" in event and "text" in event["message"]:
                    sender_id = event["sender"]["id"]
                    text = event["message"]["text"]
                    print(f"User said: {text}")
                    reply = get_claude_response(text)
                    print(f"Bot reply: {reply}")
                    send_message(sender_id, reply)
    except Exception as e:
        print(f"Webhook error: {e}")
    return "OK", 200

@app.route("/")
def home():
    return "Dhaka Exclusive Bot Running ✅", 200

@app.route("/privacy")
def privacy():
    return """
    <h1>Privacy Policy - Dhaka Exclusive</h1>
    <p>আমরা আপনার ব্যক্তিগত তথ্য সংগ্রহ করি না।</p>
    <p>Facebook Messenger-এর মাধ্যমে আসা মেসেজ শুধু কাস্টমার সার্ভিসের জন্য ব্যবহার করা হয়।</p>
    <p>যোগাযোগ: dhakaexclusive.com</p>
    """, 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
