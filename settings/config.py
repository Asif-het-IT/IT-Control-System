# settings/config.py

from pathlib import Path

# ---------- PATHS ----------
BASE_DIR = Path(__file__).parent.parent

# NAS paths
AFRICA_BASE = Path(r"\\het-nas\Tally-Africa\T-Current\Africa")
AFRICA_FOLDERS = ["99924", "20231", "40031", "60031"]

TALLY_BASE = Path(r"\\het-nas\Tally-Africa")
TALLY_MAP = {
    "T-Kano": "Ambariyya - Kano",
    "T-BukShop": "Noor - BukShop",
    "T-Abuja": "Fazal - Abuja",
    "T-Lagos": "Dua - Lagos"
}

LAUNDRY_NAS_BASE = Path(r"\\het-NAS\G-SSS300")
LAUNDRY_BRANCHES = [
    {
        "Key": "BR1-Qusais-SB",
        "BackupPath": Path("Cloud/1 - SSS300 - New SQL/Backup"),
        "ExcelPath": Path("Cloud/1 - SSS300 - New SQL/ExportsToExcel"),
        "Friendly": "BR1 Qusais-SB"
    },
    {
        "Key": "BR2-DMP",
        "BackupPath": Path("Cloud/SSS300 - SQL  - DMP/Backup"),
        "ExcelPath": Path("Cloud/SSS300 - SQL  - DMP/ExportsToExcel"),
        "Friendly": "BR2 DMP"
    },
    {
        "Key": "BR3-CB",
        "BackupPath": Path("Cloud/ABRStarTouch/Backup"),
        "ExcelPath": Path("Cloud/ABRStarTouch/ExportsToExcel"),
        "Friendly": "BR3 CB"
    },
    {
        "Key": "BR4-JVC",
        "BackupPath": Path("Cloud/SSS300 Laundry - JVC - SQL/Backup"),
        "ExcelPath": Path("Cloud/SSS300 Laundry - JVC - SQL/ExportsToExcel"),
        "Friendly": "BR4 JVC"
    },
    {
        "Key": "BR5-DSO",
        "BackupPath": Path("Cloud/SSS300 - DSO - SQL/Backup"),
        "ExcelPath": Path("Cloud/SSS300 - DSO - SQL/ExportsToExcel"),
        "Friendly": "BR5 DSO"
    },
    {
        "Key": "BR6-BH",
        "BackupPath": Path("Cloud/SSS300 - BH - SQL/Backup"),
        "ExcelPath": Path("Cloud/SSS300 - BH - SQL/ExportsToExcel"),
        "Friendly": "BR6 BH"
    }
]

# Qsync path
QSYNC_EXE_PATH = Path(r"C:\Program Files (x86)\QNAP\Qsync\Qsync.exe")

# Dedup sync paths
DEDUP_SOURCE = Path(r"E:\SSS300 - Backup - All Outlets")
DEDUP_DEST = Path(r"D:\01 - SSS 300 LAUNDRY - Exports To Excel")
SETTINGS_FOLDER = DEDUP_DEST / "Settings"
INDEX_FILE = SETTINGS_FOLDER / "copied_index.csv"
DEDUP_LOG_FILE = SETTINGS_FOLDER / "sync_log.txt"
DEDUP_ERROR_FILE = SETTINGS_FOLDER / "errors.log"
CONFIG_FILE = SETTINGS_FOLDER / "config.json"

# Backwards-compatible export path for older job files that expect BASE_EXPORT_PATH
BASE_EXPORT_PATH = DEDUP_DEST  # Path object; other modules can str() it

# Email
EMAIL_SUBJECT_TEMPLATE = "Combined Test Report - {date}"
