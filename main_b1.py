import os
import random
import time
import json
import csv
import requests

# =========================
# CONFIG
# =========================
BASE_URL = "http://localhost"
API_KEY = "339a46994a188577974dd49cf3c752e1e42d1db1749072992e19bc6b956d90a0"
API_USERNAME = "user1"

# =========================
# CSV FILES
# =========================
QUORA_POSTS_FILE = "quora_posts.csv"
QUORA_COMMENTS_FILE = "quora_comments.csv"

# =========================
# CATEGORIES
# =========================
CATEGORIES = [
    {"name": "iGaming Discussion", "color": "E45735", "text_color": "FFFFFF",
     "description": "Discuss online gaming industry trends and regulations."},
    {"name": "Affiliate Marketing", "color": "25AAE2", "text_color": "FFFFFF",
     "description": "Share tips and strategies for affiliate campaigns."},
    {"name": "Crypto & Investment", "color": "F7941D", "text_color": "FFFFFF",
     "description": "Cryptocurrency, forex, and investment opportunities."},
    {"name": "SEO & Traffic", "color": "3AB54A", "text_color": "FFFFFF",
     "description": "Digital marketing and traffic strategies."},
    {"name": "Make Money Online", "color": "92278F", "text_color": "FFFFFF",
     "description": "Freelancing, e-commerce, and online income."},
    {"name": "Malaysia Business", "color": "D0021B", "text_color": "FFFFFF",
     "description": "Business news and economy in Malaysia."},
]

# =========================
# USERS
# =========================
USERS = ["klgamer88", "affiliateking", "cryptomalaysia", "saborneo", "penangtrader", "johordigital", "seaborneo", "mloopmy","cryptofox","mike88","asianbiz","trafficking"]

# =========================
# DATA LOADING
# =========================

def load_csv(filename):
    if not filename or not os.path.exists(filename):
        return []
    try:
        with open(filename, mode='r', encoding='utf-8') as f:
            return list(csv.DictReader(f))
    except Exception as e:
        print(f"Error loading {filename}: {e}")
        return []

def get_topics_from_data():
    all_topics = []
    
    # Load Quora data
    quora_posts = load_csv(QUORA_POSTS_FILE)
    quora_comments = load_csv(QUORA_COMMENTS_FILE)
    
    # Group Quora comments by post_id
    quora_comments_by_post = {}
    for c in quora_comments:
        pid = c.get("post_id")
        if pid not in quora_comments_by_post:
            quora_comments_by_post[pid] = []
        quora_comments_by_post[pid].append({
            "id": c.get("comment_id"),
            "parent_id": c.get("parent_id"),
            "body": c.get("body", "")
        })

    for q in quora_posts:
        title = q.get("title", "").strip()
        if not title: continue
        
        # Discourse requires titles to be at least 15 characters
        if len(title) < 15:
            title = title + " - Discussion"
            if len(title) < 15:
                title = title.ljust(15, '.')

        # Map Quora topic to our categories
        q_topic = q.get("topic", "").lower()
        cat = "Make Money Online"
        if "invest" in q_topic or "economy" in q_topic: cat = "Crypto & Investment"
        elif "malaysia" in q_topic: cat = "Malaysia Business"
        elif "igaming" in q_topic or "gambling" in q_topic: cat = "iGaming Discussion"
        
        raw = q.get("selftext", "")
        if not raw:
            raw = f"Discussing: {title}\nSource: {q.get('url', 'Quora')}"
            
        all_topics.append({
            "id": q.get("id"),
            "title": title,
            "raw": raw,
            "category": cat,
            "replies": quora_comments_by_post.get(q.get("id"), [])
        })
        
    return all_topics

# =========================
# DISCOURSE API FUNCTIONS
# =========================

def get_headers(impersonate_user=None):
    return {
        "Api-Key": API_KEY,
        "Api-Username": impersonate_user if impersonate_user else API_USERNAME,
        "Content-Type": "application/json"
    }

