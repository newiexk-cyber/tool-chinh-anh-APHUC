from __future__ import annotations
import os
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable, Optional
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

from src.utils import get_logger, normalize_vn

logger = get_logger("magimir_controller")

PHOTO_EXTS = {".jpg", ".jpeg", ".png", ".cr2", ".arw", ".nef", ".dng"}


def is_magimir_running() -> bool:
    """
    Checks whether MAGIMIR desktop application is currently running.
    Cross-platform check for Windows and macOS.
    """
    sys_name = platform.system().lower()

    if sys_name == "windows":
        # 1. Check via psutil for MagiMir / MagiMir2
        try:
            import psutil
            for p in psutil.process_iter(["name"]):
                pname = (p.name() or "").lower()
                if "magimir" in pname:
                    return True
        except Exception:
            pass

        # 2. Check via pywinauto windows
        try:
            import pywinauto

            desktop = pywinauto.Desktop(backend="uia")
            windows = desktop.windows()
            for w in windows:
                title = w.window_text().lower()
                if "magimir" in title and "inspect" not in title:
                    return True
        except Exception:
            pass

        # 3. Fallback to tasklist command on Windows
        try:
            out = subprocess.check_output(
                ["tasklist"],
                stderr=subprocess.DEVNULL,
                text=True,
            )
            if "magimir" in out.lower():
                return True
        except Exception:
            pass
        return False

    elif sys_name == "darwin":
        # macOS AppleScript check
        try:
            script = 'tell application "System Events" to return (name of processes) contains "Magimir"'
            res = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                check=False,
            )
            return "true" in res.stdout.lower()
        except Exception:
            return False

    return False


def count_valid_photos(folder: Path | str) -> int:
    """
    Counts complete photo files in folder:
    - Must be a regular file
    - Extension must be in PHOTO_EXTS
    - Must have file size > 0
    - Must NOT end with .tmp or .crdownload
    """
    p = Path(folder)
    if not p.exists() or not p.is_dir():
        return 0

    count = 0
    try:
        for f in p.iterdir():
            if not f.is_file():
                continue
            if f.name.endswith(".tmp") or f.name.endswith(".crdownload"):
                continue
            if f.suffix.lower() in PHOTO_EXTS and f.stat().st_size > 0:
                count += 1
    except Exception:
        pass
    return count


def find_magimir_done_folder(cust_workspace: Path, chon_dir: Path) -> Optional[Path]:
    """
    Tự động tìm thư mục DONE do MagiMir sinh ra khi người dùng export ảnh:
    Kiểm tra cả:
    1. chon_dir / 'DONE' hoặc chon_dir / 'done'
    2. cust_workspace / 'DONE' hoặc cust_workspace / 'done'
    3. Thư mục con có tên chứa DONE/done và có ảnh
    """
    search_dirs = [chon_dir, cust_workspace]
    for parent in search_dirs:
        if not parent or not parent.exists():
            continue
        try:
            for item in parent.iterdir():
                if item.is_dir() and item.name.upper() in ["DONE", "DA_CHON_DONE"]:
                    return item
        except Exception:
            pass
    return None


def is_folder_finished_exporting(
    done_folder: Path,
    expected_count: int,
) -> tuple[bool, int]:
    """
    Kiểm tra xem thư mục DONE đã xuất xong ảnh hay chưa:
    - Có ít nhất 1 ảnh hợp lệ
    - Đạt đủ số lượng expected_count (hoặc >= expected_count)
    - Không còn file tạm (.tmp, .crdownload...)
    """
    if not done_folder or not done_folder.exists():
        return False, 0

    current_count = count_valid_photos(done_folder)
    if current_count == 0:
        return False, 0

    try:
        has_tmp = any(
            f.name.endswith(".tmp") or f.name.endswith(".crdownload")
            for f in done_folder.iterdir()
            if f.is_file()
        )
        if has_tmp:
            return False, current_count
    except Exception:
        pass

    if current_count >= expected_count and expected_count > 0:
        return True, current_count

    return False, current_count

