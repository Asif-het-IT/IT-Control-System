import os
import sys
import shutil
import hashlib
import csv
import logging
from datetime import datetime

# ==================================================
# GUI SAFE PATH
# ==================================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JOBS_DIR = os.path.join(BASE_DIR, "jobs")
if JOBS_DIR not in sys.path:
    sys.path.insert(0, JOBS_DIR)

try:
    from email_job import send_report_email
except Exception:
    send_report_email = None

# ==================================================
# SETTINGS
# ==================================================
SOURCE_ROOT = r"E:\SSS300 - Backup - All Outlets"
DEST_ROOT = r"D:\01 - SSS 300 LAUNDRY - Exports To Excel\All Branches"
SETTINGS_FOLDER = os.path.join(DEST_ROOT, "Done", "Settings")

os.makedirs(SETTINGS_FOLDER, exist_ok=True)

INDEX_FILE = os.path.join(SETTINGS_FOLDER, "copied_index.csv")
LOG_FILE = os.path.join(SETTINGS_FOLDER, "sync_log.txt")
ERROR_FILE = os.path.join(SETTINGS_FOLDER, "errors.log")

FILE_PATTERN = ".xlsx"

BRANCHES = [
    {"Key": "BR1-Qusais-SB", "Sub": r"BR1-Qusais-SB\Cloud\1 - SSS300 - New SQL\ExportsToExcel"},
    {"Key": "BR2-DMP", "Sub": r"BR2-DMP\Cloud\SSS300 - SQL  - DMP\ExportsToExcel"},
    {"Key": "BR3-CB", "Sub": r"BR3-CB\Cloud\ABRStarTouch\ExportsToExcel"},
    {"Key": "BR4-JVC", "Sub": r"BR4-JVC\Cloud\SSS300 Laundry - JVC - SQL\ExportsToExcel"},
    {"Key": "BR5-DSO", "Sub": r"BR5-DSO\Cloud\SSS300 - DSO - SQL\ExportsToExcel"},
    {"Key": "BR6-BH", "Sub": r"BR6-BH\Cloud\SSS300 - BH - SQL\ExportsToExcel"},
]

# ==================================================
# LOGGING
# ==================================================
logging.basicConfig(filename=LOG_FILE, level=logging.INFO)

def log(msg):
    print(msg)
    logging.info(msg)

def log_error(msg):
    print("ERROR:", msg)
    with open(ERROR_FILE, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now()}\t{msg}\n")

# ==================================================
# HASH
# ==================================================
def get_file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

# ==================================================
# LOAD INDEX
# ==================================================
index_by_hash = {}
index_rows = []

if os.path.exists(INDEX_FILE):
    with open(INDEX_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            index_rows.append(r)
            index_by_hash[r["Hash"]] = r

# ==================================================
# SAFE COPY (FIXED)
# ==================================================
def safe_copy_file(src, dest_dir, index_by_hash):
    file_hash = get_file_sha256(src)

    # 🔒 HARD DEDUP – already copied
    if file_hash in index_by_hash:
        log(f"SKIP (already indexed): {src}")
        return None

    os.makedirs(dest_dir, exist_ok=True)
    fname = os.path.basename(src)
    dest_path = os.path.join(dest_dir, fname)

    # name conflict but content different
    if os.path.exists(dest_path):
        existing_hash = get_file_sha256(dest_path)
        if existing_hash == file_hash:
            log(f"SKIP (same file exists): {src}")
            return None
        else:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            base, ext = os.path.splitext(fname)
            dest_path = os.path.join(dest_dir, f"{base}__{ts}{ext}")

    shutil.copy2(src, dest_path)
    log(f"COPIED: {src} -> {dest_path}")

    return {
        "Hash": file_hash,
        "FileName": os.path.basename(dest_path),
        "SourcePath": src,
        "DestPath": dest_path,
        "DateCopied": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

# ==================================================
# HTML EMAIL
# ==================================================
def build_html_report(rows):
    if not rows:
        return "<p>No new Excel files copied.</p>"

    tr = ""
    for r in rows:
        tr += f"""
        <tr>
            <td>{r['FileName']}</td>
            <td>{r['SourcePath']}</td>
            <td>{r['DestPath']}</td>
            <td>{r['DateCopied']}</td>
        </tr>
        """

    return f"""
    <h3>Laundry Excel Copy Report</h3>
    <table border="1" cellpadding="6" cellspacing="0">
        <tr>
            <th>File</th><th>Source</th><th>Destination</th><th>Date</th>
        </tr>
        {tr}
    </table>
    """

# ==================================================
# MAIN JOB
# ==================================================
def run_laundry_job():
    log("===== COPY JOB START =====")
    new_entries = []

    for b in BRANCHES:
        src_base = os.path.join(SOURCE_ROOT, b["Sub"])
        if not os.path.exists(src_base):
            continue

        for root, _, files in os.walk(src_base):
            for f in files:
                if not f.lower().endswith(FILE_PATTERN):
                    continue

                src = os.path.join(root, f)
                entry = safe_copy_file(src, DEST_ROOT, index_by_hash)

                if entry:
                    new_entries.append(entry)
                    index_by_hash[entry["Hash"]] = entry

    if new_entries:
        index_rows.extend(new_entries)
        with open(INDEX_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["Hash", "FileName", "SourcePath", "DestPath", "DateCopied"]
            )
            writer.writeheader()
            writer.writerows(index_rows)

    if send_report_email:
        send_report_email(
            subject=f"Laundry Excel Copy Report - {datetime.now().strftime('%d-%b-%Y')}",
            body=build_html_report(new_entries),
            html=True
        )

    log(f"===== COPY JOB END | New files: {len(new_entries)} =====")
    return len(new_entries)

# ==================================================
# GUI SAFE
# ==================================================
if __name__ == "__main__":
    print("GUI-safe: call run_laundry_job() from GUI only")
