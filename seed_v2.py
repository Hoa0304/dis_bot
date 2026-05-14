import requests
import random
import time
import json
import csv
import os

# =========================
# CONFIG
# =========================
BASE_URL = "http://localhost"
API_KEY = "339a46994a188577974dd49cf3c752e1e42d1db1749072992e19bc6b956d90a0"
API_USERNAME = "hoa"
PASSWORD = "Test123456!"

admin_headers = {
    "Api-Key": API_KEY,
    "Api-Username": API_USERNAME,
    "Content-Type": "application/json"
}

# =========================
# CSV FILES
# =========================
REDDIT_FILES = [
    {"posts": "reddit_malaysia_posts.csv", "comments": "reddit_malaysia_comments.csv", "default_cat": "Malaysia Business"},
    {"posts": "reddit_MalaysianPF_posts.csv", "comments": "reddit_MalaysianPF_comments.csv", "default_cat": "Crypto & Investment"},
    {"posts": "reddit_Bolehland_posts.csv", "comments": "", "default_cat": "Malaysia Business"},
]
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
USERS = ["klgamer88", "affiliateking", "cryptomalaysia", "saborneo", "penangtrader", "johordigital", "seaborneo", "mloopmy"]

# =========================
# DATA LOADING
# =========================

def load_csv(filename):
    if not os.path.exists(filename):
        return []
    try:
        with open(filename, mode='r', encoding='utf-8') as f:
            return list(csv.DictReader(f))
    except Exception as e:
        print(f"Error loading {filename}: {e}")
        return []

def get_topics_from_data():
    all_topics = []
    
    # Load Reddit data
    for item in REDDIT_FILES:
        posts = load_csv(item["posts"])
        comments = load_csv(item["comments"]) if item["comments"] else []
        
        # Group comments by post_id
        comments_by_post = {}
        for c in comments:
            pid = c.get("post_id")
            if pid not in comments_by_post:
                comments_by_post[pid] = []
            comments_by_post[pid].append(c.get("body", ""))
            
        for p in posts:
            # Filter: only self-posts with content or interesting titles
            content = p.get("selftext", "").strip()
            if not content and not p.get("url"):
                continue
            
            # Use original URL if no text
            raw = content if content else f"Link: {p.get('url')}"
            
            all_topics.append({
                "title": p.get("title"),
                "raw": raw,
                "category": item["default_cat"],
                "replies": comments_by_post.get(p.get("id"), [])
            })
            
    # Load Quora data
    quora_posts = load_csv(QUORA_POSTS_FILE)
    quora_comments = load_csv(QUORA_COMMENTS_FILE)
    
    # Group Quora comments by post_id
    quora_comments_by_post = {}
    for c in quora_comments:
        pid = c.get("post_id")
        if pid not in quora_comments_by_post:
            quora_comments_by_post[pid] = []
        quora_comments_by_post[pid].append(c.get("body", ""))

    for q in quora_posts:
        # Map Quora topic to our categories
        q_topic = q.get("topic", "").lower()
        cat = "Make Money Online"
        if "invest" in q_topic or "economy" in q_topic: cat = "Crypto & Investment"
        elif "malaysia" in q_topic: cat = "Malaysia Business"
        elif "igaming" in q_topic or "gambling" in q_topic: cat = "iGaming Discussion"
        
        raw = q.get("selftext", "")
        if not raw:
            raw = f"Discussing: {q.get('title')}\nSource: {q.get('url', 'Quora')}"
            
        all_topics.append({
            "title": q.get("title"),
            "raw": raw,
            "category": cat,
            "replies": quora_comments_by_post.get(q.get("id"), [])
        })
        
    return all_topics

# =========================
# DISCOURSE API FUNCTIONS
# =========================

def get_or_create_category(name, color, text_color, description):
    # Check if exists
    r = requests.get(f"{BASE_URL}/categories.json", headers=admin_headers)
    if r.status_code == 200:
        cats = r.json()["category_list"]["categories"]
        for c in cats:
            if c["name"].lower() == name.lower():
                return c["id"]
                
    # Create if not found
    data = {"name": name, "color": color, "text_color": text_color, "description": description}
    r = requests.post(f"{BASE_URL}/categories.json", headers=admin_headers, json=data)
    if r.status_code == 200:
        return r.json()["category"]["id"]
    return None

def login_user(username):
    session = requests.Session()
    try:
        csrf_data = session.get(f"{BASE_URL}/session/csrf.json").json()
        csrf = csrf_data["csrf"]
        r = session.post(
            f"{BASE_URL}/session.json",
            headers={"X-CSRF-Token": csrf, "Content-Type": "application/json"},
            json={"login": username, "password": PASSWORD}
        )
        if r.status_code == 200:
            new_csrf = session.get(f"{BASE_URL}/session/csrf.json").json()["csrf"]
            return {"session": session, "csrf": new_csrf}
    except:
        pass
    return None

def post_topic(user_session, title, raw, category_id):
    data = {"title": title, "raw": raw, "category": category_id}
    r = user_session["session"].post(
        f"{BASE_URL}/posts.json",
        headers={"X-CSRF-Token": user_session["csrf"], "Content-Type": "application/json"},
        json=data
    )
    if r.status_code == 200:
        return r.json().get("topic_id")
    return None

def post_reply(user_session, topic_id, raw):
    data = {"topic_id": topic_id, "raw": raw}
    user_session["session"].post(
        f"{BASE_URL}/posts.json",
        headers={"X-CSRF-Token": user_session["csrf"], "Content-Type": "application/json"},
        json=data
    )

# =========================
# MAIN
# =========================

if __name__ == "__main__":
    print("INVEST MALAYSIA CLUB - CSV Seeder")
    print("Loading data...")
    all_data = get_topics_from_data()
    print(f"Loaded {len(all_data)} topics total.")
    
    if not all_data:
        print("No data to seed. Check your CSV files.")
        exit()

    # Prep categories
    cat_map = {}
    for c in CATEGORIES:
        cid = get_or_create_category(c["name"], c["color"], c["text_color"], c["description"])
        if cid: cat_map[c["name"]] = cid
        
    # Login users
    print("Logging in users...")
    user_sessions = {}
    for u in USERS:
        sess = login_user(u)
        if sess: user_sessions[u] = sess
        
    if not user_sessions:
        print("Error: Could not login any users. Check your USERS list and PASSWORD.")
        exit()
        
    active_users = list(user_sessions.keys())

    # Shuffle and seed
    random.shuffle(all_data)
    
    # User requested to seed EVERYTHING with a ~15s delay
    seeded = 0
    
    print(f"Starting seed for ALL {len(all_data)} topics...")
    for item in all_data:
        cat_id = cat_map.get(item["category"])
        if not cat_id: continue
        
        author = random.choice(active_users)
        topic_id = post_topic(user_sessions[author], item["title"], item["raw"], cat_id)
        
        if topic_id:
            seeded += 1
            print(f"[{seeded}] Seeded: {item['title'][:50]}...")
            
            # Post replies
            replies = item["replies"]
            if replies:
                num_replies = min(len(replies), random.randint(2, 5))
                for reply_text in random.sample(replies, num_replies):
                    replier = random.choice(active_users)
                    post_reply(user_sessions[replier], topic_id, reply_text)
                    time.sleep(random.uniform(2, 4))
            
            # Wait ~15s between topics as requested
            time.sleep(random.uniform(10, 15))
            
    print(f"Done! Seeded {seeded} topics.")
