import os
import re
import json
import logging
from datetime import datetime
from html import escape
from email_job import send_report_email  # Ensure this exists in your jobs folder

# ================= CONFIG =================
# Base Paths
AFRICA_BASE = r"\\het-nas\Tally-Africa\T-Current\Africa"
TALLY_BASE = r"\\het-nas\Tally-Africa"
LAUNDRY_BASE = r"\\het-nas\G-SSS300"

# Output / Logs
LOG_BASE = r"D:\01 - SSS 300 LAUNDRY - Exports To Excel\logs"
os.makedirs(LOG_BASE, exist_ok=True)
TIMESTAMP = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
TXT_LOG_FILE = os.path.join(LOG_BASE, f"NAS_Report_{TIMESTAMP}.txt")
JSON_STATE_FILE = os.path.join(LOG_BASE, "nas_state_test.json")

# Conflicted file regex
CONFLICT_PATTERN = re.compile(
    r"^(?P<name>.+?)\(Conflicted copy (?P<date>\d{4}-\d{2}-\d{2}) by .+?\)\.900$",
    re.IGNORECASE
)

# Tally mapping
TALLY_MAP = {
    "T-Kano": "Ambariyya - Kano",
    "T-BukShop": "Noor - BukShop",
    "T-Abuja": "Fazal - Abuja",
    "T-Lagos": "Dua - Lagos"
}

# Laundry mapping
LAUNDRY_MAP = {
    "BR1-Qusais-SB": {
        "backup": r"BR1-Qusais-SB\Cloud\1 - SSS300 - New SQL\Backup",
        "excel": r"BR1-Qusais-SB\Cloud\1 - SSS300 - New SQL\ExportsToExcel"
    },
    "BR2-DMP": {
        "backup": r"BR2-DMP\Cloud\SSS300 - SQL  - DMP\Backup",
        "excel": r"BR2-DMP\Cloud\SSS300 - SQL  - DMP\ExportsToExcel"
    },
    "BR3-CB": {
        "backup": r"BR3-CB\Cloud\ABRStarTouch\Backup",
        "excel": r"BR3-CB\Cloud\ABRStarTouch\ExportsToExcel"
    },
    "BR4-JVC": {
        "backup": r"BR4-JVC\Cloud\SSS300 Laundry - JVC - SQL\Backup",
        "excel": r"BR4-JVC\Cloud\SSS300 Laundry - JVC - SQL\ExportsToExcel"
    },
    "BR5-DSO": {
        "backup": r"BR5-DSO\Cloud\SSS300 - DSO - SQL\Backup",
        "excel": r"BR5-DSO\Cloud\SSS300 - DSO - SQL\ExportsToExcel"
    },
    "BR6-BH": {
        "backup": r"BR6-BH\Cloud\SSS300 - BH - SQL\Backup",
        "excel": r"BR6-BH\Cloud\SSS300 - BH - SQL\ExportsToExcel"
    }
}

