#!/bin/bash
# ==============================================================================
# MUNCI STUDIO | BOT AUTO-CLAIM 24/24 (macOS Catalina 10.15 Intel i5 & tat ca macOS)
# Quet Google Sheet moi 30s de tu dong dien ten PHUC vao Cot O
# ==============================================================================

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

# Uu tien tim python3 truc tiep tu he thong Mac
PY_EXEC=""
for p in /usr/local/bin/python3 $(which python3 2>/dev/null) python3 .venv/bin/python; do
    if [ -x "$p" ]; then
        PY_EXEC="$p"
        break
    fi
done

if [ -z "$PY_EXEC" ]; then
    echo "[!] Khong tim thay Python 3 tren may."
    read -p "Nhan Enter de thoat..."
    exit 1
fi

echo "[*] Python dang dung: $($PY_EXEC --version) tai $PY_EXEC"

# Kiem tra dung cac module bot can (google.oauth2 + googleapiclient).
# Cai bang "$PY_EXEC -m pip" de chac chan cai vao DUNG ban Python dang chay bot.
if ! "$PY_EXEC" -c "from google.oauth2 import service_account; from googleapiclient.discovery import build" &>/dev/null; then
    echo "[*] Dang cai dat thu vien ket noi Google Sheet & Drive vao $PY_EXEC ..."
    "$PY_EXEC" -m pip install --upgrade google-auth google-api-python-client google-auth-httplib2 google-auth-oauthlib
    if ! "$PY_EXEC" -c "from google.oauth2 import service_account; from googleapiclient.discovery import build"; then
        echo "[!] Cai thu vien Google that bai. Kiem tra ket noi mang roi chay lai."
        read -p "Nhan Enter de thoat..."
        exit 1
    fi
fi

echo "[*] Bot da san sang! Bat dau chay ngam 24/24..."
"$PY_EXEC" src/auto_claim_bot.py --interval 30

read -p "Nhan Enter neu chuong trinh dung..."