def simulate_retouch_photos(
    chon_dir: Path,
    done_dir: Path,
    preset_name: str = "Default_Preset",
    delay_per_photo: float = 0.25,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
) -> bool:
    """
    Simulates photo retouching using Pillow enhancements when MAGIMIR is not running
    or when simulation mode is active.
    Transforms each photo from chon_dir into a retouched photo in done_dir.
    """
    done_dir.mkdir(parents=True, exist_ok=True)
    source_photos = [
        f
        for f in chon_dir.iterdir()
        if f.is_file() and f.suffix.lower() in PHOTO_EXTENSIONS_SIM and f.stat().st_size > 0
    ]

    total = len(source_photos)
    if total == 0:
        logger.warning(f"Không có ảnh nào trong {chon_dir} để xử lý.")
        return False

    logger.info(
        f"[SIMULATION] Bắt đầu giả lập chỉnh {total} ảnh qua Preset '{preset_name}'..."
    )

    for idx, photo_path in enumerate(source_photos, start=1):
        target_name = photo_path.name
        if not target_name.upper().endswith("_DONE.JPG"):
            stem = photo_path.stem.replace("_CHON", "")
            target_name = f"{stem}_DONE.jpg"

        dest_path = done_dir / target_name

        try:
            with Image.open(photo_path) as raw_img:
                from PIL import ImageOps
                img = ImageOps.exif_transpose(raw_img)

                # Apply simulated retouch: sharpen, enhance color & contrast
                enhanced = img.filter(ImageFilter.UnsharpMask(radius=2, percent=150))
                enhancer = ImageEnhance.Color(enhanced)
                enhanced = enhancer.enhance(1.15)
                contrast = ImageEnhance.Contrast(enhanced)
                enhanced = contrast.enhance(1.08)

                enhanced.save(dest_path, format="JPEG", quality=95)
        except Exception as e:
            logger.warning(f"Lỗi khi xử lý ảnh {photo_path.name}: {e}. Sao chép trực tiếp.")
            # Fallback to copying
            import shutil

            shutil.copy2(photo_path, dest_path)

        if progress_callback:
            progress_callback(idx, total, target_name)

        time.sleep(delay_per_photo)

    logger.info(f"[SIMULATION] Đã hoàn tất chỉnh {total} ảnh vào: {done_dir}")
    return True


PHOTO_EXTENSIONS_SIM = {".jpg", ".jpeg", ".png", ".cr2", ".arw", ".nef", ".dng"}


TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "assets" / "templates"


def find_on_screen(template_name: str, confidence: float = 0.8) -> Optional[tuple[int, int]]:
    """
    Locates a template image on screen using OpenCV template matching.
    Returns (center_x, center_y) or None if not found.
    """
    try:
        attach_default_desktop()
        import cv2
        import numpy as np
        import pyautogui

        tpl_path = TEMPLATES_DIR / template_name
        if not tpl_path.exists():
            return None

        tpl = cv2.imread(str(tpl_path))
        if tpl is None:
            return None
        th, tw = tpl.shape[:2]

        screenshot = pyautogui.screenshot()
        screen_bgr = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

        res = cv2.matchTemplate(screen_bgr, tpl, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)

        if max_val >= confidence:
            center_x = max_loc[0] + tw // 2
            center_y = max_loc[1] + th // 2
            logger.info(f"Đã tìm thấy '{template_name}' trên màn hình tại ({center_x}, {center_y}) với độ khớp {max_val:.2f}")
            return center_x, center_y
        return None
    except Exception as e:
        logger.debug(f"Không thể tìm template '{template_name}': {e}")
        return None


MAGIMIR_EXE_PATH = Path(r"D:\02_HinhAnh_Media\PTS\MagiMir2\MagiMir2.exe")


def attach_default_desktop():
    """Attaches the current thread to the interactive 'default' desktop on Windows."""
    if platform.system().lower() == "windows":
        try:
            import ctypes
            u = ctypes.windll.user32
            hdesk = u.OpenDesktopW("default", 0, False, 0x01FF)
            if hdesk:
                u.SetThreadDesktop(hdesk)
        except Exception:
            pass


