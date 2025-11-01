# run_once.py
import logging
from main import run_all_cycles, database

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    database.initialize_database()
    run_all_cycles()
