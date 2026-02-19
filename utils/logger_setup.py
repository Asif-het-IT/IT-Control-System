import logging
import sys

logger = logging.getLogger("het_logger")
logger.setLevel(logging.INFO)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)

formatter = logging.Formatter("[%(levelname)s %(asctime)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
console_handler.setFormatter(formatter)

if not logger.handlers:
    logger.addHandler(console_handler)

console_handler.flush = sys.stdout.flush
