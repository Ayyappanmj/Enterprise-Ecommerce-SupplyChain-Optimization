"""Centralized logging configuration used by every ETL module."""
import logging
import os

LOG_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "logs"
)
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "etl.log")


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:  # avoid duplicate handlers on repeated calls
        return logger

    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(fmt)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(fmt)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger
