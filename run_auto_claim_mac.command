#!/bin/bash
# ==============================================================================
# MUNCI STUDIO | BOT AUTO-CLAIM 24/24 (macOS Catalina 10.15 Intel i5 & tat ca macOS)
# Quet Google Sheet moi 30s de tu dong dien ten PHUC vao Cot O
# ==============================================================================

set -e
cd "$(dirname "$0")"

# Gỡ bỏ cờ cách ly macOS
if command -v xattr &>/dev/null; then
    xattr -dr com.apple.quarantine . 2>/dev/null || true
fi

echo "========================================================================"
echo "   BOT TU DONG NHAN DON (PHUC) | MUNCI STUDIO 24/24"
echo "   Doi may: MacBook Pro 2017 (macOS Catalina - Intel Core i5)"
echo "   Chu ky quet: Moi 30 giay | Nhan Ctrl + C de dung."
echo "========================================================================"
echo ""

VENV_DIR=".venv"
# Neu chua co venv hoac venv bi thieu, tao venv nhanh
if [ ! -d "$VENV_DIR" ] || [ ! -f "$VENV_DIR/bin/python" ]; then
    echo "[*] Khoi tao moi truong ao .venv..."
    /usr/local/bin/python3 -m venv "$VENV_DIR" || python3 -m venv "$VENV_DIR"
fi

PY_EXEC="$VENV_DIR/bin/python"
PIP_EXEC="$VENV_DIR/bin/pip"

# Kiem tra xem da co google module trong venv chua
if ! "$PY_EXEC" -c "import google.auth, googleapiclient" &>/dev/null; then
    echo "[*] Dang cai dat thu vien ket noi Google cho bot..."
    "$PIP_EXEC" install google-api-python-client google-auth google-auth-httplib2 google-auth-oauthlib -q
fi

echo "[*] Bot da san sang va dang chay lien tuc 24/24..."
exec "$PY_EXEC" src/auto_claim_bot.py --interval 30
