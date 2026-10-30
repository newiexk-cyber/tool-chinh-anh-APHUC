#!/bin/bash
# -----------------------------------------------------------------------------
# BOT AUTO-NHẬN VIỆC (PHÚC) - MUNCI STUDIO (macOS Apple Silicon / Intel)
# -----------------------------------------------------------------------------

cd "$(dirname "$0")"

echo "======================================================================"
echo "   BOT TỰ ĐỘNG QUÉT CẢ 2 BẢNG GOOGLE SHEET & NHẬN ĐƠN MỚI CHO PHÚC"
echo "   Chạy ngầm liên tục mỗi 30 giây để bắt đơn ngay khi khách chọn ảnh!"
echo "======================================================================"
echo ""

# Find python3
if command -v python3 &>/dev/null; then
    PY_CMD="python3"
elif command -v python &>/dev/null; then
    PY_CMD="python"
else
    echo "[ERROR] Không tìm thấy Python 3 trên macOS."
    echo "Vui lòng cài đặt qua Homebrew: brew install python"
    read -p "Nhấn Enter để thoát..."
    exit 1
fi

echo "[1] Đang khởi động Bot quét tự động..."
echo "Nhấn Ctrl + C để tạm dừng bot bất kỳ lúc nào."
echo ""

$PY_CMD src/auto_claim_bot.py --interval 30

