from __future__ import annotations
import io
import os
import re
import time
from pathlib import Path
from typing import Any, Callable, Optional
from PIL import Image, ImageDraw, ImageFont

from src.utils import normalize_vn, get_logger, check_has_credentials

logger = get_logger("drive_manager")

# Regex to extract 25+ character Google Drive file/folder ID
DRIVE_ID_REGEX = re.compile(r"([-\w]{25,})")

# Supported photo extensions
PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".cr2", ".arw", ".nef", ".dng"}


def extract_drive_id(url: str) -> str:
    """
    Extracts Google Drive folder ID from URL or returns raw ID.
    Supports /folders/{id}, /d/{id}, id={id}, and raw IDs.
    """
    if not url:
        return ""
    clean_val = str(url).strip()
    match = DRIVE_ID_REGEX.search(clean_val)
    if match:
        return match.group(1)
    return clean_val


def normalize_photo_code(code: str) -> str:
    """
    Chuẩn hóa mã ảnh để so khớp linh hoạt:
    - Loại bỏ khoảng trắng thừa
    - Tách lấy số nếu có (ví dụ: 'IMG_0123.jpg' -> '123', '0005' -> '5')
    - Nếu không có số, trả về chuỗi thường không có phần mở rộng
    """
    if not code:
        return ""
    clean = str(code).strip()
    # Loại bỏ đuôi file nếu có
    clean = re.sub(r"\.[a-zA-Z0-9]+$", "", clean)
    # Tìm chuỗi số cuối cùng hoặc duy nhất trong mã
    num_matches = re.findall(r"\d+", clean)
    if num_matches:
        # Lấy cụm số cuối cùng (thường là số thứ tự ảnh vd: DSC_0123 -> 123)
        num_str = num_matches[-1].lstrip("0")
        return num_str if num_str else "0"
    return clean.lower()


def match_photo_code(filename: str, target_codes: list[str], folder_name: str = "") -> bool:
    """
    Kiểm tra xem filename (hoặc thư mục chứa nó) có khớp với bất kỳ mã nào trong target_codes không.
    - So khớp chính xác số thứ tự (ví dụ '33' chỉ khớp 'A33', 'IMG_0033', KHÔNG khớp 'A133').
    - Hỗ trợ tiền tố chữ như 'A' trong 'A1' hoặc Thư mục 'A':
      Ví dụ 'A1' sẽ khớp file 'A1.jpg', hoặc file '1.jpg' nằm trong thư mục 'A'.
      Sẽ KHÔNG khớp nhầm với 'B1.jpg' hay file '1.jpg' trong thư mục 'B'.
    """
    if not filename or not target_codes:
        return False

    clean_f = re.sub(r"\.[a-zA-Z0-9]+$", "", str(filename)).strip()
    
    # Kiểm tra xem tên thư mục chứa ảnh có chữ cái A, B... không
    folder_prefix = ""
    if folder_name:
        f_match = re.search(r"\b([a-zA-Z])\b", folder_name)
        if f_match:
            folder_prefix = f_match.group(1).upper()

    nums_f = re.findall(r"\d+", clean_f)
    num_f = (nums_f[-1].lstrip("0") or "0") if nums_f else None
    
    # Trích xuất tiền tố chữ cái của file (vd: 'A1' -> 'A') hoặc lấy từ thư mục
    file_prefix_match = re.match(r"^([a-zA-Z]+)", clean_f)
    file_prefix = file_prefix_match.group(1).upper() if file_prefix_match else folder_prefix

    stem_f = clean_f.lower()

    for tc in target_codes:
        clean_tc = str(tc).strip()
        if not clean_tc:
            continue

        # Trích xuất tiền tố từ mã khách chọn (vd: 'A1' -> tiền tố 'A', số '1')
        tc_prefix_match = re.match(r"^([a-zA-Z]+)", clean_tc)
        tc_prefix = tc_prefix_match.group(1).upper() if tc_prefix_match else ""

        nums_tc = re.findall(r"\d+", clean_tc)
        num_tc = (nums_tc[-1].lstrip("0") or "0") if nums_tc else None

        # 1. Cả 2 đều có số: Phải trùng khớp chính xác số thứ tự
        if num_f is not None and num_tc is not None:
            if num_f == num_tc:
                # Nếu mã khách có chỉ định tiền tố (A hoặc B), kiểm tra khớp tiền tố
                if tc_prefix:
                    if file_prefix and file_prefix != tc_prefix:
                        continue  # Khác set (ví dụ khách chọn A1 mà file là B1)
                return True
            continue

        # 2. Không có số: So khớp tên file chính xác
        stem_tc = clean_tc.lower()
        if stem_tc == stem_f or (stem_tc in stem_f and len(stem_tc) >= 4):
            return True

    return False



