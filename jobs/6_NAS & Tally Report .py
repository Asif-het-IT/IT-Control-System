# jobs/Tally_Current_Backup.py
import os
import json
from datetime import datetime

from jobs.email_job import send_report_email

# ==========================
# PATHS & SETTINGS
# ==========================
LOG_BASE = r"D:\01 - SSS 300 LAUNDRY - Exports To Excel\logs"
os.makedirs(LOG_BASE, exist_ok=True)

JSON_STATE_FILE = os.path.join(LOG_BASE, "nas_state_test.json")

TODAY_KEY = datetime.now().strftime("%Y-%m-%d")
NOW_ISO = datetime.now().isoformat(timespec="seconds")

# ==========================
# AFRICA SETTINGS
# ==========================
AFRICA_BASE = r"\\het-nas\Tally-Africa\T-Current\Africa"
AFRICA_FOLDERS = ["99924", "20231", "40031", "60031"]

# ==========================
# TALLY SETTINGS
# ==========================
TALLY_BASE = r"\\het-NAS\Tally-Africa"
TALLY_MAP = {
    "T-Kano": "Ambariyya - Kano",
    "T-BukShop": "Noor - BukShop",
    "T-Abuja": "Fazal - Abuja",
    "T-Lagos": "Dua - Lagos"
}

# ==========================
# LOAD JSON STATE
# ==========================
state = {}
if os.path.exists(JSON_STATE_FILE):
    try:
        with open(JSON_STATE_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)
    except Exception:
        state = {}

state.setdefault("history", {})
state["last_run"] = NOW_ISO

# ==========================
# CHECK FUNCTIONS
# ==========================
def check_africa():
    data = {}
    for folder in AFRICA_FOLDERS:
        path = os.path.join(AFRICA_BASE, folder)
        if not os.path.exists(path):
            data[folder] = {"status": "MISSING", "latest_file": None}
            continue
        files = [f for f in os.listdir(path)
                 if f.startswith("TranMgr") and f.endswith(".900")]
        data[folder] = {
            "status": "OK" if files else "MISSING",
            "latest_file": max(files) if files else None
        }
    return data


def check_tally():
    data = {}
    for key, name in TALLY_MAP.items():
        path = os.path.join(TALLY_BASE, key)
        if not os.path.exists(path):
            data[name] = {"status": "MISSING", "latest_file": None}
            continue
        all_files = []
        for root, _, files in os.walk(path):
            for f in files:
                full = os.path.join(root, f)
                all_files.append((f, os.path.getmtime(full)))
        if all_files:
            latest = max(all_files, key=lambda x: x[1])[0]
            data[name] = {"status": "OK", "latest_file": latest}
        else:
            data[name] = {"status": "MISSING", "latest_file": None}
    return data


# ==========================
# HTML REPORT
# ==========================
def build_html(data):
    def row(name, info):
        color = "#2ecc71" if info["status"] == "OK" else "#e74c3c"
        return f"""
        <tr>
            <td>{name}</td>
            <td>{info['latest_file'] or '—'}</td>
            <td style="color:{color};font-weight:bold;">{info['status']}</td>
        </tr>
        """

    africa_rows = "".join(row(k, v) for k, v in data["africa"].items())
    tally_rows = "".join(row(k, v) for k, v in data["tally"].items())

    return f"""
    <html>
    <body style="font-family:Arial;">
        <marquee><h3>(het) Automation App</h3></marquee>
        <marquee><h3>Tally Nas Cloud Report</h3></marquee>

        <h2>NAS & Tally Daily Report</h2>
        <p><b>Date:</b> {TODAY_KEY}</p>

        <h3>Africa Status</h3>
        <table border="1" cellpadding="6" cellspacing="0">
            <tr><th>Folder</th><th>Latest File</th><th>Status</th></tr>
            {africa_rows}
        </table>

        <h3 style="margin-top:20px;">Tally Status</h3>
        <table border="1" cellpadding="6" cellspacing="0">
            <tr><th>Branch</th><th>Latest File</th><th>Status</th></tr>
            {tally_rows}
        </table>

        <p style="margin-top:30px;font-size:12px;color:#666;">
            Asif Ali - IT & Digital Marketing Manager<br>
            HARISH EXIM TRADING FZC<br>
            Mob: +971 50 140 9840
        </p>
    </body>
    </html>
    """


# ==========================
# GUI ENTRY POINT (IMPORTANT)
# ==========================
def run_job():
    today_data = {
        "checked_at": NOW_ISO,
        "africa": check_africa(),
        "tally": check_tally()
    }

    state["history"][TODAY_KEY] = today_data

    with open(JSON_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)

    html_body = build_html(today_data)

    send_report_email(
        subject=f"NAS & Tally Report - {TODAY_KEY}",
        body=html_body,
        html=True
    )

    print("NAS check completed successfully.")
    return "NAS & Tally Report Sent"
