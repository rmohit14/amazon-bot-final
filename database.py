# database.py
import sqlite3
from contextlib import closing
from config import DB_FILENAME
import os

def initialize_database():
    with closing(sqlite3.connect(DB_FILENAME)) as conn:
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS posted_deals (
                asin TEXT PRIMARY KEY,
                title TEXT,
                url TEXT,
                posted_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # We'll be updating existing records, so let's make sure the timestamp updates.
        # The previous logic will be replaced, but this is good practice.
        c.execute("""
            CREATE TRIGGER IF NOT EXISTS update_posted_at_on_replace
            AFTER UPDATE ON posted_deals
            FOR EACH ROW
            BEGIN
                UPDATE posted_deals SET posted_at = CURRENT_TIMESTAMP WHERE asin = OLD.asin;
            END;
        """)
        conn.commit()

def is_deal_already_posted(asin: str) -> bool:
    """Checks if a deal with the given ASIN has already been posted TODAY."""
    if not asin:
        return False
    with closing(sqlite3.connect(DB_FILENAME)) as conn:
        c = conn.cursor()
        # This query now checks if the ASIN was posted on the CURRENT_DATE.
        c.execute("""
            SELECT 1 
            FROM posted_deals 
            WHERE asin = ? AND DATE(posted_at) = DATE('now', 'localtime')
        """, (asin,))
        return c.fetchone() is not None

def record_posted_deal(asin: str, title: str, url: str) -> None:
    """Records or updates a posted deal. If it exists from a previous day, it updates the timestamp."""
    if not asin:
        return
    with closing(sqlite3.connect(DB_FILENAME)) as conn:
        c = conn.cursor()
        # 'INSERT OR REPLACE' will insert a new row or replace the existing one if the ASIN (PRIMARY KEY) matches.
        # This effectively updates the timestamp to the current time.
        c.execute("INSERT OR REPLACE INTO posted_deals (asin, title, url) VALUES (?, ?, ?)",
                  (asin, title, url))

        conn.commit()
