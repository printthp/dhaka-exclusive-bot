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
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN", "")
WHATSAPP_PHONE_NUMBER_ID = os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
CATALOGUE_ID = os.environ.get("CATALOGUE_ID", "4177718442481756")
RAILWAY_URL = os.environ.get("RAILWAY_URL", "https://web-production-126eb.up.railway.app")
DATABASE_URL = os.environ.get("DATABASE_URL", "")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO = os.environ.get("GITHUB_REPO", "printthp/dhaka-exclusive-bot")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash-latest")
GEMINI_FALLBACK_MODELS = [
    "gemini-1.5-flash-latest",
    "gemini-1.5-flash",
    "gemini-1.5-pro",
    "gemini-2.0-flash",
    "gemini-2.5-flash",
]

# Build Bengali constants at runtime - avoids source encoding issues.
def _b(hex_str):
    return bytes.fromhex(hex_str.replace(" ", "")).decode("utf-8")

BN_ORDER_CONFIRM = _b("e0a685e0a6b0e0a78de0a6a1e0a6bee0a6b020e0a6a8e0a6bfe0a6b6e0a78de0a69ae0a6bfe0a6a4")
BN_EKTU_PROBLEM  = _b("e0a68fe0a695e0a69fe0a78120e0a6b8e0a6aee0a6b8e0a78de0a6afe0a6be20e0a6b9e0a69ae0a78de0a69be0a7872c20e0a68fe0a695e0a69fe0a78120e0a6aae0a6b0e0a78720e0a686e0a6ace0a6bee0a6b020e0a6ace0a6b2e0a781e0a6a8e0a5a4")
BN_CHHOBI_PROBLEM = _b("e0a69be0a6ace0a6bfe0a69fe0a6be20e0a6a6e0a787e0a696e0a6a4e0a78720e0a6aae0a6bee0a69ae0a78de0a69be0a6bf20e0a6a8e0a6be2c20e0a69fe0a787e0a695e0a78de0a6b8e0a69fe0a78720e0a6b2e0a6bfe0a696e0a781e0a6a8e0a5a4")
BN_BHOYESH       = _b("e0a6ade0a6afe0a6bce0a787e0a6b820e0a6aee0a787e0a6b8e0a787e0a69c20e0a6b6e0a781e0a6a8e0a6a4e0a78720e0a6aae0a6bee0a69ae0a78de0a69be0a6bf20e0a6a8e0a6be2c20e0a69fe0a787e0a695e0a78de0a6b8e0a69fe0a78720e0a6b2e0a6bfe0a696e0a781e0a6a8e0a5a4")
BN_VIDEO         = _b("e0a6ade0a6bfe0a6a1e0a6bfe0a69320e0a6a6e0a787e0a696e0a6be20e0a6afe0a6bee0a69ae0a78de0a69be0a78720e0a6a8e0a6be2c20e0a69be0a6ace0a6bf20e0a6ace0a6be20e0a69fe0a787e0a695e0a78de0a6b8e0a69f20e0a6aae0a6bee0a6a0e0a6bee0a6a8e0a5a4")
BN_FILE          = _b("e0a6abe0a6bee0a687e0a6b220e0a6b8e0a6bee0a6aae0a78be0a6b0e0a78de0a69f20e0a695e0a6b0e0a6bf20e0a6a8e0a6be2c20e0a69be0a6ace0a6bf20e0a6ace0a6be20e0a69fe0a787e0a695e0a78de0a6b8e0a69f20e0a6aae0a6bee0a6a0e0a6bee0a6a8e0a5a4")
BN_STICKER       = _b("e0a6a0e0a6bfe0a69520e0a686e0a69be0a787")
BN_IMG_FAIL_M    = _b("e0a69be0a6ace0a6bf20e0a6aae0a78de0a6b0e0a6b8e0a787e0a6b820e0a695e0a6b0e0a6be20e0a6afe0a6bee0a69ae0a78de0a69be0a78720e0a6a8e0a6be2c20e0a686e0a6ace0a6bee0a6b020e0a6aae0a6bee0a6a0e0a6bee0a6a8e0a5a4")
BN_IMG_RETRY_M   = _b("e0a69be0a6ace0a6bfe0a69fe0a6be20e0a686e0a6b8e0a787e0a6a8e0a6bf2c20e0a686e0a6ace0a6bee0a6b020e0a6aae0a6bee0a6a0e0a6bee0a6a8e0a5a4")
BN_IMG_RETRY_W   = _b("e0a69be0a6ace0a6bfe0a69fe0a6be20e0a686e0a6b8e0a787e0a6a8e0a6bf2c20e0a686e0a6ace0a6bee0a6b020e0a6aae0a6bee0a6a0e0a6bee0a6a8e0a5a4")
BN_WH_DOC        = _b("e0a6a1e0a695e0a781e0a6aee0a787e0a6a8e0a78de0a69f20e0a6b8e0a6bee0a6aae0a78be0a6b0e0a78de0a69f20e0a695e0a6b0e0a6bf20e0a6a8e0a6be2c20e0a69be0a6ace0a6bf20e0a6ace0a6be20e0a69fe0a787e0a695e0a78de0a6b8e0a69f20e0a6aae0a6bee0a6a0e0a6bee0a6a8e0a5a4")
BN_WEBSITE       = _b("6468616b616578636c75736976652e6f7267")
BN_PRIVACY       = _b("e0a686e0a6aee0a6b0e0a6be20e0a686e0a6aae0a6a8e0a6bee0a6b020e0a6ace0a78de0a6afe0a695e0a78de0a6a4e0a6bfe0a697e0a6a420e0a6a4e0a6a5e0a78de0a6af20e0a6b8e0a682e0a697e0a78de0a6b0e0a6b920e0a695e0a6b0e0a6bf20e0a6a8e0a6bee0a5a4")

