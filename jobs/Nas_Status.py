# jobs/1_Nas_Status.py

"""
(het) Asif Ali
"""


import os
import json
import logging
from datetime import datetime
from email_job import send_report_email
import re
import hashlib


# ==================================================
# PATHS & LOGGING
# ==================================================
BASE_PATH = r"\\het-nas\Tally-Africa\T-Current"
LOG_BASE = r"D:\01 - SSS 300 LAUNDRY - Exports To Excel\logs"
os.makedirs(LOG_BASE, exist_ok=True)

NOW = datetime.now()
TODAY = NOW.strftime("%Y-%m-%d")
TIMESTAMP = NOW.strftime("%Y-%m-%d_%H-%M-%S")

TXT_LOG = os.path.join(LOG_BASE, f"Tally_Report_{TIMESTAMP}.txt")
JSON_STATE = os.path.join(LOG_BASE, "tally_state.json")

logging.basicConfig(
    filename=TXT_LOG,
    level=logging.INFO,
    format="%(asctime)s\t%(levelname)s\t%(message)s",
)

def log(msg):
    print(msg)
    logging.info(msg)

# ==================================================
# VALID TALLY FILE PREFIXES
# ==================================================
VALID_PREFIX = (
    "TranMgr", "Manager", "LinkMgr", "TranInf",
    "CmpSave", "Company", "AddlCmp", "SumTran"
)

# ==================================================
# FRIENDLY BRANCH NAME MAP
# ==================================================
BRANCH_NAME_MAP = {
    "10000": "Senegal - Sattar",
    "10002": "Cameroon - Hope Textile",
    "20231": "BUK SHOP - NOOR IMPORT",
    "40031": "ABUJA - FAZAL",
    "56819": "Mail - Salam Textile OLD",
    "56823": "Mail - Salam Textile",
    "60031": "LAGOS - DUA TRADING",
    "77725": "Abidjan - Fashion Fusion",
    "99924": "KANO - Ambariya OLD",
    "99934": "KANO - Ambariya Fertilizer",
    "40021": "ABUJA - FAZAL OLD - 2021",
    "40022": "ABUJA - FAZAL OLD - 2022",
    "40024": "ABUJA - FAZAL OLD - 2024",
    "20221": "BUK SHOP - NOOR IMPORT - 2021",
    "20222": "BUK SHOP - NOOR IMPORT - 2022",
    "34020": "KANO - Ambariya OLD 2020",
    "34021": "KANO - Ambariya OLD 2021",
    "34022": "KANO - Ambariya OLD 2022",
    "60001": "LAGOS - DUA TRADING OLD 2020",
    "60021": "LAGOS - DUA TRADING OLD 2021",
    "60022": "LAGOS - DUA TRADING OLD 2022",
    "10001": "DXB - GROUP",
    "10003": "AFRICAN FUND MANAGEMENT",
    "10025": "MAIN SHOP",
    "10026": "BRANCH SHOP",
    "10027": "INPEX SHOP",
    "52365": "SSS 300 LAUNDRY",
    "56984": "Harish Exim LLC",
    "76541": "Harish Exim Trading FZC",
    "86532": "Harish Exim LLC OLD",
    "60022old": "LAGOS OLD",
}

# ==================================================
# LAUNDRY CHECK
# ==================================================
LAUNDRY_BRANCHES = {
    "BR1-Qusais-SB": {
        "backup": r"\\het-nas\G-SSS300\BR1-Qusais-SB\Cloud\1 - SSS300 - New SQL\Backup",
        "excel": r"\\het-nas\G-SSS300\BR1-Qusais-SB\Cloud\1 - SSS300 - New SQL\ExportsToExcel",
    },
    "BR2-DMP": {
        "backup": r"\\het-nas\G-SSS300\BR2-DMP\Cloud\SSS300 - SQL  - DMP\Backup",
        "excel": r"\\het-nas\G-SSS300\BR2-DMP\Cloud\SSS300 - SQL  - DMP\ExportsToExcel",
    },
    "BR3-CB": {
        "backup": r"\\het-nas\G-SSS300\BR3-CB\Cloud\ABRStarTouch\Backup",
        "excel": r"\\het-nas\G-SSS300\BR3-CB\Cloud\ABRStarTouch\ExportsToExcel",
    },
    "BR4-JVC": {
        "backup": r"\\het-nas\G-SSS300\BR4-JVC\Cloud\SSS300 Laundry - JVC - SQL\Backup",
        "excel": r"\\het-nas\G-SSS300\BR4-JVC\Cloud\SSS300 Laundry - JVC - SQL\ExportsToExcel",
    },
    "BR5-DSO": {
        "backup": r"\\het-nas\G-SSS300\BR5-DSO\Cloud\SSS300 - DSO - SQL\Backup",
        "excel": r"\\het-nas\G-SSS300\BR5-DSO\Cloud\SSS300 - DSO - SQL\ExportsToExcel",
    },
    "BR6-BH": {
        "backup": r"\\het-nas\G-SSS300\BR6-BH\Cloud\SSS300 - BH - SQL\Backup",
        "excel": r"\\het-nas\G-SSS300\BR6-BH\Cloud\SSS300 - BH - SQL\ExportsToExcel",
    },
}

def latest_file_info(path):
    try:
        if not os.path.exists(path):
            log(f"Path not found: {path}")
            return None, None
        files = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
        if not files:
            log(f"No files in: {path}")
            return None, None
        latest_file = max(files, key=lambda f: os.path.getmtime(os.path.join(path, f)))
        latest_date = datetime.fromtimestamp(os.path.getmtime(os.path.join(path, latest_file))).strftime("%d-%b-%Y")
        return latest_file, latest_date
    except Exception as e:
        log(f"Error reading {path}: {e}")
        return None, None

