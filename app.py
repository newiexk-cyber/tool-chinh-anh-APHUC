from __future__ import annotations
import os
import platform
import re
import sys
import time
from pathlib import Path
import pandas as pd
import streamlit as st

# Setup paths and import backend modules
ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

import unicodedata

from src.utils import (
    get_platform,
    setup_logging,
    get_logger,
    normalize_vn,
    read_latest_logs,
)

try:
    from src.utils import strip_accents
except ImportError:
    def strip_accents(text):
        if not text:
            return ""
        s = str(text).replace("Đ", "D").replace("đ", "d")
        nfkd = unicodedata.normalize("NFKD", s)
        return "".join(c for c in nfkd if not unicodedata.combining(c)).upper().strip()


def pick_folder_dialog(current_path: str = "") -> str:
    """Mở hộp thoại chọn thư mục chuẩn OS trên Windows hoặc macOS khi chạy local."""
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        selected = filedialog.askdirectory(initialdir=current_path or None)
        root.destroy()
        return selected
    except Exception as e:
        logger.warning(f"Không thể mở hộp thoại chọn thư mục: {e}")
        return ""


def open_folder_in_os(folder_path: Path | str) -> None:
    """Mở thư mục trong File Explorer (Windows) hoặc Finder (macOS)."""
    import subprocess
    p_str = str(Path(folder_path).resolve())
    try:
        if sys.platform == "win32":
            subprocess.Popen(f'explorer "{p_str}"')
        elif sys.platform == "darwin":
            subprocess.Popen(["open", p_str])
        else:
            subprocess.Popen(["xdg-open", p_str])
    except Exception as e:
        st.warning(f"Không thể mở thư mục '{p_str}': {e}")

import importlib
import src.sheet_manager
import src.drive_manager
import src.magimir_controller
importlib.reload(src.sheet_manager)
importlib.reload(src.drive_manager)
importlib.reload(src.magimir_controller)

from src.sheet_manager import (
    load_sheet_data,
    assign_staff,
    assign_staff_in_memory,
    mark_done,
    mark_done_in_memory,
    extract_spreadsheet_id,
)
from src.drive_manager import (
    extract_drive_id,
    download_chon_folder,
    upload_done_folder,
    get_customer_parent_day,
    get_drive_service,
    auto_select_and_organize_drive,
    sanitize_folder_name,
)
from src.magimir_controller import (
    process_customer_photos,
    is_magimir_running,
    count_valid_photos,
    wait_for_exported_photos,
    find_magimir_done_folder,
    is_folder_finished_exporting,
)

# Initialize application logging
setup_logging()
logger = get_logger("app_ui")