def generate_mock_photos(
    local_dir: Path, count: int = 5, customer_name: str = "Khách Hàng"
) -> list[Path]:
    """
    Generates realistic sample .jpg photo files using Pillow when credentials.json
    is absent or mock mode is active, allowing end-to-end testing without remote access.
    """
    local_dir.mkdir(parents=True, exist_ok=True)
    generated_files: list[Path] = []

    colors = [
        (45, 52, 54),
        (9, 132, 227),
        (0, 184, 148),
        (108, 92, 231),
        (225, 112, 85),
    ]

    for i in range(1, count + 1):
        filename = f"IMG_{i:04d}_CHON.jpg"
        file_path = local_dir / filename

        # Create 800x600 test image
        bg_color = colors[(i - 1) % len(colors)]
        img = Image.new("RGB", (800, 600), color=bg_color)
        draw = ImageDraw.Draw(img)

        # Draw decorative card and text
        draw.rectangle([40, 40, 760, 560], outline=(255, 255, 255), width=3)
        draw.text(
            (60, 80),
            f"MUNCI STUDIO - PHOTO SAMPLE #{i}",
            fill=(255, 255, 255),
        )
        draw.text((60, 130), f"Khach Hang: {customer_name}", fill=(220, 220, 220))
        draw.text((60, 180), f"Thu muc: CHON | File: {filename}", fill=(200, 200, 200))
        draw.text(
            (60, 500),
            "Chế độ Mô phỏng An toàn (Safe Mock)",
            fill=(255, 234, 167),
        )

        img.save(file_path, format="JPEG", quality=90)
        generated_files.append(file_path)

    return generated_files


def get_drive_service(credentials_path: Optional[Path | str] = None) -> Any:
    """
    Builds authorized Google Drive API v3 Resource service.
    """
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    if credentials_path is None:
        credentials_path = Path("config/credentials.json")
    else:
        credentials_path = Path(credentials_path)

    scopes = [
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/spreadsheets",
    ]

    # Hỗ trợ đọc từ Streamlit Secrets khi deploy lên Streamlit Community Cloud
    try:
        import streamlit as st
        if hasattr(st, "secrets") and "gcp_service_account" in st.secrets:
            creds = service_account.Credentials.from_service_account_info(
                dict(st.secrets["gcp_service_account"]), scopes=scopes
            )
            return build("drive", "v3", credentials=creds)
    except Exception:
        pass

    if not credentials_path.exists():
        raise FileNotFoundError(f"Không tìm thấy file credentials tại: {credentials_path.resolve()}")

    creds = service_account.Credentials.from_service_account_file(
        str(credentials_path), scopes=scopes
    )
    return build("drive", "v3", credentials=creds)


def get_customer_parent_day(service: Any, customer_folder_id: str) -> str:
    """
    Finds the name of the parent 'NGÀY' folder in Google Drive (e.g., '18.10 tiệm' or '22.10 tiệm').
    Falls back to current date if not found.
    """
    from datetime import datetime
    try:
        meta = service.files().get(
            fileId=customer_folder_id,
            fields="id, name, parents",
            supportsAllDrives=True,
        ).execute()
        parents = meta.get("parents", [])
        if parents:
            p_info = service.files().get(
                fileId=parents[0],
                fields="id, name",
                supportsAllDrives=True,
            ).execute()
            p_name = p_info.get("name", "")
            # Extract number from parent name (e.g., 'NGÀY 18' -> '18')
            num_match = re.search(r"\d+", p_name)
            if num_match:
                day_num = int(num_match.group())
                return f"{day_num:02d}.10 tiệm"
    except Exception as e:
        logger.debug(f"Không thể lấy thư mục ngày của khách: {e}")

    now = datetime.now()
    return f"{now.day:02d}.{now.month:02d} tiệm"


def is_chon_folder_name(name: str) -> bool:
    """
    Kiểm tra tên thư mục có phải là thư mục chứa ảnh đã chọn hay không.
    Hỗ trợ các biến thể: 'Chọn', 'Đã chọn', 'Hình chọn', 'Ảnh chọn', 'Selected', 'CHON', 'DA CHON'...
    """
    if not name:
        return False
    from src.utils import strip_accents
    norm = strip_accents(str(name)).upper()
    keywords = ["CHON", "DA CHON", "HINH CHON", "ANH CHON", "SELECTED"]
    return any(kw in norm for kw in keywords)


