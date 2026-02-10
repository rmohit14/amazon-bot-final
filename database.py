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
    """
    Checks if the deal has already been posted TODAY.
    Returns True if any record for this ASIN has today's date.
    """
    if not asin:
        return False
    
    # Get all records matching this ASIN
    results = db.search(Posted.asin == asin)
    
    if not results:
        return False
    
    today_str = str(date.today())
    
    # ITERATE through all results. If ANY record matches today, return True.
    # This fixes the bug where result[0] might be an old record.
    for res in results:
        if res.get("date") == today_str:
            return True
            
    return False

def record_posted_deal(asin: str, title: str, url: str):
    """
    Records the deal with today's date.
    Uses upsert to ensure we update the existing record or create a single new one.
    """
    if not asin:
        return

    today_str = str(date.today())
    
    # specific data packet
    deal_data = {
        "asin": asin,
        "title": title,
        "url": url,
        "date": today_str,
        "timestamp": datetime.now().isoformat()
    }
    
    # UPSERT: Update if exists, Insert if not. 
    # This prevents duplicate entries for the same ASIN in the DB.
    db.upsert(deal_data, Posted.asin == asin)