# Page Configuration
st.set_page_config(
    page_title="Auto Retouch Studio - MAGIMIR",
    page_icon="📸",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom High-End Modern Studio CSS
CUSTOM_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    
    /* Top Header Gradient Banner */
    .studio-header {
        background: linear-gradient(135deg, #1e1e2f 0%, #161623 50%, #0d0d15 100%);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 24px 32px;
        margin-bottom: 24px;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.35);
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    
    .studio-title {
        font-size: 28px;
        font-weight: 800;
        background: linear-gradient(90deg, #a78bfa 0%, #f472b6 50%, #38bdf8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
        letter-spacing: -0.5px;
    }
    
    .studio-subtitle {
        color: #94a3b8;
        font-size: 14px;
        margin-top: 4px;
        font-weight: 500;
    }
    
    /* Metric Cards Styling */
    div[data-testid="metric-container"] {
        background: rgba(30, 30, 46, 0.7);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.07);
        padding: 16px 20px;
        border-radius: 14px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    
    div[data-testid="metric-container"]:hover {
        transform: translateY(-2px);
        border-color: rgba(167, 139, 250, 0.4);
    }
    
    /* Terminal Log Container */
    .terminal-box {
        background-color: #0c0d14;
        border: 1px solid #1e293b;
        border-radius: 12px;
        padding: 16px;
        font-family: 'JetBrains Mono', 'Consolas', monospace;
        font-size: 12.5px;
        color: #38bdf8;
        height: 220px;
        overflow-y: auto;
        line-height: 1.6;
        box-shadow: inset 0 2px 8px rgba(0, 0, 0, 0.6);
    }
    
    .log-line {
        margin: 2px 0;
        white-space: pre-wrap;
    }
    
    .badge-pill {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 12px;
        font-weight: 600;
        margin-right: 6px;
    }
    .badge-win { background: #1e3a8a; color: #93c5fd; }
    .badge-mac { background: #4c1d95; color: #d8b4fe; }
    .badge-mock { background: #78350f; color: #fde68a; }
    .badge-real { background: #064e3b; color: #6ee7b7; }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# Session State Initialization
if "customers_data" not in st.session_state:
    st.session_state.customers_data = []
if "selected_rows" not in st.session_state:
    st.session_state.selected_rows = set()
if "last_action_message" not in st.session_state:
    st.session_state.last_action_message = ""

# Sidebar: Configurations & Safety Gates
st.sidebar.markdown("### ⚙️ Cấu Hình & Chốt Chặn An Toàn")

# 1. Primary Safe Mode Switch
dry_run_mode = st.sidebar.toggle(
    "🛡️ Chế độ An Toàn (Lưu máy, KHÔNG up Drive)",
    value=True,
    help="Khi BẬT: Bot tải ảnh thật và chạy MagiMir lưu vào máy tính. KHÔNG upload lên Drive và KHÔNG đổi trạng thái trên Sheet để bạn kiểm tra trước. Khi TẮT: Sẽ upload lên Drive và đánh dấu DONE trên Sheet.",
)

if dry_run_mode:
    st.sidebar.warning(
        "🛡️ **ĐANG BẬT AN TOÀN (LƯU MÁY)**\n\n"
        "• Tải ảnh gốc từ Drive về máy.\n"
        "• Chạy MagiMir chỉnh & lưu vào folder DONE trên máy.\n"
        "• ❌ **KHÔNG** upload lên Drive.\n"
        "• ❌ **KHÔNG** đổi trạng thái Sheet (để bạn xem trước)."
    )
else:
    st.sidebar.error(
        "🚀 **CHẾ ĐỘ GHI THẬT (UPLOAD DRIVE)**\n\n"
        "• Sẽ upload toàn bộ ảnh DONE lên Drive của khách!\n"
        "• Sẽ đổi trạng thái khách thành 'DONE' trên Google Sheet!"
    )

# Credentials Verification
credentials_file = ROOT_DIR / "config" / "credentials.json"
has_credentials = credentials_file.exists()

# Secondary Toggle: Simulation / Mock Mode
mock_mode_default = not has_credentials
mock_mode = st.sidebar.toggle(
    "🎭 Chế độ Mô phỏng (Mock Data & Giả lập)",
    value=mock_mode_default,
    help="Bật để test trọn vẹn quy trình ngay cả khi chưa có file credentials.json hoặc chưa cài đặt MAGIMIR.",
)

DEFAULT_BRANCHES = [
    {
        "id": "munci_td",
        "name": "Chi Nhánh 1: PHOTOSHOP - [MUNCI] - [TĐ]",
        "short_name": "MUNCI [TĐ]",
        "spreadsheet_id": "164fnRPj5Rlhv8wAfrnZYAto7ZD-NCXZE2-FdIRbNru4",
        "sheet_url": "https://docs.google.com/spreadsheets/d/164fnRPj5Rlhv8wAfrnZYAto7ZD-NCXZE2-FdIRbNru4/edit",
    },
    {
        "id": "photoshop_an",
        "name": "Chi Nhánh 2: PHOTOSHOP - [ẨN]",
        "short_name": "PHOTOSHOP [ẨN]",
        "spreadsheet_id": "1F6gV4aw1l-U7rkBlKSpIvjicQj4Yr9ODkNmqusTVBgg",
        "sheet_url": "https://docs.google.com/spreadsheets/d/1F6gV4aw1l-U7rkBlKSpIvjicQj4Yr9ODkNmqusTVBgg/edit",
    },
]

# Google Sheets selector
st.sidebar.markdown("---")
st.sidebar.markdown("#### 🏢 Kết Nối Đồng Thời 2 Chi Nhánh")
for b in DEFAULT_BRANCHES:
    st.sidebar.markdown(f"• **{b['name']}**")

sheet_name_input = st.sidebar.text_input(
    "Tên Tab Sheet",
    value="THÁNG 10/2026",
)

staff_name_input = st.sidebar.text_input(
    "Tên Nhân Viên",
    value="PHÚC",
    help="Tên sẽ được điền vào Cột O khi nhận đơn",
)

preset_options = ["Preset 2 (Khuyên dùng)", "Preset 1", "Preset 3"]
preset_name_input = st.sidebar.selectbox(
    "Tên Preset MAGIMIR",
    options=preset_options,
    index=0,
    help="Preset chỉnh ảnh trong MagiMir 2 (Preset 2 là preset được quay trong video thao tác)",
)

# Thư mục lưu ảnh trên máy tính (Cross-platform)
st.sidebar.markdown("---")
st.sidebar.markdown("#### 📁 Thư Mục Lưu Ảnh Tải Về Máy")

if sys.platform == "win32":
    win_default = Path(r"D:\02_HinhAnh_Media\ẢNH CHỤP")
    default_save_path = str(win_default) if win_default.exists() else str(ROOT_DIR / "workspace")
elif sys.platform == "darwin":
    mac_default = Path.home() / "Desktop" / "ẢNH CHỤP"
    default_save_path = str(mac_default)
else:
    default_save_path = str(ROOT_DIR / "workspace")

if "save_dir_input" not in st.session_state:
    st.session_state.save_dir_input = default_save_path

is_cloud_env = Path("/mount/src").exists() or bool(os.environ.get("STREAMLIT_SERVER_ENVIRONMENT"))

if is_cloud_env:
    st.sidebar.info("☁️ **Web đang chạy trên Cloud:** Khi tải ảnh về máy tính, trình duyệt sẽ tự động mở hộp thoại cho bạn chọn chỗ lưu file nén ZIP!")
    save_dir_input = str(ROOT_DIR / "workspace")
else:
    col_d1, col_d2 = st.sidebar.columns([3, 1.2])
    with col_d2:
        if st.button("📂 Chọn", help="Bấm để chọn thư mục trên máy tính"):
            picked = pick_folder_dialog(st.session_state.save_dir_input)
            if picked:
                st.session_state.save_dir_input = picked
                st.rerun()
    with col_d1:
        save_dir_input = st.text_input(
            "Thư mục lưu ảnh:",
            value=st.session_state.save_dir_input,
            key="save_dir_input_field",
        )
        st.session_state.save_dir_input = save_dir_input

# Auto-Polling Interval Settings
st.sidebar.markdown("---")
st.sidebar.markdown("#### ⏱️ Tự động cập nhật theo thời gian")
auto_poll_enabled = st.sidebar.toggle(
    "🔄 Bật Tự Động Quét (Auto-Poll)",
    value=False,
    help="Tự động quét lại Google Sheet để nhận khách mới khi tiệm cập nhật thêm đơn trong ngày.",
)
poll_interval = st.sidebar.selectbox(
    "Chu kỳ quét định kỳ:",
    options=["1 phút", "5 phút", "15 phút", "30 phút", "1 giờ", "2 giờ", "24 giờ"],
    index=4,  # Mặc định 1 giờ
)

# Environment Badges
st.sidebar.markdown("---")
os_name = get_platform()
os_label = "Windows (x64)" if os_name == "windows" else ("macOS Apple Silicon (M1/M2/M3)" if os_name == "darwin" else "Linux/Other")
badge_os_cls = "badge-win" if os_name == "windows" else "badge-mac"

cred_label = "✅ Đã có credentials.json" if has_credentials else "⚠️ Chưa có credentials.json"
badge_cred_cls = "badge-real" if has_credentials else "badge-mock"

st.sidebar.markdown(
    f"""
    <div style="margin-bottom: 12px;">
        <span class="badge-pill {badge_os_cls}">{os_label}</span>
        <span class="badge-pill {badge_cred_cls}">{cred_label}</span>
    </div>
    """,
    unsafe_allow_html=True,
)

magimir_active = is_magimir_running()
mag_status_text = "🟢 MAGIMIR Đang Mở" if magimir_active else "⚪ MAGIMIR Chưa Mở (Dùng Giả Lập)"
st.sidebar.caption(f"Trạng thái phần mềm: **{mag_status_text}**")


# ==============================================================================
# MAIN PAGE CONTENT
# ==============================================================================

# Top Header Banner
st.markdown(
    """
    <div class="studio-header">
        <div>
            <h1 class="studio-title">AUTO RETOUCH STUDIO • MAGIMIR</h1>
            <div class="studio-subtitle">Hệ thống tự động hóa khép kín: Google Sheet (Tháng 10/2026) ➔ Google Drive ➔ MAGIMIR ➔ Upload DONE</div>
        </div>
        <div style="text-align: right;">
            <div style="font-size: 13px; color: #94a3b8;">Tiệm ảnh Trái Thơm • Munci Studio</div>
            <div style="font-size: 12px; color: #64748b; margin-top: 2px;">Phiên bản v1.2.0 Auto-Select</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

def fetch_and_filter_all_branches(
    branches: list[dict],
    sheet_name: str,
    credentials_path: Path,
    mock_mode: bool,
    staff_name: str,
) -> list[dict]:
    """
    Tải dữ liệu từ CẢ 2 BẢNG (2 Chi Nhánh) và lọc các đơn hợp lệ:
    - Bắt buộc có link Drive
    - Đã chọn hình (SL > 0 hoặc trạng thái ĐÃ CHỌN/ĐÃ CHỈNH)
    - Trạng thái chưa DONE
    - Của staff_name HOẶC chưa có người nhận (trống)
    """
    all_filtered = []
    target = strip_accents(staff_name)

    for b in branches:
        try:
            raw_data = load_sheet_data(
                spreadsheet_id=b["spreadsheet_id"],
                sheet_name=sheet_name,
                credentials_path=credentials_path,
                mock_mode=mock_mode,
            )
            for r in raw_data:
                name = strip_accents(r.get("ten_khach", ""))
                if not name or name in ["TEN KHACH", "OFF", "-", "MAU"]:
                    continue
                status = strip_accents(r.get("trang_thai", ""))
                if "DONE" in status or "CHINH" in status:
                    continue
                link = str(r.get("drive_link", "")).strip()
                if not link:
                    continue
                sl = int(r.get("sl_hinh_chon", 0) or 0)
                is_sel = (sl > 0) or ("CHON" in status)
                if not is_sel:
                    continue
                cur_staff = strip_accents(r.get("nhan_vien", ""))
                if cur_staff == target or cur_staff == "":
                    item = dict(r)
                    item["branch_id"] = b["id"]
                    item["branch_name"] = b["short_name"]
                    item["spreadsheet_id"] = b["spreadsheet_id"]
                    item["sheet_name"] = sheet_name
                    item["job_uid"] = f"{b['id']}_{r['row']}"
                    all_filtered.append(item)
        except Exception as e:
            logger.error(f"Lỗi khi tải bảng '{b['name']}': {e}")

    return all_filtered


# Auto-load initial data if empty or needed
if "has_loaded_real" not in st.session_state:
    st.session_state.has_loaded_real = False

if not st.session_state.customers_data or not st.session_state.has_loaded_real:
    st.session_state.customers_data = fetch_and_filter_all_branches(
        branches=DEFAULT_BRANCHES,
        sheet_name=sheet_name_input,
        credentials_path=credentials_file,
        mock_mode=mock_mode,
        staff_name=staff_name_input,
    )
    # TỰ ĐỘNG CHỌN (Auto-Select): Tự động chọn 100% tất cả các đơn hợp lệ theo job_uid
    st.session_state.selected_rows = {c["job_uid"] for c in st.session_state.customers_data}
    st.session_state.has_loaded_real = True

customers = st.session_state.customers_data
norm_staff_filter = strip_accents(staff_name_input)

# ==============================================================================
# BRANCH FILTER CONTROL (LỰA CHỌN CHI NHÁNH)
# ==============================================================================
branch_col_title, branch_col_filter = st.columns([1, 2.5])
with branch_col_title:
    st.markdown("#### 🏢 Chọn Chi Nhánh:")
with branch_col_filter:
    branch_labels = [
        "🌟 Tất Cả 2 Chi Nhánh",
        "📍 Chi Nhánh 1: MUNCI [TĐ]",
        "📍 Chi Nhánh 2: PHOTOSHOP [ẨN]",
    ]
    selected_branch_filter = st.radio(
        "Lựa chọn Chi Nhánh:",
        options=branch_labels,
        horizontal=True,
        index=0,
        label_visibility="collapsed",
    )

if "Chi Nhánh 1" in selected_branch_filter:
    active_customers = [c for c in customers if c.get("branch_id") == "munci_td"]
elif "Chi Nhánh 2" in selected_branch_filter:
    active_customers = [c for c in customers if c.get("branch_id") == "photoshop_an"]
else:
    active_customers = customers

# KPI Metrics Computation based on active_customers
kpi_unassigned = sum(
    1
    for c in active_customers
    if not strip_accents(c.get("nhan_vien", ""))
    and strip_accents(c.get("trang_thai", "")) != "DONE"
)

kpi_my_jobs = sum(
    1
    for c in active_customers
    if strip_accents(c.get("nhan_vien", "")) == norm_staff_filter
    and strip_accents(c.get("trang_thai", "")) != "DONE"
)

kpi_local_processing = sum(
    1
    for c in active_customers
    if c.get("local_status") in ["Đang tải", "Đang chỉnh", "Đang upload"]
)

kpi_total_actionable = len(active_customers)

# Display KPI Row
col_m1, col_m2, col_m3, col_m4 = st.columns(4)
with col_m1:
    st.metric("Chờ nhận việc (Cột O trống)", f"{kpi_unassigned} đơn", delta=f"{kpi_unassigned} có thể nhận")
with col_m2:
    st.metric(f"Đơn của {staff_name_input} cần chỉnh", f"{kpi_my_jobs} đơn", delta="Đang chờ nạp MagiMir")
with col_m3:
    st.metric("Đang xử lý tại Local", f"{kpi_local_processing} đơn", delta=None)
with col_m4:
    st.metric("Tổng đơn hiển thị", f"{kpi_total_actionable} đơn", delta=selected_branch_filter.split(":")[-1].strip())

st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)


# ==============================================================================
# THREE-STEP WORKFLOW TABS
# ==============================================================================

tab_step1, tab_step2, tab_step3 = st.tabs([
    f"⚡ BƯỚC 1: TỰ ĐỘNG NHẬN ĐƠN MỚI CHO {staff_name_input}",
    f"🎨 BƯỚC 2: CHỌN BỘ ĐỂ MAGIMIR TỰ CHỈNH & UP DRIVE",
    "🎯 BƯỚC 3: AUTO TICK MÃ ẢNH & TẠO 'ĐÃ CHỌN' (DRIVE)",
])

# ------------------------------------------------------------------------------
# TAB 1: BƯỚC 1 - AUTO TICK TÊN PHÚC CHO CÁC ĐƠN MỚI
# ------------------------------------------------------------------------------
with tab_step1:
    st.markdown("### ⚡ Bước 1: Nhận Đơn Mới Tự Động (Điền Tên Phúc Vào Cột O)")
    st.info(
        f"**Mục tiêu Bước 1:** Tự động phát hiện các Concept mới khách đã chọn ảnh mà Cột O (Nhân viên) đang trống "
        f"để điền ngay tên **'{staff_name_input}'** vào Google Sheet tương ứng của từng chi nhánh."
    )

    unassigned_list = [
        c for c in active_customers if not strip_accents(c.get("nhan_vien", ""))
    ]

    col_btn_claim, col_bot_info = st.columns([1.5, 1.5])
    with col_btn_claim:
        btn_claim_all = st.button(
            f"⚡ NHẬN TẤT CẢ {len(unassigned_list)} ĐƠN MỚI ({selected_branch_filter})",
            type="primary",
            use_container_width=True,
            disabled=(len(unassigned_list) == 0),
        )
    with col_bot_info:
        st.caption(
            "💡 **Chạy bot tự động 24/7:** Bạn có thể mở file `run_auto_claim_bot.bat` ngoài Desktop để bot tự quét ngầm cả 2 bảng mỗi 30s và cướp đơn liên tục!"
        )

    if btn_claim_all and unassigned_list:
        from collections import defaultdict
        grouped = defaultdict(list)
        for c in unassigned_list:
            sp_id = c.get("spreadsheet_id", DEFAULT_BRANCHES[0]["spreadsheet_id"])
            s_tab = c.get("sheet_name", sheet_name_input)
            grouped[(sp_id, s_tab)].append(c["row"])

        total_claimed = 0
        with st.spinner(f"Đang ghi tên '{staff_name_input}' vào {len(unassigned_list)} đơn trên các Chi Nhánh..."):
            for (sp_id, s_tab), row_nums in grouped.items():
                assign_staff(
                    spreadsheet_id=sp_id,
                    sheet_name=s_tab,
                    row_numbers=row_nums,
                    staff_name=staff_name_input,
                    dry_run=dry_run_mode,
                    credentials_path=credentials_file,
                )
                total_claimed += len(row_nums)
            for c in unassigned_list:
                c["nhan_vien"] = staff_name_input
            st.toast(f"Đã nhận thành công {total_claimed} đơn mới trên các bảng!", icon="✍️")
            st.rerun()

    if unassigned_list:
        st.markdown(f"#### 🔔 Có **{len(unassigned_list)} đơn mới** chưa có ai nhận:")
        df_unassigned = pd.DataFrame([
            {
                "CHI NHÁNH": c.get("branch_name", ""),
                "Row": c["row"],
                "STT": c["stt"],
                "TÊN KHÁCH": c["ten_khach"],
                "GÓI": c["goi"],
                "SL HÌNH": c.get("sl_hinh_chon", 0),
                "TRẠNG THÁI": c.get("trang_thai", ""),
                "LINK DRIVE": c.get("drive_link", ""),
                "NHÂN VIÊN (O)": "👉 [CHƯA CÓ AI NHẬN]",
            }
            for c in unassigned_list
        ])
        st.dataframe(df_unassigned, use_container_width=True, hide_index=True)
    else:
        st.success("🎉 Hiện tại không có đơn mới nào đang bị bỏ trống trong chi nhánh này. Tất cả đơn đã được nhận!")



# ------------------------------------------------------------------------------
# TAB 2: BƯỚC 2 - CHỌN BỘ CỦA PHÚC ĐỂ MAGIMIR CHỈNH & UP DRIVE
# ------------------------------------------------------------------------------
with tab_step2:
    st.markdown(f"### 🎨 Bước 2: Danh Sách Bộ Ảnh Của {staff_name_input} Cần Chỉnh")
    st.caption("Tick chọn những bộ bạn muốn chỉnh hôm nay rồi bấm nút **'BẮT ĐẦU CHỈNH ẢNH'** ở phía dưới.")

    my_jobs_list = [
        c for c in active_customers if strip_accents(c.get("nhan_vien", "")) == norm_staff_filter
    ]

    # Quick Select Controls
    q_col1, q_col2, _ = st.columns([2, 2, 4])
    with q_col1:
        if st.button("✅ Chọn tất cả bộ của tôi", use_container_width=True):
            st.session_state.selected_rows = {c["job_uid"] for c in my_jobs_list}
            st.rerun()
    with q_col2:
        if st.button("❌ Bỏ chọn tất cả", use_container_width=True):
            st.session_state.selected_rows.clear()
            st.rerun()

    # Table for Step 2
    table_rows = []
    for c in my_jobs_list:
        is_selected = c["job_uid"] in st.session_state.selected_rows
        table_rows.append(
            {
                "Chọn để chỉnh": is_selected,
                "CHI NHÁNH": c.get("branch_name", "MUNCI [TĐ]"),
                "Row": c["row"],
                "STT": c["stt"],
                "TÊN KHÁCH": c["ten_khach"],
                "GÓI": c["goi"],
                "SL HÌNH": c.get("sl_hinh_chon", 0),
                "TRẠNG THÁI (I)": c.get("trang_thai", ""),
                "LINK DRIVE": c.get("drive_link", ""),
                "TIẾN ĐỘ LOCAL": c.get("local_status", "Chưa tải"),
                "UID": c["job_uid"],
            }
        )

    df_table = pd.DataFrame(table_rows)

    edited_df = st.data_editor(
        df_table,
        column_config={
            "Chọn để chỉnh": st.column_config.CheckboxColumn(
                "Chọn",
                help="Tick chọn bộ ảnh này để nạp vào MagiMir",
                default=True,
            ),
            "CHI NHÁNH": st.column_config.TextColumn(
                "CHI NHÁNH",
                help="Chi nhánh của đơn",
            ),
            "LINK DRIVE": st.column_config.LinkColumn(
                "LINK DRIVE",
                help="Bấm mở thư mục Google Drive của khách",
                validate=r"^https?://.*",
                display_text="Mở Drive ↗",
            ),
            "SL HÌNH": st.column_config.NumberColumn(
                "SL HÌNH",
                format="%d ảnh",
            ),
        },
        disabled=[
            "CHI NHÁNH",
            "Row",
            "STT",
            "TÊN KHÁCH",
            "GÓI",
            "SL HÌNH",
            "TRẠNG THÁI (I)",
            "LINK DRIVE",
            "TIẾN ĐỘ LOCAL",
            "UID",
        ],
        hide_index=True,
        use_container_width=True,
        key="customer_data_editor_step2",
    )

    # Sync checkbox edits back to session_state
    new_selected = set()
    for idx, row in edited_df.iterrows():
        if row["Chọn để chỉnh"]:
            new_selected.add(str(row["UID"]))
    st.session_state.selected_rows = new_selected

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

    # Big Action Button for Step 2
    btn_col_run, btn_col_scan = st.columns([3, 1.2])
    with btn_col_run:
        run_btn = st.button(
            f"🚀 BẮT ĐẦU CHỈNH {len(st.session_state.selected_rows)} BỘ ĐÃ CHỌN (Tải CHỌN ➔ MAGIMIR ➔ Up DONE)",
            type="primary",
            use_container_width=True,
            disabled=(len(st.session_state.selected_rows) == 0),
        )
    with btn_col_scan:
        if st.button("🔄 Quét lại Cả 2 Bảng Sheet", use_container_width=True):
            with st.spinner("Đang quét dữ liệu mới nhất từ CẢ 2 BẢNG..."):
                st.session_state.customers_data = fetch_and_filter_all_branches(
                    branches=DEFAULT_BRANCHES,
                    sheet_name=sheet_name_input,
                    credentials_path=credentials_file,
                    mock_mode=mock_mode,
                    staff_name=staff_name_input,
                )
                st.session_state.selected_rows = {
                    c["job_uid"] for c in st.session_state.customers_data if strip_accents(c.get("nhan_vien", "")) == norm_staff_filter
                }
                st.toast("Đã cập nhật dữ liệu cả 2 chi nhánh mới nhất!", icon="✅")
                st.rerun()


# ------------------------------------------------------------------------------
# TAB 3: BƯỚC 3 - AUTO TICK MÃ ẢNH & TẠO 'ĐÃ CHỌN' TRÊN GOOGLE DRIVE
# ------------------------------------------------------------------------------
with tab_step3:
    st.markdown("### 🎯 Auto Tick Mã Ảnh & Tự Động Gom Vào Thư Mục 'ĐÃ CHỌN' Trên Google Drive")
    st.info(
        "💡 **Tính năng mới:** Nhập link Google Drive của khách (hoặc chọn nhanh từ danh sách khách trên Sheet) và "
        "dán danh sách mã số ảnh khách chọn (ví dụ: `0012, 0045, 108` hoặc `IMG_0012`). "
        "Tool sẽ tự động quét ảnh gốc trên Drive, so khớp đúng mã và gom vào thư mục **'ĐÃ CHỌN'**."
    )

    col_t1, col_t2 = st.columns([1.5, 1.5])
    with col_t1:
        # Gợi ý chọn nhanh link từ đơn hiện có
        customer_options = {
            f"[{c.get('branch_name', '')}] Row {c['row']} - {c['ten_khach']} ({c.get('sl_hinh_chon', 0)} ảnh)": c.get("drive_link", "")
            for c in active_customers if c.get("drive_link")
        }
        quick_pick_label = st.selectbox(
            "Chọn nhanh khách từ Google Sheet:",
            options=["-- Nhập link Drive thủ công --"] + list(customer_options.keys()),
        )
        default_link = ""
        if quick_pick_label != "-- Nhập link Drive thủ công --":
            default_link = customer_options.get(quick_pick_label, "")

        target_drive_url = st.text_input(
            "Link Thư Mục Google Drive Của Khách:",
            value=default_link,
            placeholder="https://drive.google.com/drive/folders/...",
        )

        target_folder_name = st.text_input(
            "Tên Thư Mục Tạo Mới Trên Drive:",
            value="ĐÃ CHỌN",
            help="Thư mục sẽ được tạo trên Drive của khách nếu chưa có",
        )

        safe_copy = st.checkbox(
            "🛡️ Sao chép an toàn (Giữ nguyên file ảnh gốc, copy vào ĐÃ CHỌN)",
            value=True,
            help="Khuyên dùng để không bao giờ làm mất ảnh gốc của khách.",
        )

        download_to_local_tab3 = st.checkbox(
            "📥 Tải bộ ảnh này về máy tính ngay sau khi gom xong",
            value=False,
            help=f"Tự động tải toàn bộ ảnh đã lọc về thư mục: {save_dir_input}",
        )

    with col_t2:
        codes_input = st.text_area(
            "Danh Sách Mã Số Ảnh Khách Chọn:",
            height=140,
            placeholder="Ví dụ: 0012, 0045, 108\nHoặc dán: IMG_0012, IMG_0045\n(Cách nhau bằng dấu phẩy, khoảng trắng hoặc xuống dòng)",
            help="Hệ thống tự động nhận diện cả số thứ tự lẫn tên file đầy đủ",
        )

        btn_organize = st.button(
            "🚀 BẮT ĐẦU AUTO TICK & GOM VÀO 'ĐÃ CHỌN' TRÊN DRIVE",
            type="primary",
            use_container_width=True,
            disabled=not (target_drive_url and codes_input.strip()),
        )

    if btn_organize:
        if not target_drive_url:
            st.warning("Vui lòng nhập Link Google Drive của khách!")
        elif not codes_input.strip():
            st.warning("Vui lòng nhập danh sách mã số ảnh!")
        else:
            with st.spinner("Đang quét Drive và gom ảnh vào thư mục..."):
                organize_res = auto_select_and_organize_drive(
                    customer_folder_id=target_drive_url,
                    photo_codes=codes_input,
                    target_folder_name=target_folder_name,
                    credentials_path=credentials_file,
                    copy_mode=safe_copy,
                    dry_run=dry_run_mode,
                    force_mock=mock_mode,
                )
                if organize_res.get("success"):
                    st.success(organize_res.get("message", "Đã gom ảnh thành công!"))
                    st.balloons()

                    if download_to_local_tab3 and not dry_run_mode:
                        with st.spinner("Đang tải các ảnh đã gom về máy tính..."):
                            try:
                                base_dir = Path(save_dir_input.strip() if save_dir_input.strip() else (ROOT_DIR / "workspace"))
                                cust_label = "Khach_Hang"
                                if quick_pick_label != "-- Nhập link Drive thủ công --":
                                    cust_label = sanitize_folder_name(quick_pick_label.split(" - ")[-1].split(" (")[0])
                                local_dest = base_dir / cust_label / target_folder_name
                                local_dest.mkdir(parents=True, exist_ok=True)

                                dl_progress = st.progress(0, text="Đang tải ảnh về máy...")
                                def on_tab3_dl_progress(cur, tot, fname):
                                    pct = int((cur / max(tot, 1)) * 100)
                                    dl_progress.progress(pct, text=f"Tải ảnh ({cur}/{tot}): {fname}")

                                downloaded_items = download_chon_folder(
                                    customer_folder_id=target_drive_url,
                                    local_chon_dir=local_dest,
                                    credentials_path=credentials_file,
                                    dry_run=False,
                                    force_mock=mock_mode,
                                    progress_callback=on_tab3_dl_progress,
                                )
                                st.success(f"📥 Đã tải thành công {len(downloaded_items)} ảnh về máy tại: `{local_dest}`")
                                if st.button("📂 Mở thư mục ảnh trên máy", key="btn_open_tab3_dl"):
                                    open_folder_in_os(local_dest)
                            except Exception as dl_err:
                                st.warning(f"Lỗi tải ảnh về máy: {dl_err}")

                    matched = organize_res.get("matched_files", [])
                    unmatched = organize_res.get("unmatched_codes", [])

                    c_res1, c_res2 = st.columns(2)
                    with c_res1:
                        st.markdown(f"#### ✅ Đã gom {len(matched)} ảnh:")
                        if matched:
                            st.dataframe(pd.DataFrame(matched), use_container_width=True)
                    with c_res2:
                        if unmatched:
                            st.markdown(f"#### ⚠️ Không tìm thấy {len(unmatched)} mã:")
                            st.write(", ".join(unmatched))
                        else:
                            st.info("🎉 Tất cả mã số đều được tìm thấy chính xác 100%!")
                else:
                    st.error(f"❌ Có lỗi: {organize_res.get('message')}")



if run_btn:
    if not st.session_state.selected_rows:
        st.warning("Vui lòng chọn khách hàng cần xử lý!")
    else:
        selected_customers = [
            c for c in st.session_state.customers_data
            if c.get("job_uid") in st.session_state.selected_rows or c["row"] in st.session_state.selected_rows
        ]

        # Tự động nhận việc cho các đơn đang trống nếu có
        unassigned_custs = [
            c for c in selected_customers if not strip_accents(c.get("nhan_vien", ""))
        ]
        if unassigned_custs:
            from collections import defaultdict
            grouped = defaultdict(list)
            for c in unassigned_custs:
                sp_id = c.get("spreadsheet_id", DEFAULT_BRANCHES[0]["spreadsheet_id"])
                s_tab = c.get("sheet_name", sheet_name_input)
                grouped[(sp_id, s_tab)].append(c["row"])

            with st.spinner(f"Tự động nhận việc (Gán {staff_name_input}) cho {len(unassigned_custs)} đơn trống..."):
                for (sp_id, s_tab), row_nums in grouped.items():
                    assign_staff(
                        spreadsheet_id=sp_id,
                        sheet_name=s_tab,
                        row_numbers=row_nums,
                        staff_name=staff_name_input,
                        dry_run=dry_run_mode,
                        credentials_path=credentials_file,
                    )
                for c in unassigned_custs:
                    c["nhan_vien"] = staff_name_input

        # Filter strictly: Customers not DONE
        eligible_for_run = []
        for c in selected_customers:
            status = strip_accents(c.get("trang_thai", ""))
            if status != "DONE":
                eligible_for_run.append(c)

        if not eligible_for_run:
            st.error(
                f"Không có đơn nào hợp lệ để chạy! Các đơn đã 'DONE' sẽ không chạy lại."
            )
        else:
            # GIAI ĐOẠN 1: TỰ ĐỘNG TẢI VỀ HẾT TOÀN BỘ CÁC BỘ ẢNH ĐÃ CHỌN TRƯỚC
            st.info(f"📥 **GIAI ĐOẠN 1:** Đang tự động tải về hết **{len(eligible_for_run)} bộ ảnh gốc** về máy tính (không bắt bạn chờ)...")
            
            batch_tasks = []
            download_overall = st.progress(0, text="Bắt đầu tải về...")
            
            base_media_dir = Path(save_dir_input.strip() if save_dir_input.strip() else (ROOT_DIR / "workspace"))
            try:
                base_media_dir.mkdir(parents=True, exist_ok=True)
            except Exception:
                base_media_dir = ROOT_DIR / "workspace"

            last_day_folder = None

            for c_idx, cust in enumerate(eligible_for_run, start=1):
                row_id = cust["row"]
                cust_name = cust["ten_khach"]
                drive_url = cust.get("drive_link", "")
                folder_id = extract_drive_id(drive_url)

                day_folder_name = "22.10 tiệm"
                try:
                    if not mock_mode and Path(credentials_file).exists():
                        drive_svc = get_drive_service(credentials_file)
                        day_folder_name = get_customer_parent_day(drive_svc, folder_id)
                except Exception:
                    pass
                last_day_folder = base_media_dir / day_folder_name

                sanitized_name = sanitize_folder_name(cust_name)
                cust_clean_name = f"{row_id}_{sanitized_name}"
                cust_workspace = base_media_dir / day_folder_name / cust_clean_name
                chon_dir = cust_workspace / f"{sanitized_name}_DA_CHON"
                chon_dir.mkdir(parents=True, exist_ok=True)
                # TUYỆT ĐỐI KHÔNG TẠO TRƯỚC THƯ MỤC DONE RỖNG - ĐỂ MAGIMIR TỰ TẠO KHI EXPORT

                pct = int((c_idx - 1) / len(eligible_for_run) * 100)
                download_overall.progress(
                    pct,
                    text=f"[{c_idx}/{len(eligible_for_run)}] Đang tải ảnh gốc: {cust_name} (Row {row_id})..."
                )

                downloaded_files = download_chon_folder(
                    customer_folder_id=folder_id,
                    local_chon_dir=chon_dir,
                    credentials_path=credentials_file,
                    dry_run=dry_run_mode,
                    force_mock=mock_mode,
                    customer_name=cust_name,
                )

                if downloaded_files:
                    batch_tasks.append({
                        "cust": cust,
                        "row_id": row_id,
                        "cust_name": cust_name,
                        "folder_id": folder_id,
                        "cust_workspace": cust_workspace,
                        "chon_dir": chon_dir,
                        "expected_count": len(downloaded_files),
                        "status": "waiting_magimir",
                        "done_folder": None,
                        "exported_count": 0,
                        "uploaded": False,
                    })
                else:
                    # Dọn thư mục rỗng nếu Drive không có folder CHỌN
                    try:
                        if chon_dir.exists() and not any(chon_dir.iterdir()):
                            chon_dir.rmdir()
                        if cust_workspace.exists() and not any(cust_workspace.iterdir()):
                            cust_workspace.rmdir()
                    except Exception:
                        pass
                    st.warning(
                        f"⚠️ **[Row {row_id} - {cust_name}]:** Chưa có thư mục **'CHỌN'** hoặc **'ĐÃ CHỌN'** trên Google Drive! "
                        f"(Trên Drive của khách đang có ảnh gốc nhưng chưa gom vào thư mục 'ĐÃ CHỌN'). "
                        f"👉 Bạn hãy qua **Tab Bước 3** dán mã số ảnh của khách để gom trước nhé!"
                    )

            download_overall.progress(100, text=f"✅ Đã tải về thành công toàn bộ {len(batch_tasks)}/{len(eligible_for_run)} bộ ảnh gốc!")
            st.toast(f"Đã tải xong toàn bộ {len(batch_tasks)} bộ ảnh!", icon="📥")

            # Tự động mở thư mục ảnh gốc để bạn kéo thả hàng loạt vào MagiMir
            if last_day_folder and last_day_folder.exists():
                open_folder_in_os(last_day_folder)

            # GIAI ĐOẠN 2: TỰ ĐỘNG QUÉT LIÊN TỤC & TỰ ĐỘNG UP DRIVE KHI CÓ HÌNH
            st.markdown(
                f"""
                ---
                ### 🤖 GIAI ĐOẠN 2: TỰ ĐỘNG CANH QUÉT MAGIMIR & TỰ UP LÊN DRIVE
                > 💡 **BẠN CHỈ CẦN THAO TÁC TRÊN MAGIMIR:**
                > 1. Toàn bộ ảnh gốc của **{len(batch_tasks)} khách** đã nằm sẵn trong máy tính của bạn.
                > 2. Hãy kéo các thư mục này vào **MagiMir 2** và bấm **Export** (MagiMir sẽ tự sinh thư mục `DONE`).
                > 3. Hệ thống bên dưới đang **TỰ ĐỘNG QUÉT LIÊN TỤC**. Hễ bộ nào MagiMir xuất xong là tool sẽ **TỰ BỐC ẢNH UPLOAD LÊN DRIVE** ngay lập tức, không bắt bạn chờ đợi!
                """
            )

            watcher_status = st.empty()
            
            # Vòng lặp quét tự động liên tục
            max_scan_seconds = 1800  # 30 phút canh liên tục
            start_time = time.time()
            
            while time.time() - start_time < max_scan_seconds:
                all_done = True
                
                for task in batch_tasks:
                    if task["uploaded"]:
                        continue
                    
                    all_done = False
                    
                    # Kiểm tra xem MagiMir đã tự tạo thư mục DONE và có ảnh chưa
                    done_dir = find_magimir_done_folder(task["cust_workspace"], task["chon_dir"])
                    if done_dir:
                        task["done_folder"] = done_dir
                        is_ready, cur_count = is_folder_finished_exporting(done_dir, task["expected_count"])
                        task["exported_count"] = cur_count
                        
                        if is_ready:
                            task["status"] = "uploading"
                            logger.info(f"Phát hiện MagiMir đã xuất đủ {cur_count}/{task['expected_count']} ảnh cho {task['cust_name']}. Tiến hành tự động Up Drive...")
                            
                            if dry_run_mode:
                                task["uploaded"] = True
                                task["status"] = "done_safe"
                                logger.info(f"[CHẾ ĐỘ AN TOÀN] Đã phát hiện đủ ảnh cho {task['cust_name']} (Lưu máy, chưa up Drive).")
                            else:
                                try:
                                    uploaded_files = upload_done_folder(
                                        customer_folder_id=task["folder_id"],
                                        local_done_dir=done_dir,
                                        credentials_path=credentials_file,
                                        dry_run=False,
                                    )
                                    mark_done(
                                        spreadsheet_id=sheet_url_input,
                                        sheet_name=sheet_name_input,
                                        row_number=task["row_id"],
                                        dry_run=False,
                                        credentials_path=credentials_file,
                                    )
                                    st.session_state.customers_data = mark_done_in_memory(
                                        st.session_state.customers_data, task["row_id"]
                                    )
                                    task["uploaded"] = True
                                    task["status"] = "done_uploaded"
                                    st.toast(f"✅ Đã tự động up xong khách {task['cust_name']} ({len(uploaded_files)} ảnh)!", icon="🎉")
                                except Exception as up_err:
                                    logger.error(f"Lỗi upload Drive cho {task['cust_name']}: {up_err}")
                    else:
                        task["status"] = "waiting_magimir"

                # Hiển thị bảng theo dõi tiến độ thời gian thực
                with watcher_status.container():
                    summary_cards = []
                    for t in batch_tasks:
                        if t["status"] == "done_uploaded":
                            badge = "✅ ĐÃ UP LÊN DRIVE HOÀN TẤT"
                        elif t["status"] == "done_safe":
                            badge = "🛡️ ĐÃ XONG TẠI MÁY (CHẾ ĐỘ AN TOÀN)"
                        elif t["status"] == "uploading":
                            badge = "🚀 ĐANG TẢI LÊN GOOGLE DRIVE..."
                        elif t["exported_count"] > 0:
                            badge = f"🎨 MagiMir đang xuất ({t['exported_count']}/{t['expected_count']} ảnh)..."
                        else:
                            badge = "⏳ Đang đợi MagiMir xuất thư mục DONE..."
                        
                        summary_cards.append({
                            "Khách hàng": t["cust_name"],
                            "Row": t["row_id"],
                            "Số ảnh gốc": t["expected_count"],
                            "Ảnh trong DONE": f"{t['exported_count']}/{t['expected_count']}",
                            "Trạng thái tự động": badge,
                        })
                    
                    st.markdown("#### 📡 Bảng Theo Dõi Quét Tự Động Thời Gian Thực:")
                    st.dataframe(pd.DataFrame(summary_cards), use_container_width=True, hide_index=True)
                    st.caption(f"🔄 Hệ thống đang tự động quét liên tục mỗi 2 giây... (Đã quét {int(time.time() - start_time)} giây)")

                if all_done:
                    break
                    
                time.sleep(2.0)

            if all_done:
                st.success("🎉 TẤT CẢ CÁC BỘ ẢNH ĐÃ ĐƯỢC MAGIMIR XUẤT VÀ TỰ ĐỘNG UPLOAD XONG HOÀN TOÀN!")
                st.balloons()



# ==============================================================================
# LIVE TERMINAL LOG VIEWER
# ==============================================================================

st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
st.markdown("### 🖥️ Live Terminal Log (Thời Gian Thực)")

log_head_col, log_btn_col = st.columns([8, 2])
with log_head_col:
    st.caption("Hiển thị 80 dòng log hoạt động gần nhất của hệ thống.")
with log_btn_col:
    if st.button("🔄 Làm mới Log", use_container_width=True):
        st.rerun()

recent_logs = read_latest_logs(max_lines=80)
log_html = "".join([f"<div class='log-line'>{line}</div>" for line in recent_logs])

st.markdown(
    f"""
    <div class="terminal-box">
        {log_html}
    </div>
    """,
    unsafe_allow_html=True,
)