def get_magimir_hwnd() -> Optional[int]:
    """Finds HWND of MagiMir window by class name or window title."""
    attach_default_desktop()
    try:
        import win32gui
        import win32process
        import psutil

        # First by class
        hwnd = win32gui.FindWindow("MAGIC_MIRROR_FLUTTER_RUNNER_WINDOW", None)
        if hwnd and win32gui.IsWindow(hwnd):
            return hwnd

        # Second by process PID and title
        magimir_pids = set()
        for p in psutil.process_iter(["pid", "name"]):
            pname = (p.info["name"] or "").lower()
            if "magimir" in pname:
                magimir_pids.add(p.info["pid"])

        found = []
        def enum_cb(h, acc):
            try:
                _, pid = win32process.GetWindowThreadProcessId(h)
                txt = win32gui.GetWindowText(h).lower()
                cls = win32gui.GetClassName(h).lower()
                if pid in magimir_pids or "magimir" in txt or "magic_mirror" in cls:
                    if win32gui.IsWindowVisible(h):
                        acc.append(h)
            except Exception:
                pass
            return True

        win32gui.EnumWindows(enum_cb, found)
        if found:
            return found[0]
    except Exception:
        pass
    return None


def force_focus_window(hwnd: int) -> bool:
    """Forces window to the foreground using Windows AttachThreadInput API."""
    try:
        import ctypes
        import win32con
        import win32gui
        import win32process

        fore_hwnd = win32gui.GetForegroundWindow()
        if fore_hwnd == hwnd:
            return True

        fore_thread, _ = win32process.GetWindowThreadProcessId(fore_hwnd)
        app_thread, _ = win32process.GetWindowThreadProcessId(hwnd)

        user32 = ctypes.windll.user32
        if fore_thread != app_thread:
            user32.AttachThreadInput(fore_thread, app_thread, True)
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(hwnd)
            win32gui.BringWindowToTop(hwnd)
            user32.AttachThreadInput(fore_thread, app_thread, False)
        else:
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(hwnd)
            win32gui.BringWindowToTop(hwnd)
        time.sleep(0.5)
        return True
    except Exception as e:
        logger.warning(f"Lỗi khi force_focus_window: {e}")
        return False


def ensure_magimir_ready() -> Optional[int]:
    """
    Ensures MagiMir 2 is running and focused as active foreground window.
    If not running, attempts to launch MagiMir2.exe from D:\\02_HinhAnh_Media\\PTS\\MagiMir2\\MagiMir2.exe.
    """
    hwnd = get_magimir_hwnd()
    if not hwnd and MAGIMIR_EXE_PATH.exists():
        logger.info(f"MagiMir chưa mở. Đang tự động khởi chạy từ: {MAGIMIR_EXE_PATH}...")
        try:
            subprocess.Popen([str(MAGIMIR_EXE_PATH)], cwd=str(MAGIMIR_EXE_PATH.parent))
            for _ in range(15):
                time.sleep(1.0)
                hwnd = get_magimir_hwnd()
                if hwnd:
                    logger.info("MagiMir 2 đã khởi động thành công!")
                    time.sleep(2.0)
                    break
        except Exception as e:
            logger.warning(f"Không thể khởi chạy MagiMir tự động: {e}")

    if hwnd:
        force_focus_window(hwnd)
        time.sleep(0.8)
        return hwnd
    return None


