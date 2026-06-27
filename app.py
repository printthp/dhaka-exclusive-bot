import os
import re
import json
import time
import base64
import threading
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN", "")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "dhaka123")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
CATALOGUE_ID = os.environ.get("CATALOGUE_ID", "4177718442481756")
RAILWAY_URL = os.environ.get("RAILWAY_URL", "https://web-production-126eb.up.railway.app")
DATABASE_URL = os.environ.get("DATABASE_URL", "")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO = os.environ.get("GITHUB_REPO", "printthp/dhaka-exclusive-bot")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash")
# Fallback list if the default model is not available for the current API version
GEMINI_FALLBACK_MODELS = [
    "gemini-1.5-flash",
    "gemini-1.5-pro",
    "gemini-2.0-flash",
    "gemini-2.5-flash",
]

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
        # Products cache: includes `active` and `product_id` columns referenced elsewhere
        cur.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id SERIAL PRIMARY KEY,
                product_id TEXT UNIQUE,
                name TEXT,
                price TEXT,
                active BOOLEAN DEFAULT TRUE,
                image_url TEXT,
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """)
        # Safe migration for existing deployments
        cur.execute("ALTER TABLE products ADD COLUMN IF NOT EXISTS product_id TEXT")
        cur.execute("ALTER TABLE products ADD COLUMN IF NOT EXISTS name TEXT")
        cur.execute("ALTER TABLE products ADD COLUMN IF NOT EXISTS price TEXT")
        cur.execute("ALTER TABLE products ADD COLUMN IF NOT EXISTS active BOOLEAN DEFAULT TRUE")
        cur.execute("ALTER TABLE products ADD COLUMN IF NOT EXISTS image_url TEXT")
        cur.execute("ALTER TABLE products ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW()")
        cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS products_product_id_idx ON products (product_id)")
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

def upsert_product(product_id, name, price, active, image_url):
    try:
        if not product_id:
            return
        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO products (product_id, name, price, active, image_url, updated_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
            ON CONFLICT (product_id) DO UPDATE
            SET name = EXCLUDED.name,
                price = EXCLUDED.price,
                active = EXCLUDED.active,
                image_url = EXCLUDED.image_url,
                updated_at = NOW()
        """, (product_id, name, price, bool(active), image_url))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Upsert product error: {e}")

def get_active_products_text(limit=50):
    try:
        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT name, price FROM products
            WHERE active = TRUE
            ORDER BY updated_at DESC
            LIMIT %s
        """, (limit,))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        if rows:
            return "\n".join([f"{r[0]} | {r[1]} | স্টক: আছে" for r in rows])
        return ""
    except Exception as e:
        print(f"Get products error: {e}")
        return ""

def get_product_image_url(product_name):
    try:
        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute("SELECT name, image_url FROM products WHERE active = TRUE LIMIT 100")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        if rows:
            words = [w.lower() for w in (product_name or "").split() if len(w) > 2]
            for name, image_url in rows:
                lname = (name or "").lower()
                if any(w in lname for w in words):
                    return image_url or ""
        return ""
    except Exception as e:
        print(f"Get image error: {e}")
        return ""

def extract_knowledge_from_conversation(history):
    """Completed conversation থেকে জ্ঞান extract করে knowledge base এ save করে"""
    try:
        if len(history) < 6:
            return
        conv_text = "\n".join([f"{m['role']}: {m['content']}" for m in history])
        prompt = f"""তুমি একটি e-commerce conversation বিশ্লেষক।
এই কথোপকথন থেকে দরকারী তথ্য বের করো।
শুধু একটি JSON array return করো (কোনো explanation, code block বা markdown নয়), যেমন:
[{{"category": "জনপ্রিয় পণ্য", "content": "কাস্টমাররা X পণ্য বেশি জিজ্ঞেস করে"}},
 {{"category": "সাধারণ প্রশ্ন", "content": "ডেলিভারি টাইম নিয়ে প্রশ্ন আসে"}},
 {{"category": "আপত্তি", "content": "দাম বেশি মনে হয় কাস্টমারদের"}}]

