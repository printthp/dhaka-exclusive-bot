import os
import requests
import threading
import time
import base64
from flask import Flask, request, jsonify

app = Flask(__name__)

PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN", "")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "dhaka123")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
CATALOGUE_ID = "4177718442481756"
RAILWAY_URL = os.environ.get("RAILWAY_URL", "https://web-production-126eb.up.railway.app")

# কাস্টমারের conversation history রাখবো
conversation_history = {}

def get_catalogue_products():
    try:
        url = f"https://graph.facebook.com/v18.0/{CATALOGUE_ID}/products"
        params = {
            "access_token": PAGE_ACCESS_TOKEN,
            "fields": "name,price,currency,availability,description,url",
            "limit": 50
        }
        response = requests.get(url, params=params)
        data = response.json()
        if "data" in data and len(data["data"]) > 0:
            text = ""
            for p in data["data"][:50]:
                name = p.get("name", "")
                price = p.get("price", "")
                avail = "আছে" if p.get("availability") == "in stock" else "নেই"
                text += f"{name} | {price} | স্টক: {avail}\n"
            return text
        return ""
    except Exception as e:
        print(f"Catalogue error: {e}")
        return ""

def analyze_image(image_url, catalogue_data):
    try:
        img_response = requests.get(image_url, timeout=10)
        if img_response.status_code != 200:
            return "ছবিটা ঠিকমতো আসেনি, আরেকটু পরে পাঠান।"
        
        image_data = base64.b64encode(img_response.content).decode('utf-8')
        content_type = img_response.headers.get('content-type', 'image/jpeg')

        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json={
                "model": "claude-haiku-4-5",
                "max_tokens": 200,
                "system": f"""তুমি Dhaka Exclusive-এর কাস্টমার সার্ভিস রিয়া।
কাস্টমার একটা ছবি পাঠিয়েছে।

আমাদের প্রোডাক্ট লিস্ট:
{catalogue_data}

ছবি দেখে প্রোডাক্ট চেনো এবং আমাদের catalogue থেকে মিলিয়ে দাম বলো।
যদি না থাকে: "এই প্রোডাক্টটা এখন আমাদের কাছে নেই, তবে আমাদের ওয়েবসাইটে দেখুন: dhakaexclusive.org"
স্বাভাবিক বাংলায় ২-৩ লাইনে বলো।""",
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "image", "source": {"type": "base64", "media_type": content_type, "data": image_data}},
                        {"type": "text", "text": "এই প্রোডাক্টের দাম কত?"}
                    ]
                }]
            }
        )
        data = response.json()
        if "content" in data:
            return data["content"][0]["text"]
        return "ছবিটা দেখতে পাচ্ছি না, একটু বড় করে পাঠান।"
    except Exception as e:
        print(f"Image error: {e}")
        return "ছবিটা দেখতে পাচ্ছি না, টেক্সটে লিখে জানান কী দরকার।"

