import os
import requests
from flask import Flask, request, jsonify
import anthropic

app = Flask(__name__)

PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """তুমি Dhaka Exclusive-এর কাস্টমার সার্ভিস AI assistant।
তোমার কাজ:
- কাস্টমারদের প্রোডাক্ট সম্পর্কে তথ্য দেওয়া
- অর্ডার সংক্রান্ত প্রশ্নের উত্তর দেওয়া
- বাংলায় বা ইংরেজিতে উত্তর দেওয়া (কাস্টমার যে ভাষায় লিখবে)
- সবসময় বিনয়ী ও সহায়ক থাকা
- প্রয়োজনে অর্ডার করতে সাহায্য করা"""

def get_claude_response(user_message):
    try:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=500,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}]
        )
        return message.content[0].text
    except Exception as e:
        print(f"Claude error: {e}")
        return "দুঃখিত, এই মুহূর্তে উত্তর দিতে পারছি না। অনুগ্রহ করে একটু পরে চেষ্টা করুন।"

def send_message(recipient_id, message_text):
    url = "https://graph.facebook.com/v18.0/me/messages"
    headers = {"Content-Type": "application/json"}
    params = {"access_token": PAGE_ACCESS_TOKEN}
    data = {
        "recipient": {"id": recipient_id},
        "message": {"text": message_text}
    }
    response = requests.post(url, headers=headers, params=params, json=data)
    print(f"Send message response: {response.json()}")
    return response.json()

@app.route("/webhook", methods=["GET"])
def verify_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    print(f"Webhook verify: mode={mode}, token={token}")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
    return "Forbidden", 403

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    print(f"Received webhook data: {data}")

    if data.get("object") == "page":
        for entry in data.get("entry", []):
            for event in entry.get("messaging", []):
                sender_id = event["sender"]["id"]
                if "message" in event and "text" in event["message"]:
                    user_text = event["message"]["text"]
                    print(f"Message from {sender_id}: {user_text}")
                    reply = get_claude_response(user_text)
                    send_message(sender_id, reply)

    return jsonify({"status": "ok"}), 200

@app.route("/", methods=["GET"])
def home():
    return "Dhaka Exclusive Bot is running! ✅", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
