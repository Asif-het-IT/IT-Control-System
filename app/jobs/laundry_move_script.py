# jobs/3_Laundry_Move_Done.py

import os
import shutil
import sys
import traceback
from datetime import datetime

# =========================
# GUI SAFE PATH
# =========================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JOBS_DIR = os.path.join(BASE_DIR, "jobs")
if JOBS_DIR not in sys.path:
    sys.path.insert(0, JOBS_DIR)

# =========================
# EMAIL IMPORT
# =========================
try:
    from email_job import send_report_email
except Exception:
    send_report_email = None

# =========================
# CONFIG
# =========================
SOURCE_FOLDER = r"D:\01 - SSS 300 LAUNDRY - Exports To Excel\All Branches"
DONE_FOLDER = os.path.join(SOURCE_FOLDER, "Done")
REPORTS_FOLDER = os.path.join(BASE_DIR, "reports")

os.makedirs(DONE_FOLDER, exist_ok=True)
os.makedirs(REPORTS_FOLDER, exist_ok=True)

# =========================
# HELPERS
# =========================
def parse_name_get_prefix_and_date(name):
    parts = name.rsplit("-", 3)
    if len(parts) != 4:
        return None, None
    prefix, day, month, year = parts
    try:
        d = str(int(day)).zfill(2)
        m = str(int(month)).zfill(2)
        y = str(int(year))
    except:
        return None, None
    return prefix, f"{d}-{m}-{y}"

def build_index(folder):
    excel, txt = {}, {}
    for f in os.listdir(folder):
        path = os.path.join(folder, f)
        if not os.path.isfile(path):
            continue
        name, ext = os.path.splitext(f)
        prefix, date = parse_name_get_prefix_and_date(name)
        if not prefix:
            continue
        key = (prefix, date)
        if ext.lower() == ".xlsx":
            excel[key] = f
        elif ext.lower() == ".txt":
            txt[key] = f
    return excel, txt

def safe_move(src, dst):
    if os.path.exists(dst):
        base, ext = os.path.splitext(dst)
        dst = f"{base}__{datetime.now().strftime('%H%M%S')}{ext}"
    shutil.move(src, dst)

# =========================
# HTML TABLE (PROPER)
# =========================
def build_html_email(rows, summary):
    html = """
    <html>
    <body style="font-family:Arial;font-size:13px;">
    <h3>Laundry Excel Move Done Report</h3>

    <table border="1" cellpadding="6" cellspacing="0" width="100%"
           style="border-collapse:collapse;">
      <tr style="background:#f2f2f2;">
        <th>Branch</th>
        <th>Date</th>
        <th>Excel File</th>
        <th>TXT File</th>
        <th>Status</th>
      </tr>
    """

    for r in rows:
        color = "green" if r["status"] == "Moved" else "red"
        html += f"""
        <tr>
          <td>{r['branch']}</td>
          <td>{r['date']}</td>
          <td>{r['excel']}</td>
          <td>{r['txt']}</td>
          <td style="color:{color};font-weight:bold;">
            {r['status']}
          </td>
        </tr>
        """

    html += f"""
    </table>
    <br>
    <b>Summary:</b> {summary}
    </body>
    </html>
    """
    return html

# =========================
# MAIN JOB
# =========================
def run_move_excel(send_email=True):
    table_rows = []
    logs = []

    try:
        excel, txt = build_index(SOURCE_FOLDER)
        all_keys = sorted(set(excel) | set(txt))

        total = moved = skipped = 0

        for key in all_keys:
            total += 1
            prefix, date = key
            ex = excel.get(key)
            tx = txt.get(key)

            if ex and tx:
                safe_move(os.path.join(SOURCE_FOLDER, ex),
                          os.path.join(DONE_FOLDER, ex))
                safe_move(os.path.join(SOURCE_FOLDER, tx),
                          os.path.join(DONE_FOLDER, tx))
                moved += 1
                table_rows.append({
                    "branch": prefix,
                    "date": date,
                    "excel": ex,
                    "txt": tx,
                    "status": "Moved"
                })
            else:
                skipped += 1
                table_rows.append({
                    "branch": prefix,
                    "date": date,
                    "excel": ex or "-",
                    "txt": tx or "-",
                    "status": "Skipped"
                })

        summary = f"Total: {total}, Moved: {moved}, Skipped: {skipped}"

    except Exception as e:
        logs.append(str(e))
        summary = "ERROR occurred"

    # =========================
    # EMAIL SEND (REAL FIX)
    # =========================
    if send_email and send_report_email:
        html_body = build_html_email(table_rows, summary)
        send_report_email(
            subject=f"Laundry Move Done Report - {datetime.now().strftime('%d-%b-%Y')}",
            body=html_body,
            html=True
        )

    return summary

# =========================
# DIRECT RUN
# =========================
if __name__ == "__main__":
    print(run_move_excel(True))
