import json
import time
import csv
import os
import re
import html
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

# CONFIG
COOKIE_FILE = "www.quora.com_13-05-2026.json"
POSTS_FILE = "quora_posts.csv"
COMMENTS_FILE = "quora_comments.csv"

TOPICS = [
    "https://www.quora.com/topic/Malaysia",
    "https://www.quora.com/topic/iGaming",
    "https://www.quora.com/topic/Online-Gambling",
    "https://www.quora.com/topic/Making-Money-Online-in-Malaysia",
]

def clean_text(text):
    if not text: return ""
    text = html.unescape(text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    ui_junk = ["(more)", "Upvote", "Share", "View Upvotes", "Answered by", "Add Comment", "Continue Reading"]
    for junk in ui_junk:
        text = text.replace(junk, "")
    return text.strip()

def load_cookies(driver, filepath):
    if not os.path.exists(filepath): return False
    try:
        with open(filepath, 'r') as f:
            cookies = json.load(f)
            if isinstance(cookies, dict) and 'cookies' in cookies: cookies = cookies['cookies']
        driver.get("https://www.quora.com/robots.txt")
        time.sleep(2)
        for cookie in cookies:
            c = {'name': cookie['name'], 'value': cookie['value'], 'path': cookie.get('path', '/'), 'domain': cookie.get('domain', '.quora.com')}
            try: driver.add_cookie(c)
            except: pass
        driver.get("https://www.quora.com")
        time.sleep(5)
        return True
    except: return False

def scrape_topic(driver, topic_url):
    print(f"Scraping topic: {topic_url}")
    driver.get(topic_url)
    time.sleep(8)
    
    for i in range(15):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        if i % 5 == 0: print(f"  Scroll {i+1}/15...")
    
    results = []
    # Identify containers that hold the post
    containers = driver.find_elements(By.CSS_SELECTOR, ".q-click-wrapper")
    print(f"  Found {len(containers)} content wrappers. Extracting with user-provided selectors...")
    
    unique_links = set()
    for container in containers:
        try:
            # 1. Title (span with background: none)
            title = ""
            try:
                # Prioritize user's observation: span with background: none
                title_el = container.find_element(By.CSS_SELECTOR, "span[style*='background: none']")
                title = title_el.text.strip()
            except:
                # Fallback
                try:
                    title_el = container.find_element(By.CSS_SELECTOR, ".qu-fontWeight--bold")
                    title = title_el.text.strip()
                except: continue
            
            if len(title) < 15: continue
            
            # 2. Link
            href = ""
            try:
                link_els = container.find_elements(By.CSS_SELECTOR, "a.puppeteer_test_link, a.qu-cursor--pointer")
                for l in link_els:
                    h = l.get_attribute("href")
                    if h and "quora.com/" in h and not any(x in h for x in ["/profile/", "/topic/", "/about", "/notifications"]):
                        href = h
                        break
                if not href: continue
            except: continue

            if "/answer/" in href: href = href.split("/answer/")[0]
            if href in unique_links: continue
            unique_links.add(href)
            
            # 3. Snippet (span with class q-box)
            snippet = ""
            try:
                snippet_el = container.find_element(By.CSS_SELECTOR, "span.q-box")
                snippet = clean_text(snippet_el.text)
                if snippet == title: snippet = ""
            except:
                try:
                    snippet_el = container.find_element(By.CSS_SELECTOR, ".q-text")
                    snippet = clean_text(snippet_el.text)
                except: pass
            
            results.append({
                "topic": topic_url.split("/")[-1],
                "question": title,
                "url": href,
                "snippet": snippet
            })
        except: continue
        
    print(f"  Extraction complete. Unique items found: {len(results)}")
    return results

def scrape_question_details(driver, url):
    try:
        driver.get(url)
        time.sleep(4)
        
        # Expand
        try:
            read_mores = driver.find_elements(By.CSS_SELECTOR, ".puppeteer_test_read_more_button")
            for rm in read_mores:
                try: driver.execute_script("arguments[0].click();", rm)
                except: pass
        except: pass

        # User's observation for comments/answers
        # span with style="font-weight: normal; font-style: normal; background: none;"
        answer_selectors = [
            "span[style*='font-weight: normal'][style*='font-style: normal'][style*='background: none']",
            "span.q-box",
            ".Answer .q-text"
        ]
        
        answers = []
        for selector in answer_selectors:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            for el in elements:
                try:
                    if not el.is_displayed(): continue
                    t = clean_text(el.text)
                    if len(t) > 60 and t not in answers:
                        # Skip UI junk
                        if any(x in t for x in ["Upvote", "Share", "View Upvotes", "Answered by"]): continue
                        answers.append(t)
                except: continue
            if len(answers) >= 8: break
        return answers
    except: return []

def main():
    options = Options()
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-notifications")
    driver = webdriver.Chrome(options=options)
    
    try:
        if load_cookies(driver, COOKIE_FILE):
            all_posts = []
            all_comments = []
            
            for topic_url in TOPICS:
                cards = scrape_topic(driver, topic_url)
                for card in cards:
                    post_id = card['url'].split('/')[-1] if card['url'] else f"q_{abs(hash(card['question']))}"
                    content = card['snippet']
                    
                    extra_answers = scrape_question_details(driver, card['url'])
                    
                    if not content and extra_answers:
                        content = extra_answers[0]
                        extra_answers = extra_answers[1:]
                    
                    if not content: continue
                    
                    all_posts.append({
                        "id": post_id, "title": card['question'], "selftext": content,
                        "author": "QuoraUser", "score": 0, "url": card['url'], "topic": card['topic']
                    })
                    for i, ans in enumerate(extra_answers):
                        all_comments.append({
                            "post_id": post_id, "comment_id": f"{post_id}_ans_{i}",
                            "parent_id": post_id, "author": "QuoraReplier", "body": ans, "score": 0
                        })
                    print(f"    [OK] {card['question'][:50]}... (+{len(extra_answers)} answers)")

            if all_posts:
                with open(POSTS_FILE, 'w', newline='', encoding='utf-8') as f:
                    csv.DictWriter(f, fieldnames=["id", "title", "selftext", "author", "score", "url", "topic"]).writeheader()
                    csv.DictWriter(f, fieldnames=["id", "title", "selftext", "author", "score", "url", "topic"]).writerows(all_posts)
            if all_comments:
                with open(COMMENTS_FILE, 'w', newline='', encoding='utf-8') as f:
                    csv.DictWriter(f, fieldnames=["post_id", "comment_id", "parent_id", "author", "body", "score"]).writeheader()
                    csv.DictWriter(f, fieldnames=["post_id", "comment_id", "parent_id", "author", "body", "score"]).writerows(all_comments)
                
            print(f"SUCCESS: Saved {len(all_posts)} posts.")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
