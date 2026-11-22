#!/bin/bash
# ==============================================================================
# MUNCI STUDIO | BOT AUTO-CLAIM 24/24 (macOS Apple Silicon & Intel)
# Tu dong quet Google Sheet va nhan don moi lien tuc moi 30 giay
# ==============================================================================

set -e
cd "$(dirname "$0")"

# Reset quarantine
if command -v xattr &>/dev/null; then
    xattr -dr com.apple.quarantine . 2>/dev/null || true
fi

echo "========================================================================"
echo "   BOT TU DONG NHAN DON (PHUC) | MUNCI STUDIO 24/24"
echo "   Chu ky quet: Moi 30 giay | Nhan Ctrl + C de dung."
echo "========================================================================"
echo ""

VENV_DIR=".venv"
if [ -f "$VENV_DIR/bin/python" ]; then
    PY_EXEC="$VENV_DIR/bin/python"
else
    if command -v python3 &>/dev/null; then
        PY_EXEC="python3"
    else
        echo "[ERROR] Chua co Python 3 tren may. Vui long chay run_mac.command truoc de tu dong cai dat!"
        read -p "Nhan Enter de thoat..."
        exit 1
    fi
fi

echo "[*] Dang chay bot treo ngam 24/24..."
exec "$PY_EXEC" src/auto_claim_bot.py --interval 30