def find_chon_folder_recursive(
    service: Any, root_folder_id: str, max_depth: int = 4
) -> Optional[dict[str, str]]:
    """
    Quét đệ quy đa tầng từ root_folder_id để tìm thư mục con chứa ảnh đã chọn.
    Áp dụng BFS (Breadth-First Search) để ưu tiên tầng gần nhất, duyệt tối đa max_depth tầng.
    """
    # 1. Kiểm tra xem chính thư mục root_folder_id có phải là thư mục chọn không
    try:
        self_meta = service.files().get(
            fileId=root_folder_id,
            fields="id, name",
            supportsAllDrives=True,
        ).execute()
        if is_chon_folder_name(self_meta.get("name", "")):
            return {"id": self_meta["id"], "name": self_meta["name"]}
    except Exception as e:
        logger.debug(f"Không thể lấy metadata root_folder_id {root_folder_id}: {e}")

    # 2. Duyệt BFS qua các tầng thư mục con
    from collections import deque
    queue = deque([(root_folder_id, 0)])
    visited = {root_folder_id}

    while queue:
        current_id, current_depth = queue.popleft()
        if current_depth >= max_depth:
            continue

        query = (
            f"'{current_id}' in parents and "
            "mimeType = 'application/vnd.google-apps.folder' and "
            "trashed = false"
        )
        try:
            resp = service.files().list(
                q=query,
                fields="files(id, name)",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
            ).execute()
            folders = resp.get("files", [])
        except Exception as e:
            logger.debug(f"Lỗi truy vấn thư mục con của {current_id}: {e}")
            continue

        # Kiểm tra trước tất cả các thư mục con ở tầng hiện tại
        for folder in folders:
            f_id = folder.get("id")
            f_name = folder.get("name", "")
            if is_chon_folder_name(f_name):
                logger.info(f"Đã tìm thấy thư mục chọn tại độ sâu {current_depth + 1}: '{f_name}' (ID: {f_id})")
                return {"id": f_id, "name": f_name}

        # Nếu chưa tìm thấy ở tầng này, thêm vào queue để duyệt tầng tiếp theo
        for folder in folders:
            f_id = folder.get("id")
            if f_id and f_id not in visited and (current_depth + 1) < max_depth:
                visited.add(f_id)
                queue.append((f_id, current_depth + 1))

    return None


def find_chon_subfolder(service: Any, customer_folder_id: str) -> Optional[dict[str, str]]:
    """
    Wrapper tương thích ngược: Sử dụng tìm kiếm đệ quy find_chon_folder_recursive.
    """
    return find_chon_folder_recursive(service, customer_folder_id, max_depth=4)



def find_or_create_done_subfolder(service: Any, customer_folder_id: str) -> str:
    """
    Finds or creates a 'DONE' folder inside customer_folder_id.
    """
    from src.utils import strip_accents
    query = (
        f"'{customer_folder_id}' in parents and "
        "mimeType = 'application/vnd.google-apps.folder' and "
        "trashed = false"
    )
    response = service.files().list(
        q=query,
        fields="files(id, name)",
        supportsAllDrives=True,
        includeItemsFromAllDrives=True,
    ).execute()
    files = response.get("files", [])

    for f in files:
        norm_name = strip_accents(f.get("name", ""))
        if norm_name == "DONE":
            return f["id"]

    # Create new folder 'DONE'
    metadata = {
        "name": "DONE",
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [customer_folder_id],
    }
    folder = service.files().create(
        body=metadata,
        fields="id",
        supportsAllDrives=True,
    ).execute()
    logger.info(f"Đã tạo mới thư mục 'DONE' trên Google Drive (ID: {folder.get('id')}).")
    return folder.get("id")


def sanitize_folder_name(name: str) -> str:
    """
    Chuẩn hóa tên thư mục local an toàn: không dấu, giữ nguyên hoa/thường, thay khoảng trắng bằng gạch dưới.
    Ví dụ: 'Trần Thị Mai' -> 'Tran_Thi_Mai'
    """
    if not name:
        return "KHACH_HANG"
    import unicodedata
    s = str(name).replace("Đ", "D").replace("đ", "d").strip()
    nfkd = unicodedata.normalize("NFKD", s)
    clean = "".join(c for c in nfkd if not unicodedata.combining(c))
    clean = re.sub(r"[^\w\s-]", "", clean)
    clean = re.sub(r"[\s-]+", "_", clean)
    return clean.strip("_") or "KHACH_HANG"


