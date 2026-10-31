from __future__ import annotations
"""
AUTO-CLAIM BOT: Tự động nhận việc (Điền tên PHÚC) khi có Concept mới
-------------------------------------------------------------------
Mục đích:
- Chạy ngầm định kỳ (ví dụ mỗi 30s - 60s).
- Tự động quét Google Sheet (Sheet 'THÁNG 10/2026').
- Ngay khi phát hiện đơn có khách ĐÃ CHỌN ảnh mà Cột O (Nhân viên) đang TRỐNG:
  -> Lập tức điền tên 'PHÚC' vào Cột O trên Sheet thật để nhận việc trước!

Sử dụng:
    python src/auto_claim_bot.py [--interval 30] [--dry-run]
"""

import sys
import os
import time
import argparse
from pathlib import Path

# Đảm bảo import từ thư mục gốc
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

# UTF-8 cho Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from src.utils import get_logger, strip_accents
from src.sheet_manager import load_sheet_data, assign_staff, get_spreadsheet_sheet_names

logger = get_logger("auto_claim_bot")

DEFAULT_SHEETS = [
    {
        "id": "164fnRPj5Rlhv8wAfrnZYAto7ZD-NCXZE2-FdIRbNru4",
        "name": "PHOTOSHOP - [MUNCI] - [TĐ]",
        "tab": "THÁNG 10/2026",
    },
    {
        "id": "1F6gV4aw1l-U7rkBlKSpIvjicQj4Yr9ODkNmqusTVBgg",
        "name": "PHOTOSHOP - [ẨN]",
        "tab": "THÁNG 10/2026",
    },
]
DEFAULT_STAFF = "PHÚC"


def run_claim_cycle(spreadsheet_id: str, sheet_name: str, staff_name: str, dry_run: bool) -> int:
    """
    Quét 1 vòng kiểm tra và tự động nhận tất cả các đơn trống thỏa mãn trên 1 sheet.
    Trả về số lượng đơn vừa nhận.
    """
    cred_path = ROOT_DIR / "config" / "credentials.json"
    rows = load_sheet_data(
        spreadsheet_id=spreadsheet_id,
        sheet_name=sheet_name,
        credentials_path=cred_path,
        mock_mode=False,
        only_eligible=False,
    )

    unassigned_rows = []
    for r in rows:
        name = strip_accents(r.get("ten_khach", ""))
        if not name or name in ["TEN KHACH", "OFF", "-", "MAU", "0FF"]:
            continue

        status = strip_accents(r.get("trang_thai", ""))
        # BỎ QUA nếu đã hoàn tất (DONE) hoặc đã chỉnh xong (ĐÃ CHỈNH):
        if "DONE" in status or "CHINH" in status:
            continue

        link = str(r.get("drive_link", "")).strip()
        if not link:
            continue

        sl_hinh = int(r.get("sl_hinh_chon", 0) or 0)
        is_selected = (sl_hinh > 0) or ("CHON" in status)
        if not is_selected:
            continue

        cur_staff = strip_accents(r.get("nhan_vien", ""))
        if cur_staff == "":
            unassigned_rows.append(r)

    if not unassigned_rows:
        return 0

    row_numbers = [r["row"] for r in unassigned_rows]
    names = [r["ten_khach"] for r in unassigned_rows]
    logger.info(f"⚡ [PHÁT HIỆN ĐƠN MỚI] Có {len(row_numbers)} đơn chưa có người nhận: {names}")

    res = assign_staff(
        spreadsheet_id=spreadsheet_id,
        sheet_name=sheet_name,
        row_numbers=row_numbers,
        staff_name=staff_name,
        dry_run=dry_run,
        credentials_path=cred_path,
    )

    if res.get("success"):
        mode_str = "[TEST - DRY_RUN]" if dry_run else "[THẬT TRÊN SHEET]"
        logger.info(f"✅ {mode_str} Đã tự động điền '{staff_name}' vào Cột O cho các Row: {row_numbers}!")
        for r in unassigned_rows:
            print(f"  👉 ĐÃ NHẬN: Row {r['row']} - Khách: {r['ten_khach']} (SL: {r.get('sl_hinh_chon', 0)} ảnh)")
    else:
        logger.error(f"❌ Lỗi nhận việc: {res.get('error')}")

    return len(row_numbers)


def main():
    parser = argparse.ArgumentParser(description="Auto-Claim Bot: Tự động điền PHÚC khi có concept mới trên cả 2 bảng")
    parser.add_argument("--interval", type=int, default=30, help="Chu kỳ quét (giây). Mặc định 30s")
    parser.add_argument("--dry-run", action="store_true", help="Bật chế độ thử nghiệm an toàn (không ghi thật)")
    parser.add_argument("--staff", type=str, default=DEFAULT_STAFF, help="Tên nhân viên điền vào (vd: PHÚC)")
    args = parser.parse_args()

    mode_txt = "🛡️ DRY_RUN (An Toàn - Không ghi thật)" if args.dry_run else "🔥 PRODUCTION (GHI THẬT VÀO SHEET)"
    print("=" * 75)
    print("⚡ BOT TỰ ĐỘNG NHẬN ĐƠN CHO PHÚC (AUTO-CLAIM BOT - QUÉT CẢ 2 BẢNG)")
    for s in DEFAULT_SHEETS:
        print(f"• Bảng: {s['name']} (ID: {s['id']}) | Tab: {s['tab']}")
    print(f"• Nhân viên: {args.staff}")
    print(f"• Chế độ: {mode_txt}")
    print(f"• Chu kỳ quét: Mỗi {args.interval} giây")
    print("=" * 75)
    print("Bot đang chạy ngầm... Nhấn Ctrl + C để dừng.\n")

    while True:
        try:
            now_str = time.strftime("%H:%M:%S %d/%m/%Y")
            total_claimed = 0
            for s_info in DEFAULT_SHEETS:
                scan_text = f"[{now_str}] Đang quét bảng '{s_info['name']}'..."
                print(scan_text.ljust(85), end="\r")
                # Tự động lấy tab tháng mới nhất nếu có
                current_tab = s_info.get("tab", "THÁNG 10/2026")
                try:
                    all_tabs = get_spreadsheet_sheet_names(s_info["id"])
                    if all_tabs:
                        current_tab = all_tabs[0]
                except Exception:
                    pass

                claimed = run_claim_cycle(
                    spreadsheet_id=s_info["id"],
                    sheet_name=current_tab,
                    staff_name=args.staff,
                    dry_run=args.dry_run,
                )
                total_claimed += claimed

            if total_claimed > 0:
                print(f"\n[{now_str}] 🎉 Vừa tự động nhận thành công {total_claimed} đơn mới!")
            time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\n[-] Bot đã tạm dừng.")
            break
        except Exception as e:
            logger.error(f"Lỗi trong vòng lặp bot: {e}")
            time.sleep(args.interval)


if __name__ == "__main__":
    main()
