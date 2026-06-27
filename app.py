import os
import requests
import threading
import time
import base64
import json
from flask import Flask, request, jsonify

app = Flask(__name__)

PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN", "")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "dhaka123")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
CATALOGUE_ID = "4177718442481756"
RAILWAY_URL = os.environ.get("RAILWAY_URL", "https://web-production-126eb.up.railway.app")
DATABASE_URL = os.environ.get("DATABASE_URL", "")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO = os.environ.get("GITHUB_REPO", "printthp/dhaka-exclusive-bot")

IGNORE_PATTERNS = ["🔥","👏","❤️","😍","👍","🙏","😊","💯","✅","🎉","😂","🥰","💕","🌹","👌","💪"]

# ========== Database ==========
def get_db_conn():
    import psycopg2
    return psycopg2.connect(DATABASE_URL)

def init_db():
    try:
        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                sender_id TEXT PRIMARY KEY,
                history JSONB DEFAULT '[]',
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_base (
                id SERIAL PRIMARY KEY,
                category TEXT,
                content TEXT,
                source TEXT DEFAULT 'auto',
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        conn.commit()
        cur.close()
        conn.close()
        print("Database initialized ✅")
    except Exception as e:
        print(f"DB init error: {e}")

def get_history(sender_id):
    try:
        conn = get_db_conn()
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
        if len(history) > 60:
            history = history[-60:]
        conn = get_db_conn()
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

def get_knowledge():
    try:
        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute("SELECT category, content FROM knowledge_base ORDER BY created_at DESC LIMIT 40")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        if rows:
            return "\n".join([f"[{r[0]}] {r[1]}" for r in rows])
        return ""
    except Exception as e:
        print(f"Knowledge error: {e}")
        return ""

def save_knowledge(category, content, source="auto"):
    try:
        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO knowledge_base (category, content, source) VALUES (%s, %s, %s)",
            (category, content, source)
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Save knowledge error: {e}")

def extract_knowledge_from_conversation(history):
    """Completed conversation থেকে জ্ঞান extract করে knowledge base এ save করে"""
    try:
        if len(history) < 6:
            return
        conv_text = "\n".join([f"{m['role']}: {m['content']}" for m in history])
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
                "system": """তুমি একটি e-commerce conversation বিশ্লেষক।
এই কথোপকথন থেকে দরকারী তথ্য বের করো।
JSON array format এ দাও, যেমন:
[{"category": "জনপ্রিয় পণ্য", "content": "কাস্টমাররা X পণ্য বেশি জিজ্ঞেস করে"},
 {"category": "সাধারণ প্রশ্ন", "content": "ডেলিভারি টাইম নিয়ে প্রশ্ন আসে"},
 {"category": "আপত্তি", "content": "দাম বেশি মনে হয় কাস্টমারদের"}]

category গুলো হতে পারে: জনপ্রিয় পণ্য, সাধারণ প্রশ্ন, আপত্তি, সফল কৌশল, অভিযোগ
গুরুত্বপূর্ণ না হলে [] দাও।""",
                "messages": [{"role": "user", "content": conv_text}]
            }
        )
        data = response.json()
        if "content" in data:
            text = data["content"][0]["text"].strip()
            try:
                items = json.loads(text)
                for item in items:
                    if "category" in item and "content" in item:
                        save_knowledge(item["category"], item["content"])
                print(f"Knowledge extracted: {len(items)} items")
            except:
                pass
    except Exception as e:
        print(f"Extract knowledge error: {e}")

# ========== GitHub Auto-Update ==========
def github_update_file(filename, new_content, commit_message="Bot auto-update"):
    try:
        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json"
        }
        get_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{filename}"
        get_resp = requests.get(get_url, headers=headers)
        sha = get_resp.json().get("sha", "")
        encoded = base64.b64encode(new_content.encode()).decode()
        put_resp = requests.put(get_url, headers=headers, json={
            "message": commit_message,
            "content": encoded,
            "sha": sha
        })
        if put_resp.status_code in [200, 201]:
            print(f"GitHub commit successful: {filename}")
            return True
        print(f"GitHub commit failed: {put_resp.json()}")
        return False
    except Exception as e:
        print(f"GitHub error: {e}")
        return False

# ========== Helpers ==========
def is_meaningful_message(text):
    text = text.strip()
    if len(text) <= 1:
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
    requests.post(
        "https://graph.facebook.com/v18.0/me/messages",
        params={"access_token": PAGE_ACCESS_TOKEN},
        json={"recipient": {"id": recipient_id}, "message": {"text": text}}
    )

