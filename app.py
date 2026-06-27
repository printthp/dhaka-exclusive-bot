import os
import requests
import threading
import time
from flask import Flask, request, jsonify

app = Flask(__name__)

PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN", "")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "dhaka123")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
RAILWAY_URL = os.environ.get("RAILWAY_URL", "https://web-production-126eb.up.railway.app")

SYSTEM_PROMPT = """তুমি Dhaka Exclusive-এর AI কাস্টমার সার্ভিস assistant।
ওয়েবসাইট: https://dhakaexclusive.org

তোমার কাজ:
- কাস্টমার বাংলায় বা ইংরেজিতে যেভাবে লিখবে সেভাবে উত্তর দাও
- প্রোডাক্টের দাম, স্টক, ডেলিভারি সম্পর্কে তথ্য দাও
- অর্ডার করতে সাহায্য করো
- সবসময় বিনয়ী ও সহায়ক থাকো
- কাস্টমার ছবি পাঠালে বলো: "আপনার পছন্দের পণ্যটি দেখুন আমাদের ওয়েবসাইটে: https://dhakaexclusive.org"
- কমেন্টে সংক্ষিপ্ত ও আকর্ষণীয় উত্তর দাও
- শেষে সবসময় ওয়েবসাইট লিংক দাও: https://dhakaexclusive.org"""

def get_claude_response(user_message, is_comment=False):
    try:
        system = SYSTEM_PROMPT
        if is_comment:
            system += "\n\nএটি একটি Facebook পোস্টের কমেন্ট। সংক্ষিপ্ত ও আকর্ষণীয় রিপ্লাই দাও।"

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
                "system": system,
                "messages": [{"role": "user", "content": user_message}]
            }
        )
        data = response.json()
        if "content" in data:
            return data["content"][0]["text"]
        else:
            print(f"Claude error: {data}")
            return "ধন্যবাদ! বিস্তারিত জানতে ভিজিট করুন: https://dhakaexclusive.org"
    except Exception as e:
        print(f"Exception: {e}")
        return "ধন্যবাদ! বিস্তারিত জানতে ভিজিট করুন: https://dhakaexclusive.org"

def send_message(recipient_id, text):
    response = requests.post(
        "https://graph.facebook.com/v18.0/me/messages",
        params={"access_token": PAGE_ACCESS_TOKEN},
        json={
            "recipient": {"id": recipient_id},
            "message": {"text": text}
        }
    )
    print(f"Send message: {response.json()}")

def reply_comment(comment_id, text):
    response = requests.post(
        f"https://graph.facebook.com/v18.0/{comment_id}/replies",
        params={"access_token": PAGE_ACCESS_TOKEN},
        json={"message": text}
    )
    print(f"Comment reply: {response.json()}")

def keep_alive():
    while True:
        time.sleep(600)
        try:
            requests.get(f"{RAILWAY_URL}/")
            print("Keep alive ping sent")
        except:
            pass

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
        # Messenger মেসেজ
        if data.get("object") == "page":
            for entry in data.get("entry", []):
                # মেসেজ হ্যান্ডেল
                for event in entry.get("messaging", []):
                    sender_id = event["sender"]["id"]
                    if "message" in event:
                        msg = event["message"]
                        if "text" in msg:
                            text = msg["text"]
                            print(f"User said: {text}")
                            reply = get_claude_response(text)
                            send_message(sender_id, reply)
                        elif "attachments" in msg:
                            # ছবি পাঠালে
                            reply = get_claude_response("কাস্টমার একটি ছবি পাঠিয়েছে, প্রোডাক্ট সম্পর্কে জানতে চাইছে")
                            send_message(sender_id, reply)

                # কমেন্ট হ্যান্ডেল
                for change in entry.get("changes", []):
                    if change.get("field") == "feed":
                        value = change.get("value", {})
                        if value.get("item") == "comment" and value.get("verb") == "add":
                            comment_id = value.get("comment_id")
                            comment_text = value.get("message", "")
                            print(f"Comment: {comment_text}")
                            if comment_text:
                                reply = get_claude_response(comment_text, is_comment=True)
                                reply_comment(comment_id, reply)

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
    <p>যোগাযোগ: dhakaexclusive.org</p>
    """, 200

# Keep alive thread শুরু করো
thread = threading.Thread(target=keep_alive)
thread.daemon = True
thread.start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