def get_claude_response(sender_id, user_message, catalogue_data, is_comment=False):
    try:
        # Conversation history রাখো
        if sender_id not in conversation_history:
            conversation_history[sender_id] = []
        
        conversation_history[sender_id].append({
            "role": "user",
            "content": user_message
        })
        
        # শুধু শেষ ১০টা message রাখো
        if len(conversation_history[sender_id]) > 10:
            conversation_history[sender_id] = conversation_history[sender_id][-10:]

        system = f"""তুমি Dhaka Exclusive-এর কাস্টমার সার্ভিস প্রতিনিধি রিয়া।

তোমার ব্যক্তিত্ব:
- মিষ্টি, বন্ধুত্বপূর্ণ, ধৈর্যশীল
- একদম মানুষের মতো কথা বলো
- কাস্টমার যা জিজ্ঞেস করে ঠিক সেটার উত্তর দাও
- অতিরিক্ত তথ্য দিও না
- ছোট ছোট বাক্যে কথা বলো
- emoji একটু ব্যবহার করো, বেশি না
- bold বা markdown ব্যবহার করো না
- website link শুধু দরকার হলে দাও, বারবার না

কথা বলার ধরন:
- "জি আপু/ভাই" দিয়ে শুরু করো
- কাস্টমার বাংলায় লিখলে বাংলায়, ইংরেজিতে লিখলে বাংলায় উত্তর দাও
- দাম জিজ্ঞেস করলে সরাসরি দাম বলো
- প্রোডাক্ট না থাকলে বিকল্প suggest করো
- অর্ডার করতে চাইলে website link দাও

আমাদের প্রোডাক্ট:
{catalogue_data if catalogue_data else "এই মুহূর্তে লোড হয়নি"}

ওয়েবসাইট: dhakaexclusive.org"""

        if is_comment:
            system += "\n\nএটা পোস্টের কমেন্ট। ১-২ লাইনে উত্তর দাও, inbox এ আসতে বলো।"

        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json={
                "model": "claude-haiku-4-5",
                "max_tokens": 300,
                "system": system,
                "messages": conversation_history[sender_id]
            }
        )
        data = response.json()
        if "content" in data:
            reply = data["content"][0]["text"]
            # Reply history তে রাখো
            conversation_history[sender_id].append({
                "role": "assistant",
                "content": reply
            })
            return reply
        return "একটু সমস্যা হচ্ছে, একটু পরে আবার বলুন।"
    except Exception as e:
        print(f"Claude error: {e}")
        return "একটু সমস্যা হচ্ছে, একটু পরে আবার বলুন।"

def send_message(recipient_id, text):
    response = requests.post(
        "https://graph.facebook.com/v18.0/me/messages",
        params={"access_token": PAGE_ACCESS_TOKEN},
        json={"recipient": {"id": recipient_id}, "message": {"text": text}}
    )
    print(f"Send: {response.json()}")

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
        catalogue_data = get_catalogue_products()
        if data.get("object") == "page":
            for entry in data.get("entry", []):
                for event in entry.get("messaging", []):
                    sender_id = event["sender"]["id"]
                    if "message" in event:
                        msg = event["message"]
                        # নিজের message ignore করো
                        if msg.get("is_echo"):
                            continue
                        if "text" in msg:
                            reply = get_claude_response(sender_id, msg["text"], catalogue_data)
                            send_message(sender_id, reply)
                        elif "attachments" in msg:
                            for attachment in msg["attachments"]:
                                if attachment["type"] == "image":
                                    image_url = attachment["payload"]["url"]
                                    reply = analyze_image(image_url, catalogue_data)
                                    send_message(sender_id, reply)
                                elif attachment["type"] == "audio":
                                    send_message(sender_id, "ভয়েস মেসেজ শুনতে পাচ্ছি না, টেক্সটে লিখুন 😊")

                for change in entry.get("changes", []):
                    if change.get("field") == "feed":
                        value = change.get("value", {})
                        if value.get("item") == "comment" and value.get("verb") == "add":
                            comment_id = value.get("comment_id")
                            comment_text = value.get("message", "")
                            from_id = value.get("from", {}).get("id", "")
                            # নিজের পেজের comment ignore করো
                            if comment_text and from_id != "107165985626486":
                                reply = get_claude_response(from_id, comment_text, catalogue_data, is_comment=True)
                                reply_comment(comment_id, reply)
    except Exception as e:
        print(f"Webhook error: {e}")
    return "OK", 200

@app.route("/")
def home():
    return "Dhaka Exclusive Bot Running ✅", 200

@app.route("/privacy")
def privacy():
    return "<h1>Privacy Policy - Dhaka Exclusive</h1><p>আমরা আপনার তথ্য সংগ্রহ করি না।</p>", 200

thread = threading.Thread(target=keep_alive)
thread.daemon = True
thread.start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
