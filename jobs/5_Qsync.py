# ==========================================================
# IT ADMIN - DXB SERVER REPORT (ENTERPRISE FINAL)
# GUI SAFE | AUTO EMAIL | LOCAL + PUBLIC IP
# ==========================================================

import os
import csv
import psutil
import platform
import subprocess
from datetime import datetime, timedelta

# ================= CONFIG =================
BASE_DIR = r"C:\SystemMonitor"
LOGIN_CSV = os.path.join(BASE_DIR, "login_history.csv")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
QSYNC_PATH = r"C:\Program Files (x86)\QNAP\Qsync\Qsync.exe"

# ================= EMAIL =================
try:
    import email_job
    send_report_email = email_job.send_report_email
except Exception:
    send_report_email = None

# ================= STORAGE =================
def setup_storage():
    os.makedirs(BASE_DIR, exist_ok=True)
    os.makedirs(REPORTS_DIR, exist_ok=True)
    if not os.path.exists(LOGIN_CSV):
        with open(LOGIN_CSV, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(
                ["timestamp", "username", "logon_type", "source_ip"]
            )

# ================= LOGIN HISTORY =================
def extract_value(text, key):
    for line in text.splitlines():
        if key in line:
            return line.split(":", 1)[1].strip()
    return "N/A"

def collect_logins():
    setup_storage()
    cmd = 'wevtutil qe Security /q:"*[System[(EventID=4624)]]" /f:text /c:5'
    try:
        output = subprocess.check_output(cmd, shell=True, text=True, errors="ignore")
        with open(LOGIN_CSV, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            for block in output.split("Event["):
                if "Account Name:" in block:
                    user = extract_value(block, "Account Name:")
                    if user.lower() in ("system", "local service"):
                        continue
                    writer.writerow([
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        user,
                        extract_value(block, "Logon Type:"),
                        extract_value(block, "Source Network Address:")
                    ])
    except Exception:
        pass

def login_summary_24h():
    cutoff = datetime.now() - timedelta(hours=24)
    total, last = 0, "N/A"

    if not os.path.exists(LOGIN_CSV):
        return total, last

    with open(LOGIN_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                ts = datetime.strptime(row["timestamp"], "%Y-%m-%d %H:%M:%S")
                if ts >= cutoff:
                    total += 1
                    last = f"{row['username']} @ {row['timestamp']}"
            except Exception:
                pass
    return total, last

# ================= QSYNC =================
def qsync_status():
    for p in psutil.process_iter(["exe", "create_time"]):
        try:
            if p.info["exe"] and p.info["exe"].lower() == QSYNC_PATH.lower():
                up = datetime.now() - datetime.fromtimestamp(p.info["create_time"])
                return "Running", str(up).split(".")[0]
        except Exception:
            pass
    try:
        subprocess.Popen(QSYNC_PATH)
        return "Restarted", "0:00:00"
    except Exception:
        return "Failed", "N/A"

# ================= NETWORK =================
def local_lan_ip():
    try:
        out = subprocess.check_output("ipconfig", text=True, errors="ignore")
        for line in out.splitlines():
            line = line.strip()
            if line.startswith("IPv4 Address"):
                ip = line.split(":")[-1].strip()
                if not ip.startswith(("169.254", "127.")):
                    return ip
    except Exception:
        pass
    return "N/A"

def public_ip():
    try:
        out = subprocess.check_output(
            'powershell -Command "(Invoke-RestMethod -Uri https://api.ipify.org)"',
            text=True,
            timeout=5
        )
        return out.strip()
    except Exception:
        return "N/A"

# ================= HTML TEMPLATES =================
EMAIL_HTML = """<!DOCTYPE html>
<html><body style="font-family:Arial;background:#f7f7f7;padding:20px">
<div style="max-width:600px;margin:auto;background:#fff;padding:20px;border-radius:10px">
<h2 style="text-align:center">IT Admin - DXB Server Report</h2>
<p style="text-align:center;color:#666">Generated: {{NOW}}</p>
<table width="100%" cellpadding="8" cellspacing="0" style="border-collapse:collapse">
<tr><th align="left">System</th><td>{{SYSTEM}}</td></tr>
<tr><th align="left">OS</th><td>{{OS}}</td></tr>
<tr><th align="left">Network</th><td>Local IP: {{LOCAL_IP}}<br>Public IP: {{PUBLIC_IP}}</td></tr>
<tr><th align="left">Qsync</th><td>{{QSYNC}}</td></tr>
<tr><th align="left">Uptime</th><td>{{UPTIME}}</td></tr>
<tr><th align="left">Logins (24h)</th><td>{{LOGIN}}</td></tr>
</table>
<hr>
<div style="text-align:center;font-size:13px;color:#555">
<strong>Asif Ali</strong><br>
IT & Digital Marketing Manager<br>
HARISH EXIM TRADING FZC<br>
📞 +971 50 140 9840
</div>
</div></body></html>
"""

BROWSER_HTML = """<!DOCTYPE html>
<html><head><style>
body{font-family:Arial;background:#f4f6f8;padding:20px}
.box{max-width:600px;margin:auto;background:#fff;padding:20px;border-radius:10px}
.banner{overflow:hidden;white-space:nowrap;background:#e8f5e9;padding:8px;margin-top:15px}
.banner span{display:inline-block;padding-left:100%;animation:scroll 12s linear infinite}
@keyframes scroll{from{transform:translateX(0)}to{transform:translateX(-100%)}}
</style></head>
<body>
<div class="box">
<h2 style="text-align:center">IT Admin - DXB Server Report</h2>
<p style="text-align:center;color:#666">Generated: {{NOW}}</p>
<p><b>System:</b> {{SYSTEM}}</p>
<p><b>OS:</b> {{OS}}</p>
<p><b>Network:</b><br>Local IP: {{LOCAL_IP}}<br>Public IP: {{PUBLIC_IP}}</p>
<p><b>Qsync:</b> {{QSYNC}} ({{UPTIME}})</p>
<p><b>Logins:</b> {{LOGIN}}</p>
<div class="banner"><span>Asif Ali — HARISH EXIM TRADING FZC — +971 50 140 9840</span></div>
</div></body></html>
"""

def render(tpl, ctx):
    for k, v in ctx.items():
        tpl = tpl.replace(f"{{{{{k}}}}}", v)
    return tpl

# ================= GUI ENTRY =================
def generate_html():
    collect_logins()
    q_status, q_uptime = qsync_status()
    logins, last = login_summary_24h()

    now = datetime.now().strftime("%d/%b/%Y %I:%M:%S %p")
    ctx = {
        "NOW": now,
        "SYSTEM": platform.node(),
        "OS": f"{platform.system()} {platform.release()}",
        "LOCAL_IP": local_lan_ip(),
        "PUBLIC_IP": public_ip(),
        "QSYNC": q_status,
        "UPTIME": q_uptime,
        "LOGIN": f"{logins} | Last: {last}"
    }

    email_html = render(EMAIL_HTML, ctx)
    browser_html = render(BROWSER_HTML, ctx)

    # Save browser version
    fname = f"DXB_Server_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    fpath = os.path.join(REPORTS_DIR, fname)
    with open(fpath, "w", encoding="utf-8") as f:
        f.write(browser_html)

    # Send Email
    if send_report_email:
        send_report_email(
            subject=f"IT Admin - DXB Server Report ({now})",
            body=email_html,
            html=True
        )

    return fpath

# ================= MAIN =================
if __name__ == "__main__":
    generate_html()
