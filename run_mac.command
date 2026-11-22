#!/bin/bash
# ==============================================================================
# MUNCI STUDIO | macOS ONE-CLICK LAUNCHER & ENVIRONMENT SETUP
# Tuong thich: macOS Sonoma, Sequoia, Ventura, Monterey, Big Sur (Apple Silicon M1/M2/M3 & Intel)
# ==============================================================================

set -e
cd "$(dirname "$0")"

echo "========================================================================"
echo "   MUNCI STUDIO | AUTO RETOUCH & DRIVE WORKFLOW"
echo "   Kiem tra moi truong va khoi dong he thong tren macOS..."
echo "========================================================================"
echo ""

# 1. Tu dong go bo quarantine neu tai ve tu Zalo / Drive / Web
if command -v xattr &>/dev/null; then
    xattr -dr com.apple.quarantine . 2>/dev/null || true
fi

# 2. Tim kiem Python 3 san co tren macOS
PY_BIN=""
for candidate in python3 /usr/local/bin/python3 /opt/homebrew/bin/python3 $(which python3 2>/dev/null); do
    if [ -x "$candidate" ] && "$candidate" -c "import sys; exit(0 if sys.version_info >= (3, 9) else 1)" 2>/dev/null; then
        PY_BIN="$candidate"
        break
    fi
done

if [ -z "$PY_BIN" ]; then
    echo "[!] Chua phat hien Python 3 tren may."
    echo "    Dang kiem tra trinh cai dat..."
    
    if command -v brew &>/dev/null; then
        echo "[*] Dang dung Homebrew de cai dat Python 3..."
        brew install python
        PY_BIN=$(which python3)
    else
        echo ""
        echo "========================================================================"
        echo "   MAY MAC CHUA CO PYTHON 3. VUI LONG CHON 1 TRONG 2 CACH DON GIAN:"
        echo "   Cach 1: Mo Terminal va go lenh: xcode-select --install"
        echo "   Cach 2: Tai ban cai Python tai: https://www.python.org/downloads/mac-osx/"
        echo "========================================================================"
        echo ""
        read -p "Nhan Enter de thoat sau khi cai Python..."
        exit 1
    fi
fi

echo "[1/3] Python phu hop: $($PY_BIN --version) tai $PY_BIN"

# 3. Tao Virtual Environment (.venv) de khong bao gio bi loi PEP 668 (externally-managed-environment)
VENV_DIR=".venv"
if [ ! -d "$VENV_DIR" ] || [ ! -f "$VENV_DIR/bin/python" ]; then
    echo "[2/3] Dang khoi tao moi truong ao (.venv) lan dau tren Mac..."
    "$PY_BIN" -m venv "$VENV_DIR"
fi

VENV_PY="$VENV_DIR/bin/python"
VENV_PIP="$VENV_DIR/bin/pip"

# 4. Kiem tra va cai dat thu vien
echo "[3/3] Dang kiem tra va dong bo thu vien (requirements)..."
"$VENV_PIP" install --upgrade pip -q
"$VENV_PIP" install -r requirements.txt -q

echo ""
echo "========================================================================"
echo "   HE THONG DA SAN SANG! DANG MO DASHBOARD TREN TRINH DUYET..."
echo "   Dia chi truy cap: http://localhost:8501"
echo "   Nhan Ctrl + C de dung he thong."
echo "========================================================================"
echo ""

exec "$VENV_DIR/bin/streamlit" run app.py --server.headless=false --server.fileWatcherType=none