def safe_body(text):
    text = str(text).strip()
    if len(text) < 20:
        # Pad with some natural looking text if it's too short
        padding = " ... (detailed discussion follows)"
        text = text + padding
        if len(text) < 20:
            text = text.ljust(20, '.')
    return text

def request_with_retry(method, url, **kwargs):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            r = requests.request(method, url, **kwargs)
            if r.status_code == 429:
                wait_time = (attempt + 1) * 30  # Wait 30, 60, 90 seconds
                print(f"      Rate limited (429). Waiting {wait_time} seconds...")
                time.sleep(wait_time)
                continue
            return r
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            time.sleep(5)
    return None

def get_or_create_category(name, color, text_color, description):
    try:
        r = request_with_retry("GET", f"{BASE_URL}/categories.json", headers=get_headers(), timeout=10)
        if r and r.status_code == 200:
            cats = r.json()["category_list"]["categories"]
            for c in cats:
                if c["name"].lower() == name.lower():
                    return c["id"]
        
        data = {"name": name, "color": color, "text_color": text_color, "description": description}
        r = request_with_retry("POST", f"{BASE_URL}/categories.json", headers=get_headers(), json=data, timeout=10)
        if r and r.status_code == 200:
            return r.json()["category"]["id"]
    except:
        pass
    return None

def post_topic(username, title, raw, category_id):
    raw = safe_body(raw)
    data = {"title": title, "raw": raw, "category": category_id}
    try:
        r = request_with_retry(
            "POST",
            f"{BASE_URL}/posts.json",
            headers=get_headers(username),
            json=data,
            timeout=15
        )
        if r and r.status_code == 200:
            return r.json().get("topic_id")
        elif r:
            print(f"      Error posting topic as {username}: {r.status_code} - {r.text[:100]}")
    except Exception as e:
        print(f"      Exception: {e}")
    return None

def post_reply(username, topic_id, raw, reply_to_post_number=None):
    raw = safe_body(raw)
    data = {"topic_id": topic_id, "raw": raw}
    if reply_to_post_number:
        data["reply_to_post_number"] = reply_to_post_number
        
    try:
        r = request_with_retry(
            "POST",
            f"{BASE_URL}/posts.json",
            headers=get_headers(username),
            json=data,
            timeout=15
        )
        if r and r.status_code == 200:
            return r.json().get("post_number")
    except:
        pass
    return None

# =========================
# MAIN
# =========================

if __name__ == "__main__":
    print("INVEST MALAYSIA CLUB - Quora Seeder (main_b1)")
    print("Loading data...")
    all_data = get_topics_from_data()
    print(f"Loaded {len(all_data)} topics.")
    
    if not all_data:
        print("No data to seed.")
        exit()

    cat_map = {}
    for c in CATEGORIES:
        cid = get_or_create_category(c["name"], c["color"], c["text_color"], c["description"])
        if cid: cat_map[c["name"]] = cid
        
    random.shuffle(all_data)
    
    seeded = 0
    for item in all_data:
        cat_id = cat_map.get(item["category"])
        if not cat_id: continue
        
        author = random.choice(USERS)
        topic_id = post_topic(author, item["title"], item["raw"], cat_id)
        
        if topic_id:
            seeded += 1
            print(f"[{seeded}] Seeded: {item['title'][:50]}...")
            
            post_num_map = {item["id"]: 1}
            replies = item["replies"]
            if replies:
                num_replies = min(len(replies), 15)
                for reply_data in replies[:num_replies]:
                    parent_id = reply_data["parent_id"]
                    reply_to = post_num_map.get(parent_id, 1)
                    
                    replier = random.choice(USERS)
                    new_post_num = post_reply(replier, topic_id, reply_data["body"], reply_to)
                    if new_post_num:
                        post_num_map[reply_data["id"]] = new_post_num
                        
                    time.sleep(random.uniform(3, 5))
            
            time.sleep(random.uniform(15, 30))
            
    print(f"Done! Seeded {seeded} topics.")
