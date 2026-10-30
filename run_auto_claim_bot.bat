@echo off
chcp 65001 >nul
title BOT AUTO-NHẬN VIỆC (PHÚC) - MUNCI STUDIO

echo ======================================================================
echo    BOT TỰ ĐỘNG QUÉT CẢ 2 BẢNG GOOGLE SHEET & NHẬN ĐƠN MỚI CHO PHÚC
echo    Chạy ngầm liên tục mỗi 30 giây để bắt đơn ngay khi khách chọn ảnh!
echo ======================================================================
echo.

cd /d "%~dp0"

echo [1] Đang khởi động Bot quét tự động...
echo Nhấn Ctrl + C để tạm dừng bot bất kỳ lúc nào.
echo.

python src/auto_claim_bot.py --interval 30

pause
