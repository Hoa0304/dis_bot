import requests
import random
import time
import json
import csv
import os


BASE_URL = os.environ.get("DISCOURSE_URL", "https://unretrenchable-retha-unobservant.ngrok-free.dev").rstrip("/")
API_KEY = os.environ.get("DISCOURSE_API_KEY", "339a46994a188577974dd49cf3c752e1e42d1db1749072992e19bc6b956d90a0")
API_USERNAME = os.environ.get("DISCOURSE_USERNAME", "user1")

FILE_PAIRS = [
    {
        "posts": "reddit_malaysia_posts.csv",
        "comments": "reddit_malaysia_comments.csv",
        "category": "Malaysia Business"
    },
    {
        "posts": "reddit_MalaysianPF_posts.csv",
        "comments": "reddit_MalaysianPF_comments.csv",
        "category": "Crypto & Investment"
    },
    {
        "posts": "reddit_Bolehland_posts.csv",
        "comments": "reddit_Bolehland_comments.csv",
        "category": "iGaming Discussion"
    },
    {
        "posts": "quora_posts.csv",
        "comments": "quora_comments.csv",
        "category": "Affiliate Marketing"
    }
]

USERS = ["klgamer88", "affiliateking", "cryptomalaysia", "saborneo", "penangtrader", "johordigital", "seaborneo", "mloopmy","cryptofox","mike88","asianbiz","trafficking"]


def load_csv(filename):
    if not filename or not os.path.exists(filename):
        return []
    data = []
    try:
        with open(filename, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                data.append(row)
    except Exception as e:
        print(f"Error loading {filename}: {e}")
    return data

def get_category_id(name):
    url = f"{BASE_URL}/categories.json"
    headers = {
        "Api-Key": API_KEY, 
        "Api-Username": API_USERNAME,
        "ngrok-skip-browser-warning": "true"
    }
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            cats = r.json().get("category_list", {}).get("categories", [])
            for c in cats:
                if c["name"].lower() == name.lower():
                    return c["id"]
    except Exception as e:
        print(f"Error getting category ID: {e}")
    return None

def create_topic(username, title, raw, category_id):
    url = f"{BASE_URL}/posts.json"
    headers = {
        "Api-Key": API_KEY, 
        "Api-Username": API_USERNAME,
        "ngrok-skip-browser-warning": "true"
    }
    payload = {
        "title": title,
        "raw": raw,
        "category": category_id,
        "api_username": username
    }
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=15)
        if r.status_code == 200:
            return r.json().get("topic_id")
        else:
            print(f"Failed to create topic: {r.status_code} - {r.text}")
    except Exception as e:
        print(f"Error creating topic: {e}")
    return None

def post_reply(username, topic_id, raw, reply_to_post_number=None):
    url = f"{BASE_URL}/posts.json"
    headers = {
        "Api-Key": API_KEY, 
        "Api-Username": API_USERNAME,
        "ngrok-skip-browser-warning": "true"
    }
    payload = {
        "topic_id": topic_id,
        "raw": raw,
        "api_username": username
    }
    if reply_to_post_number:
        payload["reply_to_post_number"] = reply_to_post_number
        
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=15)
        if r.status_code == 200:
            return r.json().get("post_number")
    except Exception as e:
        print(f"Error posting reply: {e}")
    return None

def process_pair(pair):
    posts = load_csv(pair["posts"])
    comments = load_csv(pair["comments"])
    cat_name = pair["category"]
    
    if not posts:
        print(f"No posts found for {cat_name}. Skipping.")
        return
        
    print(f"Processing {len(posts)} topics for category: {cat_name}")
    cat_id = get_category_id(cat_name)
    if not cat_id:
        print(f"Category '{cat_name}' not found. Using default.")
        cat_id = 1 # Default category
        
    # Group comments by post ID
    comments_by_post = {}
    for c in comments:
        pid = c.get("post_id")
        if pid not in comments_by_post:
            comments_by_post[pid] = []
        comments_by_post[pid].append(c)
        
    seeded = 0
    for p in posts:
        title = p.get("title", "").strip()
        raw = p.get("selftext", "").strip() or p.get("body", "").strip()
        
        if not title or len(title) < 15:
            if title: title = title + " - Discussion"
            else: continue
            
        if not raw:
            raw = f"Discussion about {title}"

        author = random.choice(USERS)
        print(f"Seeding topic: {title[:50]}... by {author}")
        
        topic_id = create_topic(author, title, raw, cat_id)
        if topic_id:
            seeded += 1
            # Process replies
            post_replies = comments_by_post.get(p.get("id"), [])
            post_num_map = {p.get("id"): 1}
            
            num_replies = min(len(post_replies), 5)
            for r_data in post_replies[:num_replies]:
                replier = random.choice(USERS)
                reply_body = r_data.get("body", "").strip()
                if not reply_body: continue
                
                reply_to = 1 
                post_num = post_reply(replier, topic_id, reply_body, reply_to)
                time.sleep(random.uniform(2, 5))
                
            wait = random.uniform(30, 60)
            print(f"Waiting {wait:.1f}s...")
            time.sleep(wait)
            
    print(f"Finished {cat_name}: Seeded {seeded} topics.")

def main():
    print(f"Starting Forum Bot. Target: {BASE_URL}")
    for pair in FILE_PAIRS:
        try:
            process_pair(pair)
        except Exception as e:
            print(f"Error processing {pair['category']}: {e}")
    print("All tasks completed.")

if __name__ == "__main__":
    main()
