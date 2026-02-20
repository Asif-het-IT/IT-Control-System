#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
het Automation Dashboard – Professional Version (ROMAN URDU)
Author: Asif Ali
"""

# ----------------------------------------------------
# Standard imports
# ----------------------------------------------------
import sys
import os
import importlib
import traceback
import threading
from pathlib import Path
from queue import Queue, Empty
from typing import Any, Dict, List, Optional

# ----------------------------------------------------
# Project root in sys.path
# ----------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ----------------------------------------------------
# Logging
# ----------------------------------------------------
import logging

LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "app.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)

def write_log(msg: str) -> None:
    logging.info(msg)

def write_error(msg: str) -> None:
    logging.error(msg)

# ----------------------------------------------------
# Clipboard helper (pyperclip optional)
# ----------------------------------------------------
def copy_text(text: str) -> bool:
    try:
        import pyperclip
        pyperclip.copy(text)
        return True
    except Exception:
        return False

# ----------------------------------------------------
# CustomTkinter
# ----------------------------------------------------
try:
    import customtkinter as ctk
except Exception as exc:
    raise RuntimeError("customtkinter not installed – run 'pip install customtkinter'") from exc

# ----------------------------------------------------
# Discover jobs in jobs/* …
# ----------------------------------------------------
def discover_jobs() -> List[Dict[str, Any]]:
    jobs_dir = ROOT / "jobs"
    results: List[Dict[str, Any]] = []

    if not jobs_dir.is_dir():
        return results

    for path in sorted(jobs_dir.glob("*.py")):
        if path.name.startswith("__"):
            continue
        modname = path.stem
        fullname = f"jobs.{modname}"
        try:
            module = importlib.import_module(fullname)
        except Exception as exc:
            results.append(
                {
                    "module_name": modname,
                    "display": modname.title(),
                    "error": f"ImportError: {exc}",
                    "exception": traceback.format_exc(),
                    "callable": None,
                    "module": None,
                }
            )
            continue

        # Best “entry point” heuristic
        candidate: Optional[str] = None
        for attr in dir(module):
            func = getattr(module, attr)
            if callable(func) and (
                attr.startswith(("run_", "restart_", "generate_", "send_"))
                or attr == "main"
            ):
                candidate = attr
                break

        doc = module.__doc__
        display = (
            doc.splitlines()[0].strip()
            if doc
            else modname.replace("_", " ").title()
        )

        results.append(
            {
                "module_name": modname,
                "display": display,
                "error": None,
                "exception": None,
                "callable": candidate,
                "module": module,
            }
        )
    return results

# ----------------------------------------------------
# Call a job safely (runs in a thread)
# ----------------------------------------------------
def call_job(module_obj: Any, func_name: str, enqueue: callable) -> Any:
    mod_nm = getattr(module_obj, "__name__", getattr(module_obj, "__class__", "unknown"))
    enqueue(f"[INFO] Starting {mod_nm} (entry: {func_name})")
    write_log(f"Starting {mod_nm} (entry: {func_name})")
    try:
        if hasattr(module_obj, "run_job") and callable(module_obj.run_job):
            result = module_obj.run_job()
        else:
            func = getattr(module_obj, func_name)
            result = func() if callable(func) else None
        enqueue(f"[INFO] {mod_nm} completed.")
        write_log(f"{mod_nm} completed.")
        return result
    except Exception:
        tb = traceback.format_exc()
        enqueue(f"[ERROR] {mod_nm} failed: {exc}")
        enqueue(tb)
        write_error(f"{mod_nm} failed: {exc}\n{tb}")
        return None

# ----------------------------------------------------
# GUI App
# ----------------------------------------------------
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")

class LaundryApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("het Automation")
        self.geometry("1000x720")
        self._setup_icon()

        # UI queue for thread‑safe updates
        self.ui_queue: Queue[str] = Queue()
        self.after(200, self._process_queue)

        # ---------------- layout ----------------
        self._create_top_bar()
        self._create_main_area()

        # ---------------- state ----------------
        self.job_widgets: List[ctk.CTkFrame] = []
        self.jobs: List[Dict[str, Any]] = []

        # ---------------- load data ----------------
        self.refresh_jobs()
        self.refresh_reports()

    # ----------------------------------------------------
    def _setup_icon(self):
        ic = ROOT / "settings" / "het.ico"
        if ic.exists():
            try:
                self.iconbitmap(str(ic))
            except Exception:
                pass

    # ----------------------------------------------------
    def _create_top_bar(self):
        top = ctk.CTkFrame(self, corner_radius=0)
        top.pack(fill="x")

        title = ctk.CTkLabel(
            top,
            text="het Automations & Monitoring Dashboard",
            font=ctk.CTkFont(size=20, weight="bold"),
            pady=12,
        )
        title.pack(side="left", padx=20)

        ctk.CTkButton(
            top,
            text="Refresh Jobs",
            width=120,
            command=self.refresh_jobs,
        ).pack(side="right", padx=12, pady=12)

        ctk.CTkButton(
            top,
            text="Refresh Reports",
            width=140,
            command=self.refresh_reports,
        ).pack(side="right", padx=6, pady=12)

    # ----------------------------------------------------
    def _create_main_area(self):
        mid = ctk.CTkFrame(self)
        mid.pack(fill="both", expand=True, padx=12, pady=8)

        # --- Left: jobs list ---------------------------------
        self.tasks_panel = ctk.CTkFrame(mid, width=320)
        self.tasks_panel.pack(side="left", fill="y", padx=(0, 10), pady=6)

        lbl = ctk.CTkLabel(
            self.tasks_panel,
            text="Discovered Jobs",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        lbl.pack(pady=(8, 6))

        self.jobs_container = ctk.CTkScrollableFrame(
            self.tasks_panel, width=300, height=520
        )
        self.jobs_container.pack(padx=8, pady=6, fill="y")

        # --- Right: reports + output -------------------------
        right = ctk.CTkFrame(mid)
        right.pack(side="left", fill="both", expand=True)

        rpt_frame = ctk.CTkFrame(right)
        rpt_frame.pack(fill="x", padx=8, pady=(6, 8))

        self.reports_var = ctk.StringVar(value="")
        self.reports_menu = ctk.CTkOptionMenu(
            rpt_frame,
            values=[],
            variable=self.reports_var,
            command=self._show_report,
        )
        self.reports_menu.pack(side="left", padx=(8, 6))

        self.open_report_btn = ctk.CTkButton(
            rpt_frame,
            text="Open",
            command=self._open_selected_report,
            width=80,
        )
        self.open_report_btn.pack(side="left", padx=6)

        self.copy_btn = ctk.CTkButton(
            rpt_frame,
            text="Copy Output",
            command=self.copy_output,
            width=120,
        )
        self.copy_btn.pack(side="right", padx=6)

        self.output_box = ctk.CTkTextbox(right, width=600, height=420)
        self.output_box.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.output_box.configure(state="disabled")

        # determine if tags are supported
        self._use_tags = hasattr(self.output_box, "tag_configure")
        if self._use_tags:
            try:
                self.output_box.tag_configure("err", foreground="#FF6B6B")
                self.output_box.tag_configure("succ", foreground="#7CFC00")
            except Exception:
                self._use_tags = False

        bottom = ctk.CTkFrame(right)
        bottom.pack(fill="x", padx=8, pady=(0, 16))

        self.send_email_btn = ctk.CTkButton(
            bottom,
            text="Send Latest Report by Email",
            width=260,
            command=self.send_latest_report,
        )
        self.send_email_btn.pack(side="left", padx=8)

        footer = ctk.CTkLabel(
            self,
            text="Asif Ali — IT & Digital Marketing Manager    HARISH EXIM TRADING FZC    +971 50 140 9840",
            font=ctk.CTkFont(size=11),
        )
        footer.pack(side="bottom", fill="x", pady=6)

    # ----------------------------------------------------
    # Queue helper
    # ----------------------------------------------------
    def _enqueue_output(self, txt: str):
        self.ui_queue.put(txt)

    def _process_queue(self):
        try:
            while True:
                txt = self.ui_queue.get_nowait()
                self._append_output(txt)
        except Empty:
            pass
        self.after(200, self._process_queue)

    # ----------------------------------------------------
    def _append_output(self, line: str, tag: Optional[str] = None):
        self.output_box.configure(state="normal")
        if self._use_tags:
            if tag == "err" or line.startswith("[ERROR]"):
                self.output_box.insert("end", line + "\n", "err")
            elif tag == "succ" or line.startswith("[INFO]") or line.startswith("[SUCCESS]"):
                self.output_box.insert("end", line + "\n", "succ")
            else:
                self.output_box.insert("end", line + "\n")
        else:
            self.output_box.insert("end", line + "\n")
        self.output_box.see("end")
        self.output_box.configure(state="disabled")

    def _set_output(self, txt: str):
        self.output_box.configure(state="normal")
        self.output_box.delete("0.0", "end")
        self.output_box.insert("0.0", txt)
        self.output_box.configure(state="disabled")

    # ----------------------------------------------------
    # Reports handling
    # ----------------------------------------------------
    def refresh_reports(self):
        rpt_dir = ROOT / "reports"
        vals = sorted((f.name for f in rpt_dir.glob("*.txt")), reverse=True) if rpt_dir.is_dir() else []
        if not vals:
            vals = ["<no-reports>"]
        self.reports_menu.configure(values=vals)
        self.reports_var.set(vals[0] if vals else "")
        write_log("Reports list refreshed.")

    def _show_report(self, name: str):
        if not name or name.startswith("<"):
            return
        path = ROOT / "reports" / name
        if not path.is_file():
            self._append_output(f"[ERROR] Report not found: {name}")
            return
        with path.open("r", encoding="utf-8") as f:
            txt = f.read()
        self._set_output(txt)

    def _open_selected_report(self):
        name = self.reports_var.get()
        if not name or name.startswith("<"):
            self._append_output("[WARN] No report selected.")
            return
        self._show_report(name)

    # ----------------------------------------------------
    def copy_output(self):
        self.output_box.configure(state="normal")
        txt = self.output_box.get("0.0", "end")
        self.output_box.configure(state="disabled")
        if copy_text(txt):
            self._append_output("[INFO] Output copied to clipboard.")
        else:
            self._append_output("[WARN] pyperclip not installed — cannot copy.")

    # ----------------------------------------------------
    # Job handling
    # ----------------------------------------------------
    def refresh_jobs(self):
        # Remove old widgets
        for w in self.job_widgets:
            try:
                w.destroy()
            except Exception:
                pass
        self.job_widgets.clear()
        self.jobs = discover_jobs()

        if not self.jobs:
            lbl = ctk.CTkLabel(
                self.jobs_container,
                text="No jobs found in jobs/ folder",
                fg_color=None,
            )
            lbl.pack(pady=8)
            self.job_widgets.append(lbl)
            return

        for j in self.jobs:
            frame = ctk.CTkFrame(self.jobs_container, height=48)
            frame.pack(fill="x", padx=6, pady=6)

            name = j.get("display") or j.get("module_name")
            lbl = ctk.CTkLabel(frame, text=name, anchor="w")
            lbl.pack(side="left", padx=8)

            if j.get("error"):
                err_btn = ctk.CTkButton(
                    frame,
                    text="Import error",
                    width=120,
                    fg_color="#FF6B6B",
                    command=lambda ex=j.get("exception"): self._enqueue_output(ex),
                )
                err_btn.pack(side="right", padx=6)
                self.job_widgets.append(frame)
                continue

            cb = j.get("callable")
            mod = j.get("module")
            if not cb or mod is None:
                btn = ctk.CTkButton(
                    frame, text="No entry", width=120, fg_color="#A9A9A9"
                )
                btn.pack(side="right", padx=6)
                self.job_widgets.append(frame)
                continue

            def run_job(mod=mod, fn=cb):
                def inner():
                    self._enqueue_output(f"[INFO] Starting {mod.__name__} (entry: {fn})")
                    result = call_job(mod, fn, self._enqueue_output)
                    if isinstance(result, str) and Path(result).is_file():
                        self._enqueue_output(f"[INFO] Loaded report: {Path(result).name}")
                        self.refresh_reports()
                threading.Thread(target=inner, daemon=True).start()

            run_btn = ctk.CTkButton(
                frame,
                text="Run",
                width=120,
                fg_color="#00C851",
                hover_color="#00E676",
                command=run_job,
            )
            run_btn.pack(side="right", padx=6)

            self.job_widgets.append(frame)

    # ----------------------------------------------------
    # Email handling
    # ----------------------------------------------------
    def send_latest_report(self):
        reports = sorted(
            (f.name for f in (ROOT / "reports").glob("*.txt")),
            reverse=True,
        )
        if not reports:
            self._enqueue_output("[WARN] No report to send.")
            return
        latest = ROOT / "reports" / reports[0]
        self._enqueue_output(f"[INFO] Sending latest report: {latest.name}")

        # --------------------------------------------------------------------
        # 1️⃣ Try custom jobs.email_job.send_report_email
        # --------------------------------------------------------------------
        try:
            email_mod = importlib.import_module("jobs.email_job")
            if hasattr(email_mod, "send_report_email"):
                threading.Thread(
                    target=email_mod.send_report_email,
                    args=(None, None, str(latest)),
                    daemon=True,
                ).start()
                self._enqueue_output(
                    "[INFO] Email send started (jobs.email_job.send_report_email)."
                )
                return
        except Exception as exc:
            self._enqueue_output(f"[WARN] jobs.email_job not usable: {exc}")

        # --------------------------------------------------------------------
        # 2️⃣ Fallback: yagmail (if available)
        # --------------------------------------------------------------------
        try:
            from settings.secrets import SMTP_USER, SMTP_APP_PASSWORD, EMAIL_TO
            import yagmail

            def send():
                try:
                    yag = yagmail.SMTP(user=SMTP_USER, password=SMTP_APP_PASSWORD)
                    subj = f"het Automations & Monitoring Dashboard – {latest.name}"
                    body = f"Automated report attached: {latest.name}"
                    yag.send(to=EMAIL_TO, subject=subj, contents=[body, str(latest)])
                    self._enqueue_output("[INFO] Email sent successfully (fallback).")
                except Exception as exc:
                    self._enqueue_output(f"[ERROR] Email fallback failed: {exc}")

            threading.Thread(target=send, daemon=True).start()
        except Exception as exc:
            self._enqueue_output(f"[ERROR] No email method available: {exc}")

# ----------------------------------------------------
# Main
# ----------------------------------------------------
if __name__ == "__main__":
    app = LaundryApp()
    app.mainloop()