def control_magimir_windows(
    chon_dir: Path,
    done_dir: Path,
    preset_name: str = "2",
    timeout_seconds: int = 180,
) -> bool:
    """
    Automates MAGIMIR 2 on Windows based on calibrated video workflow:
    1. Focuses MAGIMIR window
    2. Opens 'Import Folder' -> Selects chon_dir in native Windows dialog
    3. Selects all photos with Ctrl+A
    4. Applies configured Preset (Preset 1, 2, or 3, default: 2)
    5. Clicks 'Export' -> Selects 'New folder under original directory' -> 'done' -> clicks Export
    6. Waits for exported photos to finish in {chon_dir}/done/ and moves them to done_dir
    7. Returns to 'All Projects'
    """
    try:
        import pyautogui
        import pyperclip
        import win32gui

        logger.info("[WINDOWS] Đang kết nối tới cửa sổ ứng dụng MAGIMIR 2...")
        hwnd = ensure_magimir_ready()
        if not hwnd:
            logger.warning("[WINDOWS] Không tìm thấy hoặc không thể mở ứng dụng MAGIMIR.")
            return False

        # Verify active window is not browser
        active_hwnd = win32gui.GetForegroundWindow()
        active_title = win32gui.GetWindowText(active_hwnd).lower()
        if any(b in active_title for b in ["brave", "chrome", "edge", "firefox"]):
            logger.info("Cửa sổ trình duyệt vẫn đang active, thử force focus lại MagiMir...")
            force_focus_window(hwnd)
            time.sleep(0.8)

        # Step 1: If currently inside a project, click 'All Projects' to return home
        all_proj_loc = find_on_screen("tpl_all_projects.png", confidence=0.8)
        if all_proj_loc:
            logger.info("MagiMir đang ở trong project cũ, click 'All Projects' để về trang chủ...")
            pyautogui.click(all_proj_loc[0], all_proj_loc[1])
            time.sleep(1.5)

        # Step 2: Click 'Import Folder'
        # In MagiMir home screen, Card 1 first shows "Open folder / Select images".
        # Clicking it expands into "Import Images" and "Import Folder".
        open_folder_loc = find_on_screen("card1_open_folder.png", confidence=0.75)
        if open_folder_loc:
            logger.info("Tìm thấy Card 1 (Open folder / Select images), click để mở menu...")
            pyautogui.click(open_folder_loc[0], open_folder_loc[1])
            time.sleep(0.8)

        import_loc = find_on_screen("tpl_import_folder.png", confidence=0.75) or find_on_screen("card1.png", confidence=0.75)
        if import_loc:
            # Click near 'Import Folder' inside Card 1
            pyautogui.click(import_loc[0], import_loc[1])
            time.sleep(1.2)
        else:
            # Fallback hotkey or relative click on left card
            logger.info("Không nhận dạng template Import Folder, click theo toạ độ chuẩn (105, 205)...")
            pyautogui.click(105, 205)
            time.sleep(1.2)

        # Step 3: Handle native Windows 'Select Folder' dialog
        logger.info(f"Đang nhập đường dẫn thư mục vào hộp thoại: {chon_dir.resolve()}")
        pyperclip.copy(str(chon_dir.resolve()))
        time.sleep(0.5)

        # Focus dialog path edit box and paste
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.5)
        pyautogui.press("enter")
        time.sleep(0.8)
        # Confirm folder selection (Enter or Alt+S)
        pyautogui.press("enter")
        time.sleep(2.5)

        # Step 4: Ensure all loaded photos are selected with Ctrl+A
        logger.info("Đang chọn toàn bộ ảnh (Ctrl + A)...")
        pyautogui.hotkey("ctrl", "a")
        time.sleep(0.8)

        # Step 5: Select Preset
        # Support preset "1", "2", "3" or default to "2"
        preset_key = "2"
        if "1" in str(preset_name):
            preset_key = "1"
        elif "3" in str(preset_name):
            preset_key = "3"

        preset_loc = find_on_screen(f"tpl_preset_{preset_key}.png", confidence=0.8)
        if preset_loc:
            logger.info(f"Đã tìm thấy Preset {preset_key}, tiến hành click...")
            pyautogui.click(preset_loc[0], preset_loc[1])
        else:
            # Fallback coordinate for Preset 2 (around x=1665, y=290 on 1080p)
            logger.info(f"Click Preset {preset_key} theo toạ độ tương đối...")
            y_pos = 240 if preset_key == "1" else (290 if preset_key == "2" else 340)
            pyautogui.click(1665, y_pos)

        time.sleep(1.5)

        # Step 6: Click 'Export' at top right
        export_btn_loc = find_on_screen("tpl_export_top.png", confidence=0.8)
        if export_btn_loc:
            pyautogui.click(export_btn_loc[0], export_btn_loc[1])
        else:
            # Fallback coordinate (approx x=1718, y=53)
            logger.info("Click Export top bar theo toạ độ (1718, 53)...")
            pyautogui.click(1718, 53)

        time.sleep(1.5)

        # Step 7: Configure Export Dialog
        # Look for dialog template
        export_dialog_loc = find_on_screen("tpl_blue_export_btn.png", confidence=0.75)
        if export_dialog_loc:
            # Click 'New folder under original directory' (top of dialog template)
            dx, dy = export_dialog_loc
            pyautogui.click(dx - 50, dy - 80)
            time.sleep(0.3)

            # Click folder name input box and ensure it is 'done'
            pyautogui.click(dx - 50, dy - 40)
            pyautogui.hotkey("ctrl", "a")
            pyautogui.typewrite("done")
            time.sleep(0.3)

            # Click the blue 'Export' button
            pyautogui.click(dx + 65, dy + 65)
        else:
            # Fallback to standard center coordinates of the Export modal
            logger.info("Click cấu hình hộp thoại Export theo toạ độ chuẩn...")
            # Click radio button (approx x=950, y=480)
            pyautogui.click(950, 480)
            time.sleep(0.3)
            # Click text box (approx x=950, y=520)
            pyautogui.click(950, 520)
            pyautogui.hotkey("ctrl", "a")
            pyautogui.typewrite("done")
            time.sleep(0.3)
            # Click blue Export button (approx x=1140, y=680)
            pyautogui.click(1140, 680)

        logger.info("[WINDOWS] Đã kích hoạt quá trình xuất ảnh trong MAGIMIR 2.")
        return True
    except Exception as e:
        logger.error(f"[WINDOWS] Lỗi khi điều khiển MAGIMIR: {e}")
        return False


