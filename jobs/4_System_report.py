# ---------- jobs/system_report_gui_html_email.py ----------

import os
import sys
import datetime
import platform
import psutil
import socket
import subprocess
import urllib.request

# ----------------- PATH SETUP -----------------
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JOBS_PATH = os.path.join(PROJECT_ROOT, 'jobs')
if JOBS_PATH not in sys.path:
    sys.path.insert(0, JOBS_PATH)

# ----------------- LOGGER -----------------
try:
    from utils.logger import write_log as log_info, write_error as log_error
except Exception:
    def log_info(msg): print("[INFO]", msg)
    def log_error(msg): print("[ERROR]", msg)

# ----------------- EMAIL -----------------
try:
    import email_job
    send_report_email = email_job.send_report_email
except Exception as e:
    log_error(f"Email import failed: {e}")
    send_report_email = None

# ================= COLLECTORS =================

def get_local_ip():
    try:
        return socket.gethostbyname(socket.gethostname())
    except Exception:
        return "N/A"

def get_public_ip():
    try:
        with urllib.request.urlopen("https://api.ipify.org", timeout=5) as r:
            return r.read().decode()
    except Exception:
        return "N/A"

def get_uptime():
    try:
        boot = datetime.datetime.fromtimestamp(psutil.boot_time())
        return str(datetime.datetime.now() - boot).split(".")[0]
    except Exception:
        return "N/A"

def get_antivirus():
    if platform.system() != "Windows":
        return "Not Applicable"
    try:
        result = subprocess.run(
            ["wmic", "product", "get", "name"],
            capture_output=True,
            text=True
        )
        av = [l.strip() for l in result.stdout.splitlines() if "antivirus" in l.lower()]
        return ", ".join(av) if av else "Not Detected"
    except Exception:
        return "N/A"

def get_disk_info():
    disks = []
    for part in psutil.disk_partitions():
        try:
            usage = psutil.disk_usage(part.mountpoint)
            disks.append({
                "device": part.device,
                "used": f"{usage.used / (1024**3):.2f} GB",
                "total": f"{usage.total / (1024**3):.2f} GB",
                "percent": f"{usage.percent}%"
            })
        except Exception:
            continue
    return disks

# ================= HTML FORMATTER =================

def generate_html_report(data):
    """Email-safe HTML with tables and columns"""

    return f"""
    <html>
    <body style="font-family:Segoe UI, Arial; background:#f4f6f8; padding:20px;">

    <table width="100%" cellpadding="0" cellspacing="0" style="background:#ffffff; border-radius:6px;">
        <tr>
            <td style="padding:20px;">
                <h2 style="color:#2c3e50;">System Report</h2>
                <p><strong>Generated:</strong> {data['timestamp']}</p>

                <hr>

                <h3>🖥 System Information</h3>
                <table width="100%" border="1" cellspacing="0" cellpadding="6">
                    <tr><td><b>Device Name</b></td><td>{data['node']}</td></tr>
                    <tr><td><b>OS</b></td><td>{data['os']}</td></tr>
                    <tr><td><b>Architecture</b></td><td>{data['arch']}</td></tr>
                    <tr><td><b>Processor</b></td><td>{data['cpu']}</td></tr>
                    <tr><td><b>RAM</b></td><td>{data['ram']}</td></tr>
                </table>

                <h3>💽 Disk Usage</h3>
                <table width="100%" border="1" cellspacing="0" cellpadding="6">
                    <tr>
                        <th>Disk</th><th>Used</th><th>Total</th><th>Usage</th>
                    </tr>
                    {''.join(f"<tr><td>{d['device']}</td><td>{d['used']}</td><td>{d['total']}</td><td>{d['percent']}</td></tr>" for d in data['disks'])}
                </table>

                <h3>🌐 Network & Security</h3>
                <table width="100%" border="1" cellspacing="0" cellpadding="6">
                    <tr><td><b>Local IP</b></td><td>{data['local_ip']}</td></tr>
                    <tr><td><b>Public IP</b></td><td>{data['public_ip']}</td></tr>
                    <tr><td><b>Antivirus</b></td><td>{data['antivirus']}</td></tr>
                    <tr><td><b>Uptime</b></td><td>{data['uptime']}</td></tr>
                </table>

                <p style="margin-top:20px; font-size:12px; color:#7f8c8d;">
                    Automated system report – Do not reply.
                </p>

            </td>
        </tr>
    </table>
    </body>
    </html>
    """

# ================= ORCHESTRATOR =================

def generate_and_email_report_html():
    log_info("Collecting system data...")

    ram = psutil.virtual_memory()

    data = {
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "node": platform.node(),
        "os": f"{platform.system()} {platform.release()}",
        "arch": platform.machine(),
        "cpu": f"{platform.processor()} ({psutil.cpu_count()} cores)",
        "ram": f"{ram.total / (1024**3):.2f} GB",
        "disks": get_disk_info(),
        "local_ip": get_local_ip(),
        "public_ip": get_public_ip(),
        "antivirus": get_antivirus(),
        "uptime": get_uptime()
    }

    html = generate_html_report(data)

    if send_report_email:
        send_report_email(
            subject=f"System Report - {data['timestamp']}",
            body=html,
            html=True
        )

if __name__ == "__main__":
    generate_and_email_report_html()