category গুলো হতে পারে: জনপ্রিয় পণ্য, সাধারণ প্রশ্ন, আপত্তি, সফল কৌশল, অভিযোগ
গুরুত্বপূর্ণ না হলে [] দাও।

Conversation:
{conv_text}"""
        text = call_gemini_text(prompt=prompt, max_tokens=600, temperature=0.3)
        if not text:
            return
        text = text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(json)?", "", text).strip()
            if text.endswith("```"):
                text = text[:-3].strip()
        items = json.loads(text)
        for item in items:
            if isinstance(item, dict) and "category" in item and "content" in item:
                save_knowledge(item["category"], item["content"])
        print(f"Knowledge extracted: {len(items)} items")
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
        get_resp = requests.get(get_url, headers=headers, timeout=15)
        sha = get_resp.json().get("sha", "")
        encoded = base64.b64encode(new_content.encode()).decode()
        put_resp = requests.put(get_url, headers=headers, json={
            "message": commit_message,
            "content": encoded,
            "sha": sha
        }, timeout=30)
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
    text = (text or "").strip()
    if len(text) <= 1:
        return False
    if text in IGNORE_PATTERNS:
        return False
    if all(char in '🔥👏❤️😍👍🙏😊💯✅🎉😂🥰💕🌹👌💪 ' for char in text):
        return False
    return True

def get_catalogue_products():
    """Facebook catalogue থেকে product list আনো এবং products table-এ cache করো"""
    if not CATALOGUE_ID or not PAGE_ACCESS_TOKEN:
        return ""
    try:
        url = f"https://graph.facebook.com/v18.0/{CATALOGUE_ID}/products"
        params = {
            "access_token": PAGE_ACCESS_TOKEN,
            "fields": "id,name,price,currency,availability,image_url",
            "limit": 50
        }
        response = requests.get(url, params=params, timeout=20)
        data = response.json()
        if "data" in data and len(data["data"]) > 0:
            text = ""
            for p in data["data"][:50]:
                name = p.get("name", "")
                price = p.get("price", "")
                in_stock = p.get("availability") == "in stock"
                avail = "আছে" if in_stock else "নেই"
                text += f"{name} | {price} | স্টক: {avail}\n"
                upsert_product(
                    product_id=p.get("id", ""),
                    name=name,
                    price=price,
                    active=in_stock,
                    image_url=p.get("image_url", "")
                )
            return text
        return ""
    except Exception as e:
        print(f"Catalogue error: {e}")
        return ""

def sync_catalogue_task():
    try:
        get_catalogue_products()
        print("Catalogue sync done")
    except Exception as e:
        print(f"Catalogue sync error: {e}")

# ========== Facebook Messenger Send API ==========
def send_message(recipient_id, text):
    """Facebook Messenger-এ text message পাঠাও"""
    try:
        if not PAGE_ACCESS_TOKEN:
            print("PAGE_ACCESS_TOKEN missing; message skipped")
            return {}
        resp = requests.post(
            "https://graph.facebook.com/v18.0/me/messages",
            params={"access_token": PAGE_ACCESS_TOKEN},
            json={"recipient": {"id": recipient_id}, "message": {"text": text}},
            timeout=15
        )
        if resp.status_code >= 400:
            print(f"Messenger send error: {resp.status_code} {resp.text}")
        return resp.json() if resp.text else {}
    except Exception as e:
        print(f"send_message error: {e}")
        return {}

def send_image(recipient_id, image_url):
    """Facebook Messenger-এ ছবি পাঠাও"""
    try:
        if not PAGE_ACCESS_TOKEN or not image_url:
            return {}
        resp = requests.post(
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
            },
            timeout=20
        )
        if resp.status_code >= 400:
            print(f"Messenger image send error: {resp.status_code} {resp.text}")
        return resp.json() if resp.text else {}
    except Exception as e:
        print(f"send_image error: {e}")
        return {}

def reply_comment(comment_id, text):
    """Facebook post comment-এ reply দাও"""
    try:
        if not PAGE_ACCESS_TOKEN:
            return {}
        resp = requests.post(
            f"https://graph.facebook.com/v18.0/{comment_id}/replies",
            params={"access_token": PAGE_ACCESS_TOKEN},
            json={"message": text},
            timeout=10
        )
        if resp.status_code >= 400:
            print(f"Comment reply error: {resp.status_code} {resp.text}")
        return resp.json() if resp.text else {}
    except Exception as e:
        print(f"reply_comment error: {e}")
        return {}

def download_messenger_image(image_url):
    """Messenger attachment URL → (bytes, mime_type)"""
    try:
        resp = requests.get(image_url, timeout=20)
        if resp.status_code != 200:
            return None, ""
        mime = resp.headers.get('content-type', 'image/jpeg')
        return resp.content, mime
    except Exception as e:
        print(f"download_messenger_image error: {e}")
        return None, ""

# ========== Gemini API ==========
def call_gemini_text(prompt, system=None, history=None, model=None, max_tokens=500, temperature=0.7):
    """Gemini text-only generateContent call"""
    try:
        if not GEMINI_API_KEY:
            print("GEMINI_API_KEY missing")
            return ""
        model = model or GEMINI_MODEL
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
        contents = []
        if history:
            for m in history:
                role = "user" if m.get("role") == "user" else "model"
                content = m.get("content", "")
                if isinstance(content, str):
                    contents.append({"role": role, "parts": [{"text": content}]})
        contents.append({"role": "user", "parts": [{"text": prompt}]})
        payload = {
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": temperature
            }
        }
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}
        resp = requests.post(url, json=payload, timeout=45)
        if resp.status_code >= 400:
            print(f"Gemini error: {resp.status_code} {resp.text[:400]}")
            return ""
        data = resp.json()
        candidates = data.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            if parts:
                return parts[0].get("text", "")
        return ""
    except Exception as e:
        print(f"call_gemini_text error: {e}")
        return ""

def call_gemini_multimodal(prompt, image_bytes, mime_type, system=None, history=None, model=None, max_tokens=400):
    """Gemini multimodal (text + image) generateContent call"""
    try:
        if not GEMINI_API_KEY:
            return ""
        model = model or GEMINI_MODEL
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
        image_b64 = base64.b64encode(image_bytes).decode('utf-8')
        if mime_type not in ("image/jpeg", "image/png", "image/webp", "image/gif"):
            mime_type = "image/jpeg"
        contents = []
        if history:
            for m in history[-4:]:
                role = "user" if m.get("role") == "user" else "model"
                content = m.get("content", "")
                if isinstance(content, str):
                    contents.append({"role": role, "parts": [{"text": content}]})
        contents.append({
            "role": "user",
            "parts": [
                {"inline_data": {"mime_type": mime_type, "data": image_b64}},
                {"text": prompt}
            ]
        })
        payload = {
            "contents": contents,
            "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.6}
        }
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}
        resp = requests.post(url, json=payload, timeout=60)
        if resp.status_code >= 400:
            print(f"Gemini vision error: {resp.status_code} {resp.text[:400]}")
            return ""
        data = resp.json()
        candidates = data.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            if parts:
                return parts[0].get("text", "")
        return ""
    except Exception as e:
        print(f"call_gemini_multimodal error: {e}")
        return ""

def strip_markdown(text):
    if not text:
        return text
    return text.replace("**", "").replace("__", "").replace("*", "").replace("#", "").strip()

# ========== Sales-Intelligent Gemini Reply ==========
def detect_intent(user_message):
    """Quick keyword-based intent for sales routing"""
    try:
        text = (user_message or "").lower()
        if re.search(r"\b(hi|হ্যালো|হায়|hello|hey|সালাম|আসসালামু|নমস্কার|assalamu)\b", text):
            return "greeting"
        if re.search(r"(দাম|কত|price|কেমন|কতটাকা|কত টাকা)", text):
            return "price"
        if re.search(r"(স্টক|আছে|নেই|available|stock|পণ্য)", text):
            return "stock"
        if re.search(r"(অর্ডার|order|কিনব|কিনতে|নিব|নিতে|চাই)", text):
            return "order"
        if re.search(r"(ডেলিভারি|delivery|কবে|কখন|সময়|কোথায়)", text):
            return "delivery"
        if re.search(r"(রিটার্ন|return|ফেরত|exchange|এক্সচেঞ্জ)", text):
            return "return"
        if re.search(r"(কম|কমাবে|cheap|কমিয়ে|ডিসকাউন্ট|discount|অফার)", text):
            return "negotiation"
        if re.search(r"(খারাপ|বাজে|ভুয়া|ঠকা|fraud|scam|রিপোর্ট|report|অভিযোগ)", text):
            return "complaint"
        return "general"
    except Exception:
        return "general"

def get_gemini_reply(sender_id, user_message, catalogue_data, is_comment=False):
    """Sales-intelligent Gemini-powered reply (Messenger)"""
    try:
        history = get_history(sender_id)
        history.append({"role": "user", "content": user_message})

        knowledge = get_knowledge()
        intent = detect_intent(user_message)

        system = f"""তুমি Dhaka Exclusive-এর senior sales agent রিয়া। কাস্টমারের সাথে বাংলায় কথা বলো।

