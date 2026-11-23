#!/bin/bash
# ==============================================================================
# MUNCI STUDIO | BOT AUTO-CLAIM 24/24 (macOS Catalina Intel & Apple Silicon)
# Tu dong quet ca 2 Google Sheet moi 30 giay & dien ten PHUC vao Cot O
# ==============================================================================

cd "$(dirname "$0")"

# Go bo co quarantine & thu muc .streamlit cu (tranh doc key cu)
if command -v xattr &>/dev/null; then
    xattr -dr com.apple.quarantine . 2>/dev/null || true
fi
if [ -f ".streamlit/secrets.toml" ]; then
    rm -rf ".streamlit"
fi

echo "========================================================================"
echo "   BOT TU DONG NHAN DON (PHUC) | MUNCI STUDIO 24/24"
echo "   He dieu hanh: macOS ($(uname -m)) | Chu ky quet: Moi 30 giay"
echo "   Nhan Ctrl + C de dung bot."
echo "========================================================================"
echo ""

# Uu tien dung chung .venv neu da co, neu chua thi tao nhanh
VENV_DIR=".venv"
if [ -x "$VENV_DIR/bin/python" ]; then
    PY_EXEC="$VENV_DIR/bin/python"
else
    PY_SYS=""
    for candidate in /usr/local/bin/python3 /opt/homebrew/bin/python3 "$(command -v python3 2>/dev/null)"; do
        if [ -n "$candidate" ] && [ -x "$candidate" ] && "$candidate" -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)" 2>/dev/null; then
            PY_SYS="$candidate"
            break
        fi
    done

    if [ -z "$PY_SYS" ]; then
        echo "[!] Chua tim thay Python 3.8+ tren may Mac."
        echo "    Tai Python 3.11.9 tai: https://www.python.org/ftp/python/3.11.9/python-3.11.9-macos11.pkg"
        read -p "Nhan Enter de dong..."
        exit 1
    fi

    # Neu Python he thong da cai san google.oauth2 thi dung luon; nguoc lai tao .venv sach
    if "$PY_SYS" -c "from google.oauth2 import service_account; from googleapiclient.discovery import build" 2>/dev/null; then
        PY_EXEC="$PY_SYS"
    else
        echo "[*] Dang khoi tao moi truong ao (.venv) cho Bot..."
        "$PY_SYS" -m venv "$VENV_DIR"
        PY_EXEC="$VENV_DIR/bin/python"
    fi
fi

echo "[*] Python dang dung: $($PY_EXEC --version) ($PY_EXEC)"

# Kiem tra & cai thu vien Google neu chua co (chi dung wheel dung san)
if ! "$PY_EXEC" -c "from google.oauth2 import service_account; from googleapiclient.discovery import build" 2>/dev/null; then
    echo "[*] Dang cai thu vien ket noi Google Sheet & Drive..."
    "$PY_EXEC" -m pip install --only-binary :all: "google-auth==2.29.0" "google-api-python-client==2.125.0" "google-auth-httplib2==0.2.0" "google-auth-oauthlib==1.2.0" || {
        echo "[!] Cai thu vien Google that bai. Kiem tra ket noi mang roi thu lai."
        read -p "Nhan Enter de dong..."
        exit 1
    }
fi

echo "[*] Bot da san sang! Bat dau quet 24/24..."
echo ""
"$PY_EXEC" src/auto_claim_bot.py --interval 30

echo ""
read -p "Bot da dung. Nhan Enter de dong cua so..."