def control_magimir_mac(chon_dir: Path, done_dir: Path, preset_name: str) -> bool:
    """
    Automates MAGIMIR on macOS Apple Silicon (Mac M1) using osascript,
    pbcopy, and Finder shortcut (Command + Shift + G).
    """
    try:
        import pyautogui

        logger.info("[macOS Apple Silicon] Đang kích hoạt ứng dụng MAGIMIR qua AppleScript...")

        # 1. Activate application MAGIMIR
        activate_script = 'tell application "Magimir" to activate'
        subprocess.run(["osascript", "-e", activate_script], check=False)
        time.sleep(1.0)

        # 2. Open Import Dialog via Command + O
        pyautogui.hotkey("command", "o")
        time.sleep(1.0)

        # 3. Use Finder shortcut Command + Shift + G to go to folder
        pyautogui.hotkey("command", "shift", "g")
        time.sleep(0.8)

        # Put chon_dir path to macOS clipboard using pbcopy
        p = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
        p.communicate(str(chon_dir.resolve()).encode("utf-8"))

        pyautogui.hotkey("command", "v")
        time.sleep(0.5)
        pyautogui.press("enter")
        time.sleep(0.5)
        pyautogui.press("enter")
        time.sleep(2.0)

        # 4. Trigger Export Dialog (Command + E)
        pyautogui.hotkey("command", "e")
        time.sleep(1.0)

        # Select done_dir via Command + Shift + G
        pyautogui.hotkey("command", "shift", "g")
        time.sleep(0.8)

        p = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
        p.communicate(str(done_dir.resolve()).encode("utf-8"))

        pyautogui.hotkey("command", "v")
        time.sleep(0.5)
        pyautogui.press("enter")
        time.sleep(0.5)
        pyautogui.press("enter")

        return True
    except Exception as e:
        logger.error(f"[macOS] Lỗi khi điều khiển MAGIMIR: {e}")
        return False