def download_chon_folder(
    customer_folder_id: str,
    local_chon_dir: Path | str,
    credentials_path: Optional[Path | str] = None,
    dry_run: bool = True,
    force_mock: bool = False,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
    customer_name: str = "",
) -> list[Path]:
    """
    Downloads all photo files from the customer's 'CHỌN' folder into local_chon_dir.
    If customer_name is provided, creates and saves into a dedicated subfolder '[Customer_Name]_DA_CHON'.
    If credentials.json is missing or force_mock is True, generates 5 sample images via Pillow.
    """
    target_dir = Path(local_chon_dir)
    if customer_name:
        safe_cname = sanitize_folder_name(customer_name)
        folder_suffix = f"{safe_cname}_DA_CHON"
        if not target_dir.name.endswith("_DA_CHON"):
            target_dir = target_dir / folder_suffix

    target_dir.mkdir(parents=True, exist_ok=True)

    cred_file = Path(credentials_path or "config/credentials.json")
    if force_mock or not check_has_credentials(cred_file):
        c_label = customer_name or target_dir.parent.name
        logger.info(
            f"[MOCK_DATA] Tải ảnh mô phỏng cho folder {customer_folder_id} vào {target_dir} (Khách: {c_label})..."
        )
        sample_files = generate_mock_photos(
            target_dir, count=5, customer_name=c_label
        )
        for idx, f in enumerate(sample_files, start=1):
            if progress_callback:
                progress_callback(idx, len(sample_files), f.name)
            time.sleep(0.05)
        return sample_files


    # Real Google Drive download
    from googleapiclient.http import MediaIoBaseDownload

    service = get_drive_service(cred_file)
    logger.info(f"Đang tìm thư mục con 'CHỌN' trong Drive folder: {customer_folder_id}...")
    chon_folder = find_chon_subfolder(service, customer_folder_id)

    if not chon_folder:
        logger.error(
            f"Không tìm thấy thư mục con 'CHỌN' trong Drive (ID: {customer_folder_id})! Vui lòng kiểm tra lại Drive của khách."
        )
        return []

    chon_id = chon_folder["id"]
    logger.info(f"Tìm thấy folder 'CHỌN' (ID: {chon_id}). Đang quét danh sách ảnh...")

    file_query = f"'{chon_id}' in parents and trashed = false"
    resp = service.files().list(
        q=file_query,
        fields="files(id, name, size, mimeType, shortcutDetails)",
        supportsAllDrives=True,
        includeItemsFromAllDrives=True,
    ).execute()
    drive_files = resp.get("files", [])

    photo_files = [
        f for f in drive_files if Path(f.get("name", "")).suffix.lower() in PHOTO_EXTENSIONS or f.get("mimeType") == "application/vnd.google-apps.shortcut"
    ]
    zip_files = [
        f for f in drive_files if Path(f.get("name", "")).suffix.lower() == ".zip"
    ]
    logger.info(f"Tìm thấy {len(photo_files)} file ảnh và {len(zip_files)} file zip trong thư mục 'CHỌN'.")

    downloaded: list[Path] = []
    total = len(photo_files) + len(zip_files)

    for idx, df in enumerate(photo_files, start=1):
        file_id = df["id"]
        if df.get("mimeType") == "application/vnd.google-apps.shortcut":
            file_id = df.get("shortcutDetails", {}).get("targetId", file_id)
        file_name = df["name"]
        destination = target_dir / file_name

        request = service.files().get_media(fileId=file_id, supportsAllDrives=True)
        with open(destination, "wb") as fh:
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()

        downloaded.append(destination)
        if progress_callback:
            progress_callback(idx, total, file_name)

    # Nếu có file ZIP: Tự động giải nén ra thư mục target_dir
    import zipfile
    for zf in zip_files:
        z_id = zf["id"]
        z_name = zf["name"]
        z_dest = target_dir / z_name
        req = service.files().get_media(fileId=z_id, supportsAllDrives=True)
        with open(z_dest, "wb") as fh:
            downloader = MediaIoBaseDownload(fh, req)
            done = False
            while not done:
                status, done = downloader.next_chunk()
        # Giải nén
        try:
            with zipfile.ZipFile(z_dest, 'r') as zip_ref:
                zip_ref.extractall(target_dir)
            z_dest.unlink(missing_ok=True)  # Xóa file zip sau khi giải nén
            # Cập nhật danh sách ảnh vừa giải nén
            for p in target_dir.iterdir():
                if p.is_file() and p.suffix.lower() in PHOTO_EXTENSIONS and p not in downloaded:
                    downloaded.append(p)
        except Exception as e:
            logger.warning(f"Lỗi giải nén file zip {z_name}: {e}")

    logger.info(f"Hoàn tất tải {len(downloaded)} ảnh về: {target_dir}")
    return downloaded


