from tinydb import TinyDB, Query
from datetime import date

db = TinyDB("data.json")
Posted = Query()

def initialize_database():
    pass

def is_deal_already_posted(asin: str):
    today_str = str(date.today())
    result = db.search(Posted.asin == asin)
    return any(res.get("date") == today_str for res in result)

def record_posted_deal(asin: str, title: str, url: str):
    today_str = str(date.today())
    deal_data = {"asin": asin, "title": title, "url": url, "date": today_str}
    db.upsert(deal_data, Posted.asin == asin)
