from __future__ import annotations
from pathlib import Path
from src.drive_manager import generate_mock_photos
from src.magimir_controller import (
    is_magimir_running,
    simulate_retouch_photos,
    process_customer_photos,
    count_valid_photos,
)


def test_is_magimir_running():
    # If Magimir is not currently installed or open, it should safely return False
    running = is_magimir_running()
    assert isinstance(running, bool)


def test_count_valid_photos(tmp_path: Path):
    photo_dir = tmp_path / "test_photos"
    photo_dir.mkdir()

    # Empty
    assert count_valid_photos(photo_dir) == 0

    # Add 3 valid jpgs
    generate_mock_photos(photo_dir, count=3, customer_name="Count Test")
    assert count_valid_photos(photo_dir) == 3

    # Add a .tmp file and a 0-byte file (should be excluded)
    (photo_dir / "temp_file.tmp").write_text("temporary")
    (photo_dir / "zero_byte.jpg").write_bytes(b"")

    assert count_valid_photos(photo_dir) == 3


def test_simulate_retouch_photos(tmp_path: Path):
    chon_dir = tmp_path / "CHON"
    done_dir = tmp_path / "DONE"
    generate_mock_photos(chon_dir, count=4, customer_name="Retouch Sim")

    progress_events = []

    def callback(current, total, filename):
        progress_events.append((current, total, filename))

    success = simulate_retouch_photos(
        chon_dir=chon_dir,
        done_dir=done_dir,
        preset_name="Default_Preset",
        delay_per_photo=0.01,
        progress_callback=callback,
    )

    assert success is True
    assert count_valid_photos(done_dir) == 4
    assert len(progress_events) == 4


def test_process_customer_photos_with_simulation_fallback(tmp_path: Path):
    chon_dir = tmp_path / "CHON"
    done_dir = tmp_path / "DONE"
    generate_mock_photos(chon_dir, count=3, customer_name="Fallback Test")

    success = process_customer_photos(
        chon_dir=chon_dir,
        done_dir=done_dir,
        preset_name="Vibrant_Studio",
        simulate_if_missing=True,
    )

    assert success is True
    assert count_valid_photos(done_dir) == 3


def test_templates_exist():
    from src.magimir_controller import TEMPLATES_DIR, find_on_screen
    assert TEMPLATES_DIR.exists()
    assert (TEMPLATES_DIR / "card1.png").exists()
    assert (TEMPLATES_DIR / "tpl_export_top.png").exists()
    assert (TEMPLATES_DIR / "tpl_blue_export_btn.png").exists()

    # Searching for non-existent template returns None safely
    res = find_on_screen("non_existent_template.png")
    assert res is None
