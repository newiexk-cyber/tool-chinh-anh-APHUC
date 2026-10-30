from __future__ import annotations
import re
import time
from pathlib import Path
from typing import Any, Optional
from src.utils import normalize_vn, get_logger

logger = get_logger("sheet_manager")

# Regex to extract spreadsheet ID from Google Sheet URLs
SPREADSHEET_ID_REGEX = re.compile(r"/spreadsheets/d/([a-zA-Z0-9-_]+)")


def extract_spreadsheet_id(url_or_id: str) -> str:
    """
    Extracts the Google Spreadsheet ID from either a full URL or a raw ID string.
    """
    clean_val = str(url_or_id).strip()
    match = SPREADSHEET_ID_REGEX.search(clean_val)
    if match:
        return match.group(1)
    return clean_val


def generate_mock_sheet_data() -> list[dict[str, Any]]:
    """
    Returns 5 realistic mock customer rows matching the exact 'THÁNG 10/2026' sheet layout.
    Provides rows with unassigned staff, assigned to 'PHÚC', and already 'DONE'.
    """
    return [
        {
            "row": 12,
            "stt": 1,
            "ten_khach": "Nguyễn Văn An",
            "goi": "Concept Cổ Điển",
            "col_g_selected": True,
            "sl_hinh_chon": 15,
            "trang_thai": "",
            "nhan_vien": "",
            "drive_link": "https://drive.google.com/drive/folders/1ABC_MOCK_FOLDER_AN_01",
            "local_status": "Chưa tải",
        },
        {
            "row": 15,
            "stt": 2,
            "ten_khach": "Trần Thị Mai",
            "goi": "Concept Nàng Thơ",
            "col_g_selected": True,
            "sl_hinh_chon": 20,
            "trang_thai": "",
            "nhan_vien": "PHÚC",
            "drive_link": "https://drive.google.com/drive/folders/1ABC_MOCK_FOLDER_MAI_02",
            "local_status": "Chưa tải",
        },
        {
            "row": 21,
            "stt": 3,
            "ten_khach": "Lê Hoàng Phúc",
            "goi": "Lookbook Thời Trang",
            "col_g_selected": False,
            "sl_hinh_chon": 10,
            "trang_thai": "",
            "nhan_vien": "",
            "drive_link": "https://drive.google.com/drive/folders/1ABC_MOCK_FOLDER_PHUC_03",
            "local_status": "Chưa tải",
        },
        {
            "row": 28,
            "stt": 4,
            "ten_khach": "Phạm Thùy Linh",
            "goi": "Ảnh Thẻ & Profile VIP",
            "col_g_selected": True,
            "sl_hinh_chon": 5,
            "trang_thai": "DONE",
            "nhan_vien": "PHÚC",
            "drive_link": "https://drive.google.com/drive/folders/1ABC_MOCK_FOLDER_LINH_04",
            "local_status": "Đã xong",
        },
        {
            "row": 35,
            "stt": 5,
            "ten_khach": "Võ Minh Khôi",
            "goi": "Concept Sinh Nhật Studio",
            "col_g_selected": True,
            "sl_hinh_chon": 25,
            "trang_thai": "",
            "nhan_vien": "NAM",
            "drive_link": "https://drive.google.com/drive/folders/1ABC_MOCK_FOLDER_KHOI_05",
            "local_status": "Chưa tải",
        },
    ]


def filter_eligible_jobs(
    rows: list[dict[str, Any]], staff_name: str = "PHÚC", require_drive_link: bool = True
) -> list[dict[str, Any]]:
    """
    Lọc danh sách khách hàng chính xác theo yêu cầu nghiệp vụ:
    1. Thuộc tháng hiện tại (THÁNG 10/2026)
    2. Mục ĐÃ CHỌN: Có số lượng hình (Col H > 0) hoặc Trạng thái (Col I) là 'ĐÃ CHỌN' / 'ĐÃ CHỈNH'
    3. Trạng thái (Col I) KHÔNG PHẢI LÀ 'DONE'
    4. Bắt buộc có link Drive để tải ảnh (nếu require_drive_link=True)
    5. Nhân viên (Col O) thỏa mãn 1 trong 2 điều kiện:
       - Đã gán cho staff_name ('PHÚC', không phân biệt hoa thường và dấu)
       - HOẶC đang trống (chưa có nhân viên nào nhận)
    """
    from src.utils import strip_accents

    target_staff = strip_accents(staff_name)
    eligible = []

    for r in rows:
        name = strip_accents(r.get("ten_khach", ""))
        if not name or name in ["TEN KHACH", "OFF", "-", "MAU"]:
            continue

        status = strip_accents(r.get("trang_thai", ""))
        # BỎ QUA nếu đã hoàn tất (DONE) hoặc đã chỉnh xong (ĐÃ CHỈNH):
        if "DONE" in status or "CHINH" in status:
            continue

        link = str(r.get("drive_link", "")).strip()
        if require_drive_link and not link:
            continue

        sl_hinh = int(r.get("sl_hinh_chon", 0) or 0)
        is_selected = (
            (sl_hinh > 0)
            or ("CHON" in status)
        )

        if not is_selected:
            continue

        cur_staff = strip_accents(r.get("nhan_vien", ""))
        if cur_staff == target_staff or cur_staff == "":
            eligible.append(r)

    return eligible


