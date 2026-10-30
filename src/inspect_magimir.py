from __future__ import annotations
"""
MAGIMIR UI Inspector Tool
-------------------------
Run this standalone script to inspect the window hierarchy, control identifiers,
and automation elements of MAGIMIR on your system (Windows / macOS).

Usage:
    python src/inspect_magimir.py
"""

import sys
import platform
import subprocess

# Ensure UTF-8 output on Windows terminal
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def inspect_windows():
    print("=" * 60)
    print("WINDOWS MAGIMIR INSPECTOR (pywinauto)")
    print("=" * 60)
    try:
        import psutil
        import pywinauto

        # 1. Tìm tiến trình MagiMir
        magi_pids = set()
        for p in psutil.process_iter(['pid', 'name', 'exe']):
            pname = (p.name() or '').lower()
            if "magi" in pname or "retouch" in pname:
                print(f"[TIẾN TRÌNH TÌM THẤY] PID: {p.pid} | Tên: {p.name()} | Đường dẫn: {p.info.get('exe')}")
                magi_pids.add(p.pid)

        if not magi_pids:
            print("[-] Không tìm thấy tiến trình nào của MagiMir đang chạy.")
            print("--> Vui lòng mở phần mềm MagiMir lên trước khi chạy công cụ này.")
            return

        # 2. Duyệt desktop UIA
        desktop = pywinauto.Desktop(backend="uia")
        windows = desktop.windows()
        found_windows = []

        for w in windows:
            try:
                title = w.window_text().strip()
                pid = w.process_id()
            except Exception:
                continue

            # Bỏ qua cửa sổ Terminal / Command Prompt chạy lệnh này
            if "inspect_magimir" in title.lower() or "cmd.exe" in title.lower() or "powershell" in title.lower():
                continue

            # Kiểm tra xem cửa sổ có thuộc PID của MagiMir hay title chứa magimir
            if pid in magi_pids or ("magi" in title.lower()):
                found_windows.append(w)

        if found_windows:
            for idx, w in enumerate(found_windows, 1):
                print(f"\n[{idx}] TÌM THẤY CỬA SỔ MAGIMIR: '{w.window_text()}' (PID: {w.process_id()})")
                print(f"    Handle: {w.handle} | Class: {w.class_name()}")
                print("-" * 50)
                print("    Cấu trúc điều khiển (Control Identifiers):")
                try:
                    win_spec = desktop.window(handle=w.handle)
                    win_spec.print_control_identifiers(depth=2)
                except Exception as e:
                    print(f"    Không thể in control identifiers: {e}")
        else:
            print("[-] Chưa bắt được cửa sổ giao diện chính của MagiMir qua UIA.")
            print("Danh sách tất cả các cửa sổ đang mở trên Desktop:")
            count = 0
            for w in windows:
                try:
                    t = w.window_text().strip()
                    if t and "antigravity" not in t.lower():
                        count += 1
                        print(f"  {count}. [PID: {w.process_id()}] '{t}' (Class: {w.class_name()})")
                        if count >= 20:
                            break
                except Exception:
                    pass

    except ImportError as ie:
        print(f"[-] Thiếu thư viện: {ie}. Hãy chạy: pip install pywinauto psutil")
    except Exception as e:
        print(f"[-] Lỗi kiểm tra Windows: {e}")


def inspect_mac():
    print("=" * 60)
    print("macOS MAGIMIR INSPECTOR (AppleScript / System Events)")
    print("=" * 60)
    script = """
    tell application "System Events"
        set appList to name of every application process
        return appList
    end tell
    """
    try:
        res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
        if res.returncode == 0:
            apps = res.stdout.strip().split(", ")
            magimir_apps = [a for a in apps if "magimir" in a.lower()]
            if magimir_apps:
                print(f"[FOUND] Phát hiện ứng dụng MAGIMIR đang chạy: {magimir_apps}")
            else:
                print("[-] Không thấy process nào có tên MAGIMIR.")
                print(f"Danh sách ứng dụng đang chạy: {', '.join(apps[:15])}...")
        else:
            print(f"[-] AppleScript error: {res.stderr}")
    except Exception as e:
        print(f"[-] Lỗi kiểm tra macOS: {e}")


def main():
    os_name = platform.system().lower()
    print(f"Hệ điều hành hiện tại: {platform.system()} ({platform.machine()})")
    if os_name == "windows":
        inspect_windows()
    elif os_name == "darwin":
        inspect_mac()
    else:
        print(f"Chưa hỗ trợ inspect trên nền tảng: {os_name}")


if __name__ == "__main__":
    main()
