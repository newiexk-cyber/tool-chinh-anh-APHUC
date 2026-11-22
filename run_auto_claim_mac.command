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

# Kiem tra thu vien Google, neu chua co thi tu cai ngay vao Python do
if ! "$PY_EXEC" -c "import google.auth, googleapiclient" &>/dev/null; then
    echo "[*] Dang cai dat thu vien ket noi Google Sheet & Drive vao Python..."
    "$PY_EXEC" -m pip install google-api-python-client google-auth google-auth-httplib2 google-auth-oauthlib -q
fi

echo "[*] Bot da san sang! Bat dau chay ngam 24/24..."
"$PY_EXEC" src/auto_claim_bot.py --interval 30

read -p "Nhan Enter neu chuong trinh dung..."
