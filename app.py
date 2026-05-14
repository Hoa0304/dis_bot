import os
import threading
import time
import subprocess
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "Forum Bot is running!"

def run_bot_scheduler():
    while True:
        print("--- Starting Seeding Cycle ---")
        try:
            subprocess.run(["python", "main.py"], check=True)
            print("--- Seeding Cycle Finished Successfully ---")
        except Exception as e:
            print(f"Error during seeding: {e}")
            
        print("Sleeping for 1 hour...")
        time.sleep(3600)

if __name__ == "__main__":
    threading.Thread(target=run_bot_scheduler, daemon=True).start()
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
