# app/jobs/nas_status_job.py
"""
NAS Status monitoring job for Tally and Laundry systems.
"""
import os
import json
import hashlib
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from app.core.base_job import BaseJob, JobResult, JobStatus
from app.services.email_service import send_report_email
from app.services.network_service import get_network_service
from app.services.file_service import get_file_service
from app.infrastructure.logger import get_logger

logger = get_logger("nas_status")


class NasStatusJob(BaseJob):
    """
    Job for monitoring NAS status including Tally files and Laundry backups.
    """

    # Valid Tally file prefixes
    VALID_PREFIXES = (
        "TranMgr", "Manager", "LinkMgr", "TranInf",
        "CmpSave", "Company", "AddlCmp", "SumTran"
    )

    # Branch name mappings
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

    def __init__(self, name: str, config: Dict[str, Any], branch_id: str = "default"):
        super().__init__(name, config, branch_id)
        self.network_service = get_network_service()
        self.file_service = get_file_service()

        # Job-specific config
        self.nas_base = Path(config.get('nas_base', r"\\het-nas\Tally-Africa"))
        self.laundry_base = Path(config.get('laundry_base', r"\\het-NAS\G-SSS300"))
        self.state_file = config.get('state_file')
        self.report_file = config.get('report_file')

    def validate(self) -> bool:
        """Validate job prerequisites."""
        # Check network connectivity
        if not self.network_service.check_network_path(self.nas_base):
            self.logger.error(f"NAS path not accessible: {self.nas_base}")
            return False

        if not self.network_service.check_network_path(self.laundry_base):
            self.logger.error(f"Laundry NAS path not accessible: {self.laundry_base}")
            return False

        return True

    def run(self) -> JobResult:
        """Execute the NAS status monitoring."""
        try:
            self.update_progress("Scanning Tally directories", 10)
            tally_data = self._scan_tally_tree()

            self.update_progress("Checking Laundry backups", 50)
            laundry_data = self._check_laundry()

            self.update_progress("Building report", 80)
            html_report = self._build_html_report(tally_data, laundry_data)

            self.update_progress("Saving state", 90)
            self._save_state(tally_data, laundry_data)

            self.update_progress("Sending report", 95)
            success = self._send_report(html_report)

            if success:
                self.update_progress("Report sent successfully", 100)
                return JobResult(
                    success=True,
                    data={
                        'tally_branches': len(tally_data),
                        'laundry_branches': len(laundry_data),
                        'report_sent': True
                    }
                )
            else:
                return JobResult(
                    success=False,
                    error="Failed to send report",
                    data={
                        'tally_branches': len(tally_data),
                        'laundry_branches': len(laundry_data)
                    }
                )

        except Exception as e:
            self.logger.error(f"NAS status job failed: {e}", exc_info=True)
            return JobResult(success=False, error=str(e))

    def _scan_tally_tree(self) -> List[Dict[str, Any]]:
        """Scan Tally directory tree for status information."""
        rows = []

        try:
            for root, dirs, files in os.walk(self.nas_base):
                rel_path = os.path.relpath(root, self.nas_base)
                if rel_path == ".":
                    continue

                branch_code = os.path.basename(root)
                branch_name = self.BRANCH_NAME_MAP.get(branch_code, branch_code)

                # Find TranMgr files
                tranmgr_files = [
                    os.path.join(root, f) for f in files
                    if f.startswith("TranMgr") and f.endswith(".900")
                ]

                tranmgr_date = None
                if tranmgr_files:
                    latest_file = max(tranmgr_files, key=os.path.getmtime)
                    tranmgr_date = datetime.fromtimestamp(
                        os.path.getmtime(latest_file)
                    ).strftime("%d-%b-%Y")

                # Check for conflicted files
                conflicted_files = [
                    f for f in files
                    if "(Conflicted copy" in f and f.startswith(self.VALID_PREFIXES)
                ]

                conflicted_date = None
                conflicted_users = []
                if conflicted_files:
                    conflicted_dates = []
                    for cf in conflicted_files:
                        file_path = os.path.join(root, cf)
                        conflicted_dates.append(
                            datetime.fromtimestamp(os.path.getmtime(file_path)).strftime("%d-%b-%Y")
                        )
                        # Extract username from conflicted copy filename
                        match = re.search(r'Conflicted copy.*by (.+)\.900', cf)
                        if match:
                            conflicted_users.append(match.group(1))

                    conflicted_date = max(conflicted_dates) if conflicted_dates else None

                rows.append({
                    "code": branch_code,
                    "name": branch_name,
                    "tranmgr_date": tranmgr_date or "MISSING",
                    "tranmgr_status": "OK" if tranmgr_date else "MISSING",
                    "conflicted": "YES" if conflicted_date else "NO",
                    "conflicted_date": conflicted_date or "—",
                    "conflicted_by": ", ".join(set(conflicted_users)) if conflicted_users else "—",
                    "sha256": ""  # Will be computed later
                })

        except Exception as e:
            self.logger.error(f"Failed to scan Tally tree: {e}")
            raise

        # Sort by TranMgr Date descending (newest first)
        rows.sort(
            key=lambda x: datetime.strptime(x["tranmgr_date"], "%d-%b-%Y")
            if x["tranmgr_date"] != "MISSING"
            else datetime(1900, 1, 1),
            reverse=True
        )

        return rows

    def _check_laundry(self) -> Dict[str, Dict[str, Any]]:
        """Check Laundry backup and Excel export status."""
        laundry_branches = {
            "BR1-Qusais-SB": {
                "backup": self.laundry_base / "BR1-Qusais-SB" / "Cloud" / "1 - SSS300 - New SQL" / "Backup",
                "excel": self.laundry_base / "BR1-Qusais-SB" / "Cloud" / "1 - SSS300 - New SQL" / "ExportsToExcel",
            },
            "BR2-DMP": {
                "backup": self.laundry_base / "BR2-DMP" / "Cloud" / "SSS300 - SQL  - DMP" / "Backup",
                "excel": self.laundry_base / "BR2-DMP" / "Cloud" / "SSS300 - SQL  - DMP" / "ExportsToExcel",
            },
            "BR3-CB": {
                "backup": self.laundry_base / "BR3-CB" / "Cloud" / "ABRStarTouch" / "Backup",
                "excel": self.laundry_base / "BR3-CB" / "Cloud" / "ABRStarTouch" / "ExportsToExcel",
            },
            "BR4-JVC": {
                "backup": self.laundry_base / "BR4-JVC" / "Cloud" / "SSS300 Laundry - JVC - SQL" / "Backup",
                "excel": self.laundry_base / "BR4-JVC" / "Cloud" / "SSS300 Laundry - JVC - SQL" / "ExportsToExcel",
            },
            "BR5-DSO": {
                "backup": self.laundry_base / "BR5-DSO" / "Cloud" / "SSS300 - DSO - SQL" / "Backup",
                "excel": self.laundry_base / "BR5-DSO" / "Cloud" / "SSS300 - DSO - SQL" / "ExportsToExcel",
            },
            "BR6-BH": {
                "backup": self.laundry_base / "BR6-BH" / "Cloud" / "SSS300 - BH - SQL" / "Backup",
                "excel": self.laundry_base / "BR6-BH" / "Cloud" / "SSS300 - BH - SQL" / "ExportsToExcel",
            },
        }

        results = {}

        for branch, paths in laundry_branches.items():
            backup_info = self._get_latest_file_info(paths["backup"])
            excel_info = self._get_latest_file_info(paths["excel"])

            results[branch] = {
                "backup_date": backup_info[1] or "MISSING",
                "excel_name": backup_info[0] or "MISSING",
                "excel_date": excel_info[1] or "MISSING"
            }

        return results

    def _get_latest_file_info(self, directory: Path) -> Tuple[Optional[str], Optional[str]]:
        """Get information about the latest file in a directory."""
        try:
            if not directory.exists():
                return None, None

            files = [f for f in directory.iterdir() if f.is_file()]
            if not files:
                return None, None

            latest_file = max(files, key=lambda f: f.stat().st_mtime)
            latest_date = datetime.fromtimestamp(
                latest_file.stat().st_mtime
            ).strftime("%d-%b-%Y")

            return latest_file.name, latest_date

        except Exception as e:
            self.logger.warning(f"Error reading directory {directory}: {e}")
            return None, None

    def _build_html_report(self, tally_data: List[Dict], laundry_data: Dict) -> str:
        """Build HTML report from collected data."""
        today = datetime.now().strftime("%Y-%m-%d")

        # Compute SHA256 for each branch
        for branch in tally_data:
            record_str = json.dumps(branch, sort_keys=True).encode("utf-8")
            branch["sha256"] = hashlib.sha256(record_str).hexdigest()

        html = f"""
        <html>
        <body style="font-family:Calibri">
        <h3>Tally NAS + Laundry Combined Status Report</h3>
        <p>Date: {today}</p>

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

        for row in tally_data:
            color = "#f8d7da" if row["conflicted"] == "YES" else "#d4edda"
            html += f"""
            <tr>
                <td>{row['code']}</td>
                <td>{row['name']}</td>
                <td>{row['tranmgr_date']}</td>
                <td><b>{row['tranmgr_status']}</b></td>
                <td style="background:{color};font-weight:bold;">{row['conflicted']}</td>
                <td>{row['conflicted_date']}</td>
                <td>{row['conflicted_by']}</td>
            </tr>
            """

        html += """
        </table><br>
        <h4>Laundry Backup Status</h4>
        <table border="1" cellpadding="6" cellspacing="0">
        <tr><th>Outlet</th><th>Backup</th><th>Excel Name</th><th>Excel Date</th></tr>
        """

        for branch, data in laundry_data.items():
            color = "#d4edda"  # green
            if data["backup_date"] != data["excel_date"]:
                color = "#f8d7da"  # red

            html += f"""
            <tr style="background:{color}">
                <td>{branch}</td>
                <td>{data['backup_date']}</td>
                <td>{data['excel_name']}</td>
                <td>{data['excel_date']}</td>
            </tr>
            """

        html += """
        </table>
        <p style="font-size:12px;color:#555">
        HET IT Control System - Automated Report
        </p>
        </body>
        </html>
        """

        return html

    def _save_state(self, tally_data: List[Dict], laundry_data: Dict) -> None:
        """Save job state for historical tracking."""
        if not self.state_file:
            return

        try:
            state = {"history": {}}

            # Load existing state
            if self.state_file.exists():
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)

            # Add current data
            today = datetime.now().strftime("%Y-%m-%d")
            state["history"][today] = {
                "tally": tally_data,
                "laundry": laundry_data
            }

            # Save state
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2)

        except Exception as e:
            self.logger.error(f"Failed to save state: {e}")

    def _send_report(self, html_content: str) -> bool:
        """Send the HTML report via email."""
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            subject = f"Tally NAS & Laundry Combined Report - {today}"

            return send_report_email(
                subject=subject,
                body=html_content,
                html=True
            )

        except Exception as e:
            self.logger.error(f"Failed to send report: {e}")
            return False