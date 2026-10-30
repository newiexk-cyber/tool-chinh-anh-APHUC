from __future__ import annotations
import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import unicodedata
from typing import Any

# Default log file location
DEFAULT_LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
DEFAULT_LOG_FILE = DEFAULT_LOG_DIR / "app.log"


def normalize_vn(text: Any) -> str:
    """
    Normalizes Vietnamese text to Unicode NFC and strips surrounding whitespace.
    Crucial for handling differences between macOS (NFD) and Windows (NFC)
    when matching folder names like 'CHỌN', staff names like 'PHÚC', and 'DONE'.
    """
    if text is None:
        return ""
    str_val = str(text)
    if not str_val:
        return ""
    return unicodedata.normalize("NFC", str_val).strip()


def strip_accents(text: Any) -> str:
    """
    Strips Vietnamese diacritics and converts to uppercase for flexible, bulletproof matching.
    Example: 'PHÚC' -> 'PHUC', 'ĐÃ CHỌN' -> 'DA CHON'
    """
    if not text:
        return ""
    # Convert 'Đ'/'đ' manually first
    s = str(text).replace("Đ", "D").replace("đ", "d")
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).upper().strip()


def get_platform() -> str:
    """
    Identifies the underlying operating system platform.
    Returns:
        'windows' for Windows (win32)
        'darwin' for macOS (Apple Silicon / Intel)
        'other' for Linux/others
    """
    if sys.platform == "win32":
        return "windows"
    elif sys.platform == "darwin":
        return "darwin"
    return "other"


def setup_logging(log_file: Path | str | None = None) -> None:
    """
    Configures application-wide logging with:
    1. Rotating File Handler (encoding='utf-8', 5MB per file, 3 backups)
    2. Stream Handler (Console stdout)
    """
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    if log_file is None:
        target_path = DEFAULT_LOG_FILE
    else:
        target_path = Path(log_file)

    target_path.parent.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Avoid duplicate handlers if setup_logging is called multiple times
    if not any(isinstance(h, RotatingFileHandler) for h in root_logger.handlers):
        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        # File handler
        file_handler = RotatingFileHandler(
            target_path, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.INFO)
        root_logger.addHandler(file_handler)

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logging.INFO)
        root_logger.addHandler(console_handler)


def get_logger(name: str = "app") -> logging.Logger:
    """
    Retrieves or creates a named logger instance.
    """
    return logging.getLogger(name)


def read_latest_logs(max_lines: int = 80, log_file: Path | str | None = None) -> list[str]:
    """
    Reads the latest N lines from the log file. Useful for displaying in the Streamlit UI.
    """
    if log_file is None:
        target_path = DEFAULT_LOG_FILE
    else:
        target_path = Path(log_file)

    if not target_path.exists():
        return ["Chưa có dữ liệu log."]

    try:
        with open(target_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
            return [line.rstrip() for line in lines[-max_lines:]]
    except Exception as e:
        return [f"Không thể đọc log: {e}"]
