import os
import time
from tinydb import TinyDB, Query
from datetime import datetime, date, timedelta
import config  # Import config to get the correct filename

# Use the path defined in config
db = TinyDB(config.DB_FILENAME)
Posted = Query()

def initialize_database():
    """Ensure DB exists and clean up old records to keep file size small."""
    if not os.path.exists(config.DB_FILENAME):
        # Just triggering a write creates the file
        db.insert({"_init": True})
        db.remove(Query()._init == True)
    
    # Cleanup records older than 7 days to prevent git bloat
    try:
        cutoff_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        # Note: TinyDB query for date string comparison might differ based on format
        # Simple iteration for cleanup is safer for small DBs
        all_docs = db.all()
        ids_to_remove = [doc.doc_id for doc in all_docs if doc.get('date') and doc.get('date') < cutoff_date]
        if ids_to_remove:
            db.remove(doc_ids=ids_to_remove)
    except Exception as e:
        print(f"DB Cleanup warning: {e}")

def is_deal_already_posted(asin: str) -> bool:
    """Checks if deal was posted within the last 3 days (prevent repost spam)."""
    if not asin:
        return False
    
    results = db.search(Posted.asin == asin)
    if not results:
        return False
    
    # Check if posted recently (e.g., last 3 days)
    # If you strictly want 'Today only', use: if res.get("date") == str(date.today()):
    today = datetime.now()
    three_days_ago = today - timedelta(days=3)
    
    for res in results:
        posted_date_str = res.get("date")
        try:
            posted_date = datetime.strptime(posted_date_str, "%Y-%m-%d")
            if posted_date >= three_days_ago:
                return True
        except ValueError:
            continue
            
    return False

def record_posted_deal(asin: str, title: str, url: str):
    if not asin:
        return

    deal_data = {
        "asin": asin,
        "title": title,
        "url": url,
        "date": str(date.today()),
        "timestamp": datetime.now().isoformat()
    }
    
    db.upsert(deal_data, Posted.asin == asin)
