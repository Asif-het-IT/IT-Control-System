# jobs/speed_test_job.py
import os
import json
from datetime import datetime
import threading
from speedtest import Speedtest
from jobs.email_job import send_report_email
import matplotlib.pyplot as plt
from io import BytesIO
import base64

# ==========================
# PATHS & SETTINGS
# ==========================
LOG_DIR = r"D:\01 - SSS 300 LAUNDRY - Exports To Excel\logs"
os.makedirs(LOG_DIR, exist_ok=True)
JSON_FILE = os.path.join(LOG_DIR, "internet_speed_history.json")

# ==========================
# Load last 7 runs
# ==========================
history = []
if os.path.exists(JSON_FILE):
    try:
        with open(JSON_FILE, "r", encoding="utf-8") as f:
            history = json.load(f)
    except:
        history = []

# ==========================
# Run Speed Test
# ==========================
def run_speedtest(gui_enqueue=None):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        if gui_enqueue:
            gui_enqueue("[INFO] Starting Speedtest...")
        st = Speedtest()
        st.get_best_server()

        download = st.download() / 1_000_000  # Mbps
        upload = st.upload() / 1_000_000
        ping = st.results.ping

        result = {
            "timestamp": timestamp,
            "download": round(download, 2),
            "upload": round(upload, 2),
            "ping": round(ping, 1)
        }

        history.append(result)
        history[:] = history[-7:]  # last 7 runs

        with open(JSON_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)

        if gui_enqueue:
            gui_enqueue(f"[RESULT] Download: {result['download']} Mbps | Upload: {result['upload']} Mbps | Ping: {result['ping']} ms")
            gui_enqueue("[INFO] Generating trend chart...")

        # Plot trend
        fig, ax = plt.subplots(figsize=(4,1))
        downloads = [r["download"] for r in history]
        uploads = [r["upload"] for r in history]
        pings = [r["ping"] for r in history]

        ax.plot(downloads, color='green', label='DL', marker='o')
        ax.plot(uploads, color='blue', label='UL', marker='o')
        ax.plot(pings, color='red', label='Ping', marker='o')
        ax.set_xticks(range(len(history)))
        ax.set_xticklabels([r["timestamp"].split()[1] for r in history], rotation=45, fontsize=8)
        ax.set_yticklabels([])
        ax.set_ylabel("")
        ax.legend(loc='upper right', fontsize=6)
        plt.tight_layout()

        buf = BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        chart_base64 = base64.b64encode(buf.read()).decode('utf-8')
        buf.close()
        plt.close(fig)

        html = f"""
        <html><body>
        <h3>Internet Speed Test</h3>
        <p><b>Download:</b> {result['download']} Mbps | 
           <b>Upload:</b> {result['upload']} Mbps | 
           <b>Ping:</b> {result['ping']} ms</p>
        <p>Trend last 7 runs:</p>
        <img src="data:image/png;base64,{chart_base64}" />
        </body></html>
        """

        # Email
        try:
            send_report_email(subject=f"Internet Speed Test - {timestamp}", body=html, html=True)
            if gui_enqueue:
                gui_enqueue("[INFO] Report emailed successfully.")
        except Exception as e:
            if gui_enqueue:
                gui_enqueue(f"[ERROR] Email failed: {e}")

        if gui_enqueue:
            gui_enqueue("[INFO] Speedtest completed.")
        return result

    except Exception as e:
        if gui_enqueue:
            gui_enqueue(f"[ERROR] Speedtest failed: {e}")
        return None

# ==========================
# GUI ENTRY
# ==========================
def run_job(gui_enqueue=None):
    thread = threading.Thread(target=run_speedtest, kwargs={"gui_enqueue": gui_enqueue}, daemon=True)
    thread.start()
    return "Speedtest started..."