সবচেয়ে গুরুত্বপূর্ণ নিয়ম:
- কাস্টমার যা জিজ্ঞেস করে, সরাসরি সেই উত্তর দাও
- plain text এ লেখো, কোনো *, **, # markdown নয়
- ছোট ছোট বাক্য, সহজ ও স্বাভাবিক ভাষা
- আগের কথা মনে রেখে উত্তর দাও
- emoji খুব কম ব্যবহার করো
- সবসময় বাংলায় উত্তর দাও

বর্তমান intent: {intent}

সালাম বা হ্যালো পেলে:
উষ্ণভাবে স্বাগত জানাও। বলো আমরা কী কী পণ্য বিক্রি করি। জিজ্ঞেস করো কী সাহায্য লাগবে।

দাম জিজ্ঞেস করলে:
প্রথমেই catalogue থেকে দাম বলো। তারপর পণ্যের বিশেষত্ব ও অর্ডার করার অনুরোধ করো।

স্টক বা পণ্য আছে কিনা জিজ্ঞেস করলে:
catalogue দেখে সরাসরি বলো আছে বা নেই।

দামাদামি / কমাবে করলে (negotiation):
১ম বার: এটাই আমাদের সেরা দাম, কোয়ালিটি দেখলে বুঝবেন।
২য় বার: original product, দাম fixed।
৩য় বার: ২টা নিলে একটু দেখা যায়।
শেষমেশ: আপনার জন্য ২০-৩০ টাকা কমিয়ে দিচ্ছি, এটাই শেষ অফার।

