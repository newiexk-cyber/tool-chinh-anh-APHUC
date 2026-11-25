from __future__ import annotations
from src.auto_claim_bot import is_claimable_row


def test_claimable_da_chon_unassigned():
    row = {
        "row": 10,
        "ten_khach": "Ngọc Trinh",
        "sl_hinh_chon": 10,
        "trang_thai": "ĐÃ CHỌN",
        "nhan_vien": "",
        "drive_link": "https://drive.google.com/drive/folders/abc",
    }
    assert is_claimable_row(row) is True


def test_claimable_da_chinh_unassigned_with_and_without_link():
    row_with_link = {
        "row": 11,
        "ten_khach": "Lam Peihua",
        "sl_hinh_chon": 10,
        "trang_thai": "ĐÃ CHỈNH",
        "nhan_vien": "",
        "drive_link": "https://drive.google.com/drive/folders/abc",
    }
    row_without_link = {
        "row": 12,
        "ten_khach": "Duyen Nhat Ha",
        "sl_hinh_chon": 5,
        "trang_thai": "ĐÃ CHỈNH",
        "nhan_vien": "",
        "drive_link": "",
    }
    assert is_claimable_row(row_with_link) is True
    assert is_claimable_row(row_without_link) is True


def test_claimable_any_other_non_done_status_or_sl_positive():
    row_custom_status = {
        "row": 13,
        "ten_khach": "Thanh Tùng",
        "sl_hinh_chon": 0,
        "trang_thai": "CHỜ CHỈNH GẤP",
        "nhan_vien": "",
        "drive_link": "",
    }
    row_sl_only = {
        "row": 14,
        "ten_khach": "Mai Phương",
        "sl_hinh_chon": 8,
        "trang_thai": "",
        "nhan_vien": "",
        "drive_link": "",
    }
    assert is_claimable_row(row_custom_status) is True
    assert is_claimable_row(row_sl_only) is True


def test_not_claimable_when_assigned_or_done_or_unselected_or_invalid_name():
    # Already assigned to someone else
    assert is_claimable_row({
        "ten_khach": "Mỹ Duyên",
        "sl_hinh_chon": 5,
        "trang_thai": "ĐÃ CHỈNH",
        "nhan_vien": "CHÍ",
    }) is False

    # Already DONE
    assert is_claimable_row({
        "ten_khach": "Ly Na",
        "sl_hinh_chon": 5,
        "trang_thai": "DONE",
        "nhan_vien": "",
    }) is False

    # Not yet selected (SL=0 and empty status)
    assert is_claimable_row({
        "ten_khach": "Bích Hạnh Đỗ",
        "sl_hinh_chon": 0,
        "trang_thai": "",
        "nhan_vien": "",
        "drive_link": "https://drive.google.com/drive/folders/abc",
    }) is False

    # Non-customer rows
    for fake_name in ["", "OFF", "0FF", "MẪU", "mẫu 2", "-", "TÊN KHÁCH"]:
        assert is_claimable_row({
            "ten_khach": fake_name,
            "sl_hinh_chon": 5,
            "trang_thai": "ĐÃ CHỌN",
            "nhan_vien": "",
        }) is False
