"""
Reddit r/malaysia Crawler
Crawls posts from multiple sort tabs (hot, top, new, rising) and saves to CSV.
Uses Reddit's public JSON API - no auth needed.
"""

import requests
import csv
import time
import json
import os
import html
import re

SUBREDDITS = ["malaysia", "MalaysianPF", "Bolehland"]
OUTPUT_FILE_TEMPLATE = "/home/hoa/forum-bot/reddit_{subreddit}_posts.csv"
COMMENTS_FILE_TEMPLATE = "/home/hoa/forum-bot/reddit_{subreddit}_comments.csv"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 InvestMalaysiaBot/1.0"
}

# Sort types and time filters to maximize unique posts
ENDPOINTS = [
    {"sort": "hot", "params": {}},
    {"sort": "new", "params": {}},
    {"sort": "rising", "params": {}},
    {"sort": "top", "params": {"t": "all"}},
    {"sort": "top", "params": {"t": "year"}},
    {"sort": "top", "params": {"t": "month"}},
    {"sort": "top", "params": {"t": "week"}},
    {"sort": "controversial", "params": {"t": "all"}},
    {"sort": "controversial", "params": {"t": "year"}},
    {"sort": "controversial", "params": {"t": "month"}},
]

def clean_text(text):
    """Clean HTML entities and excessive whitespace"""
    if not text:
        return ""
    text = html.unescape(text)
    text = re.sub(r'&amp;', '&', text)
    text = re.sub(r'&lt;', '<', text)
    text = re.sub(r'&gt;', '>', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def fetch_posts(subreddit, sort, params, after=None, limit=100):
    """Fetch a page of posts from Reddit JSON API"""
    url = f"https://www.reddit.com/r/{subreddit}/{sort}.json"
    p = {"limit": limit, "raw_json": 1}
    p.update(params)
    if after:
        p["after"] = after

    try:
        r = requests.get(url, headers=HEADERS, params=p, timeout=15)
        if r.status_code == 429:
            print("  Rate limited, waiting 60s...")
            time.sleep(60)
            return fetch_posts(sort, params, after, limit)
        if r.status_code != 200:
            print(f"  HTTP {r.status_code}")
            return [], None
        data = r.json()
        children = data["data"]["children"]
        after_token = data["data"].get("after")
        return children, after_token
    except Exception as e:
        print(f"  Error: {e}")
        return [], None


def fetch_comments(subreddit, post_id, limit=100):
    """Fetch all comments including nested replies using recursion"""
    url = f"https://www.reddit.com/r/{subreddit}/comments/{post_id}.json"
    try:
        r = requests.get(url, headers=HEADERS, params={"limit": limit, "raw_json": 1}, timeout=15)
        if r.status_code == 429:
            print("    Rate limited on comments, waiting 60s...")
            time.sleep(60)
            return fetch_comments(subreddit, post_id, limit)
        if r.status_code != 200:
            return []
        
        data = r.json()
        if len(data) < 2:
            return []
            
        return extract_replies_recursive(data[1]["data"], post_id)
    except Exception as e:
        print(f"    Comment error: {e}")
        return []

def extract_replies_recursive(data, post_id, parent_id=None):
    """Recursively extract comments and their replies"""
    comments = []
    if not data or "children" not in data:
        return comments
        
    for child in data["children"]:
        if child["kind"] != "t1":
            continue
            
        c = child["data"]
        cid = c.get("id")
        if not cid: continue
        
        comments.append({
            "post_id": post_id,
            "comment_id": cid,
            "parent_id": parent_id if parent_id else post_id,
            "author": c.get("author", "[deleted]"),
            "body": clean_text(c.get("body", "")),
            "score": c.get("score", 0),
            "created_utc": c.get("created_utc", 0),
        })
        
        # Check for nested replies
        replies = c.get("replies")
        if replies and isinstance(replies, dict) and "data" in replies:
            comments.extend(extract_replies_recursive(replies["data"], post_id, cid))
            
    return comments


def crawl_all(subreddit):
    """Main crawl loop - get as many unique posts as possible"""
    all_posts = {}  # keyed by post id to deduplicate
    all_comments = []

    for endpoint in ENDPOINTS:
        sort = endpoint["sort"]
        params = endpoint["params"]
        label = f"{sort}"
        if "t" in params:
            label += f"/{params['t']}"

        print(f"\n{'='*50}")
        print(f"Crawling: r/{subreddit}/{label}")
        print(f"{'='*50}")

        after = None
        page = 0
        max_pages = 10  # 10 pages x 100 = up to 1000 per endpoint

        while page < max_pages:
            page += 1
            posts, after = fetch_posts(subreddit, sort, params, after)

            if not posts:
                print(f"  Page {page}: No more posts")
                break

            new_count = 0
            for post in posts:
                d = post["data"]
                pid = d["id"]
                if pid in all_posts:
                    continue  # skip duplicate
                new_count += 1

                flair = ""
                if d.get("link_flair_text"):
                    flair = d["link_flair_text"]

                all_posts[pid] = {
                    "id": pid,
                    "title": clean_text(d.get("title", "")),
                    "selftext": clean_text(d.get("selftext", "")),
                    "author": d.get("author", "[deleted]"),
                    "score": d.get("score", 0),
                    "upvote_ratio": d.get("upvote_ratio", 0),
                    "num_comments": d.get("num_comments", 0),
                    "created_utc": d.get("created_utc", 0),
                    "url": d.get("url", ""),
                    "permalink": f"https://www.reddit.com{d.get('permalink', '')}",
                    "flair": clean_text(flair),
                    "is_self": d.get("is_self", False),
                    "domain": d.get("domain", ""),
                    "over_18": d.get("over_18", False),
                    "sort_source": label,
                }

            print(f"  Page {page}: {len(posts)} fetched, {new_count} new (total unique: {len(all_posts)})")

            if not after:
                print("  No more pages")
                break

            time.sleep(2)  # be nice to Reddit

    # Now fetch comments for top posts (by score)
    print(f"\n{'='*50}")
    print(f"Fetching comments for top posts...")
    print(f"{'='*50}")

    sorted_posts = sorted(all_posts.values(), key=lambda x: x["score"], reverse=True)
    # Fetch comments for top 100 self-text posts
    comment_targets = [p for p in sorted_posts if p["is_self"] and p["selftext"]][:100]
    # Also include top 50 link posts
    comment_targets += [p for p in sorted_posts if not p["is_self"]][:50]

    for i, post in enumerate(comment_targets):
        print(f"  [{i+1}/{len(comment_targets)}] {post['title'][:60]}...")
        comments = fetch_comments(subreddit, post["id"])
        all_comments.extend(comments)
        time.sleep(1.5)

    return all_posts, all_comments


def save_to_csv(subreddit, posts, comments):
    """Save posts and comments to CSV files"""
    # Save posts
    post_list = sorted(posts.values(), key=lambda x: x["score"], reverse=True)

    output_file = OUTPUT_FILE_TEMPLATE.format(subreddit=subreddit)
    comments_file = COMMENTS_FILE_TEMPLATE.format(subreddit=subreddit)

    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "id", "title", "selftext", "author", "score", "upvote_ratio",
            "num_comments", "created_utc", "url", "permalink", "flair",
            "is_self", "domain", "over_18", "sort_source"
        ])
        writer.writeheader()
        writer.writerows(post_list)

    print(f"\nSaved {len(post_list)} posts to {output_file}")

    # Save comments
    with open(comments_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "post_id", "comment_id", "parent_id", "author", "body", "score", "created_utc"
        ])
        writer.writeheader()
        writer.writerows(comments)

    print(f"Saved {len(comments)} comments to {comments_file}")


if __name__ == "__main__":
    print("Reddit Malaysia Multi-Subreddit Crawler")
    print("=" * 50)
    for sub in SUBREDDITS:
        posts, comments = crawl_all(sub)
        save_to_csv(sub, posts, comments)
    print("\nDone all subreddits!")