def parse_sheet_response(response_data: dict, start_row: int = 1) -> list[dict[str, Any]]:
    """
    Parses Google Sheets API v4 raw rowData response.
    Specifically extracts formatted text and the hidden hyperlink under Column C (TÊN KHÁCH).
    """
    rows_out: list[dict[str, Any]] = []
    sheets = response_data.get("sheets", [])
    if not sheets:
        return rows_out

    data_blocks = sheets[0].get("data", [])
    if not data_blocks:
        return rows_out

    row_data = data_blocks[0].get("rowData", [])
    block_start = data_blocks[0].get("startRow", 0)

    for idx, row_item in enumerate(row_data):
        current_sheet_row = block_start + idx + 1  # 1-indexed Excel row
        values = row_item.get("values", [])
        if not values or len(values) < 3:
            continue

        def get_val(col_idx: int) -> str:
            if col_idx < len(values):
                cell = values[col_idx]
                return str(cell.get("formattedValue", "")).strip()
            return ""

        def get_hyperlink(col_idx: int) -> str:
            if col_idx < len(values):
                cell = values[col_idx]
                return str(cell.get("hyperlink", "")).strip()
            return ""

        # Column indices:
        # Col B (Index 1): STT
        # Col C (Index 2): TÊN KHÁCH (Text + Hyperlink)
        # Col D (Index 3): GÓI
        # Col G (Index 6): CHECKBOX (TRUE/FALSE)
        # Col H (Index 7): SL HÌNH CHỌN
        # Col I (Index 8): TRẠNG THÁI
        # Col O (Index 14): NHÂN VIÊN
        raw_stt = get_val(1)
        ten_khach = get_val(2)
        drive_link = get_hyperlink(2)
        goi = get_val(3)
        col_g_raw = get_val(6).upper()
        col_h_raw = get_val(7)
        trang_thai = get_val(8)
        nhan_vien = get_val(14)

        # Skip header or completely empty rows
        if not ten_khach or ten_khach.upper() in ["TÊN KHÁCH", "TEN KHACH"]:
            continue

        stt_num = 0
        try:
            stt_num = int(raw_stt)
        except ValueError:
            stt_num = idx

        sl_hinh = 0
        try:
            sl_hinh = int(col_h_raw)
        except ValueError:
            sl_hinh = 0

        col_g_bool = col_g_raw in ["TRUE", "1", "YES", "ĐÃ CHỌN", "X"]

        rows_out.append(
            {
                "row": current_sheet_row,
                "stt": stt_num,
                "ten_khach": normalize_vn(ten_khach),
                "goi": goi,
                "col_g_selected": col_g_bool,
                "sl_hinh_chon": sl_hinh,
                "trang_thai": normalize_vn(trang_thai),
                "nhan_vien": normalize_vn(nhan_vien),
                "drive_link": drive_link,
                "local_status": "Chưa tải",
            }
        )

    return rows_out


