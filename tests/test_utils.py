from __future__ import annotations
import unicodedata
from pathlib import Path
from src.utils import normalize_vn, get_platform, setup_logging, get_logger


def test_normalize_vn_nfd_to_nfc():
    # Decomposed NFD string for "CHỌN"
    nfd_text = unicodedata.normalize("NFD", "CHỌN")
    # Must be normalized to precomposed NFC
    nfc_text = normalize_vn(nfd_text)
    assert nfc_text == "CHỌN"
    assert unicodedata.is_normalized("NFC", nfc_text)


def test_normalize_vn_phuc_and_whitespace():
    raw_text = "   PHÚC  \t\n"
    assert normalize_vn(raw_text) == "PHÚC"


def test_normalize_vn_empty_or_none():
    assert normalize_vn("") == ""
    assert normalize_vn(None) == ""
    assert normalize_vn(123) == "123"


def test_get_platform():
    plat = get_platform()
    assert plat in ["windows", "darwin", "other"]


def test_setup_logging(tmp_path: Path):
    log_file = tmp_path / "test_app.log"
    setup_logging(log_file)
    logger = get_logger("test_module")
    logger.info("Test log message for verification")

    assert log_file.exists()
    content = log_file.read_text(encoding="utf-8")
    assert "Test log message for verification" in content