def upload_done_folder(
    customer_folder_id: str,
    local_done_dir: Path | str,
    credentials_path: Optional[Path | str] = None,
    dry_run: bool = True,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
) -> list[str]:
    """
    Uploads all edited photos from local_done_dir to Google Drive 'DONE' folder.
    If dry_run=True, simulates upload and logs each file.
    """
    done_path = Path(local_done_dir)
    if not done_path.exists():
        logger.warning(f"Thư mục local {done_path} không tồn tại!")
        return []

    local_files = [
        p
        for p in done_path.iterdir()
        if p.is_file() and p.suffix.lower() in PHOTO_EXTENSIONS and not p.name.endswith(".tmp")
    ]

    total = len(local_files)
    if total == 0:
        logger.warning(f"Không có file ảnh nào trong {done_path} để upload.")
        return []

    uploaded_names: list[str] = []

    if dry_run:
        logger.info(
            f"[DRY_RUN] Giả lập tạo thư mục 'DONE' và upload {total} ảnh lên Drive folder {customer_folder_id}:"
        )
        for idx, f in enumerate(local_files, start=1):
            logger.info(f"[DRY_RUN] ({idx}/{total}) Giả lập upload: {f.name} ({f.stat().st_size} bytes)")
            uploaded_names.append(f.name)
            if progress_callback:
                progress_callback(idx, total, f.name)
            time.sleep(0.05)
        return uploaded_names

    # Real upload
    cred_file = Path(credentials_path or "config/credentials.json")
    if not check_has_credentials(cred_file):
        raise FileNotFoundError(f"Cần file {cred_file} để thực thi upload thật!")

    from googleapiclient.http import MediaFileUpload

    service = get_drive_service(cred_file)
    done_drive_id = find_or_create_done_subfolder(service, customer_folder_id)

    for idx, f in enumerate(local_files, start=1):
        file_metadata = {"name": f.name, "parents": [done_drive_id]}
        media = MediaFileUpload(str(f), resumable=True)
        service.files().create(body=file_metadata, media_body=media, fields="id").execute()
        uploaded_names.append(f.name)
        logger.info(f"Đã upload lên Drive: {f.name} ({idx}/{total})")
        if progress_callback:
            progress_callback(idx, total, f.name)

    return uploaded_names


def parse_photo_codes(input_codes: Any) -> list[str]:
    """
    Phân tích chuỗi hoặc danh sách mã số ảnh một cách thông minh:
    - Hỗ trợ mọi ký tự phân cách: dấu phẩy (,), dấu chấm (.), dấu chấm phẩy (;),
      dấu gạch ngang (-), dấu gạch chéo (/), khoảng trắng, tab, xuống dòng.
    - Tự động kế thừa tiền tố thư mục/set:
      Ví dụ 'A1, 2, 3, 4' -> tự động mở rộng thành 'A1', 'A2', 'A3', 'A4'.
      Ví dụ 'B1, 2. 3' hoặc 'B1 B2 B3' -> 'B1', 'B2', 'B3'.
    - Bỏ qua các từ phụ như 'ảnh', 'hình'.
    """
    if not input_codes:
        return []

    text_to_parse = ""
    if isinstance(input_codes, (list, tuple, set)):
        text_to_parse = " ".join(str(x) for x in input_codes if x)
    else:
        text_to_parse = str(input_codes)

    clean_text = re.sub(r"\.(jpg|jpeg|png|cr2|arw|nef|dng|raw)\b", "", text_to_parse, flags=re.IGNORECASE)
    text_norm = re.sub(r"([a-zA-Z])\.(\d+)", r"\1\2", clean_text)
    tokens = re.split(r"[,;|\s\n\r/\\-]+|\.(?=\s|\d|$)", text_norm)

    raw_tokens = []
    for t in tokens:
        c = t.strip()
        if c and c.lower() not in (".", ",", "-", ";", "/", "\\", "ảnh", "hình", "hinh", "anh"):
            raw_tokens.append(c)

    results = []
    current_prefix = ""

    for t in raw_tokens:
        prefix_match = re.match(r"^([a-zA-Z]+)(\d+)$", t)
        if prefix_match:
            current_prefix = prefix_match.group(1).upper()
            num = prefix_match.group(2)
            results.append(f"{current_prefix}{num}")
        elif t.isdigit():
            # Bare number: inherit prefix if present (e.g. A1, 2, 3 -> A1, A2, A3)
            if current_prefix:
                results.append(f"{current_prefix}{t}")
            else:
                results.append(t)
        else:
            results.append(t)

    return results


