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

# কাস্টমারের conversation history
conversation_history = {}

# শুধু emoji বা অর্থহীন মেসেজ filter করো
IGNORE_PATTERNS = ["🔥", "👏", "❤️", "😍", "👍", "🙏", "😊", "💯", "✅", "🎉"]

def is_meaningful_message(text):
    text = text.strip()
    if len(text) <= 2:
        return False
    if text in IGNORE_PATTERNS:
        return False
    if all(char in '🔥👏❤️😍👍🙏😊💯✅🎉😂🥰💕🌹' for char in text):
        return False
    return True

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

def analyze_image(image_url, catalogue_data, conversation_context=""):
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

আমাদের প্রোডাক্ট:
{catalogue_data}

আগের কথোপকথন:
{conversation_context}

ছবি দেখে প্রোডাক্ট চেনো, catalogue থেকে মিলিয়ে দাম বলো।
২-৩ লাইনে স্বাভাবিক বাংলায় বলো।
না থাকলে: "এই প্রোডাক্টটা এখন নেই, dhakaexclusive.org এ দেখুন" """,
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "image", "source": {"type": "base64", "media_type": content_type, "data": image_data}},
                        {"type": "text", "text": "এই প্রোডাক্টটা কী? দাম কত?"}
                    ]
                }]
            }
        )
        data = response.json()
        if "content" in data:
            return data["content"][0]["text"]
        return "ছবিটা দেখতে পাচ্ছি না, টেক্সটে লিখুন।"
    except Exception as e:
        print(f"Image error: {e}")
        return "ছবিটা দেখতে পাচ্ছি না, টেক্সটে লিখুন।"

def get_claude_response(sender_id, user_message, catalogue_data, is_comment=False):
    try:
        if sender_id not in conversation_history:
            conversation_history[sender_id] = []

        conversation_history[sender_id].append({
            "role": "user",
            "content": user_message
        })

        # শেষ ১০টা message রাখো
        if len(conversation_history[sender_id]) > 10:
            conversation_history[sender_id] = conversation_history[sender_id][-10:]

        system = f"""তুমি Dhaka Exclusive-এর কাস্টমার সার্ভিস রিয়া।

ব্যক্তিত্ব:
- একদম মানুষের মতো, স্বাভাবিক কথা বলো
- কাস্টমার যা জিজ্ঞেস করে শুধু সেটার উত্তর দাও
- আগের কথা মনে রেখে উত্তর দাও
- ছোট বাক্য, সহজ বাংলা
- "জি আপু" বা "জি ভাই" দিয়ে শুরু করো
- emoji খুব কম, স্বাভাবিক কথায়
- bold বা * ব্যবহার করো না
- website link বারবার দিও না

উদাহরণ:
কাস্টমার: "এটা কি চুলায় ব্যবহার করা যাবে?"
রিয়া: "জি আপু, কোন প্রোডাক্টটার কথা বলছেন? নাম বা ছবি দিলে বলতে পারবো।"

কাস্টমার: "টিফিন বক্সের দাম কত?"
রিয়া: "জি ভাই, Milton 4 Layer Tiffin Box দুই ধরনের আছে — Classic ১৬৯০ টাকা, Tasty ১৫৯০ টাকা। কোনটা নেবেন?"

আমাদের প্রোডাক্ট:
{catalogue_data if catalogue_data else "এই মুহূর্তে লোড হয়নি"}

ওয়েবসাইট: dhakaexclusive.org"""

        if is_comment:
            system += "\n\nএটা পোস্টের কমেন্ট। ১ লাইনে বলো এবং inbox এ আসতে বলো।"

        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json={
                "model": "claude-haiku-4-5",
                "max_tokens": 250,
                "system": system,
                "messages": conversation_history[sender_id]
            }
        )
        data = response.json()
        if "content" in data:
            reply = data["content"][0]["text"]
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
    try:
        catalogue_data = get_catalogue_products()
        if data.get("object") == "page":
            for entry in data.get("entry", []):
                # Messenger মেসেজ
                for event in entry.get("messaging", []):
                    sender_id = event["sender"]["id"]
                    if "message" in event:
                        msg = event["message"]
                        if msg.get("is_echo"):
                            continue
                        if "text" in msg:
                            text = msg["text"]
                            # অর্থহীন মেসেজ ignore করো
                            if not is_meaningful_message(text):
                                print(f"Ignored: {text}")
                                continue
                            print(f"User said: {text}")
                            reply = get_claude_response(sender_id, text, catalogue_data)
                            send_message(sender_id, reply)
                        elif "attachments" in msg:
                            for attachment in msg["attachments"]:
                                if attachment["type"] == "image":
                                    image_url = attachment["payload"]["url"]
                                    context = str(conversation_history.get(sender_id, ""))
                                    reply = analyze_image(image_url, catalogue_data, context)
                                    conversation_history.setdefault(sender_id, []).append({"role": "user", "content": "[ছবি পাঠিয়েছে]"})
                                    conversation_history[sender_id].append({"role": "assistant", "content": reply})
                                    send_message(sender_id, reply)
                                elif attachment["type"] == "audio":
                                    send_message(sender_id, "ভয়েস মেসেজ শুনতে পাচ্ছি না, টেক্সটে লিখুন 😊")

                # কমেন্ট — reaction ignore করো
                for change in entry.get("changes", []):
                    if change.get("field") == "feed":
                        value = change.get("value", {})
                        # শুধু comment handle করো, reaction না
                        if value.get("item") == "comment" and value.get("verb") == "add":
                            comment_id = value.get("comment_id")
                            comment_text = value.get("message", "")
                            from_id = value.get("from", {}).get("id", "")
                            page_id = "107165985626486"
                            if comment_text and from_id != page_id and is_meaningful_message(comment_text):
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
