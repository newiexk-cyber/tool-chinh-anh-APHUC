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
if [ -f "$VENV_DIR/bin/python" ]; then
    PY_EXEC="$VENV_DIR/bin/python"
else
    # Tim Python 3 neu chua chay run_mac.command
    PY_CANDIDATE=""
    for candidate in python3 /usr/local/bin/python3 /opt/homebrew/bin/python3 $(which python3 2>/dev/null); do
        if [ -x "$candidate" ] && "$candidate" -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)" 2>/dev/null; then
            PY_CANDIDATE="$candidate"
            break
        fi
    done

    if [ -n "$PY_CANDIDATE" ]; then
        PY_EXEC="$PY_CANDIDATE"
    else
        echo "[!] Chua phat hien Python 3 tren may. Vui long mo run_mac.command truoc de cai dat!"
        read -p "Nhan Enter de thoat..."
        exit 1
    fi
fi

echo "[*] Bot dang chay lien tuc 24/24..."
exec "$PY_EXEC" src/auto_claim_bot.py --interval 30