def process_customer_photos(
    chon_dir: Path | str,
    done_dir: Path | str,
    preset_name: str = "Default_Preset",
    simulate_if_missing: bool = True,
    timeout_seconds: int = 180,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
) -> bool:
    """
    Coordinates photo processing:
    1. Checks if MAGIMIR is active. If not or simulation mode is requested,
       uses simulate_retouch_photos with visual progress.
    2. If active, triggers Windows/macOS desktop automation.
    3. Runs File Watcher polling done_dir until all original photos are exported.
    """
    c_path = Path(chon_dir)
    d_path = Path(done_dir)
    d_path.mkdir(parents=True, exist_ok=True)

    input_count = count_valid_photos(c_path)
    if input_count == 0:
        logger.warning(f"Không có ảnh hợp lệ nào trong {c_path}.")
        return False

    running = is_magimir_running()
    sys_name = platform.system().lower()

    if not running or simulate_if_missing:
        if not running:
            logger.info("MAGIMIR chưa mở. Tự động chuyển sang chế độ mô phỏng chuyên nghiệp.")
        else:
            logger.info("Chế độ mô phỏng được bật chủ động.")
        return simulate_retouch_photos(
            chon_dir=c_path,
            done_dir=d_path,
            preset_name=preset_name,
            delay_per_photo=0.15,
            progress_callback=progress_callback,
        )

    # Real desktop automation
    success = False
    if sys_name == "windows":
        success = control_magimir_windows(c_path, d_path, preset_name)
    elif sys_name == "darwin":
        success = control_magimir_mac(c_path, d_path, preset_name)
    else:
        logger.warning(f"Hệ điều hành {sys_name} chưa hỗ trợ desktop automation. Dùng simulation.")
        return simulate_retouch_photos(
            chon_dir=c_path,
            done_dir=d_path,
            preset_name=preset_name,
            delay_per_photo=0.15,
            progress_callback=progress_callback,
        )

    if not success:
        logger.error("Điều khiển MAGIMIR 2 thất bại hoặc không thể mở được hộp thoại chọn thư mục trong MagiMir!")
        return False

def wait_for_exported_photos(
    chon_dir: Path,
    done_dir: Path,
    expected_count: int,
    timeout_seconds: int = 600,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
) -> bool:
    """
    Watches for exported photos from MagiMir in {chon_dir}/done/ or {done_dir}.
    Copies any exported photos into done_dir when ready.
    """
    magimir_export_dir = chon_dir / "done"
    logger.info(
        f"File Watcher đang đợi {expected_count} ảnh xuất ra tại {done_dir} hoặc {magimir_export_dir}..."
    )
    start_time = time.time()
    last_reported = 0

    while time.time() - start_time < timeout_seconds:
        count_in_d = count_valid_photos(done_dir)
        count_in_sub = count_valid_photos(magimir_export_dir) if magimir_export_dir.exists() else 0
        current_done = max(count_in_d, count_in_sub)

        if current_done != last_reported:
            last_reported = current_done
            logger.info(f"Tiến độ xuất ảnh: {current_done}/{expected_count}")
            if progress_callback:
                progress_callback(current_done, expected_count, f"Đã xuất {current_done}/{expected_count} ảnh")

        if current_done >= expected_count:
            time.sleep(1.5)
            # Sync photos to done_dir if they are in chon_dir / 'done'
            if magimir_export_dir.exists() and done_dir.resolve() != magimir_export_dir.resolve():
                import shutil
                for exported_file in magimir_export_dir.iterdir():
                    if exported_file.is_file() and exported_file.suffix.lower() in PHOTO_EXTS:
                        shutil.copy2(exported_file, done_dir / exported_file.name)
            return True

        time.sleep(1.0)

    # Partial export sync on timeout
    if magimir_export_dir.exists() and done_dir.resolve() != magimir_export_dir.resolve():
        import shutil
        for exported_file in magimir_export_dir.iterdir():
            if exported_file.is_file() and exported_file.suffix.lower() in PHOTO_EXTS:
                shutil.copy2(exported_file, done_dir / exported_file.name)
    return count_valid_photos(done_dir) > 0
