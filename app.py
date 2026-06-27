import os
import requests
import threading
import time
import base64
import psycopg2
import json
from flask import Flask, request, jsonify

app = Flask(__name__)

PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN", "")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "dhaka123")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
CATALOGUE_ID = "4177718442481756"
RAILWAY_URL = os.environ.get("RAILWAY_URL", "https://web-production-126eb.up.railway.app")
DATABASE_URL = os.environ.get("DATABASE_URL", "")

IGNORE_PATTERNS = ["🔥","👏","❤️","😍","👍","🙏","😊","💯","✅","🎉","😂","🥰","💕","🌹","👌","💪"]

def init_db():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                sender_id TEXT PRIMARY KEY,
                history JSONB DEFAULT '[]',
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """)
        conn.commit()
        cur.close()
        conn.close()
        print("Database initialized")
    except Exception as e:
        print(f"DB init error: {e}")

def get_history(sender_id):
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("SELECT history FROM conversations WHERE sender_id = %s", (sender_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        if row:
            return row[0] if isinstance(row[0], list) else json.loads(row[0])
        return []
    except Exception as e:
        print(f"Get history error: {e}")
        return []

def save_history(sender_id, history):
    try:
        if len(history) > 50:
            history = history[-50:]
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO conversations (sender_id, history, updated_at)
            VALUES (%s, %s, NOW())
            ON CONFLICT (sender_id) DO UPDATE
            SET history = %s, updated_at = NOW()
        """, (sender_id, json.dumps(history), json.dumps(history)))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Save history error: {e}")

def is_meaningful_message(text):
    text = text.strip()
    if len(text) <= 2:
        return False
    if text in IGNORE_PATTERNS:
        return False
    if all(char in '🔥👏❤️😍👍🙏😊💯✅🎉😂🥰💕🌹👌💪 ' for char in text):
        return False
    return True

def get_catalogue_products():
    try:
        url = f"https://graph.facebook.com/v18.0/{CATALOGUE_ID}/products"
        params = {
            "access_token": PAGE_ACCESS_TOKEN,
            "fields": "name,price,currency,availability,image_url",
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

def get_product_image_url(product_name):
    try:
        url = f"https://graph.facebook.com/v18.0/{CATALOGUE_ID}/products"
        params = {
            "access_token": PAGE_ACCESS_TOKEN,
            "fields": "name,image_url",
            "limit": 50
        }
        response = requests.get(url, params=params)
        data = response.json()
        if "data" in data:
            for p in data["data"]:
                if any(word.lower() in p.get("name", "").lower() for word in product_name.split()):
                    return p.get("image_url", "")
        return ""
    except:
        return ""

def send_message(recipient_id, text):
    response = requests.post(
        "https://graph.facebook.com/v18.0/me/messages",
        params={"access_token": PAGE_ACCESS_TOKEN},
        json={"recipient": {"id": recipient_id}, "message": {"text": text}}
    )
    print(f"Send: {response.status_code}")

def send_image(recipient_id, image_url):
    try:
        response = requests.post(
            "https://graph.facebook.com/v18.0/me/messages",
            params={"access_token": PAGE_ACCESS_TOKEN},
            json={
                "recipient": {"id": recipient_id},
                "message": {
                    "attachment": {
                        "type": "image",
                        "payload": {"url": image_url, "is_reusable": True}
                    }
                }
            }
        )
        print(f"Image sent: {response.status_code}")
    except Exception as e:
        print(f"Image send error: {e}")

def reply_comment(comment_id, text):
    response = requests.post(
        f"https://graph.facebook.com/v18.0/{comment_id}/replies",
        params={"access_token": PAGE_ACCESS_TOKEN},
        json={"message": text}
    )
    print(f"Comment reply: {response.status_code}")

def analyze_image(image_url, catalogue_data, history):
    try:
        img_response = requests.get(image_url, timeout=15)
        if img_response.status_code != 200:
            return "ছবিটা ঠিকমতো আসেনি, আরেকটু পরে পাঠান।"
        image_data = base64.b64encode(img_response.content).decode('utf-8')
        content_type = img_response.headers.get('content-type', 'image/jpeg')
        if 'jpeg' not in content_type and 'jpg' not in content_type and 'png' not in content_type:
            content_type = 'image/jpeg'
        context = "\n".join([f"{m['role']}: {m['content']}" for m in history[-4:]])
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json={
                "model": "claude-opus-4-6",
                "max_tokens": 300,
                "system": f"""তুমি Dhaka Exclusive-এর sales agent রিয়া।

আমাদের প্রোডাক্ট:
{catalogue_data}

আগের কথা:
{context}

নিয়ম:
- ছবি দেখে প্রোডাক্ট চিনে catalogue থেকে দাম বলো
- plain text এ লেখো, bold বা * বা ** একদম ব্যবহার করো না
- ২-৩ লাইনে স্বাভাবিক বাংলায় বলো
- থাকলে দাম বলো এবং order করতে উৎসাহিত করো
- না থাকলে বলো: এটা এখন নেই, তবে আমাদের আরও অনেক প্রোডাক্ট আছে""",
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "image", "source": {"type": "base64", "media_type": content_type, "data": image_data}},
                        {"type": "text", "text": "এই প্রোডাক্টটা কী? দাম কত? আমাদের catalogue এ আছে?"}
                    ]
                }]
            }
        )
        data = response.json()
        print(f"Image analysis response: {data}")
        if "content" in data:
            return data["content"][0]["text"]
        return "ছবিটা দেখতে পাচ্ছি না, টেক্সটে লিখুন।"
    except Exception as e:
        print(f"Image error: {e}")
        return "ছবিটা দেখতে পাচ্ছি না, টেক্সটে লিখুন।"