def send_image(recipient_id, image_url):
    try:
        requests.post(
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
    except Exception as e:
        print(f"Image send error: {e}")

def reply_comment(comment_id, text):
    requests.post(
        f"https://graph.facebook.com/v18.0/{comment_id}/replies",
        params={"access_token": PAGE_ACCESS_TOKEN},
        json={"message": text}
    )

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
- plain text এ লেখো, bold বা * বা ** ব্যবহার করো না
- ২-৩ লাইনে স্বাভাবিক বাংলায় বলো
- দাম বলো এবং অর্ডার করতে উৎসাহিত করো""",
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
        history = get_history(sender_id)
        history.append({"role": "user", "content": user_message})

        knowledge = get_knowledge()

        system = f"""তুমি Dhaka Exclusive-এর sales agent রিয়া। কাস্টমারের সাথে বাংলায় কথা বলো।

সবচেয়ে গুরুত্বপূর্ণ নিয়ম:
- কাস্টমার যা জিজ্ঞেস করে, সরাসরি সেই উত্তর দাও
- plain text এ লেখো, কোনো *, **, # markdown নয়
- ছোট ছোট বাক্য, সহজ ও স্বাভাবিক ভাষা
- আগের কথা মনে রেখে উত্তর দাও
- emoji খুব কম ব্যবহার করো

সালাম বা হ্যালো পেলে:
উষ্ণভাবে স্বাগত জানাও। বলো আমরা কী কী পণ্য বিক্রি করি। জিজ্ঞেস করো কী সাহায্য লাগবে।

দাম জিজ্ঞেস করলে:
প্রথমেই দাম বলো। তারপর পণ্যের বিশেষত্ব ও অর্ডার করার অনুরোধ করো।

স্টক বা পণ্য আছে কিনা জিজ্ঞেস করলে:
catalogue দেখে সরাসরি বলো আছে বা নেই।

দামাদামি করলে:
১ম বার: এটাই আমাদের সেরা দাম, কোয়ালিটি দেখলে বুঝবেন।
২য় বার: original product, দাম fixed।
৩য় বার: ২টা নিলে একটু দেখা যায়।
শেষমেশ: আপনার জন্য ২০-৩০ টাকা কমিয়ে দিচ্ছি।

অর্ডার নিতে চাইলে একটা একটা করে জিজ্ঞেস করো:
পদক্ষেপ ১: "আপনার নাম কী?"
পদক্ষেপ ২: "আপনার ফোন নম্বর?"
পদক্ষেপ ৩: "সম্পূর্ণ ঠিকানা?"
পদক্ষেপ ৪: "ঢাকার ভেতরে নাকি বাইরে?"

সব তথ্য পেলে summary দাও:
অর্ডার নিশ্চিত!
প্রোডাক্ট: [নাম]
দাম: [দাম]
ডেলিভারি: [৮০/১৩০] টাকা
মোট: [মোট]
নাম: [নাম]
ফোন: [নম্বর]
ঠিকানা: [ঠিকানা]
ধন্যবাদ আপনার অর্ডারের জন্য!

ডেলিভারি চার্জ: ঢাকার ভেতরে ৮০ টাকা, বাইরে ১৩০ টাকা

রাগী কাস্টমার হলে: "সত্যিই দুঃখিত। কী সমস্যা হয়েছে বলুন, সমাধান করবো।"

আমাদের পণ্য তালিকা:
{catalogue_data if catalogue_data else "এই মুহূর্তে লোড হয়নি"}

{f"কাস্টমারদের কাছ থেকে শেখা তথ্য:{chr(10)}{knowledge}" if knowledge else ""}

ওয়েবসাইট: dhakaexclusive.org"""

        if is_comment:
            system += "\n\nএটা Facebook পোস্টের কমেন্ট। সংক্ষেপে ১ লাইনে রিপ্লাই দাও এবং inbox এ message করতে বলো।"

        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json={
                "model": "claude-sonnet-4-6",
                "max_tokens": 500,
                "system": system,
                "messages": history
            }
        )
        data = response.json()
        if "content" in data:
            reply = data["content"][0]["text"]
            history.append({"role": "assistant", "content": reply})
            save_history(sender_id, history)

            # অর্ডার confirm হলে conversation থেকে শিখো
            if "অর্ডার নিশ্চিত" in reply:
                threading.Thread(
                    target=extract_knowledge_from_conversation,
                    args=(history,),
                    daemon=True
                ).start()

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
                                    send_message(sender_id, "ভয়েস মেসেজ শুনতে পাচ্ছি না, টেক্সটে লিখুন।")

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

def fetch_facebook_conversations(limit=50):
    """Facebook Page থেকে পুরনো conversations fetch করে"""
    try:
        url = "https://graph.facebook.com/v18.0/me/conversations"
        params = {
            "access_token": PAGE_ACCESS_TOKEN,
            "fields": "id,participants",
            "limit": limit
        }
        resp = requests.get(url, params=params)
        data = resp.json()
        if "error" in data:
            print(f"Facebook conversations error: {data['error']}")
            return []
        return data.get("data", [])
    except Exception as e:
        print(f"Fetch conversations error: {e}")
        return []

def fetch_conversation_messages(conversation_id, limit=30):
    """একটি conversation-এর সব message fetch করে"""
    try:
        url = f"https://graph.facebook.com/v18.0/{conversation_id}/messages"
        params = {
            "access_token": PAGE_ACCESS_TOKEN,
            "fields": "message,from,created_time",
            "limit": limit
        }
        resp = requests.get(url, params=params)
        data = resp.json()
        if "error" in data:
            return []
        return data.get("data", [])
    except Exception as e:
        print(f"Fetch messages error: {e}")
        return []

def get_page_id():
    """Page ID বের করো"""
    try:
        resp = requests.get(
            "https://graph.facebook.com/v18.0/me",
            params={"access_token": PAGE_ACCESS_TOKEN, "fields": "id"}
        )
        return resp.json().get("id", "")
    except:
        return ""

def sync_facebook_history_task(num_conversations):
    """Background task: Facebook থেকে পুরনো conversations এনে শেখো"""
    try:
        print(f"Starting Facebook history sync: {num_conversations} conversations...")
        page_id = get_page_id()
        conversations = fetch_facebook_conversations(limit=num_conversations)
        print(f"Found {len(conversations)} conversations")

        learned = 0
        for conv in conversations:
            conv_id = conv.get("id", "")
            if not conv_id:
                continue

            raw_messages = fetch_conversation_messages(conv_id, limit=40)
            if not raw_messages:
                continue

            # Facebook message format কে Claude history format এ convert করো
            history = []
            for msg in reversed(raw_messages):
                sender_id = msg.get("from", {}).get("id", "")
                text = msg.get("message", "").strip()
                if not text:
                    continue
                role = "assistant" if sender_id == page_id else "user"
                history.append({"role": role, "content": text})

            if len(history) >= 4:
                extract_knowledge_from_conversation(history)
                learned += 1
                time.sleep(1)

        print(f"Facebook history sync done. Learned from {learned} conversations.")
        save_knowledge("সিস্টেম", f"Facebook history sync সম্পন্ন। {learned}টি conversation থেকে শেখা হয়েছে।", source="sync")
    except Exception as e:
        print(f"Sync task error: {e}")

@app.route("/sync-facebook", methods=["POST"])
def sync_facebook():
    """Facebook Page-এর পুরনো conversations fetch করে knowledge base এ যোগ করো।
    Body: {"limit": 50}  (কতটা conversation আনবে)
    """
    auth = request.headers.get("X-Auth-Token", "")
    if auth != VERIFY_TOKEN:
        return jsonify({"error": "Unauthorized"}), 401
    data = request.json or {}
    limit = min(int(data.get("limit", 50)), 200)

    threading.Thread(
        target=sync_facebook_history_task,
        args=(limit,),
        daemon=True
    ).start()

    return jsonify({
        "status": "started",
        "message": f"Background এ {limit}টি conversation sync শুরু হয়েছে। /knowledge দিয়ে দেখুন।"
    }), 200

@app.route("/learn-history", methods=["POST"])
def learn_history():
    """পুরনো কাস্টমার কথোপকথন ফিড করে জ্ঞান অর্জন করাও।
    Body: {"conversations": [{"messages": [{"role": "user/assistant", "content": "..."}]}]}
    """
    auth = request.headers.get("X-Auth-Token", "")
    if auth != VERIFY_TOKEN:
        return jsonify({"error": "Unauthorized"}), 401
    data = request.json
    conversations = data.get("conversations", [])
    if not conversations:
        return jsonify({"error": "No conversations provided"}), 400

    learned = 0
    for conv in conversations:
        messages = conv.get("messages", [])
        if messages:
            extract_knowledge_from_conversation(messages)
            learned += 1
        time.sleep(0.5)

    return jsonify({"status": "success", "learned_from": learned}), 200

@app.route("/add-knowledge", methods=["POST"])
def add_knowledge():
    """সরাসরি knowledge base এ তথ্য যোগ করো।
    Body: {"category": "...", "content": "..."}
    """
    auth = request.headers.get("X-Auth-Token", "")
    if auth != VERIFY_TOKEN:
        return jsonify({"error": "Unauthorized"}), 401
    data = request.json
    category = data.get("category", "")
    content = data.get("content", "")
    if not category or not content:
        return jsonify({"error": "category and content required"}), 400
    save_knowledge(category, content, source="manual")
    return jsonify({"status": "saved"}), 200

@app.route("/knowledge", methods=["GET"])
def view_knowledge():
    """Knowledge base দেখো"""
    auth = request.headers.get("X-Auth-Token", "")
    if auth != VERIFY_TOKEN:
        return jsonify({"error": "Unauthorized"}), 401
    knowledge = get_knowledge()
    return jsonify({"knowledge": knowledge}), 200

@app.route("/update-bot", methods=["POST"])
def update_bot():
    auth = request.headers.get("X-Auth-Token", "")
    if auth != VERIFY_TOKEN:
        return jsonify({"error": "Unauthorized"}), 401
    data = request.json
    new_code = data.get("code", "")
    if not new_code:
        return jsonify({"error": "No code provided"}), 400
    success = github_update_file("app.py", new_code, "Auto-update from Claude")
    if success:
        return jsonify({"status": "success"}), 200
    return jsonify({"error": "GitHub update failed"}), 500

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
