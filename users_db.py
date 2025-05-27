import json
import time

DB_FILE = "pro_users.json"
TRIAL_DAYS = 3

def load_db():
    try:
        with open(DB_FILE) as f:
            return json.load(f)
    except:
        return {}

def save_db(db):
    with open(DB_FILE, "w") as f:
        json.dump(db, f)

def is_pro(user_id):
    db = load_db()
    if str(user_id) in db:
        return db[str(user_id)]["until"] > time.time()
    return False

def add_pro(user_id, days):
    db = load_db()
    until = int(time.time()) + days*24*60*60
    db[str(user_id)] = {"until": until}
    save_db(db)

def pro_until(user_id):
    db = load_db()
    if str(user_id) in db:
        return db[str(user_id)]["until"]
    return None

def start_trial(user_id):
    add_pro(user_id, TRIAL_DAYS)
