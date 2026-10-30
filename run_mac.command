#!/bin/bash
# -----------------------------------------------------------------------------
# MUNCI STUDIO - AUTO RETOUCH AUTOMATION (Mac M1 Apple Silicon / Intel)
# -----------------------------------------------------------------------------

cd "$(dirname "$0")"

echo "======================================================================"
echo "   MUNCI STUDIO - AUTO RETOUCH AUTOMATION (MAGIMIR DESKTOP)"
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

echo "[1/2] Kiểm tra và cài đặt thư viện cần thiết..."
$PY_CMD -m pip install -r requirements.txt -q

echo ""
echo "[2/2] Đang khởi động Web Dashboard (Streamlit)..."
echo "Địa chỉ truy cập: http://localhost:8501"
echo ""

$PY_CMD -m streamlit run app.py
