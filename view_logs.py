#!/usr/bin/env python3
"""
Log Viewer Script - View AI activity logs from the ecommerce scraper.

Usage:
    python view_logs.py                    # List all sessions
    python view_logs.py --session SESSION_ID  # View specific session
    python view_logs.py --session SESSION_ID --thoughts  # View AI thoughts
    python view_logs.py --session SESSION_ID --tools     # View tool calls
    python view_logs.py --session SESSION_ID --tasks     # View task events
"""

import sys
import os

# Add the current directory to Python path so we can import ecommerce_scraper
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ecommerce_scraper.logging.log_viewer import main

if __name__ == "__main__":
    main()