IGNORE_PATTERNS = [
    "🔥","👏","❤️","😍","👍","🙏","😊","💯","✅","🎉","😂","🥰","💕","🌹","👌","💪"
]

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
        print("Database initialized OK")
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
            return "\n".join([f"{r[0]} | {r[1]} | in stock" for r in rows])
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
    try:
        if len(history) < 6:
            return
        conv_text = "\n".join([f"{m['role']}: {m['content']}" for m in history])
        prompt = (
            "You are an e-commerce conversation analyzer.\n"
            "Extract useful insights from this conversation.\n"
            "Return ONLY a JSON array (no explanation, no code block, no markdown), e.g.:\n"
            '[{"category": "popular products", "content": "Customers often ask about X"}]\n'
            "categories: popular products, common questions, objections, successful tactics, complaints\n"
            "Return [] if nothing useful.\n\n"
            f"Conversation:\n{conv_text}"
        )
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
        encoded = base64.b64encode(new_content.encode("utf-8")).decode("ascii")
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
    if all(c in "🔥👏❤️😍👍🙏😊💯✅🎉😂🥰💕🌹👌💪 " for c in text):
        return False
    return True

def get_catalogue_products():
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
                avail = "available" if in_stock else "out of stock"
                text += f"{name} | {price} | {avail}\n"
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
    try:
        resp = requests.get(image_url, timeout=20)
        if resp.status_code != 200:
            return None, ""
        mime = resp.headers.get('content-type', 'image/jpeg')
        return resp.content, mime
    except Exception as e:
        print(f"download_messenger_image error: {e}")
        return None, ""

# ========== WhatsApp Cloud API ==========
def send_whatsapp_message(to_number, text):
    try:
        if not WHATSAPP_TOKEN or not WHATSAPP_PHONE_NUMBER_ID:
            print("WhatsApp credentials missing; message skipped")
            return {}
        resp = requests.post(
            f"https://graph.facebook.com/v18.0/{WHATSAPP_PHONE_NUMBER_ID}/messages",
            headers={
                "Authorization": f"Bearer {WHATSAPP_TOKEN}",
                "Content-Type": "application/json"
            },
            json={
                "messaging_product": "whatsapp",
                "to": to_number,
                "type": "text",
                "text": {"body": text}
            },
            timeout=15
        )
        if resp.status_code >= 400:
            print(f"WhatsApp send error: {resp.status_code} {resp.text}")
        return resp.json() if resp.text else {}
    except Exception as e:
        print(f"send_whatsapp_message error: {e}")
        return {}