def get_claude_response(sender_id, user_message, catalogue_data, is_comment=False):
    try:
        history = get_history(sender_id)
        history.append({"role": "user", "content": user_message})

        system = f"""তুমি Dhaka Exclusive-এর অভিজ্ঞ sales agent রিয়া।

সবচেয়ে গুরুত্বপূর্ণ নিয়ম:
- plain text এ লেখো
- bold, *, **, markdown একদম ব্যবহার করো না
- ছোট ছোট বাক্য
- জি আপু বা জি ভাই দিয়ে শুরু করো
- আগের সব কথা মনে রেখে কথা বলো
- emoji খুব কম, ১-২টা

ডেলিভারি চার্জ:
- ঢাকার ভেতরে: ৮০ টাকা
- ঢাকার বাইরে: ১৩০ টাকা

ডিসকাউন্ট নীতি:
কাস্টমার দাম কমাতে চাইলে সহজে দিও না। ধাপে ধাপে:
১ম বার: এই দামটাই আমাদের সেরা দাম, কোয়ালিটি দেখলে বুঝবেন।
২য় বার: এটা original product, দামটা fixed।
৩য় বার: ২টা নিলে একটু দেখা যায়।
শেষে: ঠিক আছে, আপনার জন্য ২০-৩০ টাকা কমিয়ে দিচ্ছি।

রাগী কাস্টমার:
তর্ক করো না। বলো: আমি সত্যিই দুঃখিত। কী সমস্যা হয়েছে বলুন, সমাধান করবো।

অর্ডার নেওয়া:
কাস্টমার অর্ডার করতে চাইলে একে একে নাও:
১. নাম
২. ফোন নম্বর
৩. সম্পূর্ণ ঠিকানা
৪. ঢাকার ভেতরে নাকি বাইরে

সব তথ্য পেলে এই format এ summary দাও (plain text, কোনো bold নেই):
অর্ডার নিশ্চিত!
প্রোডাক্ট: [নাম]
দাম: [দাম]
ডেলিভারি: [৮০/১৩০] টাকা
মোট: [মোট]
নাম: [নাম]
ফোন: [নম্বর]
ঠিকানা: [ঠিকানা]
ধন্যবাদ আপনার অর্ডারের জন্য!

আমাদের প্রোডাক্ট:
{catalogue_data if catalogue_data else "লোড হয়নি"}

ওয়েবসাইট: dhakaexclusive.org"""

        if is_comment:
            system += "\n\nএটা পোস্টের কমেন্ট। ১ লাইনে বলো এবং inbox এ message করতে বলো।"

        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json={
                "model": "claude-haiku-4-5",
                "max_tokens": 400,
                "system": system,
                "messages": history
            }
        )
        data = response.json()
        if "content" in data:
            reply = data["content"][0]["text"]
            history.append({"role": "assistant", "content": reply})
            save_history(sender_id, history)
            return reply
        return "একটু সমস্যা হচ্ছে, একটু পরে আবার বলুন।"
    except Exception as e:
        print(f"Claude error: {e}")
        return "একটু সমস্যা হচ্ছে, একটু পরে আবার বলুন।"

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
                for event in entry.get("messaging", []):
                    sender_id = event["sender"]["id"]
                    if "message" in event:
                        msg = event["message"]
                        if msg.get("is_echo"):
                            continue
                        if "text" in msg:
                            text = msg["text"]
                            if not is_meaningful_message(text):
                                continue
                            print(f"User {sender_id}: {text}")
                            reply = get_claude_response(sender_id, text, catalogue_data)
                            send_message(sender_id, reply)
                            if "অর্ডার নিশ্চিত" in reply:
                                img_url = get_product_image_url(text)
                                if img_url:
                                    send_image(sender_id, img_url)
                        elif "attachments" in msg:
                            for attachment in msg["attachments"]:
                                if attachment["type"] == "image":
                                    history = get_history(sender_id)
                                    reply = analyze_image(attachment["payload"]["url"], catalogue_data, history)
                                    history.append({"role": "user", "content": "[ছবি পাঠিয়েছে]"})
                                    history.append({"role": "assistant", "content": reply})
                                    save_history(sender_id, history)
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
                            if comment_text and from_id != "107165985626486" and is_meaningful_message(comment_text):
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

init_db()

thread = threading.Thread(target=keep_alive)
thread.daemon = True
thread.start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
