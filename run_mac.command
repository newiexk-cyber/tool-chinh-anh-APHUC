#!/bin/bash
# ==============================================================================
# MUNCI STUDIO | macOS ONE-CLICK LAUNCHER & ENVIRONMENT SETUP
# Tương thích 100% macOS Catalina 10.15 (MacBook Pro 2017 Intel Core i5)
# và tất cả các dòng macOS khác (Sonoma, Sequoia, Ventura, Monterey, Big Sur)
# ==============================================================================

set -e
cd "$(dirname "$0")"

echo "========================================================================"
echo "   MUNCI STUDIO | AUTO RETOUCH & DRIVE WORKFLOW"
echo "   Dang kiem tra cau hinh macOS Catalina 10.15 (Intel Core i5)..."
echo "========================================================================"
echo ""

# 1. Tu dong go bo quarantine tren macOS Catalina
if command -v xattr &>/dev/null; then
    xattr -dr com.apple.quarantine . 2>/dev/null || true
fi

# 2. Tim kiem Python 3 san co (Python 3.8 tro len)
PY_BIN=""
for candidate in /usr/local/bin/python3 python3 /opt/homebrew/bin/python3 $(which python3 2>/dev/null); do
    if [ -x "$candidate" ] && "$candidate" -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)" 2>/dev/null; then
        PY_BIN="$candidate"
        break
    fi
done

if [ -z "$PY_BIN" ]; then
    echo "========================================================================"
    echo "   [!] CHUA PHAT HIEN PYTHON 3.8+ TREN MACOS CATALINA."
    echo "========================================================================"
    read -p "Nhan Enter de dong cua so nay..."
    exit 1
fi

echo "[1/3] Phat hien Python: $($PY_BIN --version) tai $PY_BIN"

# 3. Tao Virtual Environment (.venv) doc lap cho may Mac
VENV_DIR=".venv"
if [ ! -d "$VENV_DIR" ] || [ ! -f "$VENV_DIR/bin/python" ]; then
    echo "[2/3] Dang khoi tao moi truong ao (.venv) lan dau tien tren Mac..."
    "$PY_BIN" -m venv "$VENV_DIR"
fi

VENV_PY="$VENV_DIR/bin/python"
VENV_PIP="$VENV_DIR/bin/pip"

# 4. Kiem tra va cai dat thu vien voi prebuilt wheel cho macOS Catalina Intel
echo "[3/3] Dang kiem tra thu vien requirements (toi uu cho macOS Catalina)..."
"$VENV_PIP" install --upgrade pip -q

# Cai dat pyarrow phien ban prebuilt wheel 15.0.2 truoc de khong bi loi bien dich Rust/libcst
if [ "$(uname -s)" = "Darwin" ] && [ "$(uname -m)" = "x86_64" ]; then
    "$VENV_PIP" install "pyarrow==15.0.2" -q || true
    "$VENV_PIP" install "streamlit<=1.38.0" -q || true
fi

"$VENV_PIP" install -r requirements.txt --prefer-binary -q

echo ""
echo "========================================================================"
echo "   HE THONG DA SAN SANG! DANG KHOI DONG STREAMLIT WEB..."
echo "   Dia chi truy cap: http://localhost:8501"
echo "   Nhan Ctrl + C trong cua so nay de dung."
echo "========================================================================"
echo ""

# Toi uu tai nguyen cho Core i5 2017: tat watcher nang
exec "$VENV_DIR/bin/streamlit" run app.py --server.headless=false --server.fileWatcherType=none --browser.gatherUsageStats=false
