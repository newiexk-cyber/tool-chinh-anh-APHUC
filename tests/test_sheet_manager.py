from __future__ import annotations
from src.sheet_manager import (
    generate_mock_sheet_data,
    filter_eligible_jobs,
    parse_sheet_response,
    assign_staff_in_memory,
    mark_done_in_memory,
)


def test_generate_mock_sheet_data():
    data = generate_mock_sheet_data()
    assert len(data) == 5
    # Verify required keys
    for row in data:
        assert "row" in row
        assert "stt" in row
        assert "ten_khach" in row
        assert "goi" in row
        assert "col_g_selected" in row
        assert "sl_hinh_chon" in row
        assert "trang_thai" in row
        assert "nhan_vien" in row
        assert "drive_link" in row


def test_filter_eligible_jobs():
    mock_rows = [
        # Eligible: col_g is True, not done
        {
            "row": 2,
            "ten_khach": "Khách A",
            "drive_link": "https://drive.google.com/drive/folders/1234567890123456789012345",
            "col_g_selected": True,
            "sl_hinh_chon": 10,
            "trang_thai": "",
            "nhan_vien": "",
        },
        # Ineligible: already DONE
        {
            "row": 3,
            "ten_khach": "Khách B",
            "drive_link": "https://drive.google.com/drive/folders/1234567890123456789012345",
            "col_g_selected": True,
            "sl_hinh_chon": 5,
            "trang_thai": "DONE",
            "nhan_vien": "PHÚC",
        },
        # Eligible: col_g False but sl_hinh_chon > 0
        {
            "row": 4,
            "ten_khach": "Khách C",
            "drive_link": "https://drive.google.com/drive/folders/1234567890123456789012345",
            "col_g_selected": False,
            "sl_hinh_chon": 12,
            "trang_thai": "",
            "nhan_vien": "PHÚC",
        },
        # Ineligible: no drive link
        {
            "row": 5,
            "ten_khach": "Khách D",
            "drive_link": "",
            "col_g_selected": True,
            "sl_hinh_chon": 12,
            "trang_thai": "",
            "nhan_vien": "",
        },
    ]

    eligible = filter_eligible_jobs(mock_rows)
    assert len(eligible) == 2
    assert eligible[0]["row"] == 2
    assert eligible[1]["row"] == 4


def test_parse_sheet_response():
    # Simulates Google Sheets API response with rowData and hyperlinks in Col C (index 2)
    sample_response = {
        "sheets": [
            {
                "data": [
                    {
                        "startRow": 0,
                        "rowData": [
                            # Header row
                            {
                                "values": [
                                    {"formattedValue": ""},
                                    {"formattedValue": "STT"},
                                    {"formattedValue": "TÊN KHÁCH"},
                                    {"formattedValue": "GÓI"},
                                    {"formattedValue": ""},
                                    {"formattedValue": ""},
                                    {"formattedValue": "CHỌN"},
                                    {"formattedValue": "SL HÌNH"},
                                    {"formattedValue": "TRẠNG THÁI"},
                                ]
                            },
                            # Data row 2 (1-indexed row 2)
                            {
                                "values": [
                                    {"formattedValue": ""},
                                    {"formattedValue": "1"},  # B: STT
                                    {
                                        "formattedValue": "Nguyễn Văn An",
                                        "hyperlink": "https://drive.google.com/drive/folders/1AbCdEfGhIjKlMnOpQrStUvWxYz",
                                    },  # C: Name + Link
                                    {"formattedValue": "Concept Cổ Điển"},  # D: Gói
                                    {"formattedValue": ""},  # E
                                    {"formattedValue": ""},  # F
                                    {"formattedValue": "TRUE"},  # G: Checkbox
                                    {"formattedValue": "15"},  # H: SL hình
                                    {"formattedValue": ""},  # I: Trạng thái
                                    {"formattedValue": ""},  # J
                                    {"formattedValue": ""},  # K
                                    {"formattedValue": ""},  # L
                                    {"formattedValue": ""},  # M
                                    {"formattedValue": ""},  # N
                                    {"formattedValue": ""},  # O: Nhân viên
                                ]
                            },
                        ]
                    }
                ]
            }
        ]
    }

    parsed = parse_sheet_response(sample_response, start_row=1)
    assert len(parsed) == 1
    item = parsed[0]
    assert item["row"] == 2
    assert item["stt"] == 1
    assert item["ten_khach"] == "Nguyễn Văn An"
    assert item["drive_link"] == "https://drive.google.com/drive/folders/1AbCdEfGhIjKlMnOpQrStUvWxYz"
    assert item["col_g_selected"] is True
    assert item["sl_hinh_chon"] == 15
    assert item["nhan_vien"] == ""


def test_assign_staff_in_memory():
    rows = generate_mock_sheet_data()
    # Find row with empty staff
    unassigned_row = next(r["row"] for r in rows if not r["nhan_vien"])
    updated = assign_staff_in_memory(rows, [unassigned_row], staff_name="PHÚC")
    target = next(r for r in updated if r["row"] == unassigned_row)
    assert target["nhan_vien"] == "PHÚC"


def test_mark_done_in_memory():
    rows = generate_mock_sheet_data()
    row_num = rows[0]["row"]
    updated = mark_done_in_memory(rows, row_num)
    target = next(r for r in updated if r["row"] == row_num)
    assert target["trang_thai"] == "DONE"