def check_laundry():
    out = {}
    for branch, paths in LAUNDRY_BRANCHES.items():
        backup_file, backup_date = latest_file_info(paths["backup"])
        excel_file, excel_date = latest_file_info(paths["excel"])
        out[branch] = {
            "backup_date": backup_date or "MISSING",
            "excel_name": excel_file or "MISSING",
            "excel_date": excel_date or "MISSING"
        }
    return out

# ==================================================
# CORE TALLY SCAN
# ==================================================
def scan_tally_tree():
    rows = []
    for root, dirs, files in os.walk(BASE_PATH):
        rel = os.path.relpath(root, BASE_PATH)
        if rel == ".":
            continue
        code = os.path.basename(root)
        name = BRANCH_NAME_MAP.get(code, code)

        # TranMgr files
        tranmgr_files = [os.path.join(root, f) for f in files if f.startswith("TranMgr") and f.endswith(".900")]
        tranmgr_date = None
        if tranmgr_files:
            latest = max(tranmgr_files, key=os.path.getmtime)
            tranmgr_date = datetime.fromtimestamp(os.path.getmtime(latest)).strftime("%d-%b-%Y")

        # Conflicted files (multiple)
        conflicted_files = [f for f in files if "(Conflicted copy" in f and f.startswith(VALID_PREFIX)]
        conflicted_date = None
        conflicted_by = "—"
        if conflicted_files:
            conflicted_dates = []
            conflicted_users = []
            for cf in conflicted_files:
                conflicted_dates.append(datetime.fromtimestamp(os.path.getmtime(os.path.join(root, cf))).strftime("%d-%b-%Y"))
                m = re.search(r'Conflicted copy.*by (.+)\.900', cf)
                if m:
                    conflicted_users.append(m.group(1))
            conflicted_date = max(conflicted_dates)
            conflicted_by = ", ".join(set(conflicted_users)) if conflicted_users else "—"

        rows.append({
            "code": code,
            "name": name,
            "tranmgr_date": tranmgr_date or "MISSING",
            "tranmgr_status": "OK" if tranmgr_date else "MISSING",
            "conflicted": "YES" if conflicted_date else "NO",
            "conflicted_date": conflicted_date or "—",
            "conflicted_by": conflicted_by
        })

    # Sort by TranMgr Date descending (new → old)
    rows.sort(key=lambda x: datetime.strptime(x["tranmgr_date"], "%d-%b-%Y") if x["tranmgr_date"] != "MISSING" else datetime(1900,1,1), reverse=True)
    return rows

# ==================================================
# BUILD HTML
# ==================================================
def build_html(tally_rows, laundry_rows):
    html = f"""
    <html>
    <body style="font-family:Calibri">
    <h3>Tally NAS + Laundry Combined Status Report</h3>
    <p>Date: {TODAY}</p>

    <h4>Tally Status</h4>
    <table border="1" cellpadding="6" cellspacing="0">
    <tr>
        <th>Code</th>
        <th>Branch Name</th>
        <th>TranMgr Date</th>
        <th>Status</th>
        <th>Conflicted</th>
        <th>Conflicted Date</th>
        <th>Conflicted By User</th>
    </tr>
    """

    for r in tally_rows:
        color = "#f8d7da" if r["conflicted"] == "YES" else "#d4edda"
        html += f"""
        <tr>
            <td>{r['code']}</td>
            <td>{r['name']}</td>
            <td>{r['tranmgr_date']}</td>
            <td><b>{r['tranmgr_status']}</b></td>
            <td style="background:{color};font-weight:bold;">{r['conflicted']}</td>
            <td>{r['conflicted_date']}</td>
            <td>{r['conflicted_by']}</td>
        </tr>
        """

    html += """
    </table><br>
    <h4>Laundry Backup Status</h4>
    <table border="1" cellpadding="6" cellspacing="0">
    <tr><th>Outlet</th><th>Backup</th><th>Excel Name</th><th>Excel Date</th></tr>
    """

    for branch, v in laundry_rows.items():
        color = "#d4edda"  # green
        if v["backup_date"] != v["excel_date"]:
            color = "#f8d7da"  # red

        html += f"""
        <tr style="background:{color}">
            <td>{branch}</td>
            <td>{v['backup_date']}</td>
            <td>{v['excel_name']}</td>
            <td>{v['excel_date']}</td>
        </tr>
        """

    html += """
    </table>
    <p style="font-size:12px;color:#555">
    (het) Asif Ali – IT & Digital Marketing Manager
    </p>
    </body>
    </html>
    """
    return html

# ==================================================
# MAIN JOB
# ==================================================
def run_job():
    log("Tally NAS + Laundry job started")
    tally_data = scan_tally_tree()
    laundry_data = check_laundry()

    # Save state + SHA256 for records (not in email)
    state = {"history": {}}
    if os.path.exists(JSON_STATE):
        with open(JSON_STATE, "r", encoding="utf-8") as f:
            state = json.load(f)

    # Compute SHA256 for each branch (Tally + Laundry combined string)
    for branch in tally_data:
        record_str = json.dumps(branch, sort_keys=True).encode("utf-8")
        branch["sha256"] = hashlib.sha256(record_str).hexdigest()

    state["history"][TODAY] = {"tally": tally_data, "laundry": laundry_data}
    with open(JSON_STATE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)

    html = build_html(tally_data, laundry_data)
    send_report_email(
        subject=f"Tally NAS & Laundry Combined Report - {TODAY}",
        body=html,
        html=True
    )
    log("Tally NAS + Laundry report sent successfully")
    return "DONE"

if __name__ == "__main__":
    run_job()
