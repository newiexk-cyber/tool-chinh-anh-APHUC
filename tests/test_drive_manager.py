from __future__ import annotations
from pathlib import Path
from src.drive_manager import (
    extract_drive_id,
    generate_mock_photos,
    download_chon_folder,
    upload_done_folder,
    normalize_photo_code,
    match_photo_code,
    find_chon_folder_recursive,
    auto_select_and_organize_drive,
)


def test_extract_drive_id():
    url1 = "https://drive.google.com/drive/folders/1ABC123_xyz-9876543210abcdefg"
    assert extract_drive_id(url1) == "1ABC123_xyz-9876543210abcdefg"

    url2 = "https://drive.google.com/drive/u/0/folders/1Sv3pxheEfamWKTSY96vwzQOi8bXK_lqJ"
    assert extract_drive_id(url2) == "1Sv3pxheEfamWKTSY96vwzQOi8bXK_lqJ"

    raw_id = "1ABC123_xyz-9876543210abcdefg"
    assert extract_drive_id(raw_id) == "1ABC123_xyz-9876543210abcdefg"

    empty_url = ""
    assert extract_drive_id(empty_url) == ""


def test_generate_mock_photos(tmp_path: Path):
    target_dir = tmp_path / "CHON"
    photos = generate_mock_photos(target_dir, count=5, customer_name="Test Customer")

    assert len(photos) == 5
    for p in photos:
        assert p.exists()
        assert p.suffix.lower() == ".jpg"
        assert p.stat().st_size > 0


def test_download_chon_folder_mock_fallback(tmp_path: Path):
    target_dir = tmp_path / "workspace" / "12_Nguyen_Van_An" / "CHON"
    progress_calls = []

    def callback(current, total, filename):
        progress_calls.append((current, total, filename))

    files = download_chon_folder(
        customer_folder_id="1ABC_MOCK_FOLDER",
        local_chon_dir=target_dir,
        dry_run=True,
        force_mock=True,
        progress_callback=callback,
    )

    assert len(files) == 5
    assert len(progress_calls) == 5
    assert all(f.exists() for f in files)


def test_upload_done_folder_dry_run(tmp_path: Path):
    done_dir = tmp_path / "DONE"
    generate_mock_photos(done_dir, count=3, customer_name="Test Finished")

    uploaded = upload_done_folder(
        customer_folder_id="1ABC_CUSTOMER_FOLDER",
        local_done_dir=done_dir,
        dry_run=True,
    )

    assert len(uploaded) == 3


def test_normalize_photo_code():
    assert normalize_photo_code("0005") == "5"
    assert normalize_photo_code("5") == "5"
    assert normalize_photo_code("IMG_0123") == "123"
    assert normalize_photo_code("DSC_0045.JPG") == "45"
    assert normalize_photo_code("   789   ") == "789"
    assert normalize_photo_code("nonumeric") == "nonumeric"


def test_match_photo_code():
    targets = ["5", "12", "0123", "IMG_456"]
    assert match_photo_code("IMG_0005.jpg", targets) is True
    assert match_photo_code("DSC_0012.cr2", targets) is True
    assert match_photo_code("123.png", targets) is True
    assert match_photo_code("IMG_456.arw", targets) is True
    assert match_photo_code("IMG_9999.jpg", targets) is False


def test_find_chon_folder_recursive():
    class MockFiles:
        def __init__(self, folder_tree):
            self.tree = folder_tree

        def get(self, fileId, **kwargs):
            class Request:
                def __init__(self, data):
                    self.data = data
                def execute(self):
                    return self.data
            return Request(self.tree.get(fileId, {"id": fileId, "name": "Unknown"}))

        def list(self, q="", **kwargs):
            class Request:
                def __init__(self, items):
                    self.items = items
                def execute(self):
                    return {"files": self.items}
            # Parse parent from q
            import re
            m = re.search(r"'([^']+)' in parents", q)
            parent = m.group(1) if m else ""
            children = [
                {"id": fid, "name": f["name"]}
                for fid, f in self.tree.items()
                if f.get("parent") == parent
            ]
            return Request(children)

    class MockDriveService:
        def __init__(self, folder_tree):
            self._files = MockFiles(folder_tree)
        def files(self):
            return self._files

    tree = {
        "root": {"id": "root", "name": "Folder Khách An", "parent": None},
        "sub1": {"id": "sub1", "name": "25.10 Studio", "parent": "root"},
        "sub2": {"id": "sub2", "name": "Ảnh Gốc", "parent": "sub1"},
        "sub_chon": {"id": "sub_chon", "name": "Khách ĐÃ CHỌN 15 hình", "parent": "sub2"},
    }

    mock_service = MockDriveService(tree)
    found = find_chon_folder_recursive(mock_service, "root", max_depth=4)
    from src.utils import strip_accents
    assert found is not None
    assert found["id"] == "sub_chon"
    assert "CHON" in strip_accents(found["name"])

    # Case: root folder itself is CHON
    tree_self = {"chon_root": {"id": "chon_root", "name": "CHỌN", "parent": None}}
    found_self = find_chon_folder_recursive(MockDriveService(tree_self), "chon_root")
    assert found_self is not None
    assert found_self["id"] == "chon_root"

    # Case: No matching folder
    tree_empty = {"root2": {"id": "root2", "name": "Album Cuoi", "parent": None}}
    assert find_chon_folder_recursive(MockDriveService(tree_empty), "root2") is None


def test_download_chon_folder_with_customer_name(tmp_path: Path):
    ws = tmp_path / "workspace"
    files = download_chon_folder(
        customer_folder_id="1ABC_MOCK",
        local_chon_dir=ws,
        customer_name="Trần Thị Mai",
        force_mock=True,
    )
    assert len(files) == 5
    assert files[0].parent.name == "Tran_Thi_Mai_DA_CHON"
    assert files[0].parent.exists()


def test_auto_select_and_organize_drive_mock():
    res = auto_select_and_organize_drive(
        customer_folder_id="1ABC_MOCK_FOLDER",
        photo_codes=["1", "3", "99"],
        target_folder_name="ĐÃ CHỌN",
        force_mock=True,
    )
    assert res["success"] is True
    assert len(res["matched_files"]) == 2
    assert "99" in res["unmatched_codes"]
    assert res["target_folder_name"] == "ĐÃ CHỌN"




