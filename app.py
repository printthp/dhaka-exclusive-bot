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
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_FALLBACK_MODELS = ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-flash-lite-latest"]

def _b(hex_str):
    return bytes.fromhex(hex_str.replace(" ", "")).decode("utf-8")

BN_ORDER_CONFIRM  = _b("e0a685e0a6b0e0a78de0a6a1e0a6bee0a6b020e0a6a8e0a6bfe0a6b6e0a78de0a69ae0a6bfe0a6a4")
BN_EKTU_PROBLEM   = _b("e0a68fe0a695e0a69fe0a78120e0a6b8e0a6aee0a6b8e0a78de0a6afe0a6be20e0a6b9e0a69ae0a78de0a69be0a7872c20e0a68fe0a695e0a69fe0a78120e0a6aae0a6b0e0a78720e0a686e0a6ace0a6bee0a6b020e0a6ace0a6b2e0a781e0a6a8e0a5a4")
BN_CHHOBI_PROBLEM = _b("e0a69be0a6ace0a6bfe0a69fe0a6be20e0a6a6e0a787e0a696e0a6a4e0a78720e0a6aae0a6bee0a69ae0a78de0a69be0a6bf20e0a6a8e0a6be2c20e0a69fe0a787e0a695e0a78de0a6b8e0a69fe0a78720e0a6b2e0a6bfe0a696e0a781e0a6a8e0a5a4")
BN_BHOYESH        = _b("e0a6ade0a6afe0a6bce0a787e0a6b820e0a6aee0a787e0a6b8e0a787e0a69c20e0a6b6e0a781e0a6a8e0a6a4e0a78720e0a6aae0a6bee0a69ae0a78de0a69be0a6bf20e0a6a8e0a6be2c20e0a69fe0a787e0a695e0a78de0a6b8e0a69fe0a78720e0a6b2e0a6bfe0a696e0a781e0a6a8e0a5a4")
BN_VIDEO          = _b("e0a6ade0a6bfe0a6a1e0a6bfe0a69320e0a6a6e0a787e0a696e0a6be20e0a6afe0a6bee0a69ae0a78de0a69be0a78720e0a6a8e0a6be2c20e0a69be0a6ace0a6bf20e0a6ace0a6be20e0a69fe0a787e0a695e0a78de0a6b8e0a69f20e0a6aae0a6bee0a6a0e0a6bee0a6a8e0a5a4")
BN_FILE           = _b("e0a6abe0a6bee0a687e0a6b220e0a6b8e0a6bee0a6aae0a78be0a6b0e0a78de0a69f20e0a695e0a6b0e0a6bf20e0a6a8e0a6be2c20e0a69be0a6ace0a6bf20e0a6ace0a6be20e0a69fe0a787e0a695e0a78de0a6b8e0a69f20e0a6aae0a6bee0a6a0e0a6bee0a6a8e0a5a4")
BN_STICKER        = _b("e0a6a0e0a6bfe0a69520e0a686e0a69be0a787")
BN_IMG_FAIL_M     = _b("e0a69be0a6ace0a6bf20e0a6aae0a78de0a6b0e0a6b8e0a787e0a6b820e0a695e0a6b0e0a6be20e0a6afe0a6bee0a69ae0a78de0a69be0a78720e0a6a8e0a6be2c20e0a686e0a6ace0a6bee0a6b020e0a6aae0a6bee0a6a0e0a6bee0a6a8e0a5a4")
BN_IMG_RETRY_M    = _b("e0a69be0a6ace0a6bfe0a69fe0a6be20e0a686e0a6b8e0a787e0a6a8e0a6bf2c20e0a686e0a6ace0a6bee0a6b020e0a6aae0a6bee0a6a0e0a6bee0a6a8e0a5a4")
BN_IMG_RETRY_W    = _b("e0a69be0a6ace0a6bfe0a69fe0a6be20e0a686e0a6b8e0a787e0a6a8e0a6bf2c20e0a686e0a6ace0a6bee0a6b020e0a6aae0a6bee0a6a0e0a6bee0a6a8e0a5a4")
BN_WH_DOC         = _b("e0a6a1e0a695e0a781e0a6aee0a787e0a6a8e0a78de0a69f20e0a6b8e0a6bee0a6aae0a78be0a6b0e0a78de0a69f20e0a695e0a6b0e0a6bf20e0a6a8e0a6be2c20e0a69be0a6ace0a6bf20e0a6ace0a6be20e0a69fe0a787e0a695e0a78de0a6b8e0a69f20e0a6aae0a6bee0a6a0e0a6bee0a6a8e0a5a4")
BN_WEBSITE        = _b("6468616b616578636c75736976652e6f7267")
BN_PRIVACY        = _b("e0a686e0a6aee0a6b0e0a6be20e0a686e0a6aae0a6a8e0a6bee0a6b020e0a6ace0a78de0a6afe0a695e0a78de0a6a4e0a6bfe0a697e0a6a420e0a6a4e0a6a5e0a78de0a6af20e0a6b8e0a682e0a697e0a78de0a6b0e0a6b920e0a695e0a6b0e0a6bf20e0a6a8e0a6bee0a5a4")