def get_spreadsheet_sheet_names(
    spreadsheet_id: str,
    credentials_path: Optional[Path | str] = None,
) -> list[str]:
    """
    Lấy danh sách tất cả các tab (sheets) từ Google Spreadsheet.
    Tự động xếp tab mới nhất lên đầu. Nếu không thể kết nối, fallback về danh sách các tháng gần nhất.
    """
    from datetime import datetime
    now = datetime.now()

    # Danh sách dự phòng theo lịch thực tế (từ tháng sau đến các tháng trước)
    fallback_tabs = []
    for offset in range(0, 12):
        m = (now.month - offset - 1) % 12 + 1
        y = now.year + ((now.month - offset - 1) // 12)
        tab_name = f"THÁNG {m:02d}/{y}"
        if tab_name not in fallback_tabs:
            fallback_tabs.append(tab_name)

    try:
        service = get_sheets_service(credentials_path)
        meta = service.spreadsheets().get(
            spreadsheetId=spreadsheet_id,
            fields="sheets(properties(title))",
        ).execute()
        sheet_titles = [
            s["properties"]["title"]
            for s in meta.get("sheets", [])
            if s.get("properties", {}).get("title")
        ]
        if sheet_titles:
            # Lọc các tab có chữ 'THÁNG'
            month_tabs = [t for t in sheet_titles if "THANG" in normalize_vn(t).upper()]
            other_tabs = [t for t in sheet_titles if t not in month_tabs]
            # Đảo ngược thứ tự để tab tháng tạo sau cùng (mới nhất) nằm lên đầu
            month_tabs.reverse()
            return month_tabs + other_tabs
    except Exception as e:
        logger.debug(f"Không thể lấy danh sách tab từ Google Sheet: {e}")

    return fallback_tabs


def get_sheets_service(credentials_path: Optional[Path | str] = None) -> Any:
    """
    Initializes and returns an authorized Google Sheets API v4 Resource service.
    """
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    if credentials_path is None:
        credentials_path = Path("config/credentials.json")
    else:
        credentials_path = Path(credentials_path)

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]

    # Hỗ trợ đọc từ Streamlit Secrets khi deploy lên Streamlit Community Cloud
    try:
        import streamlit as st
        if hasattr(st, "secrets") and "gcp_service_account" in st.secrets:
            creds = service_account.Credentials.from_service_account_info(
                dict(st.secrets["gcp_service_account"]), scopes=scopes
            )
            return build("sheets", "v4", credentials=creds)
    except Exception:
        pass

    if not credentials_path.exists():
        raise FileNotFoundError(f"Không tìm thấy file credentials tại: {credentials_path.resolve()}")

    creds = service_account.Credentials.from_service_account_file(
        str(credentials_path), scopes=scopes
    )
    return build("sheets", "v4", credentials=creds)


def load_sheet_data(
    spreadsheet_id: str,
    sheet_name: str = "THÁNG 10/2026",
    credentials_path: Optional[Path | str] = None,
    mock_mode: bool = False,
    only_eligible: bool = False,
    staff_name: str = "PHÚC",
) -> list[dict[str, Any]]:
    """
    Fetches customer rows from Google Sheets or returns Mock Data.
    Uses fields="sheets.data.rowData.values(formattedValue,hyperlink)" to capture embedded Drive URLs.
    If only_eligible=True, automatically filters strictly for:
      - Đơn của staff_name chưa DONE
      - Hoặc đơn đã chọn nhưng chưa có nhân viên nào nhận
    """
    if mock_mode:
        logger.info("[MOCK_DATA] Sử dụng dữ liệu giả lập Google Sheet (5 khách hàng mẫu).")
        raw = generate_mock_sheet_data()
        return filter_eligible_jobs(raw, staff_name=staff_name) if only_eligible else raw

    cred_file = Path(credentials_path or "config/credentials.json")
    if not check_has_credentials(cred_file):
        logger.warning(
            f"Chưa có credentials tại '{cred_file}'. Tự động chuyển sang Mock Data."
        )
        raw = generate_mock_sheet_data()
        return filter_eligible_jobs(raw, staff_name=staff_name) if only_eligible else raw

    clean_id = extract_spreadsheet_id(spreadsheet_id)
    range_target = f"'{sheet_name}'!A1:O2000"
    max_retries = 2

    for attempt in range(max_retries + 1):
        try:
            service = get_sheets_service(cred_file)
            logger.info(f"Đang đọc dữ liệu từ Google Sheet {clean_id} [{range_target}] (Lần {attempt + 1})...")

            request = service.spreadsheets().get(
                spreadsheetId=clean_id,
                ranges=[range_target],
                fields="sheets.data.rowData.values(formattedValue,hyperlink)",
            )
            response = request.execute()
            parsed_rows = parse_sheet_response(response, start_row=1)
            logger.info(f"Đã đọc thành công {len(parsed_rows)} dòng dữ liệu từ Google Sheet.")
            if only_eligible:
                filtered = filter_eligible_jobs(parsed_rows, staff_name=staff_name)
                logger.info(f"Sau khi lọc đơn của {staff_name} & đơn trống: còn {len(filtered)} đơn cần xử lý.")
                return filtered
            return parsed_rows
        except Exception as e:
            if attempt < max_retries:
                logger.warning(f"Lỗi kết nối khi đọc Google Sheet {clean_id} ({e}). Đang thử lại sau 2 giây...")
                time.sleep(2)
            else:
                logger.error(f"Lỗi khi đọc Google Sheet {clean_id}: {e}")
                if mock_mode:
                    logger.info("Chế độ mock_mode=True: sử dụng dữ liệu giả lập fallback.")
                    raw = generate_mock_sheet_data()
                    return filter_eligible_jobs(raw, staff_name=staff_name) if only_eligible else raw
                # Chế độ sản xuất (kết nối thật): Tuyệt đối KHÔNG trả về dữ liệu giả lập
                # để tránh nhận nhầm đơn ảo và tránh ghi nhầm vào Sheet thật.
                return []
    return []


