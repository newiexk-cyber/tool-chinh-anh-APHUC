#!/bin/bash
# ==============================================================================
# MUNCI STUDIO | macOS ONE-CLICK LAUNCHER (WEB DASHBOARD & STEP 3)
# Tuong thich 100% macOS Catalina 10.15 (Intel Core i5) & Apple Silicon M1/M2/M3/M4
# ==============================================================================

cd "$(dirname "$0")"

echo "========================================================================"
echo "   MUNCI STUDIO | AUTO RETOUCH & DRIVE WORKFLOW"
echo "   Dang khoi dong tren macOS ($(uname -m))..."
echo "========================================================================"
echo ""

# 1. Go bo co quarantine & thu muc .streamlit cu (tranh doc key cu)
if command -v xattr &>/dev/null; then
    xattr -dr com.apple.quarantine . 2>/dev/null || true
fi
if [ -f ".streamlit/secrets.toml" ]; then
    rm -rf ".streamlit"
fi

# 2. Tim Python 3.8+ (uu tien ban cai chinh thuc /usr/local/bin/python3 tren Catalina)
PY_BIN=""
for candidate in /usr/local/bin/python3 /opt/homebrew/bin/python3 "$(command -v python3 2>/dev/null)"; do
    if [ -n "$candidate" ] && [ -x "$candidate" ] && "$candidate" -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)" 2>/dev/null; then
        PY_BIN="$candidate"
        break
    fi
done

if [ -z "$PY_BIN" ]; then
    echo "[!] Chua tim thay Python 3.8+ tren may Mac."
    echo "    Vui long cai Python 3.11.9 tai:"
    echo "    https://www.python.org/ftp/python/3.11.9/python-3.11.9-macos11.pkg"
    echo ""
    read -p "Nhan Enter de dong..."
    exit 1
fi

echo "[1/3] Python: $($PY_BIN --version) ($PY_BIN)"

# 3. Tao moi truong ao .venv dung chung cho ca Dashboard va Bot Auto-Claim
VENV_DIR=".venv"
if [ ! -x "$VENV_DIR/bin/python" ]; then
    echo "[2/3] Dang tao moi truong ao (.venv) lan dau..."
    "$PY_BIN" -m venv "$VENV_DIR" || {
        echo "[!] Loi tao .venv. Hay chay lai hoac kiem tra Python."
        read -p "Nhan Enter de dong..."
        exit 1
    }
fi

VENV_PY="$VENV_DIR/bin/python"
VENV_PIP="$VENV_DIR/bin/pip"

# 4. Kiem tra & cai thu vien (chi dung wheel dung san tren Catalina Intel)
if ! "$VENV_PY" -c "import streamlit, pandas; from google.oauth2 import service_account; from googleapiclient.discovery import build" 2>/dev/null; then
    echo "[3/3] Dang cai dat thu vien lan dau (mat khoang 30-60 giay)..."
    "$VENV_PIP" install --upgrade pip -q 2>/dev/null || true
    if [ "$(uname -s)" = "Darwin" ] && [ "$(uname -m)" = "x86_64" ]; then
        "$VENV_PIP" install --only-binary :all: -r requirements.txt || {
            echo "[!] Cai thu vien that bai. Kiem tra ket noi mang roi thu lai."
            read -p "Nhan Enter de dong..."
            exit 1
        }
    else
        "$VENV_PIP" install --prefer-binary -r requirements.txt || {
            echo "[!] Cai thu vien that bai. Kiem tra ket noi mang roi thu lai."
            read -p "Nhan Enter de dong..."
            exit 1
        }
    fi
else
    echo "[3/3] Thu vien da san sang."
fi

echo ""
echo "========================================================================"
echo "   HE THONG DA SAN SANG! DANG MO TRINH DUYET..."
echo "   Dia chi: http://localhost:8501"
echo "   Nhan Ctrl + C trong cua so nay de dung."
echo "========================================================================"
echo ""

"$VENV_PY" -m streamlit run app.py --server.headless=false --server.fileWatcherType=none --browser.gatherUsageStats=false

echo ""
read -p "Chuong trinh da dung. Nhan Enter de dong cua so..."
