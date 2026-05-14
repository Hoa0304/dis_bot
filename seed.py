import requests
import random
import time

BASE_URL = "http://localhost"

API_KEY = "339a46994a188577974dd49cf3c752e1e42d1db1749072992e19bc6b956d90a0"
API_USERNAME = "hoa"

PASSWORD = "Test123456!"

admin_headers = {
    "Api-Key": API_KEY,
    "Api-Username": API_USERNAME,
    "Content-Type": "application/json"
}

users = [
    "mike88",
    "cryptofox",
    "asianbiz",
    "seohero",
    "trafficking"
]

topics = [
    {
        "title": "Best areas to start online business in Malaysia?",
        "raw": "I'm researching digital business opportunities in Malaysia."
    },
    {
        "title": "How active is the iGaming scene in KL?",
        "raw": "Seeing a lot of affiliate discussions lately."
    }
]

comments = [
    "Interesting point about the Malaysia market.",
    "Affiliate industry is growing fast there.",
    "A lot of opportunities in Southeast Asia now.",
    "SEO still works well for affiliate traffic."
]

# =========================
# LOGIN
# =========================
def login_user(username):

    session = requests.Session()

    csrf = session.get(
        f"{BASE_URL}/session/csrf.json"
    ).json()["csrf"]

    headers = {
        "X-CSRF-Token": csrf,
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    data = {
        "login": username,
        "password": PASSWORD
    }

    r = session.post(
        f"{BASE_URL}/session.json",
        headers=headers,
        json=data
    )

    print(f"LOGIN {username}: {r.status_code}")

    if r.status_code == 200:

        csrf = session.get(
            f"{BASE_URL}/session/csrf.json"
        ).json()["csrf"]

        return {
            "session": session,
            "csrf": csrf
        }

    return None

# =========================
# CREATE TOPIC
# =========================
def create_topic(user_data, username):

    topic = random.choice(topics)

    unique_id = random.randint(1000,9999)

    data = {
        "title": f"{topic['title']} #{unique_id}",
        "raw": topic["raw"],
        "category": 12
    }

    r = user_data["session"].post(
        f"{BASE_URL}/posts.json",
        headers={
            "X-CSRF-Token": user_data["csrf"],
            "Content-Type": "application/json"
        },
        json=data
    )

    print(f"TOPIC {username}: {r.status_code}")

    if r.status_code != 200:
        print(r.text)
        return None

    return r.json()["topic_id"]

# =========================
# CREATE REPLY
# =========================
def create_reply(user_data, topic_id):

    message = random.choice(comments)
    message += f" #{random.randint(1000,9999)}"

    data = {
        "topic_id": topic_id,
        "raw": message
    }

    r = user_data["session"].post(
        f"{BASE_URL}/posts.json",
        headers={
            "X-CSRF-Token": user_data["csrf"],
            "Content-Type": "application/json"
        },
        json=data
    )

    print("REPLY:", r.status_code, message)

    if r.status_code != 200:
        print(r.text)

# =========================
# MAIN
# =========================

# login all users ONCE
logged_users = {}

for username in users:

    data = login_user(username)

    if data:
        logged_users[username] = data

    time.sleep(2)

print("\n==== ALL USERS LOGGED IN ====\n")

# create topics
for username in users:

    user_data = logged_users[username]

    topic_id = create_topic(
        user_data,
        username
    )

    if topic_id:

        # replies
        for _ in range(random.randint(2,5)):

            reply_username = random.choice(users)

            create_reply(
                logged_users[reply_username],
                topic_id
            )

            time.sleep(random.randint(3,6))

    time.sleep(random.randint(5,10))