def assign_staff(
    spreadsheet_id: str,
    sheet_name: str,
    row_numbers: list[int],
    staff_name: str = "PHÚC",
    dry_run: bool = True,
    credentials_path: Optional[Path | str] = None,
) -> dict[str, Any]:
    """
    Assigns staff_name to Column O for the specified rows.
    If dry_run=True, strictly writes to log and does NOT touch the remote spreadsheet.
    """
    norm_staff = normalize_vn(staff_name)
    if dry_run:
        for r in row_numbers:
            logger.info(
                f"[DRY_RUN] Giả lập điền '{norm_staff}' vào ô O{r} trên Sheet '{sheet_name}'. Sheet gốc KHÔNG bị sửa đổi."
            )
        return {
            "success": True,
            "dry_run": True,
            "updated_rows": row_numbers,
            "message": f"[DRY_RUN] Đã giả lập gán '{norm_staff}' cho {len(row_numbers)} đơn.",
        }

    cred_file = Path(credentials_path or "config/credentials.json")
    if not check_has_credentials(cred_file):
        raise FileNotFoundError(f"Cần file {cred_file} để thực thi ghi dữ liệu thật!")

    try:
        service = get_sheets_service(cred_file)
        clean_id = extract_spreadsheet_id(spreadsheet_id)
        data_updates = [
            {"range": f"'{sheet_name}'!O{row_num}", "values": [[norm_staff]]}
            for row_num in row_numbers
        ]
        body = {"valueInputOption": "USER_ENTERED", "data": data_updates}
        logger.info(f"Đang ghi '{norm_staff}' vào {len(row_numbers)} ô Cột O trên Sheet thật...")
        res = (
            service.spreadsheets()
            .values()
            .batchUpdate(spreadsheetId=clean_id, body=body)
            .execute()
        )
        logger.info(f"Ghi thành công {res.get('totalUpdatedCells', len(row_numbers))} ô lên Google Sheet.")
        return {
            "success": True,
            "dry_run": False,
            "updated_rows": row_numbers,
            "message": f"Đã ghi '{norm_staff}' vào {len(row_numbers)} đơn trên Google Sheet.",
        }
    except Exception as e:
        logger.error(f"Lỗi khi ghi tên nhân viên lên Google Sheet: {e}")
        return {"success": False, "error": str(e)}


def assign_staff_in_memory(
    rows: list[dict[str, Any]], row_numbers: list[int], staff_name: str = "PHÚC"
) -> list[dict[str, Any]]:
    """
    Helper to update in-memory list of rows during DRY_RUN or Mock sessions.
    """
    norm_staff = normalize_vn(staff_name)
    updated = []
    for r in rows:
        row_copy = dict(r)
        if row_copy["row"] in row_numbers:
            row_copy["nhan_vien"] = norm_staff
        updated.append(row_copy)
    return updated


def mark_done(
    spreadsheet_id: str,
    sheet_name: str,
    row_number: int,
    dry_run: bool = True,
    credentials_path: Optional[Path | str] = None,
) -> bool:
    """
    Updates Column I of row_number to 'DONE'.
    Respects dry_run flag.
    """
    if dry_run:
        logger.info(
            f"[DRY_RUN] Giả lập cập nhật ô I{row_number} thành 'DONE' trên Sheet '{sheet_name}'."
        )
        return True

    cred_file = Path(credentials_path or "config/credentials.json")
    if not check_has_credentials(cred_file):
        logger.warning(f"Không có {cred_file}, bỏ qua cập nhật DONE trên Sheet.")
        return False

    try:
        service = get_sheets_service(cred_file)
        clean_id = extract_spreadsheet_id(spreadsheet_id)
        range_target = f"'{sheet_name}'!I{row_number}"
        body = {"values": [["DONE"]]}
        service.spreadsheets().values().update(
            spreadsheetId=clean_id,
            range=range_target,
            valueInputOption="USER_ENTERED",
            body=body,
        ).execute()
        logger.info(f"Đã cập nhật ô I{row_number} thành 'DONE' trên Google Sheet.")
        return True
    except Exception as e:
        logger.error(f"Lỗi khi cập nhật DONE ô I{row_number}: {e}")
        return False


def mark_done_in_memory(rows: list[dict[str, Any]], row_number: int) -> list[dict[str, Any]]:
    """
    Helper to update in-memory list for mark_done during DRY_RUN / Mock sessions.
    """
    updated = []
    for r in rows:
        row_copy = dict(r)
        if row_copy["row"] == row_number:
            row_copy["trang_thai"] = "DONE"
            row_copy["local_status"] = "Đã xong"
        updated.append(row_copy)
    return updated