অভিযোগ / রাগী কাস্টমার হলে:
প্রথমে ক্ষমা চাও। বলো "সত্যিই দুঃখিত। কী সমস্যা হয়েছে বলুন, সমাধান করবো।"

অর্ডার নিতে চাইলে একটা একটা করে জিজ্ঞেস করো:
পদক্ষেপ ১: "আপনার নাম কী?"
পদক্ষেপ ২: "আপনার ফোন নম্বর?"
পদক্ষেপ ৩: "সম্পূর্ণ ঠিকানা?"
পদক্ষেপ ৪: "ঢাকার ভেতরে নাকি বাইরে?"

সব তথ্য পেলে summary দাও এই ফরম্যাটে:
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

Upsell / Cross-sell:
কাস্টমার যে পণ্য জিজ্ঞেস করেছে তার সাথে মানানসই ১টা related product suggest করো (catalogue থেকে)।

আমাদের পণ্য তালিকা:
{catalogue_data if catalogue_data else "এই মুহূর্তে লোড হয়নি"}

{f"কাস্টমারদের কাছ থেকে শেখা তথ্য:{chr(10)}{knowledge}" if knowledge else ""}

ওয়েবসাইট: dhakaexclusive.org"""

        if is_comment:
            system += "\n\nএটা Facebook পোস্টের কমেন্ট। সংক্ষেপে ১ লাইনে রিপ্লাই দাও এবং inbox এ message করতে বলো।"

        # Gemini expects "model" role; pass last 30 turns only
        gemini_history = []
        for m in history[-31:-1]:  # exclude the just-appended user turn
            role = "user" if m.get("role") == "user" else "model"
            content = m.get("content", "")
            if isinstance(content, str):
                gemini_history.append({"role": role, "content": content})

        reply = call_gemini_text(
            prompt=user_message,
            system=system,
            history=gemini_history,
            max_tokens=500,
            temperature=0.7
        )

        if not reply:
            return "একটু সমস্যা হচ্ছে, একটু পরে আবার বলুন।"

        reply = strip_markdown(reply)

        history.append({"role": "assistant", "content": reply})
        save_history(sender_id, history)

        # অর্ডার confirm হলে background-এ knowledge extract করো
        if "অর্ডার নিশ্চিত" in reply:
            threading.Thread(
                target=extract_knowledge_from_conversation,
                args=(history,),
                daemon=True
            ).start()

        return reply
    except Exception as e:
        print(f"get_gemini_reply error: {e}")
        return "একটু সমস্যা হচ্ছে, একটু পরে আবার বলুন।"

def analyze_image_with_gemini(image_bytes, mime_type, catalogue_data, history):
    """ছবি বিশ্লেষণ করে product সম্পর্কে বলো (multimodal Gemini)"""
    try:
        context = "\n".join([f"{m['role']}: {m['content']}" for m in history[-4:]])
        system = f"""তুমি Dhaka Exclusive-এর sales agent রিয়া।
