# utils/logger.py
import os
from datetime import datetime

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LOG_DIR = os.path.join(ROOT, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, "system.log")

def write_log(msg):
    """Write normal info logs"""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[INFO {ts}] {msg}"
    print(line)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

def write_error(msg):
    """Write error logs"""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[ERROR {ts}] {msg}"
    print(line)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass
