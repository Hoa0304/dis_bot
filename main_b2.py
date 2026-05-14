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
API_USERNAME = "user1" # Admin username

# =========================
# CSV FILES
# =========================
POSTS_FILE = "reddit_Bolehland_posts.csv"
COMMENTS_FILE = "" 
DEFAULT_CAT = "Malaysia Business"

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
    
    posts = load_csv(POSTS_FILE)
    comments = load_csv(COMMENTS_FILE)
    
    comments_by_post = {}
    for c in comments:
        pid = c.get("post_id")
        if pid not in comments_by_post:
            comments_by_post[pid] = []
        comments_by_post[pid].append({
            "id": c.get("comment_id"),
            "parent_id": c.get("parent_id"),
            "body": c.get("body", "")
        })
        
    for p in posts:
        title = p.get("title", "").strip()
        content = p.get("selftext", "").strip()
        
        if not title: continue
        if not content and not p.get("url"): continue
        
        # Discourse requires titles to be at least 15 characters by default
        if len(title) < 15:
            title = title + " - Discussion" # Padding to reach min length
            if len(title) < 15:
                title = title.ljust(15, '.')
        
        raw = content if content else f"Link: {p.get('url')}"
        
        all_topics.append({
            "id": p.get("id"),
            "title": title,
            "raw": raw,
            "category": DEFAULT_CAT,
            "replies": comments_by_post.get(p.get("id"), [])
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

def get_or_create_category(name, color, text_color, description):
    print(f"Checking category: {name}...")
    try:
        r = requests.get(f"{BASE_URL}/categories.json", headers=get_headers(), timeout=10)
        if r.status_code == 200:
            cats = r.json()["category_list"]["categories"]
            for c in cats:
                if c["name"].lower() == name.lower():
                    print(f"  Found existing category: {name} (ID: {c['id']})")
                    return c["id"]
        
        print(f"  Category not found, creating: {name}...")
        data = {"name": name, "color": color, "text_color": text_color, "description": description}
        r = requests.post(f"{BASE_URL}/categories.json", headers=get_headers(), json=data, timeout=10)
        if r.status_code == 200:
            cid = r.json()["category"]["id"]
            print(f"  Created category: {name} (ID: {cid})")
            return cid
        else:
            print(f"  Failed to create category: {r.status_code} - {r.text[:100]}")
    except Exception as e:
        print(f"  Error in category check: {e}")
    return None

def post_topic(username, title, raw, category_id):
    data = {"title": title, "raw": raw, "category": category_id}
    try:
        r = requests.post(
            f"{BASE_URL}/posts.json",
            headers=get_headers(username),
            json=data,
            timeout=15
        )
        if r.status_code == 200:
            return r.json().get("topic_id")
        else:
            print(f"      Error posting topic as {username}: {r.status_code} - {r.text[:100]}")
    except Exception as e:
        print(f"      Exception posting topic: {e}")
    return None

def post_reply(username, topic_id, raw, reply_to_post_number=None):
    data = {"topic_id": topic_id, "raw": raw}
    if reply_to_post_number:
        data["reply_to_post_number"] = reply_to_post_number
        
    try:
        r = requests.post(
            f"{BASE_URL}/posts.json",
            headers=get_headers(username),
            json=data,
            timeout=15
        )
        if r.status_code == 200:
            return r.json().get("post_number")
    except:
        pass
    return None

# =========================
# MAIN
# =========================

if __name__ == "__main__":
    print("INVEST MALAYSIA CLUB - Reddit Bolehland Seeder (main_b2)")
    print("Loading data...")
    all_data = get_topics_from_data()
    print(f"Loaded {len(all_data)} topics.")
    
    if not all_data:
        print("No data to seed. Check your CSV files.")
        exit()

    print("Initializing categories...")
    cat_map = {}
    for c in CATEGORIES:
        cid = get_or_create_category(c["name"], c["color"], c["text_color"], c["description"])
        if cid: 
            cat_map[c["name"]] = cid
        
    if not cat_map:
        print("CRITICAL: Could not find or create any categories. Check your BASE_URL and API_KEY.")
        exit()
        
    random.shuffle(all_data)
    
    seeded = 0
    for item in all_data:
        cat_id = cat_map.get(item["category"])
        if not cat_id:
            print(f"  Skipping: Category '{item['category']}' not initialized.")
            continue
        
        author = random.choice(USERS)
        topic_id = post_topic(author, item["title"], item["raw"], cat_id)
        
        if topic_id:
            seeded += 1
            print(f"[{seeded}] Seeded: {item['title'][:50]}...")
            
            # Map IDs to Discourse post numbers
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
                        
                    time.sleep(random.uniform(1, 3))
            
            time.sleep(random.uniform(5, 10))
        else:
            # If even the admin/first user fails, there's a big problem
            print("  Failed to seed current topic. Moving to next...")
            
    print(f"Done! Seeded {seeded} topics.")
