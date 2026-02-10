#!/usr/bin/env python3
"""
Run the bot once without scheduling
Perfect for GitHub Actions or cron jobs
"""

import logging
import sys
import os
from datetime import datetime

# Import from main
import config
import database
from main import (
    run_all_cycles,
    send_value_add_content,
    deal_counter
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot.log")
    ]
)

def main():
    """Run bot once - perfect for GitHub Actions"""
    
    logging.info("="*60)
    logging.info("🚀 Starting Amazon Deals Bot (Single Run Mode)")
    logging.info(f"⏰ Run time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logging.info("="*60)
    
    # Verify environment variables
    if not os.getenv("TELEGRAM_BOT_TOKEN"):
        logging.error("❌ TELEGRAM_BOT_TOKEN not found in environment!")
        logging.error("Set it in GitHub Secrets: Settings → Secrets → Actions")
        sys.exit(1)
    
    # Initialize database
    try:
        database.initialize_database()
        logging.info("✅ Database initialized")
    except Exception as e:
        logging.error(f"❌ Database initialization failed: {e}")
        sys.exit(1)
    
    # Run the bot
    try:
        logging.info("🔍 Starting deal search...")
        run_all_cycles()
        logging.info("✅ Deal search completed successfully!")
        
    except Exception as e:
        logging.critical(f"❌ Bot execution failed: {e}", exc_info=True)
        sys.exit(1)
    
    logging.info("="*60)
    logging.info("🎉 Bot run completed successfully!")
    logging.info("="*60)

if __name__ == "__main__":
    main()