IGNORE_PATTERNS = ["🔥","👏","❤️","😍","👍","🙏","😊","💯","✅","🎉","😂","🥰","💕","🌹","👌","💪"]

# ========== In-Memory Product Cache ==========
_product_cache = {"products": [], "text": "", "index": {}, "updated_at": 0}
_cache_lock = threading.Lock()
CATALOGUE_TTL = 600  # 10 minutes

# ========== FAQ Instant Answers ==========
FAQ_ANSWERS = {
    r"(delivery charge|ডেলিভারি চার্জ|delivery cost|shipping|কতদিন|কবে পাবো|কত দিন লাগবে)":
        "ঢাকার ভেতরে ১-২ দিন ৮০ টাকায়, ঢাকার বাইরে ২-৩ দিন ১৩০ টাকায় ডেলিভারি হয়।",
    r"(return|ফেরত|রিটার্ন|exchange|বদলে|পরিবর্তন)":
        "পণ্য পাওয়ার ৩ দিনের মধ্যে অব্যবহৃত ও original packaging-এ ফেরত দেওয়া যাবে।",
    r"(payment|পেমেন্ট|bkash|বিকাশ|nagad|নগদ|rocket|রকেট|cash on delivery|cod|ক্যাশ)":
        "বিকাশ, নগদ, রকেট ও ক্যাশ অন ডেলিভারি সব গ্রহণ করা হয়।",
    r"(original|আসল|real|fake|copy|নকল|duplicate|ভেজাল)":
        "আমাদের সব পণ্য ১০০% original। কোয়ালিটি নিয়ে সম্পূর্ণ গ্যারান্টি দিচ্ছি।",
    r"(contact|যোগাযোগ|helpline|hotline|customer care|কাস্টমার কেয়ার)":
        f"আমাদের website: {BN_WEBSITE} — এখানে message করলেও সাথে সাথে সাহায্য করা হবে।",
    r"(warranty|ওয়ারেন্টি|guarantee|গ্যারান্টি)":
        "পণ্যভেদে ৭ দিন থেকে ৬ মাস পর্যন্ত warranty আছে। সঠিক তথ্যের জন্য পণ্যের নাম বলুন।",
    r"(track|ট্র্যাক|parcel|পার্সেল|কোথায় আছে|status)":
        "আপনার অর্ডারের ট্র্যাকিং নম্বর দিন, আমরা আপডেট জানাবো।",
}

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

