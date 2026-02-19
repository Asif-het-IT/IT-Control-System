# app/jobs/speed_test_job.py
"""
Internet speed test job.
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
import matplotlib.pyplot as plt
import base64
from io import BytesIO

from app.core.base_job import BaseJob, JobResult
from app.services.email_service import send_report_email
from app.infrastructure.logger import get_logger

logger = get_logger("speed_test")


class SpeedTestJob(BaseJob):
    """
    Job for testing internet speed and generating trend reports.
    """

    def __init__(self, name: str, config: Dict[str, Any], branch_id: str = "default"):
        super().__init__(name, config, branch_id)

        # Job-specific config
        self.history_file = config.get('history_file')
        self.max_history = config.get('max_history', 7)  # Keep last 7 runs

    def validate(self) -> bool:
        """Validate job prerequisites."""
        try:
            import speedtest
            return True
        except ImportError:
            self.logger.error("speedtest-cli not installed")
            return False

    def run(self) -> JobResult:
        """Execute internet speed test."""
        try:
            self.update_progress("Initializing speed test", 10)

            import speedtest
            st = speedtest.Speedtest()

            self.update_progress("Finding best server", 30)
            st.get_best_server()

            self.update_progress("Testing download speed", 50)
            download = st.download() / 1_000_000  # Mbps

            self.update_progress("Testing upload speed", 70)
            upload = st.upload() / 1_000_000

            ping = st.results.ping

            result = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "download": round(download, 2),
                "upload": round(upload, 2),
                "ping": round(ping, 1)
            }

            self.update_progress("Updating history", 80)
            self._update_history(result)

            self.update_progress("Generating chart", 90)
            chart_data = self._generate_chart()

            self.update_progress("Sending report", 95)
            self._send_report(result, chart_data)

            self.update_progress("Speed test completed", 100)

            return JobResult(
                success=True,
                data=result
            )

        except Exception as e:
            self.logger.error(f"Speed test failed: {e}", exc_info=True)
            return JobResult(success=False, error=str(e))

    def _update_history(self, result: Dict[str, Any]) -> None:
        """Update speed test history."""
        if not self.history_file:
            return

        try:
            history = []

            # Load existing history
            if self.history_file.exists():
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)

            # Add new result
            history.append(result)

            # Keep only recent results
            history = history[-self.max_history:]

            # Save history
            self.history_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, indent=2)

        except Exception as e:
            self.logger.error(f"Failed to update history: {e}")

    def _generate_chart(self) -> Optional[str]:
        """Generate trend chart and return as base64."""
        if not self.history_file or not self.history_file.exists():
            return None

        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)

            if len(history) < 2:
                return None

            # Prepare data
            downloads = [r["download"] for r in history]
            uploads = [r["upload"] for r in history]
            pings = [r["ping"] for r in history]
            timestamps = [r["timestamp"].split()[1] for r in history]  # Time only

            # Create chart
            fig, ax = plt.subplots(figsize=(4, 1))

            ax.plot(downloads, color='green', label='DL', marker='o')
            ax.plot(uploads, color='blue', label='UL', marker='o')
            ax.plot(pings, color='red', label='Ping', marker='o')

            ax.set_xticks(range(len(history)))
            ax.set_xticklabels(timestamps, rotation=45, fontsize=8)
            ax.set_yticklabels([])
            ax.set_ylabel("")
            ax.legend(loc='upper right', fontsize=6)

            plt.tight_layout()

            # Convert to base64
            buf = BytesIO()
            plt.savefig(buf, format='png')
            buf.seek(0)
            chart_base64 = base64.b64encode(buf.read()).decode('utf-8')
            buf.close()
            plt.close(fig)

            return chart_base64

        except Exception as e:
            self.logger.error(f"Failed to generate chart: {e}")
            return None

    def _send_report(self, result: Dict[str, Any], chart_base64: Optional[str]) -> bool:
        """Send speed test report via email."""
        try:
            html_body = f"""
            <html><body>
            <h3>Internet Speed Test</h3>
            <p><b>Download:</b> {result['download']} Mbps |
               <b>Upload:</b> {result['upload']} Mbps |
               <b>Ping:</b> {result['ping']} ms</p>
            """

            if chart_base64:
                html_body += f"""
                <p>Trend last {self.max_history} runs:</p>
                <img src="data:image/png;base64,{chart_base64}" />
                """

            html_body += "</body></html>"

            subject = f"Internet Speed Test - {result['timestamp']}"

            return send_report_email(
                subject=subject,
                body=html_body,
                html=True
            )

        except Exception as e:
            self.logger.error(f"Failed to send speed test report: {e}")
            return False