আমাদের প্রোডাক্ট:
{catalogue_data}
আগের কথা:
{context}
নিয়ম:
- ছবি দেখে প্রোডাক্ট চিনে catalogue থেকে দাম বলো
- plain text এ লেখো, bold বা * বা ** ব্যবহার করো না
- ২-৩ লাইনে স্বাভাবিক বাংলায় বলো
- দাম বলো এবং অর্ডার করতে উৎসাহিত করো"""
        reply = call_gemini_multimodal(
            prompt="এই প্রোডাক্টটা কী? দাম কত?",
            image_bytes=image_bytes,
            mime_type=mime_type,
            system=system,
            max_tokens=300
        )
        if not reply:
            return "ছবিটা দেখতে পাচ্ছি না, টেক্সটে লিখুন।"
        return strip_markdown(reply)
    except Exception as e:
        print(f"analyze_image_with_gemini error: {e}")
        return "ছবিটা দেখতে পাচ্ছি না, টেক্সটে লিখুন।"

# ========== Keep Alive ==========
def keep_alive():
    while True:
        time.sleep(600)
        try:
            requests.get(f"{RAILWAY_URL}/", timeout=10)
            print("Keep alive ping sent")
        except:
            pass

# ========== Facebook Graph Helpers ==========
def fetch_facebook_conversations(limit=50):
    try:
        url = "https://graph.facebook.com/v18.0/me/conversations"
        params = {"access_token": PAGE_ACCESS_TOKEN, "fields": "id,participants", "limit": limit}
        resp = requests.get(url, params=params, timeout=15)
        data = resp.json()
        if "error" in data:
            print(f"Facebook conversations error: {data['error']}")
            return []
        return data.get("data", [])
    except Exception as e:
        print(f"Fetch conversations error: {e}")
        return []

def fetch_conversation_messages(conversation_id, limit=30):
    try:
        url = f"https://graph.facebook.com/v18.0/{conversation_id}/messages"
        params = {"access_token": PAGE_ACCESS_TOKEN, "fields": "message,from,created_time", "limit": limit}
        resp = requests.get(url, params=params, timeout=15)
        data = resp.json()
        if "error" in data:
            return []
        return data.get("data", [])
    except Exception as e:
        print(f"Fetch messages error: {e}")
        return []

def get_page_id():
    try:
        resp = requests.get(
            "https://graph.facebook.com/v18.0/me",
            params={"access_token": PAGE_ACCESS_TOKEN, "fields": "id"},
            timeout=10
        )
        return resp.json().get("id", "")
    except:
        return ""

def sync_facebook_history_task(num_conversations):
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

# ========== Routes ==========
@app.route("/webhook", methods=["GET"])
def verify():
    """Facebook Page webhook verification"""
    if request.args.get("hub.verify_token") == VERIFY_TOKEN:
        return request.args.get("hub.challenge"), 200
    return "Error", 403

@app.route("/webhook", methods=["POST"])
def webhook():
    """Facebook Messenger incoming webhook"""
    data = request.json
    try:
        catalogue_data = get_catalogue_products()
        if data.get("object") == "page":
            for entry in data.get("entry", []):
                # ---- Messenger inbox events ----
                for event in entry.get("messaging", []):
                    sender_id = event.get("sender", {}).get("id", "")
                    if not sender_id or "message" not in event:
                        continue
                    msg = event["message"]
                    if msg.get("is_echo"):
                        continue

                    if "text" in msg:
                        text = msg["text"]
                        if not is_meaningful_message(text):
                            continue
                        print(f"User {sender_id}: {text}")
                        reply = get_gemini_reply(sender_id, text, catalogue_data)
                        send_message(sender_id, reply)
                        if "অর্ডার নিশ্চিত" in reply:
                            img_url = get_product_image_url(text)
                            if img_url:
                                send_image(sender_id, img_url)

                    elif "attachments" in msg:
                        for attachment in msg["attachments"]:
                            if attachment.get("type") == "image":
                                image_url = attachment.get("payload", {}).get("url", "")
                                if not image_url:
                                    send_message(sender_id, "ছবি প্রসেস করা যাচ্ছে না, আবার পাঠান।")
                                    continue
                                img_bytes, mime = download_messenger_image(image_url)
                                if not img_bytes:
                                    send_message(sender_id, "ছবিটা আসেনি, আবার পাঠান।")
                                    continue
                                history = get_history(sender_id)
                                history.append({"role": "user", "content": "[ছবি পাঠিয়েছে]"})
                                reply = analyze_image_with_gemini(img_bytes, mime or "image/jpeg", catalogue_data, history)
                                history.append({"role": "assistant", "content": reply})
                                save_history(sender_id, history)
                                send_message(sender_id, reply)
                            elif attachment.get("type") == "audio":
                                send_message(sender_id, "ভয়েস মেসেজ শুনতে পাচ্ছি না, টেক্সটে লিখুন।")
                            elif attachment.get("type") == "video":
                                send_message(sender_id, "ভিডিও দেখা যাচ্ছে না, ছবি বা টেক্সট পাঠান।")
                            elif attachment.get("type") == "file":
                                send_message(sender_id, "ফাইল সাপোর্ট করি না, ছবি বা টেক্সট পাঠান।")
                            elif attachment.get("type") == "sticker":
                                send_message(sender_id, "😊")

                # ---- Feed comment events ----
                for change in entry.get("changes", []):
                    if change.get("field") == "feed":
                        value = change.get("value", {})
                        if value.get("item") == "comment" and value.get("verb") == "add":
                            comment_id = value.get("comment_id")
                            comment_text = value.get("message", "")
                            from_id = value.get("from", {}).get("id", "")
                            if comment_text and from_id != "107165985626486" and is_meaningful_message(comment_text):
                                reply = get_gemini_reply(from_id, comment_text, catalogue_data, is_comment=True)
                                reply_comment(comment_id, reply)
    except Exception as e:
        print(f"Webhook error: {e}")
    return "OK", 200

@app.route("/sync-facebook", methods=["POST"])
def sync_facebook():
    auth = request.headers.get("X-Auth-Token", "")
    if auth != VERIFY_TOKEN:
        return jsonify({"error": "Unauthorized"}), 401
    data = request.json or {}
    limit = min(int(data.get("limit", 50)), 200)
    threading.Thread(target=sync_facebook_history_task, args=(limit,), daemon=True).start()
    return jsonify({
        "status": "started",
        "message": f"Background এ {limit}টি conversation sync শুরু হয়েছে। /knowledge দিয়ে দেখুন।"
    }), 200

@app.route("/sync-catalogue", methods=["POST"])
def sync_catalogue_route():
    auth = request.headers.get("X-Auth-Token", "")
    if auth != VERIFY_TOKEN:
        return jsonify({"error": "Unauthorized"}), 401
    threading.Thread(target=sync_catalogue_task, daemon=True).start()
    return jsonify({"status": "started", "message": "Catalogue sync চলছে।"}), 200

@app.route("/learn-history", methods=["POST"])
def learn_history():
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
    auth = request.headers.get("X-Auth-Token", "")
    if auth != VERIFY_TOKEN:
        return jsonify({"error": "Unauthorized"}), 401
    knowledge = get_knowledge()
    return jsonify({"knowledge": knowledge}), 200

@app.route("/products", methods=["GET"])
def view_products():
    auth = request.headers.get("X-Auth-Token", "")
    if auth != VERIFY_TOKEN:
        return jsonify({"error": "Unauthorized"}), 401
    products_text = get_active_products_text()
    return jsonify({"products": products_text}), 200

@app.route("/update-bot", methods=["POST"])
def update_bot():
    auth = request.headers.get("X-Auth-Token", "")
    if auth != VERIFY_TOKEN:
        return jsonify({"error": "Unauthorized"}), 401
    data = request.json
    new_code = data.get("code", "")
    if not new_code:
        return jsonify({"error": "No code provided"}), 400
    success = github_update_file("app.py", new_code, "Auto-update from Gemini")
    if success:
        return jsonify({"status": "success"}), 200
    return jsonify({"error": "GitHub update failed"}), 500

@app.route("/")
def home():
    return "Dhaka Exclusive Bot (Messenger + Gemini) Running ✅", 200

@app.route("/privacy")
def privacy():
    return "<h1>Privacy Policy - Dhaka Exclusive</h1><p>আমরা আপনার তথ্য সংগ্রহ করি না।</p>", 200

@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "platform": "facebook_messenger",
        "model": GEMINI_MODEL,
        "gemini_configured": bool(GEMINI_API_KEY),
        "messenger_configured": bool(PAGE_ACCESS_TOKEN),
        "db_configured": bool(DATABASE_URL),
        "catalogue_configured": bool(CATALOGUE_ID and PAGE_ACCESS_TOKEN)
    }), 200

init_db()

# Initial catalogue sync in background
threading.Thread(target=sync_catalogue_task, daemon=True).start()

thread = threading.Thread(target=keep_alive)
thread.daemon = True
thread.start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
��পনার তথ্য সংগ্রহ করি না।</p>", 200

@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "platform": "facebook_messenger",
        "model": GEMINI_MODEL,
        "gemini_configured": bool(GEMINI_API_KEY),
        "messenger_configured": bool(PAGE_ACCESS_TOKEN),
        "db_configured": bool(DATABASE_URL),
        "catalogue_configured": bool(CATALOGUE_ID and PAGE_ACCESS_TOKEN)
    }), 200

init_db()

# Initial catalogue sync in background
threading.Thread(target=sync_catalogue_task, daemon=True).start()

thread = threading.Thread(target=keep_alive)
thread.daemon = True
thread.start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
