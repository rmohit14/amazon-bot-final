# database.py (TinyDB + GitHub persistence)
import os
from tinydb import TinyDB, Query
from datetime import datetime, date

DB_PATH = os.getenv("DB_FILENAME", "data.json")
db = TinyDB(DB_PATH)
Posted = Query()

def initialize_database():
    # TinyDB auto-creates data.json if it doesn't exist
    pass

def is_deal_already_posted(asin: str) -> bool:
    if not asin:
        return False
    result = db.search(Posted.asin == asin)
    if not result:
        return False
    # Only skip repost if it's from today
    return result[0].get("date") == str(date.today())

def record_posted_deal(asin: str, title: str, url: str):
    if not asin:
        return
    existing = db.search(Posted.asin == asin)
    if existing:
        db.update({"title": title, "url": url, "date": str(date.today())}, Posted.asin == asin)
    else:
        db.insert({
            "asin": asin,
            "title": title,
            "url": url,
            "date": str(date.today()),
            "timestamp": datetime.now().isoformat()
        })