def auto_select_and_organize_drive(
    customer_folder_id: str,
    photo_codes: list[str] | str,
    target_folder_name: str = "ĐÃ CHỌN",
    credentials_path: Optional[Path | str] = None,
    copy_mode: bool = True,
    dry_run: bool = False,
    force_mock: bool = False,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
) -> dict[str, Any]:
    """
    Tự động lọc ảnh theo danh sách mã số trên Google Drive và gom vào thư mục con (mặc định 'ĐÃ CHỌN').
    
    Tham số:
        customer_folder_id: Link hoặc ID thư mục gốc chứa ảnh của khách trên Google Drive
        photo_codes: Danh sách mã số ảnh (hỗ trợ phân cách bằng dấu phẩy, chấm, gạch, khoảng cách, xuống dòng...)
        target_folder_name: Tên thư mục đích trên Drive (mặc định: 'ĐÃ CHỌN')
        credentials_path: Đường dẫn file service account credentials.json
        copy_mode: True = Sao chép (Copy) an toàn giữ nguyên ảnh gốc; False = Di chuyển (Move)
        dry_run: Chỉ duyệt và báo cáo, không tạo folder hay copy file thật
        force_mock: Bật chế độ giả lập để kiểm thử không cần Google API
    """
    from src.utils import strip_accents

    # 1. Chuẩn hóa danh sách mã số ảnh (hỗ trợ linh hoạt mọi ký tự ngăn cách)
    raw_codes = parse_photo_codes(photo_codes)

    if not raw_codes:
        return {
            "success": False,
            "target_folder_id": "",
            "target_folder_name": target_folder_name,
            "total_scanned": 0,
            "matched_files": [],
            "unmatched_codes": [],
            "message": "Danh sách mã số ảnh rỗng!",
        }

    clean_cid = extract_drive_id(customer_folder_id)
    cred_file = Path(credentials_path or "config/credentials.json")

    # 2. Xử lý chế độ MOCK (Kiểm thử an toàn khi không có credentials hoặc force_mock)
    if force_mock or not check_has_credentials(cred_file):
        logger.info(f"[MOCK_DATA] Thực hiện lọc ảnh theo mã {raw_codes} trên mock folder {clean_cid}...")
        mock_files = [
            {"id": f"mock_file_000{i}", "name": f"IMG_{i:04d}.jpg"}
            for i in range(1, 6)
        ]
        matched: list[dict[str, str]] = []
        matched_target_codes = set()

        for mf in mock_files:
            if match_photo_code(mf["name"], raw_codes):
                matched.append(mf)
                for code in raw_codes:
                    if match_photo_code(mf["name"], [code]):
                        matched_target_codes.add(code)

        unmatched = [c for c in raw_codes if c not in matched_target_codes]
        mode_text = "Sao chép (Copy)" if copy_mode else "Di chuyển (Move)"
        return {
            "success": True,
            "target_folder_id": "mock_target_chon_id",
            "target_folder_name": target_folder_name,
            "total_scanned": len(mock_files),
            "matched_files": matched,
            "unmatched_codes": unmatched,
            "message": f"[MOCK] Đã tìm thấy {len(matched)}/{len(raw_codes)} ảnh khớp mã để {mode_text} vào '{target_folder_name}'.",
        }

    # 3. Kết nối Google Drive API v3 thật
    service = get_drive_service(cred_file)

    # 4. Tìm hoặc tạo thư mục đích (ĐÃ CHỌN) trên Google Drive
    target_norm = strip_accents(target_folder_name).upper()
    query_folder = (
        f"'{clean_cid}' in parents and "
        "mimeType = 'application/vnd.google-apps.folder' and "
        "trashed = false"
    )
    folder_resp = service.files().list(
        q=query_folder,
        fields="files(id, name)",
        supportsAllDrives=True,
        includeItemsFromAllDrives=True,
    ).execute()
    existing_folders = folder_resp.get("files", [])

    target_folder_id = ""
    for ef in existing_folders:
        if strip_accents(ef.get("name", "")).upper() == target_norm:
            target_folder_id = ef.get("id")
            logger.info(f"Đã tìm thấy thư mục đích sẵn có trên Drive: '{ef.get('name')}' (ID: {target_folder_id})")
            break

    if not target_folder_id and not dry_run:
        new_folder_meta = {
            "name": target_folder_name,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [clean_cid],
        }
        created = service.files().create(
            body=new_folder_meta,
            fields="id",
            supportsAllDrives=True,
        ).execute()
        target_folder_id = created.get("id", "")
        logger.info(f"Đã tạo mới thư mục '{target_folder_name}' trên Drive (ID: {target_folder_id})")

    # 5. Quét toàn bộ ảnh trong customer_folder_id và các thư mục con (ví dụ Folder A, Folder B...)
    drive_items: list[dict[str, Any]] = []
    subfolder_map: dict[str, str] = {}  # Lưu mapping: {'A': folder_id_A, 'B': folder_id_B}
    file_query = f"'{clean_cid}' in parents and trashed = false"
    files_resp = service.files().list(
        q=file_query,
        fields="files(id, name, mimeType)",
        pageSize=1000,
        supportsAllDrives=True,
        includeItemsFromAllDrives=True,
    ).execute()
    root_items = files_resp.get("files", [])

    for item in root_items:
        mtype = item.get("mimeType", "")
        if mtype == "application/vnd.google-apps.folder":
            sub_id = item.get("id")
            sub_name = item.get("name", "")
            # Bỏ qua thư mục đích (ĐÃ CHỌN)
            if sub_id == target_folder_id or strip_accents(sub_name).upper() == target_norm:
                continue
            
            # Ghi nhận tiền tố của thư mục con (vd 'A', 'B', 'Set A' -> 'A')
            p_match = re.search(r"\b([a-zA-Z])\b", sub_name)
            if p_match:
                subfolder_map[p_match.group(1).upper()] = sub_id
            subfolder_map[strip_accents(sub_name).upper()] = sub_id

            try:
                sub_query = f"'{sub_id}' in parents and trashed = false"
                sub_resp = service.files().list(
                    q=sub_query,
                    fields="files(id, name, mimeType)",
                    pageSize=1000,
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True,
                ).execute()
                for sub_f in sub_resp.get("files", []):
                    if Path(sub_f.get("name", "")).suffix.lower() in PHOTO_EXTENSIONS:
                        drive_items.append({
                            "id": sub_f.get("id"),
                            "name": sub_f.get("name"),
                            "folder_name": sub_name,
                            "parent_id": sub_id,
                        })
            except Exception as e:
                logger.debug(f"Không thể quét thư mục con '{sub_name}': {e}")
        elif Path(item.get("name", "")).suffix.lower() in PHOTO_EXTENSIONS:
            drive_items.append({
                "id": item.get("id"),
                "name": item.get("name"),
                "folder_name": "",
                "parent_id": clean_cid,
            })

    def get_return_folder_id(filename: str) -> str:
        """Tìm đúng thư mục gốc con (A, B...) để trả ảnh về nếu không còn được chọn."""
        f_prefix_match = re.match(r"^([a-zA-Z]+)", filename)
        if f_prefix_match:
            p_key = f_prefix_match.group(1).upper()
            if p_key in subfolder_map:
                return subfolder_map[p_key]
        return clean_cid

    matched_files: list[dict[str, Any]] = []
    matched_target_codes = set()
    already_in_target_ids: set[str] = set()
    already_in_target_names: set[str] = set()

    # Nếu thư mục ĐÃ CHỌN đã có sẵn ảnh từ lần bấm trước:
    # Đồng bộ chốt theo bộ chọn mới (Xóa/trả ảnh cũ về đúng thư mục A hoặc B ban đầu, giữ ảnh chung)
    if target_folder_id:
        try:
            old_resp = service.files().list(
                q=f"'{target_folder_id}' in parents and trashed = false",
                fields="files(id, name, mimeType)",
                pageSize=1000,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
            ).execute()
            old_files = old_resp.get("files", [])

            # Dọn trùng lặp (ví dụ vừa có shortcut vừa có file gốc do bấm cả 2 chế độ copy/move)
            file_by_name: dict[str, list[dict[str, Any]]] = {}
            for of in old_files:
                file_by_name.setdefault(of.get("name", ""), []).append(of)

            for fname, flist in file_by_name.items():
                if len(flist) > 1 and not dry_run:
                    shortcuts = [f for f in flist if f.get("mimeType") == "application/vnd.google-apps.shortcut"]
                    real_files = [f for f in flist if f.get("mimeType") != "application/vnd.google-apps.shortcut"]
                    if real_files and shortcuts:
                        for sc in shortcuts:
                            try:
                                service.files().delete(fileId=sc["id"], supportsAllDrives=True).execute()
                                logger.info(f"Đã tự động xóa shortcut thừa cho '{fname}' (ID: {sc['id']})")
                            except Exception as rm_sc_err:
                                logger.debug(f"Không thể xóa shortcut thừa: {rm_sc_err}")
                        flist[:] = real_files

            for of in old_files:
                of_name = of.get("name", "")
                if of_name in already_in_target_names:
                    continue
                if match_photo_code(of_name, raw_codes):
                    # Ảnh cũ vẫn nằm trong bộ chọn mới -> Giữ lại
                    already_in_target_ids.add(of["id"])
                    already_in_target_names.add(of_name)
                    matched_files.append({"id": of["id"], "name": of_name, "folder_name": "", "parent_id": target_folder_id})
                    for code in raw_codes:
                        if match_photo_code(of_name, [code]):
                            matched_target_codes.add(code)
                else:
                    # Ảnh cũ KHÔNG còn nằm trong bộ chọn mới -> Trả về đúng thư mục con A, B hoặc thư mục gốc
                    return_dest = get_return_folder_id(of_name)
                    if not dry_run:
                        try:
                            if of.get("mimeType") == "application/vnd.google-apps.shortcut" or copy_mode:
                                service.files().delete(fileId=of["id"], supportsAllDrives=True).execute()
                            else:
                                service.files().update(
                                    fileId=of["id"],
                                    addParents=return_dest,
                                    removeParents=target_folder_id,
                                    supportsAllDrives=True,
                                ).execute()
                            logger.info(f"Bộ chọn mới đã trả ảnh thừa '{of_name}' về thư mục ban đầu (ID: {return_dest})")
                        except Exception as rm_err:
                            logger.warning(f"Không thể trả ảnh cũ '{of_name}': {rm_err}")
                    else:
                        logger.info(f"[DRY_RUN] Sẽ trả ảnh thừa '{of_name}' về thư mục ban đầu (ID: {return_dest})")
        except Exception as e:
            logger.debug(f"Lỗi kiểm tra ảnh cũ trong thư mục đích: {e}")

    for item in drive_items:
        f_id = item.get("id")
        f_name = item.get("name", "")
        if f_id in already_in_target_ids or f_name in already_in_target_names:
            continue
        fol_name = item.get("folder_name", "")
        if match_photo_code(f_name, raw_codes, folder_name=fol_name):
            matched_files.append(item)
            already_in_target_names.add(f_name)
            for code in raw_codes:
                if match_photo_code(f_name, [code], folder_name=fol_name):
                    matched_target_codes.add(code)

    unmatched_codes = [c for c in raw_codes if c not in matched_target_codes]

    # 6. Sao chép hoặc Di chuyển các file đã khớp vào thư mục ĐÃ CHỌN
    total_matched = len(matched_files)
    logger.info(f"Quét được {len(drive_items)} ảnh. Khớp {total_matched} ảnh theo danh sách mã.")

    if not dry_run and target_folder_id:
        for idx, mf in enumerate(matched_files, start=1):
            f_id = mf["id"]
            f_name = mf["name"]
            f_parent = mf.get("parent_id", clean_cid)

            # Nếu ảnh đã nằm sẵn trong ĐÃ CHỌN từ lần trước thì giữ nguyên
            if f_id in already_in_target_ids:
                logger.info(f"[{idx}/{total_matched}] '{f_name}' đã có sẵn trong '{target_folder_name}' (giữ nguyên).")
                if progress_callback:
                    progress_callback(idx, total_matched, f_name)
                continue

            if copy_mode:
                # Copy an toàn giữ file gốc (tự động fallback sang Shortcut nếu Service Account bị giới hạn storage quota)
                try:
                    service.files().copy(
                        fileId=f_id,
                        body={"name": f_name, "parents": [target_folder_id]},
                        supportsAllDrives=True,
                    ).execute()
                    logger.info(f"[{idx}/{total_matched}] Đã copy '{f_name}' vào '{target_folder_name}'")
                except Exception as copy_err:
                    err_msg = str(copy_err)
                    if "storageQuotaExceeded" in err_msg or "quota" in err_msg.lower():
                        logger.warning(f"Service Account bị giới hạn quota Drive. Tự động tạo Shortcut cho '{f_name}'...")
                        service.files().create(
                            body={
                                "name": f_name,
                                "mimeType": "application/vnd.google-apps.shortcut",
                                "shortcutDetails": {"targetId": f_id},
                                "parents": [target_folder_id],
                            },
                            supportsAllDrives=True,
                        ).execute()
                        logger.info(f"[{idx}/{total_matched}] Đã tạo Shortcut (0MB quota) cho '{f_name}' vào '{target_folder_name}'")
                    else:
                        raise copy_err
            else:
                # Move file sang target_folder_id
                service.files().update(
                    fileId=f_id,
                    addParents=target_folder_id,
                    removeParents=f_parent,
                    supportsAllDrives=True,
                ).execute()
                logger.info(f"[{idx}/{total_matched}] Đã di chuyển '{f_name}' vào '{target_folder_name}'")

            if progress_callback:
                progress_callback(idx, total_matched, f_name)

    mode_str = "[DRY_RUN] " if dry_run else ""
    action_str = "Sao chép" if copy_mode else "Di chuyển"
    msg = f"{mode_str}Đã {action_str.lower()} thành công {total_matched}/{len(raw_codes)} ảnh vào thư mục '{target_folder_name}' trên Google Drive."
    if unmatched_codes:
        msg += f" (Không tìm thấy {len(unmatched_codes)} mã: {', '.join(unmatched_codes)})"

    return {
        "success": True,
        "target_folder_id": target_folder_id,
        "target_folder_name": target_folder_name,
        "total_scanned": len(drive_items),
        "matched_files": matched_files,
        "unmatched_codes": unmatched_codes,
        "message": msg,
    }