def send_whatsapp_image(to_number, image_url, caption=""):
    try:
        if not WHATSAPP_TOKEN or not WHATSAPP_PHONE_NUMBER_ID or not image_url:
            return {}
        payload = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "image",
            "image": {"link": image_url}
        }
        if caption:
            payload["image"]["caption"] = caption
        resp = requests.post(
            f"https://graph.facebook.com/v18.0/{WHATSAPP_PHONE_NUMBER_ID}/messages",
            headers={
                "Authorization": f"Bearer {WHATSAPP_TOKEN}",
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=20
        )
        if resp.status_code >= 400:
            print(f"WhatsApp image send error: {resp.status_code} {resp.text}")
        return resp.json() if resp.text else {}
    except Exception as e:
        print(f"send_whatsapp_image error: {e}")
        return {}

def download_whatsapp_media(media_id):
    try:
        if not WHATSAPP_TOKEN:
            return None, ""
        meta_url = f"https://graph.facebook.com/v18.0/{media_id}"
        meta_resp = requests.get(meta_url, headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}"}, timeout=15)
        meta = meta_resp.json()
        media_url = meta.get("url", "")
        mime = meta.get("mime_type", "image/jpeg")
        if not media_url:
            return None, ""
        dl = requests.get(media_url, headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}"}, timeout=30)
        if dl.status_code != 200:
            return None, ""
        return dl.content, mime
    except Exception as e:
        print(f"download_whatsapp_media error: {e}")
        return None, ""

# ========== Gemini API ==========
def _gemini_generate(payload, model, api_version="v1beta"):
    url = f"https://generativelanguage.googleapis.com/{api_version}/models/{model}:generateContent?key={GEMINI_API_KEY}"
    resp = requests.post(url, json=payload, timeout=45)
    if resp.status_code >= 400:
        return "", f"{resp.status_code} {resp.text[:300]}"
    data = resp.json()
    candidates = data.get("candidates", [])
    if candidates:
        parts = candidates[0].get("content", {}).get("parts", [])
        if parts:
            return parts[0].get("text", ""), ""
    return "", "empty candidates"

def _gemini_call_with_fallback(build_payload, caller_name):
    models_to_try = [GEMINI_MODEL] + [m for m in GEMINI_FALLBACK_MODELS if m != GEMINI_MODEL]
    versions = ["v1beta", "v1"]
    payload = build_payload()
    for api_version in versions:
        for model in models_to_try:
            text, err = _gemini_generate(payload, model, api_version)
            if text:
                if model != GEMINI_MODEL or api_version != "v1beta":
                    print(f"{caller_name}: using fallback {api_version}/{model}")
                return text
            print(f"{caller_name}: {api_version}/{model} failed -> {err[:120]}")
    return ""

def call_gemini_text(prompt, system=None, history=None, model=None, max_tokens=500, temperature=0.7):
    try:
        if not GEMINI_API_KEY:
            print("GEMINI_API_KEY missing")
            return ""
        contents = []
        if history:
            for m in history:
                role = "user" if m.get("role") == "user" else "model"
                content = m.get("content", "")
                if isinstance(content, str):
                    contents.append({"role": role, "parts": [{"text": content}]})
        contents.append({"role": "user", "parts": [{"text": prompt}]})
        def build_payload():
            payload = {
                "contents": contents,
                "generationConfig": {"maxOutputTokens": max_tokens, "temperature": temperature}
            }
            if system:
                payload["systemInstruction"] = {"parts": [{"text": system}]}
            return payload
        return _gemini_call_with_fallback(build_payload, "call_gemini_text")
    except Exception as e:
        print(f"call_gemini_text error: {e}")
        return ""

def call_gemini_multimodal(prompt, image_bytes, mime_type, system=None, history=None, model=None, max_tokens=400):
    try:
        if not GEMINI_API_KEY:
            return ""
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
        def build_payload():
            payload = {
                "contents": contents,
                "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.6}
            }
            if system:
                payload["systemInstruction"] = {"parts": [{"text": system}]}
            return payload
        return _gemini_call_with_fallback(build_payload, "call_gemini_multimodal")
    except Exception as e:
        print(f"call_gemini_multimodal error: {e}")
        return ""

def strip_markdown(text):
    if not text:
        return text
    return text.replace("**", "").replace("__", "").replace("*", "").replace("#", "").strip()

# ========== Sales-Intelligent Gemini Reply ==========
def detect_intent(user_message):
    try:
        text = (user_message or "").lower()
        if re.search(r"\b(hi|hello|hey|salam|assalamu|namaskar|namaskaram)\b", text):
            return "greeting"
        if re.search(r"(price|cost|koto|dam|koto taka|koto tk|how much)", text):
            return "price"
        if re.search(r"(stock|available|ache|nai|in stock|out of stock)", text):
            return "stock"
        if re.search(r"(order|kinbo|kinte|nibo|nite|chai|buy|purchase)", text):
            return "order"
        if re.search(r"(delivery|kobe|kokhon|somoy|kothay|where|when)", text):
            return "delivery"
        if re.search(r"(return|ferot|exchange|exchange korte)", text):
            return "return"
        if re.search(r"(kom|kombie|cheap|discount|offer|komate|less)", text):
            return "negotiation"
        if re.search(r"(kharap|baje|vuye|thaka|fraud|scam|report|complaint)", text):
            return "complaint"
        return "general"
    except Exception:
        return "general"

def get_gemini_reply(sender_id, user_message, catalogue_data, is_comment=False):
    try:
        history = get_history(sender_id)
        history.append({"role": "user", "content": user_message})

        knowledge = get_knowledge()
        intent = detect_intent(user_message)

        system = (
            "You are Riya, the senior sales agent of Dhaka Exclusive. Talk with customers in Bengali.\n\n"
            "Critical rules:\n"
            "- Directly answer what the customer asks\n"
            "- Use plain text. No markdown, no **, no *\n"
            "- Short sentences, simple natural Bengali\n"
            "- Remember prior context in the conversation\n"
            "- Use very few emojis\n"
            "- Always respond in Bengali\n\n"
            f"Current intent: {intent}\n\n"
        )

        if intent == "greeting":
            system += "When greeted: welcome warmly. Mention what we sell. Ask how you can help.\n\n"
        elif intent == "price":
            system += "When asked about price: state price from the catalogue first. Mention product highlights and invite order.\n\n"
        elif intent == "stock":
            system += "When asked about stock: check the catalogue and answer available or not.\n\n"
        elif intent == "negotiation":
            system += (
                "Negotiation ladder:\n"
                "1st time: 'This is our best price, see the quality first.'\n"
                "2nd time: 'Original product, price is fixed.'\n"
                "3rd time: 'If you take 2 I can see a little.'\n"
                "Final: 'For you I am reducing 20-30 taka, this is the final offer.'\n\n"
            )
        elif intent == "complaint":
            system += "For complaints/angry customers:\nApologize first. Say: 'Really sorry. Please tell me what happened, I will fix it.'\n\n"
        elif intent == "order":
            system += (
                "Order collection: ask step by step.\n"
                "Step 1: 'Your name?'\n"
                "Step 2: 'Phone number?'\n"
                "Step 3: 'Full address?'\n"
                "Step 4: 'Inside Dhaka or outside?'\n\n"
                "When all info collected, send summary in this format:\n"
                "Order confirmed!\n"
                "Product: [name]\n"
                "Price: [price]\n"
                "Delivery: [80/130] taka\n"
                "Total: [total]\n"
                "Name: [name]\n"
                "Phone: [number]\n"
                "Address: [address]\n"
                "Thanks for your order!\n\n"
            )
        elif intent == "delivery":
            system += "Delivery charge: Inside Dhaka 80 taka, Outside 130 taka.\n\n"
        elif intent == "return":
            system += "Return policy: 3 days if unused and original packaging. Customer pays return shipping.\n\n"

        system += (
            "Upsell / cross-sell:\n"
            "After answering, suggest 1 related product from the catalogue that fits.\n\n"
            f"Our catalogue:\n{catalogue_data if catalogue_data else 'Not loaded yet'}\n\n"
        )
        if knowledge:
            system += f"Learned from customers:\n{knowledge}\n\n"
        system += f"Website: {BN_WEBSITE}"

        if is_comment:
            system += "\n\nThis is a Facebook post comment. Reply in 1 short line and invite them to inbox."

        gemini_history = []
        for m in history[-31:-1]:
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
            return BN_EKTU_PROBLEM

        reply = strip_markdown(reply)

        history.append({"role": "assistant", "content": reply})
        save_history(sender_id, history)

        if "Order confirmed" in reply or BN_ORDER_CONFIRM in reply:
            threading.Thread(
                target=extract_knowledge_from_conversation,
                args=(history,),
                daemon=True
            ).start()

        return reply
    except Exception as e:
        print(f"get_gemini_reply error: {e}")
        return BN_EKTU_PROBLEM

def analyze_image_with_gemini(image_bytes, mime_type, catalogue_data, history):
    try:
        context = "\n".join([f"{m['role']}: {m['content']}" for m in history[-4:]])
        system = (
            "You are Riya, sales agent of Dhaka Exclusive.\n"
            f"Our products:\n{catalogue_data}\n"
            f"Prior conversation:\n{context}\n"
            "Rules:\n"
            "- Identify the product from the image and give price from catalogue\n"
            "- Plain text, no bold, no **, no *\n"
            "- 2-3 lines in natural Bengali\n"
            "- State price and invite to order"
        )
        reply = call_gemini_multimodal(
            prompt="What is this product? What is the price?",
            image_bytes=image_bytes,
            mime_type=mime_type,
            system=system,
            max_tokens=300
        )
        if not reply:
            return BN_CHHOBI_PROBLEM
        return strip_markdown(reply)
    except Exception as e:
        print(f"analyze_image_with_gemini error: {e}")
        return BN_CHHOBI_PROBLEM

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
        save_knowledge("system", f"Facebook history sync complete. Learned from {learned} conversations.", source="sync")
    except Exception as e:
        print(f"Sync task error: {e}")

# ========== Routes ==========
@app.route("/webhook", methods=["GET"])
def verify():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
    return "Error", 403

@app.route("/webhook", methods=["POST"])
def webhook():
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
                        print(f"Messenger user {sender_id}: {text}")
                        reply = get_gemini_reply(sender_id, text, catalogue_data)
                        send_message(sender_id, reply)
                        if "Order confirmed" in reply or BN_ORDER_CONFIRM in reply:
                            img_url = get_product_image_url(text)
                            if img_url:
                                send_image(sender_id, img_url)

                    elif "attachments" in msg:
                        for attachment in msg["attachments"]:
                            if attachment.get("type") == "image":
                                image_url = attachment.get("payload", {}).get("url", "")
                                if not image_url:
                                    send_message(sender_id, BN_IMG_FAIL_M)
                                    continue
                                img_bytes, mime = download_messenger_image(image_url)
                                if not img_bytes:
                                    send_message(sender_id, BN_IMG_RETRY_M)
                                    continue
                                history = get_history(sender_id)
                                history.append({"role": "user", "content": "[user sent an image]"})
                                reply = analyze_image_with_gemini(img_bytes, mime or "image/jpeg", catalogue_data, history)
                                history.append({"role": "assistant", "content": reply})
                                save_history(sender_id, history)
                                send_message(sender_id, reply)
                            elif attachment.get("type") == "audio":
                                send_message(sender_id, BN_BHOYESH)
                            elif attachment.get("type") == "video":
                                send_message(sender_id, BN_VIDEO)
                            elif attachment.get("type") == "file":
                                send_message(sender_id, BN_FILE)
                            elif attachment.get("type") == "sticker":
                                send_message(sender_id, BN_STICKER)

                # ---- Feed comment events ----
                for change in entry.get("changes", []):
                    if change.get("field") == "feed":
                        value = change.get("value", {})
                        if value.get("item") == "comment" and value.get("verb") == "add":
                            comment_id = value.get("comment_id")
                            comment_text = value.get("message", "")
                            from_id = value.get("from", {}).get("id", "")
                            if comment_text and is_meaningful_message(comment_text):
                                reply = get_gemini_reply(from_id, comment_text, catalogue_data, is_comment=True)
                                reply_comment(comment_id, reply)

        # ---- WhatsApp Cloud API events ----
        elif data.get("object") == "whatsapp_business_account":
            for entry in data.get("entry", []):
                for change in entry.get("changes", []):
                    value = change.get("value", {})
                    contacts = value.get("contacts", [])
                    from_number = ""
                    if contacts:
                        from_number = contacts[0].get("wa_id", "")
                    for msg in value.get("messages", []):
                        if not from_number:
                            from_number = msg.get("from", "")
                        if not from_number:
                            continue
                        mtype = msg.get("type", "")
                        if mtype == "text":
                            text = msg.get("text", {}).get("body", "")
                            if not is_meaningful_message(text):
                                continue
                            print(f"WhatsApp user {from_number}: {text}")
                            reply = get_gemini_reply(from_number, text, catalogue_data)
                            send_whatsapp_message(from_number, reply)
                            if "Order confirmed" in reply or BN_ORDER_CONFIRM in reply:
                                img_url = get_product_image_url(text)
                                if img_url:
                                    send_whatsapp_image(from_number, img_url)
                        elif mtype == "image":
                            media_id = msg.get("image", {}).get("id", "")
                            if media_id:
                                img_bytes, mime = download_whatsapp_media(media_id)
                                if img_bytes:
                                    history = get_history(from_number)
                                    history.append({"role": "user", "content": "[user sent an image]"})
                                    reply = analyze_image_with_gemini(img_bytes, mime or "image/jpeg", catalogue_data, history)
                                    history.append({"role": "assistant", "content": reply})
                                    save_history(from_number, history)
                                    send_whatsapp_message(from_number, reply)
                                else:
                                    send_whatsapp_message(from_number, BN_IMG_RETRY_W)
                            else:
                                send_whatsapp_message(from_number, BN_IMG_RETRY_W)
                        elif mtype == "audio":
                            send_whatsapp_message(from_number, BN_BHOYESH)
                        elif mtype == "video":
                            send_whatsapp_message(from_number, BN_VIDEO)
                        elif mtype == "document":
                            send_whatsapp_message(from_number, BN_WH_DOC)
                        elif mtype == "sticker":
                            send_whatsapp_message(from_number, BN_STICKER)
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
        "message": f"Background sync started for {limit} conversations. Check /knowledge."
    }), 200

@app.route("/sync-catalogue", methods=["POST"])
def sync_catalogue_route():
    auth = request.headers.get("X-Auth-Token", "")
    if auth != VERIFY_TOKEN:
        return jsonify({"error": "Unauthorized"}), 401
    threading.Thread(target=sync_catalogue_task, daemon=True).start()
    return jsonify({"status": "started", "message": "Catalogue sync running."}), 200

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
    return "Dhaka Exclusive Bot (Messenger + WhatsApp + Gemini) Running", 200

@app.route("/privacy")
def privacy():
    return f"<h1>Privacy Policy - Dhaka Exclusive</h1><p>{BN_PRIVACY}</p>", 200

@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "platforms": ["facebook_messenger", "whatsapp"],
        "model": GEMINI_MODEL,
        "gemini_configured": bool(GEMINI_API_KEY),
        "messenger_configured": bool(PAGE_ACCESS_TOKEN),
        "whatsapp_configured": bool(WHATSAPP_TOKEN and WHATSAPP_PHONE_NUMBER_ID),
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