def get_active_products_from_db(limit=100):
    try:
        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT product_id, name, price, image_url FROM products
            WHERE active = TRUE ORDER BY updated_at DESC LIMIT %s
        """, (limit,))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [{"id": r[0], "name": r[1], "price": r[2], "image_url": r[3] or ""} for r in rows]
    except Exception as e:
        print(f"Get products DB error: {e}")
        return []

# ========== Product Cache + Index ==========
def build_product_index(products):
    index = {}
    for p in products:
        words = re.split(r'[\W_]+', (p.get("name") or "").lower())
        for word in words:
            if len(word) > 1:
                index.setdefault(word, []).append(p)
    return index

def find_similar_products(query, index, top_n=3):
    if not query or not index:
        return []
    words = re.split(r'[\W_]+', query.lower())
    scores = {}
    for w in words:
        if len(w) < 2:
            continue
        for p in index.get(w, []):
            key = p.get("name", "")
            if key not in scores:
                scores[key] = {"score": 0, "product": p}
            scores[key]["score"] += 1
    ranked = sorted(scores.values(), key=lambda x: x["score"], reverse=True)
    return [r["product"] for r in ranked[:top_n]]

def refresh_product_cache():
    """Facebook API থেকে products আনো, DB-তে save করো, cache update করো"""
    products = []
    text_lines = []
    try:
        if CATALOGUE_ID and PAGE_ACCESS_TOKEN:
            url = f"https://graph.facebook.com/v18.0/{CATALOGUE_ID}/products"
            params = {
                "access_token": PAGE_ACCESS_TOKEN,
                "fields": "id,name,price,currency,availability,image_url",
                "limit": 100
            }
            resp = requests.get(url, params=params, timeout=20)
            data = resp.json()
            if "data" in data:
                for p in data["data"]:
                    name = p.get("name", "")
                    price = p.get("price", "")
                    in_stock = p.get("availability") == "in stock"
                    img = p.get("image_url", "")
                    pid = p.get("id", "")
                    upsert_product(pid, name, price, in_stock, img)
                    if in_stock:
                        products.append({"id": pid, "name": name, "price": price, "image_url": img})
                        text_lines.append(f"{name} | {price}")
    except Exception as e:
        print(f"Catalogue fetch error: {e}")

    # Facebook API fail করলে DB থেকে নাও
    if not products:
        products = get_active_products_from_db(100)
        text_lines = [f"{p['name']} | {p['price']}" for p in products]

    index = build_product_index(products)
    with _cache_lock:
        _product_cache["products"] = products
        _product_cache["text"] = "\n".join(text_lines)
        _product_cache["index"] = index
        _product_cache["updated_at"] = time.time()

    print(f"Catalogue refreshed: {len(products)} products")

def get_products_cached():
    with _cache_lock:
        if time.time() - _product_cache["updated_at"] < CATALOGUE_TTL and _product_cache["products"]:
            return _product_cache["products"], _product_cache["text"], _product_cache["index"]
    refresh_product_cache()
    with _cache_lock:
        return _product_cache["products"], _product_cache["text"], _product_cache["index"]

def get_product_image_url_cached(product_name):
    with _cache_lock:
        products = _product_cache.get("products", [])
    if not products or not product_name:
        return ""
    words = [w.lower() for w in re.split(r'[\W_]+', product_name) if len(w) > 1]
    for p in products:
        lname = (p.get("name") or "").lower()
        if any(w in lname for w in words):
            return p.get("image_url", "")
    return ""

# ========== FAQ Check ==========
def check_faq(text):
    for pattern, answer in FAQ_ANSWERS.items():
        if re.search(pattern, text, re.IGNORECASE):
            return answer
    return None

# ========== Order State Machine ==========
ORDER_FIELDS = ["name", "phone", "address", "location"]
ORDER_QUESTIONS = {
    "name":     "আপনার নাম কী?",
    "phone":    "আপনার ফোন নম্বর?",
    "address":  "সম্পূর্ণ ঠিকানা? (বাড়ি/রাস্তা/এলাকা/জেলা)",
    "location": "ঢাকার ভেতরে নাকি বাইরে?",
}

def detect_order_state(history):
    """
    Returns (state, collected) where state is the next field to collect
    or 'complete' if all done.
    """
    collected = {}
    in_order = False
    for msg in history:
        content = msg.get("content", "")
        role = msg.get("role", "")
        if role == "assistant" and ("অর্ডার নিন" in content or "নাম কী" in content or "ফোন নম্বর" in content or "ঠিকানা" in content or "ঢাকার ভেতরে" in content):
            in_order = True
        if in_order and role == "user":
            if "name" not in collected and "নাম কী" not in content:
                if len(content.strip()) > 1 and not any(k in content for k in ["অর্ডার", "নম্বর", "ঠিকানা"]):
                    collected["name"] = content.strip()
            elif "phone" not in collected and re.search(r'01[3-9]\d{8}', content):
                collected["phone"] = re.search(r'01[3-9]\d{8}', content).group()
            elif "address" not in collected and len(content.strip()) > 5 and "name" in collected and "phone" in collected:
                collected["address"] = content.strip()
            elif "location" not in collected and re.search(r'(ঢাকা|dhaka|বাইরে|outside|ভেতরে|inside)', content, re.IGNORECASE):
                collected["location"] = content.strip()
    for field in ORDER_FIELDS:
        if field not in collected:
            return field, collected
    return "complete", collected

def format_order_summary(collected, product_name, price):
    loc = collected.get("location", "")
    delivery = 80 if re.search(r'(ভেতরে|inside|dhaka)', loc, re.IGNORECASE) else 130
    try:
        price_num = int(re.sub(r'[^\d]', '', price))
        total = price_num + delivery
    except:
        total = f"{price} + {delivery}"
    return (
        f"অর্ডার নিশ্চিত!\n"
        f"প্রোডাক্ট: {product_name}\n"
        f"দাম: {price}\n"
        f"ডেলিভারি: {delivery} টাকা\n"
        f"মোট: {total} টাকা\n"
        f"নাম: {collected.get('name', '')}\n"
        f"ফোন: {collected.get('phone', '')}\n"
        f"ঠিকানা: {collected.get('address', '')}\n"
        f"ধন্যবাদ আপনার অর্ডারের জন্য!"
    )

def count_negotiations(history):
    count = 0
    for msg in history:
        if msg.get("role") == "user":
            if re.search(r'(কম|komie|kombie|discount|offer|সস্তা|cheap)', msg.get("content", ""), re.IGNORECASE):
                count += 1
    return count

# ========== Knowledge Extraction ==========
def extract_knowledge_from_conversation(history):
    try:
        if len(history) < 6:
            return
        conv_text = "\n".join([f"{m['role']}: {m['content']}" for m in history])
        prompt = (
            "You are an e-commerce conversation analyzer.\n"
            "Extract useful business insights from this conversation.\n"
            "Return ONLY a JSON array, e.g.:\n"
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
            text = re.sub(r"^```(json)?", "", text).strip().rstrip("```").strip()
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

def strip_markdown(text):
    if not text:
        return text
    return re.sub(r'[*_#`]+', '', text).strip()

# ========== Facebook Messenger ==========
def send_message(recipient_id, text):
    try:
        if not PAGE_ACCESS_TOKEN:
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

# ========== WhatsApp ==========
def send_whatsapp_message(to_number, text):
    try:
        if not WHATSAPP_TOKEN or not WHATSAPP_PHONE_NUMBER_ID:
            return {}
        resp = requests.post(
            f"https://graph.facebook.com/v18.0/{WHATSAPP_PHONE_NUMBER_ID}/messages",
            headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"},
            json={"messaging_product": "whatsapp", "to": to_number, "type": "text", "text": {"body": text}},
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
        payload = {"messaging_product": "whatsapp", "to": to_number, "type": "image", "image": {"link": image_url}}
        if caption:
            payload["image"]["caption"] = caption
        resp = requests.post(
            f"https://graph.facebook.com/v18.0/{WHATSAPP_PHONE_NUMBER_ID}/messages",
            headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"},
            json=payload, timeout=20
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
        meta = requests.get(
            f"https://graph.facebook.com/v18.0/{media_id}",
            headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}"}, timeout=15
        ).json()
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
    payload = build_payload()
    for api_version in ["v1beta", "v1"]:
        for model in models_to_try:
            text, err = _gemini_generate(payload, model, api_version)
            if text:
                if model != GEMINI_MODEL or api_version != "v1beta":
                    print(f"{caller_name}: fallback {api_version}/{model}")
                return text
            print(f"{caller_name}: {api_version}/{model} failed -> {err[:100]}")
    return ""

def call_gemini_text(prompt, system=None, history=None, max_tokens=500, temperature=0.7):
    try:
        if not GEMINI_API_KEY:
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
            payload = {"contents": contents, "generationConfig": {"maxOutputTokens": max_tokens, "temperature": temperature}}
            if system:
                payload["systemInstruction"] = {"parts": [{"text": system}]}
            return payload
        return _gemini_call_with_fallback(build_payload, "call_gemini_text")
    except Exception as e:
        print(f"call_gemini_text error: {e}")
        return ""

def call_gemini_multimodal(prompt, image_bytes, mime_type, system=None, history=None, max_tokens=400):
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
            payload = {"contents": contents, "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.5}}
            if system:
                payload["systemInstruction"] = {"parts": [{"text": system}]}
            return payload
        return _gemini_call_with_fallback(build_payload, "call_gemini_multimodal")
    except Exception as e:
        print(f"call_gemini_multimodal error: {e}")
        return ""

# ========== Intent Detection ==========
def detect_intent(user_message):
    text = (user_message or "").lower()
    if re.search(r"\b(hi|hello|hey|salam|assalamu|namaskar|হ্যালো|সালাম|হেলো|হাই)\b", text):
        return "greeting"
    if re.search(r"(price|cost|dam|daam|দাম|কত|how much|taka|টাকা|price কত|মূল্য)", text):
        return "price"
    if re.search(r"(stock|available|আছে|নাই|নেই|in stock|out of stock|পাওয়া যাবে)", text):
        return "stock"
    if re.search(r"(order|অর্ডার|kinbo|কিনবো|nibo|নিবো|buy|purchase|নিতে চাই)", text):
        return "order"
    if re.search(r"(delivery|ডেলিভারি|কবে|কতদিন|shipping|চার্জ)", text):
        return "delivery"
    if re.search(r"(return|ফেরত|exchange|রিটার্ন|বদলে)", text):
        return "return"
    if re.search(r"(kom|কম|discount|অফার|offer|সস্তা|cheap|ছাড়)", text):
        return "negotiation"
    if re.search(r"(kharap|খারাপ|baje|বাজে|fraud|scam|complaint|অভিযোগ|রাগ)", text):
        return "complaint"
    return "general"

# ========== Smart Image Analysis ==========
def analyze_image_smart(image_bytes, mime_type, products, product_index, history):
    """
    ১. Gemini দিয়ে ছবির পণ্য চিহ্নিত করো
    ২. Catalogue-এ মিলাও
    ৩. পেলে দাম বলো, না পেলে similar পণ্য suggest করো
    """
    try:
        # Step 1: ছবি দেখে পণ্য চিহ্নিত করো
        identified = call_gemini_multimodal(
            prompt="What product is shown in this image? Answer in Bengali only, maximum 10 words. Be specific about product type and features.",
            image_bytes=image_bytes,
            mime_type=mime_type,
            max_tokens=80
        )
        identified = strip_markdown(identified or "")

        # Step 2: Catalogue-এ মিলাও
        matches = find_similar_products(identified, product_index, top_n=3) if identified else []

        catalogue_text = "\n".join([f"{p['name']} | {p['price']}" for p in products[:50]])
        context = "\n".join([f"{m['role']}: {m['content']}" for m in history[-3:]])

        if matches:
            matched_text = "\n".join([f"- {p['name']}: {p['price']}" for p in matches])
            system = (
                "You are Riya, sales agent of Dhaka Exclusive. Respond in Bengali only.\n"
                "Rules: plain text, no markdown, max 4 lines, invite to order.\n"
                f"Customer sent an image. It appears to show: {identified}\n"
                f"Matching products in our catalogue:\n{matched_text}\n"
                "Tell the customer you found matching products, mention name and price, invite to order."
            )
        else:
            top3 = products[:3]
            similar_text = "\n".join([f"- {p['name']}: {p['price']}" for p in top3])
            system = (
                "You are Riya, sales agent of Dhaka Exclusive. Respond in Bengali only.\n"
                "Rules: plain text, no markdown, max 4 lines.\n"
                f"Customer sent an image showing: {identified}\n"
                "We don't have this exact product in our catalogue.\n"
                f"Our available products:\n{similar_text}\n"
                "Politely say we don't have exactly this product, but suggest 2-3 of our products that might interest them."
            )

        reply = call_gemini_text(
            prompt=f"Image analysis context: {context}" if context else "Respond to the image.",
            system=system,
            max_tokens=300,
            temperature=0.6
        )

        return strip_markdown(reply) if reply else BN_CHHOBI_PROBLEM

    except Exception as e:
        print(f"analyze_image_smart error: {e}")
        return BN_CHHOBI_PROBLEM

# ========== Main Reply Engine ==========
def get_gemini_reply(sender_id, user_message, catalogue_text, product_index, products, is_comment=False):
    try:
        # Step 1: FAQ instant answer (no AI needed)
        if not is_comment:
            faq_answer = check_faq(user_message)
            if faq_answer:
                history = get_history(sender_id)
                history.append({"role": "user", "content": user_message})
                history.append({"role": "assistant", "content": faq_answer})
                save_history(sender_id, history)
                return faq_answer

        # Step 2: Load history and detect context
        history = get_history(sender_id)
        history.append({"role": "user", "content": user_message})

        intent = detect_intent(user_message)
        knowledge = get_knowledge()
        neg_count = count_negotiations(history)

        # Step 3: Order state machine
        order_section = ""
        if intent == "order" or any(
            re.search(r"(অর্ডার|order|কিনবো|নিবো)", m.get("content", ""), re.IGNORECASE)
            for m in history[-6:] if m.get("role") == "assistant"
        ):
            order_state, collected = detect_order_state(history)
            if order_state != "complete" and order_state in ORDER_QUESTIONS:
                next_q = ORDER_QUESTIONS[order_state]
                order_section = f"\nOrder collection in progress. Next required field: {order_state}. Ask: '{next_q}'\n"
            elif order_state == "complete":
                # সব তথ্য আছে, summary দাও
                p_name = ""
                for msg in reversed(history):
                    if msg.get("role") == "assistant" and any(p.get("name", "") in msg.get("content", "") for p in products):
                        for p in products:
                            if p.get("name", "") in msg.get("content", ""):
                                p_name = p["name"]
                                p_price = p["price"]
                                break
                        break
                if p_name:
                    summary = format_order_summary(collected, p_name, p_price)
                    history.append({"role": "assistant", "content": summary})
                    save_history(sender_id, history)
                    threading.Thread(target=extract_knowledge_from_conversation, args=(history,), daemon=True).start()
                    return summary

        # Step 4: Build system prompt
        negotiation_guidance = ""
        if intent == "negotiation" or neg_count > 0:
            if neg_count == 0:
                negotiation_guidance = "1st negotiation: 'This is our best price, quality speaks for itself.'\n"
            elif neg_count == 1:
                negotiation_guidance = "2nd negotiation: 'Original product, price is fixed.'\n"
            elif neg_count == 2:
                negotiation_guidance = "3rd negotiation: 'If you take 2, I can see a little discount.'\n"
            else:
                negotiation_guidance = "Final: 'For you only, reducing 20-30 taka. Final offer.'\n"

        system = (
            "You are Riya, senior sales agent of Dhaka Exclusive. Always respond in Bengali.\n\n"
            "CRITICAL RULES:\n"
            "- Directly answer what the customer asks\n"
            "- Use ONLY prices from the catalogue below — never invent prices\n"
            "- Plain text only. No markdown, no **, no *, no #\n"
            "- Maximum 4 lines per reply\n"
            "- Natural, friendly Bengali\n"
            "- Remember all prior context\n\n"
            f"Intent: {intent}\n"
            f"{order_section}"
            f"{negotiation_guidance}"
        )

        if intent == "greeting":
            system += "Greet warmly, briefly introduce our shop, ask how you can help.\n\n"
        elif intent == "price":
            system += "State price from catalogue immediately. Then mention 1 product highlight. Invite to order.\n\n"
        elif intent == "stock":
            system += "Check catalogue and confirm available or not. If not available, suggest closest alternative.\n\n"
        elif intent == "complaint":
            system += "Apologize sincerely first. Say: 'Really sorry. Tell me what happened, I will fix it.'\n\n"
        elif intent == "delivery":
            system += "Delivery: Inside Dhaka 80 taka 1-2 days. Outside 130 taka 2-3 days.\n\n"
        elif intent == "return":
            system += "Return: within 3 days, unused, original packaging. Customer covers return shipping.\n\n"

        system += (
            "After answering, suggest 1 related product from catalogue (upsell).\n\n"
            f"CATALOGUE (use only these prices):\n{catalogue_text if catalogue_text else 'Not loaded'}\n\n"
        )
        if knowledge:
            system += f"Learned from past customers:\n{knowledge}\n\n"
        system += f"Website: {BN_WEBSITE}"

        if is_comment:
            system = (
                "You are Riya from Dhaka Exclusive. This is a Facebook post comment.\n"
                "Reply in 1 short line in Bengali. Invite them to inbox for details.\n"
                "Plain text only, no markdown.\n"
                f"Catalogue: {catalogue_text[:200] if catalogue_text else 'Not loaded'}"
            )

        # Step 5: Build Gemini history (last 30 messages)
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
            temperature=0.65
        )

        if not reply:
            return BN_EKTU_PROBLEM

        reply = strip_markdown(reply)
        history.append({"role": "assistant", "content": reply})
        save_history(sender_id, history)

        if BN_ORDER_CONFIRM in reply or "Order confirmed" in reply:
            threading.Thread(target=extract_knowledge_from_conversation, args=(history,), daemon=True).start()

        return reply

    except Exception as e:
        print(f"get_gemini_reply error: {e}")
        return BN_EKTU_PROBLEM

# ========== Background Tasks ==========
def catalogue_refresh_loop():
    time.sleep(10)
    refresh_product_cache()
    while True:
        time.sleep(CATALOGUE_TTL)
        try:
            refresh_product_cache()
        except Exception as e:
            print(f"Catalogue refresh loop error: {e}")

def has_synced_before():
    try:
        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute("SELECT id FROM knowledge_base WHERE source = 'sync' LIMIT 1")
        row = cur.fetchone()
        cur.close()
        conn.close()
        return row is not None
    except:
        return False

def keep_alive():
    time.sleep(30)
    if not has_synced_before():
        print("First startup: auto-syncing Facebook history...")
        sync_facebook_history_task(100)
    else:
        print("Facebook history already synced, skipping initial sync.")

    last_daily_sync = time.time()
    DAILY = 86400

    while True:
        time.sleep(600)
        try:
            requests.get(f"{RAILWAY_URL}/", timeout=10)
            print("Keep alive ping sent")
        except:
            pass
        if time.time() - last_daily_sync >= DAILY:
            print("Daily sync: fetching latest conversations...")
            threading.Thread(target=sync_facebook_history_task, args=(30,), daemon=True).start()
            last_daily_sync = time.time()

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
                sid = msg.get("from", {}).get("id", "")
                text = (msg.get("message") or "").strip()
                if not text:
                    continue
                role = "assistant" if sid == page_id else "user"
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
        products, catalogue_text, product_index = get_products_cached()

        if data.get("object") == "page":
            for entry in data.get("entry", []):
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
                        print(f"Messenger {sender_id}: {text}")
                        reply = get_gemini_reply(sender_id, text, catalogue_text, product_index, products)
                        send_message(sender_id, reply)

                        if BN_ORDER_CONFIRM in reply or "Order confirmed" in reply:
                            img_url = get_product_image_url_cached(text)
                            if img_url:
                                send_image(sender_id, img_url)
                            # Upsell: suggest another product
                            upsell_candidates = [p for p in products if p.get("image_url") and p["name"] not in text]
                            if upsell_candidates:
                                up = upsell_candidates[0]
                                send_message(sender_id, f"আরো দেখুন: {up['name']} — {up['price']}")

                    elif "attachments" in msg:
                        for attachment in msg["attachments"]:
                            atype = attachment.get("type")
                            if atype == "image":
                                image_url = attachment.get("payload", {}).get("url", "")
                                if not image_url:
                                    send_message(sender_id, BN_IMG_FAIL_M)
                                    continue
                                img_bytes, mime = download_messenger_image(image_url)
                                if not img_bytes:
                                    send_message(sender_id, BN_IMG_RETRY_M)
                                    continue
                                history = get_history(sender_id)
                                history.append({"role": "user", "content": "[ছবি পাঠিয়েছে]"})
                                reply = analyze_image_smart(img_bytes, mime or "image/jpeg", products, product_index, history)
                                history.append({"role": "assistant", "content": reply})
                                save_history(sender_id, history)
                                send_message(sender_id, reply)
                            elif atype == "audio":
                                send_message(sender_id, BN_BHOYESH)
                            elif atype == "video":
                                send_message(sender_id, BN_VIDEO)
                            elif atype == "file":
                                send_message(sender_id, BN_FILE)
                            elif atype == "sticker":
                                send_message(sender_id, BN_STICKER)

                for change in entry.get("changes", []):
                    if change.get("field") == "feed":
                        value = change.get("value", {})
                        if value.get("item") == "comment" and value.get("verb") == "add":
                            comment_id = value.get("comment_id")
                            comment_text = value.get("message", "")
                            from_id = value.get("from", {}).get("id", "")
                            if comment_text and is_meaningful_message(comment_text):
                                reply = get_gemini_reply(from_id, comment_text, catalogue_text, product_index, products, is_comment=True)
                                reply_comment(comment_id, reply)

        elif data.get("object") == "whatsapp_business_account":
            for entry in data.get("entry", []):
                for change in entry.get("changes", []):
                    value = change.get("value", {})
                    contacts = value.get("contacts", [])
                    from_number = contacts[0].get("wa_id", "") if contacts else ""
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
                            print(f"WhatsApp {from_number}: {text}")
                            reply = get_gemini_reply(from_number, text, catalogue_text, product_index, products)
                            send_whatsapp_message(from_number, reply)
                            if BN_ORDER_CONFIRM in reply or "Order confirmed" in reply:
                                img_url = get_product_image_url_cached(text)
                                if img_url:
                                    send_whatsapp_image(from_number, img_url)
                                upsell_candidates = [p for p in products if p.get("image_url") and p["name"] not in text]
                                if upsell_candidates:
                                    up = upsell_candidates[0]
                                    send_whatsapp_message(from_number, f"আরো দেখুন: {up['name']} — {up['price']}")
                        elif mtype == "image":
                            media_id = msg.get("image", {}).get("id", "")
                            if media_id:
                                img_bytes, mime = download_whatsapp_media(media_id)
                                if img_bytes:
                                    history = get_history(from_number)
                                    history.append({"role": "user", "content": "[ছবি পাঠিয়েছে]"})
                                    reply = analyze_image_smart(img_bytes, mime or "image/jpeg", products, product_index, history)
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
    return jsonify({"status": "started", "message": f"Syncing {limit} conversations in background."}), 200

@app.route("/sync-catalogue", methods=["POST"])
def sync_catalogue_route():
    auth = request.headers.get("X-Auth-Token", "")
    if auth != VERIFY_TOKEN:
        return jsonify({"error": "Unauthorized"}), 401
    threading.Thread(target=refresh_product_cache, daemon=True).start()
    return jsonify({"status": "started", "message": "Catalogue refresh running."}), 200

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
    return jsonify({"knowledge": get_knowledge()}), 200

@app.route("/products", methods=["GET"])
def view_products():
    auth = request.headers.get("X-Auth-Token", "")
    if auth != VERIFY_TOKEN:
        return jsonify({"error": "Unauthorized"}), 401
    with _cache_lock:
        products = _product_cache.get("products", [])
        updated = _product_cache.get("updated_at", 0)
    return jsonify({"count": len(products), "updated_at": updated, "products": products}), 200

@app.route("/update-bot", methods=["POST"])
def update_bot():
    auth = request.headers.get("X-Auth-Token", "")
    if auth != VERIFY_TOKEN:
        return jsonify({"error": "Unauthorized"}), 401
    data = request.json
    new_code = data.get("code", "")
    if not new_code:
        return jsonify({"error": "No code provided"}), 400
    success = github_update_file("app.py", new_code, "Auto-update from bot")
    return jsonify({"status": "success" if success else "error"}), 200 if success else 500

@app.route("/")
def home():
    with _cache_lock:
        product_count = len(_product_cache.get("products", []))
    return f"Dhaka Exclusive Bot Running | Products cached: {product_count}", 200

@app.route("/privacy")
def privacy():
    return f"<h1>Privacy Policy - Dhaka Exclusive</h1><p>{BN_PRIVACY}</p>", 200

@app.route("/health")
def health():
    with _cache_lock:
        product_count = len(_product_cache.get("products", []))
        cache_age = int(time.time() - _product_cache.get("updated_at", 0))
    return jsonify({
        "status": "ok",
        "platforms": ["facebook_messenger", "whatsapp"],
        "model": GEMINI_MODEL,
        "gemini_configured": bool(GEMINI_API_KEY),
        "messenger_configured": bool(PAGE_ACCESS_TOKEN),
        "whatsapp_configured": bool(WHATSAPP_TOKEN and WHATSAPP_PHONE_NUMBER_ID),
        "db_configured": bool(DATABASE_URL),
        "catalogue_configured": bool(CATALOGUE_ID and PAGE_ACCESS_TOKEN),
        "products_cached": product_count,
        "cache_age_seconds": cache_age,
    }), 200

@app.route("/test-flow", methods=["POST"])
def test_flow():
    auth = request.headers.get("X-Auth-Token", "")
    if auth != VERIFY_TOKEN:
        return jsonify({"error": "Unauthorized"}), 401
    data = request.json or {}
    sender = data.get("sender_id", "test_user_xyz")
    msg = data.get("message", "hello")
    products, catalogue_text, product_index = get_products_cached()
    out = {
        "gemini_key_set": bool(GEMINI_API_KEY),
        "catalogue_products": len(products),
        "faq_match": check_faq(msg),
        "intent": detect_intent(msg),
    }
    try:
        reply = get_gemini_reply(sender, msg, catalogue_text, product_index, products)
        out["reply"] = reply
    except Exception as e:
        out["reply_error"] = str(e)[:300]
    return jsonify(out), 200

@app.route("/debug-gemini", methods=["GET"])
def debug_gemini():
    if not GEMINI_API_KEY:
        return jsonify({"gemini_key_set": False}), 200
    test_prompt = "Say hello in one word."
    results = {}
    for api_version in ["v1beta", "v1"]:
        for model in ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-flash-lite-latest", "gemini-1.5-flash"]:
            try:
                payload = {"contents": [{"role": "user", "parts": [{"text": test_prompt}]}], "generationConfig": {"maxOutputTokens": 20}}
                text, err = _gemini_generate(payload, model, api_version)
                results[f"{api_version}/{model}"] = {"ok": bool(text), "text": text[:60] if text else "", "err": err[:100] if err else ""}
            except Exception as e:
                results[f"{api_version}/{model}"] = {"exception": str(e)[:100]}
    working = [k for k, v in results.items() if v.get("ok")]
    return jsonify({"gemini_key_set": True, "working_models": working, "results": results}), 200

# ========== Startup ==========
init_db()

threading.Thread(target=catalogue_refresh_loop, daemon=True).start()

thread = threading.Thread(target=keep_alive)
thread.daemon = True
thread.start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