# Logging
logging.basicConfig(
    filename=TXT_LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s\t%(levelname)s\t%(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

def log(msg):
    print(msg)
    logging.info(msg)

def log_error(msg):
    print(f"ERROR: {msg}")
    logging.error(msg)

# ==================== UTILITIES ====================
def get_latest_file_date(folder_path, prefix=None, suffix=None):
    if not os.path.exists(folder_path):
        return None
    files = os.listdir(folder_path)
    if prefix:
        files = [f for f in files if f.startswith(prefix)]
    if suffix:
        files = [f for f in files if f.endswith(suffix)]
    if not files:
        return None
    latest_file = max(files, key=lambda f: os.path.getmtime(os.path.join(folder_path, f)))
    mod_time = os.path.getmtime(os.path.join(folder_path, latest_file))
    return datetime.fromtimestamp(mod_time).strftime("%d-%b-%Y"), latest_file

def extract_conflicted_info(filename):
    match = CONFLICT_PATTERN.match(filename)
    if not match:
        return None
    raw_date = match.group("date")
    try:
        nice_date = datetime.strptime(raw_date, "%Y-%m-%d").strftime("%d-%b-%Y")
    except ValueError:
        nice_date = raw_date
    return match.group("name"), nice_date

# ==================== CHECK FUNCTIONS ====================
def check_africa():
    africa_folders = [f for f in os.listdir(AFRICA_BASE) if os.path.isdir(os.path.join(AFRICA_BASE, f))]
    result = {}
    for folder in africa_folders:
        folder_path = os.path.join(AFRICA_BASE, folder)
        date, _ = get_latest_file_date(folder_path, prefix="TranMgr", suffix=".900") or (None, None)
        status = "OK" if date else "Not Found"
        result[folder] = {"date": date, "status": status}
        log(f"Africa {folder}: {status}, latest={date}")
    return result

def check_tally():
    result = {}
    for key, name in TALLY_MAP.items():
        path = os.path.join(TALLY_BASE, key)
        date, latest_file = get_latest_file_date(path)
        status = "OK" if date else "Not Found"
        result[name] = {"date": date, "status": status}
        log(f"Tally {name}: {status}, latest={date}")
    return result

def check_laundry():
    result = {}
    for branch, paths in LAUNDRY_MAP.items():
        backup_path = os.path.join(LAUNDRY_BASE, paths["backup"])
        excel_path = os.path.join(LAUNDRY_BASE, paths["excel"])
        backup_date, _ = get_latest_file_date(backup_path)
        excel_date, _ = get_latest_file_date(excel_path)
        result[branch] = {"backup_date": backup_date or "—", "excel_date": excel_date or "—"}
        log(f"Laundry {branch}: Backup={backup_date}, Excel={excel_date}")
    return result

def check_conflicted():
    rows = []
    total_find = 0
    for root, dirs, files in os.walk(os.path.join(TALLY_BASE, "T-Current")):
        rel_path = os.path.relpath(root, TALLY_BASE).replace("\\","/")
        folder_name = os.path.basename(root)
        found = False
        for f in files:
            info = extract_conflicted_info(f)
            if info:
                fname, fdate = info
                rows.append({"folder": folder_name, "file": fname, "path": rel_path, "date": fdate, "status":"Find"})
                found = True
                total_find += 1
        if not found:
            rows.append({"folder": folder_name, "file":"—","path":rel_path,"date":"—","status":"Not Found"})
    return rows, total_find

# ==================== HTML ====================
def build_conflicted_html(rows, total_find):
    html = []
    html.append(f"<h4>Conflicted Files (T-Current) | Total Find: {total_find}</h4>")
    html.append("<table border=1 cellpadding=6 style='border-collapse:collapse'><tr><th>Folder</th><th>File</th><th>Path</th><th>Date</th><th>Status</th></tr>")
    for r in rows:
        css = "background:#ffecec;" if r["status"]=="Find" else "background:#f9f9f9;color:#777;"
        html.append(f"<tr style='{css}'><td>{r['folder']}</td><td>{r['file']}</td><td>{r['path']}</td><td>{r['date']}</td><td>{r['status']}</td></tr>")
    html.append("</table><br>")
    return "\n".join(html)

def build_html_report(data):
    today_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    html = []
    html.append(f"<h3>(het) Automation App</h3><h3>Tally Nas Cloud Report</h3><h3>NAS & Tally Daily Report</h3>")
    html.append(f"<p>Date: {today_str}</p>")

    # Africa
    html.append("<h4>Africa TranMgr.900</h4><table border=1 cellpadding=6 style='border-collapse:collapse'><tr><th>Branch</th><th>Date</th><th>Status</th></tr>")
    for k,v in data["africa"].items():
        html.append(f"<tr><td>{k}</td><td>{v['date'] or '—'}</td><td>{v['status']}</td></tr>")
    html.append("</table><br>")

    # Tally
    html.append("<h4>Tally Status</h4><table border=1 cellpadding=6 style='border-collapse:collapse'><tr><th>Branch</th><th>Date</th><th>Status</th></tr>")
    for k,v in data["tally"].items():
        html.append(f"<tr><td>{k}</td><td>{v['date'] or '—'}</td><td>{v['status']}</td></tr>")
    html.append("</table><br>")

    # Laundry
    html.append("<h4>Laundry Backup</h4><table border=1 cellpadding=6 style='border-collapse:collapse'><tr><th>Outlet</th><th>Backup</th><th>Excel</th></tr>")
    for k,v in data["laundry"].items():
        html.append(f"<tr><td>{k}</td><td>{v['backup_date']}</td><td>{v['excel_date']}</td></tr>")
    html.append("</table><br>")

    # Conflicted
    html.append(build_conflicted_html(data["conflicted_rows"], data["conflicted_count"]))

    # Footer
    html.append("<p>(het) Asif Ali - IT & Digital Marketing Manager<br>HARISH EXIM TRADING FZC<br>Mob: +971 50 140 9840</p>")
    return "\n".join(html)

# ==================== RUN JOB ====================
def run_job():
    state = {}
    africa_data = check_africa()
    tally_data = check_tally()
    laundry_data = check_laundry()
    conflicted_rows, conflicted_count = check_conflicted()

    state["history"] = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "africa": africa_data,
        "tally": tally_data,
        "laundry": laundry_data,
        "conflicted": {"rows": conflicted_rows, "total_find": conflicted_count}
    }

    data_for_html = {
        "africa": africa_data,
        "tally": tally_data,
        "laundry": laundry_data,
        "conflicted_rows": conflicted_rows,
        "conflicted_count": conflicted_count
    }

    html_report = build_html_report(data_for_html)

    # Save JSON
    with open(JSON_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)

    # Send email
    send_report_email(subject=f"NAS & Tally Report - {datetime.now().strftime('%Y-%m-%d')}", body=html_report, html=True)

    # Log
    log(f"NAS & Tally job completed. Total Conflicted Files: {conflicted_count}")

    # Save HTML locally
    OUTPUT_HTML = os.path.join(LOG_BASE, f"NAS_Tally_Report_{TIMESTAMP}.html")
    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html_report)
    log(f"HTML report saved: {OUTPUT_HTML}")

    return "Job Completed"

# ==================== ENTRY POINT ====================
if __name__ == "__main__":
    run_job()
