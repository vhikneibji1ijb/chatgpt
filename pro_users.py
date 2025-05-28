import json
import time

DB_FILE = "pro_users.json"

def load_db():
    try:
        with open(DB_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_db(db):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

def is_pro(user_id):
    db = load_db()
    info = db.get(str(user_id))
    if info is True:
        return True
    if isinstance(info, dict) and info.get("until"):
        return info["until"] > time.time()
    return False

def set_pro(user_id, days=30):
    db = load_db()
    db[str(user_id)] = {"until": time.time() + days*24*60*60}
    save_db(db)

def set_free(user_id):
    db = load_db()
    db.pop(str(user_id), None)
    save_db(db)
