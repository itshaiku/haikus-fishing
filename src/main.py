import os
import sys

# Must be set as early as possible (before numpy/cv2/torch) to avoid OpenMP
# runtime conflicts that can surface as WinError 1114 when loading torch DLLs.
os.environ.setdefault('KMP_DUPLICATE_LIB_OK', 'TRUE')
os.environ.setdefault('OMP_NUM_THREADS', '1')

# Redirect stdout/stderr when running as frozen EXE to prevent freezing with console=False
if getattr(sys, 'frozen', False):
    class DummyFile:
        def write(self, x): pass
        def flush(self): pass
    sys.stdout = DummyFile()
    sys.stderr = DummyFile()

def _get_macro_settings_path() -> str:
    """Return the filesystem path for macro_settings.json.

    In frozen (PyInstaller) builds, this should be a persistent, user-writable
    location (AppData) rather than the temporary _MEIPASS extraction directory.
    """

    override = os.environ.get('HAIKU_FISHING_CONFIG_PATH')
    if override:
        return override

    if getattr(sys, 'frozen', False):
        base = os.environ.get('APPDATA') or os.environ.get('LOCALAPPDATA') or os.path.expanduser('~')
        return os.path.join(base, 'Haiku Fishing', 'macro_settings.json')

    project_root = os.path.dirname(os.path.dirname(__file__))
    return os.path.join(project_root, 'macro_settings.json')

def _add_dll_search_dir(path: str) -> None:
    try:
        if not path or not os.path.isdir(path):
            return
        if hasattr(os, 'add_dll_directory'):
            os.add_dll_directory(path)
        os.environ['PATH'] = path + os.pathsep + os.environ.get('PATH', '')
    except Exception:
        pass

def _bootstrap_frozen_dlls() -> None:
    if not getattr(sys, 'frozen', False):
        return

    candidates: list[str] = []

    # onefile build: extracted to a temp _MEIPASS directory.
    if hasattr(sys, '_MEIPASS'):
        candidates.append(os.path.join(sys._MEIPASS, 'torch', 'lib'))
        candidates.append(os.path.join(sys._MEIPASS, 'cv2'))
        candidates.append(sys._MEIPASS)

    # onedir build: packaged under dist/<app>/_internal
    try:
        exe_dir = os.path.dirname(sys.executable)
        internal_dir = os.path.join(exe_dir, '_internal')
        candidates.append(os.path.join(internal_dir, 'torch', 'lib'))
        candidates.append(os.path.join(internal_dir, 'cv2'))
        candidates.append(os.path.join(internal_dir, 'numpy.libs'))
        candidates.append(internal_dir)
        candidates.append(exe_dir)
    except Exception:
        pass

    seen: set[str] = set()
    for path in candidates:
        if path and path not in seen:
            seen.add(path)
            _add_dll_search_dir(path)

    # Preload Intel OpenMP runtime early to reduce WinError 1114 during torch init.
    try:
        import ctypes
        torch_lib_dir = None

        for base in seen:
            libiomp = os.path.join(base, 'libiomp5md.dll')
            if os.path.isfile(libiomp):
                ctypes.CDLL(libiomp)
                torch_lib_dir = base
                break

        # If we can locate torch\lib, eagerly load core DLLs so later imports do
        # not fail due to loader path / init quirks under PyInstaller.
        if torch_lib_dir and os.path.isfile(os.path.join(torch_lib_dir, 'c10.dll')):
            for dll_name in ('c10.dll', 'torch_cpu.dll', 'torch_python.dll', 'torch_global_deps.dll'):
                dll_path = os.path.join(torch_lib_dir, dll_name)
                if os.path.isfile(dll_path):
                    try:
                        ctypes.CDLL(dll_path)
                    except Exception:
                        pass
    except Exception:
        pass


# Keep --ocr-selftest as isolated as possible: avoid preloading DLLs before it runs.
if '--ocr-selftest' not in sys.argv:
    _bootstrap_frozen_dlls()

if '--print-config-path' in sys.argv:
    print(_get_macro_settings_path())
    raise SystemExit(0)


def _run_ocr_selftest_and_exit() -> None:
    """Runs a focused OCR/torch loader self-test and exits.

    This runs *before* importing other third-party modules to reduce DLL/runtime
    conflicts and to provide a clean error signal in frozen builds.
    """

    import ctypes

    def _print_kv(key: str, value) -> None:
        try:
            print(f"{key}: {value}")
        except Exception:
            pass

    def _get_module_path(handle) -> str | None:
        try:
            buf = ctypes.create_unicode_buffer(4096)
            ctypes.windll.kernel32.GetModuleFileNameW(ctypes.c_void_p(handle), buf, len(buf))
            return buf.value or None
        except Exception:
            return None

    def _try_load_abs(dll_path: str) -> tuple[bool, str]:
        """Attempt to load a DLL and return (ok, info).

        Uses kernel32.LoadLibraryExW to avoid PyInstaller's ctypes shim hiding
        real Win32 error codes.
        """

        kernel32 = ctypes.windll.kernel32
        kernel32.GetLastError.restype = ctypes.c_uint32

        # Flags recommended for extension-style DLL loading on modern Windows.
        LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR = 0x00000100
        LOAD_LIBRARY_SEARCH_DEFAULT_DIRS = 0x00001000

        # Report if already loaded.
        already = None
        try:
            already_handle = kernel32.GetModuleHandleW(os.path.basename(dll_path))
            if already_handle:
                already = _get_module_path(already_handle) or '(loaded)'
        except Exception:
            pass

        try:
            handle = kernel32.LoadLibraryExW(dll_path, None, LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR | LOAD_LIBRARY_SEARCH_DEFAULT_DIRS)
            if not handle:
                err = kernel32.GetLastError()
                return False, f"already={already} winerror={err}"

            loaded_path = _get_module_path(handle) or dll_path
            return True, f"already={already} loaded={loaded_path}"
        except Exception as e:
            return False, f"already={already} exc={type(e).__name__} {e}"

    def _existing_dir(paths: list[str]) -> list[str]:
        out: list[str] = []
        for p in paths:
            try:
                if p and os.path.isdir(p):
                    out.append(p)
            except Exception:
                pass
        return out

    print('OCR_SELFTEST: BEGIN')
    _print_kv('sys.version', sys.version.replace('\n', ' '))
    _print_kv('sys.executable', sys.executable)
    _print_kv('sys.frozen', getattr(sys, 'frozen', False))
    _print_kv('sys._MEIPASS', getattr(sys, '_MEIPASS', None))
    _print_kv('KMP_DUPLICATE_LIB_OK', os.environ.get('KMP_DUPLICATE_LIB_OK'))
    _print_kv('OMP_NUM_THREADS', os.environ.get('OMP_NUM_THREADS'))

    exe_dir = os.path.dirname(sys.executable)
    internal_dir = os.path.join(exe_dir, '_internal')

    candidate_dirs = _existing_dir([
        getattr(sys, '_MEIPASS', ''),
        internal_dir,
        exe_dir,
        os.path.join(getattr(sys, '_MEIPASS', ''), 'torch', 'lib'),
        os.path.join(internal_dir, 'torch', 'lib'),
        os.path.join(getattr(sys, '_MEIPASS', ''), 'numpy.libs'),
        os.path.join(internal_dir, 'numpy.libs'),
    ])
    _print_kv('dll_search_dirs', candidate_dirs)
    for d in candidate_dirs:
        _add_dll_search_dir(d)

    torch_lib_dir = None
    for d in (
        os.path.join(getattr(sys, '_MEIPASS', ''), 'torch', 'lib'),
        os.path.join(internal_dir, 'torch', 'lib'),
    ):
        if d and os.path.isdir(d):
            torch_lib_dir = d
            break
    _print_kv('torch_lib_dir', torch_lib_dir)

    # Report multiple libiomp5md.dll copies if present.
    libiomp_hits: list[str] = []
    if torch_lib_dir:
        # Search nearby dirs first to keep output small.
        for d in candidate_dirs:
            p = os.path.join(d, 'libiomp5md.dll')
            if os.path.isfile(p):
                libiomp_hits.append(p)
    _print_kv('libiomp5md.dll_candidates', libiomp_hits)

    dll_ok = True
    if torch_lib_dir:
        for dll_name in ('libiomp5md.dll', 'torch_global_deps.dll', 'c10.dll', 'torch_cpu.dll', 'torch_python.dll'):
            dll_path = os.path.join(torch_lib_dir, dll_name)
            if not os.path.isfile(dll_path):
                continue
            ok, info = _try_load_abs(dll_path)
            print(f"LOAD {dll_name}: {'OK' if ok else 'FAIL'} ({info})")
            if not ok:
                dll_ok = False

    torch_ok = False
    try:
        import torch  # noqa: F401
        import torch as _torch
        _print_kv('torch.__version__', getattr(_torch, '__version__', None))
        _print_kv('torch.__file__', getattr(_torch, '__file__', None))
        torch_ok = True
    except Exception as e:
        print(f"IMPORT torch: FAIL ({e})")

    reader_ok = False
    try:
        import easyocr  # noqa: F401
        import easyocr as _easyocr
        _print_kv('easyocr.__version__', getattr(_easyocr, '__version__', None))
        # Use download_enabled=False for a fast, offline-friendly signal.
        _ = _easyocr.Reader(['en'], gpu=False, verbose=False, download_enabled=False)
        reader_ok = True
        print('EASYOCR Reader: OK')
    except Exception as e:
        print(f"EASYOCR Reader: FAIL ({e})")

    ok = bool(dll_ok and torch_ok and reader_ok)
    print('OCR_SELFTEST: OK' if ok else 'OCR_SELFTEST: FAIL')
    raise SystemExit(0 if ok else 2)


if '--ocr-selftest' in sys.argv:
    _run_ocr_selftest_and_exit()

import webview
import threading
import time
import pyautogui
import keyboard
import ctypes
from ctypes import wintypes
import mss
import numpy as np
import json
from pathlib import Path
import tkinter as tk
from watchdog import WatchdogMonitor

class StatsOverlay:
    def __init__(self, api):
        self.api = api
        self.window = None
        self.visible = False
        self.update_job = None
        self.thread = None
        
    def show(self):
        if self.visible:
            return
            
        self.visible = True
        
        # If window already exists, just show it
        if self.window:
            try:
                self.window.deiconify()
                self.window.lift()
                self.update_stats()
                print("Stats overlay window shown")
                return
            except:
                self.window = None
        
        print("Creating stats overlay window in separate thread...")
        
        def create_window():
            try:
                self.window = tk.Tk()
                self.window.title("")
                self.window.overrideredirect(True)
                self.window.attributes('-topmost', True)
                self.window.attributes('-alpha', 0.95)
                self.window.configure(bg='#1a1a1a')
                
                # Position at top-right of screen
                width = 280
                height = 130
                screen_width = self.window.winfo_screenwidth()
                x = screen_width - width - 20
                y = 20
                print(f"Positioning stats window at: {x}, {y}")
                self.window.geometry(f"{width}x{height}+{x}+{y}")
                
                # Make window draggable
                self.drag_start_x = 0
                self.drag_start_y = 0
                
                def start_drag(event):
                    self.drag_start_x = event.x
                    self.drag_start_y = event.y
                
                def do_drag(event):
                    x = self.window.winfo_x() + event.x - self.drag_start_x
                    y = self.window.winfo_y() + event.y - self.drag_start_y
                    self.window.geometry(f"+{x}+{y}")
                
                self.window.bind('<Button-1>', start_drag)
                self.window.bind('<B1-Motion>', do_drag)
                
                # Container with purple border
                border_frame = tk.Frame(self.window, bg='#9333ea', padx=2, pady=2)
                border_frame.pack(fill='both', expand=True)
                
                content_frame = tk.Frame(border_frame, bg='#1a1a1a', padx=12, pady=10)
                content_frame.pack(fill='both', expand=True)
                
                # Bind drag events to container frames too
                border_frame.bind('<Button-1>', start_drag)
                border_frame.bind('<B1-Motion>', do_drag)
                content_frame.bind('<Button-1>', start_drag)
                content_frame.bind('<B1-Motion>', do_drag)
                
                # Title (no icon)
                title_label = tk.Label(
                    content_frame,
                    text="SESSION STATS",
                    font=('Segoe UI', 10, 'bold'),
                    fg='#ffffff',
                    bg='#1a1a1a'
                )
                title_label.pack(pady=(0, 8))
                title_label.bind('<Button-1>', start_drag)
                title_label.bind('<B1-Motion>', do_drag)
                
                # Time display - centered and bigger
                self.time_label = tk.Label(
                    content_frame,
                    text="00:00:00",
                    font=('Segoe UI', 16, 'bold'),
                    fg='#ffffff',
                    bg='#1a1a1a'
                )
                self.time_label.pack(pady=(0, 8))
                self.time_label.bind('<Button-1>', start_drag)
                self.time_label.bind('<B1-Motion>', do_drag)
                
                # Stats row - horizontal layout with icons only
                stats_row = tk.Frame(content_frame, bg='#1a1a1a')
                stats_row.pack()
                
                # Fish
                fish_frame = tk.Frame(stats_row, bg='#1a1a1a')
                fish_frame.pack(side='left', padx=8)
                tk.Label(fish_frame, text="🐟", font=('Segoe UI', 12), fg='#ffffff', bg='#1a1a1a').pack(side='left')
                self.fish_label = tk.Label(fish_frame, text="0", font=('Segoe UI', 10, 'bold'), fg='#ffffff', bg='#1a1a1a')
                self.fish_label.pack(side='left', padx=(3, 0))
                
                # Fruits
                fruit_frame = tk.Frame(stats_row, bg='#1a1a1a')
                fruit_frame.pack(side='left', padx=8)
                tk.Label(fruit_frame, text="🍎", font=('Segoe UI', 12), fg='#ffffff', bg='#1a1a1a').pack(side='left')
                self.fruit_label = tk.Label(fruit_frame, text="0", font=('Segoe UI', 10, 'bold'), fg='#ffffff', bg='#1a1a1a')
                self.fruit_label.pack(side='left', padx=(3, 0))
                
                # Rate
                rate_frame = tk.Frame(stats_row, bg='#1a1a1a')
                rate_frame.pack(side='left', padx=8)
                tk.Label(rate_frame, text="📈", font=('Segoe UI', 12), fg='#ffffff', bg='#1a1a1a').pack(side='left')
                self.rate_label = tk.Label(rate_frame, text="0/hr", font=('Segoe UI', 10, 'bold'), fg='#ffffff', bg='#1a1a1a')
                self.rate_label.pack(side='left', padx=(3, 0))
                
                print("Stats overlay window created and shown!")
                
                self.update_stats()
                self.window.mainloop()
            except Exception as e:
                print(f"Error in stats overlay thread: {e}")
                import traceback
                traceback.print_exc()
        
        self.thread = threading.Thread(target=create_window, daemon=True)
        self.thread.start()
        
        # Give the window time to create
        time.sleep(0.2)
        print("Stats overlay thread started")
        
    def update_stats(self):
        if not self.visible or not self.window:
            return
            
        try:
            if self.window.winfo_exists():
                state = self.api.get_state()
                self.time_label.config(text=state['time_elapsed'])
                self.fish_label.config(text=str(state['fish_count']))
                self.fruit_label.config(text=str(state['fruit_count']))
                self.rate_label.config(text=f"{state['fish_per_hour']}/hr")
                
                self.update_job = self.window.after(1000, self.update_stats)
        except:
            pass
            
    def hide(self):
        self.visible = False
        
        if self.window:
            try:
                # Cancel the update timer
                if self.update_job:
                    self.window.after_cancel(self.update_job)
                    self.update_job = None
                
                # Hide the window (don't destroy it so we can show it again)
                self.window.withdraw()
                print("Stats overlay window hidden")
            except:
                pass

pyautogui.PAUSE = 0

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except:
        pass

# Windows API structures for SendInput (camera rotation)
class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))
    ]

class INPUT(ctypes.Structure):
    class _INPUT(ctypes.Union):
        _fields_ = [("mi", MOUSEINPUT)]
    _fields_ = [
        ("type", wintypes.DWORD),
        ("_input", _INPUT)
    ]

# Constants for SendInput
INPUT_MOUSE = 0
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010

class AreaSelector:
    def __init__(self, initial_box, callback):
        self.callback = callback
        
        self.window = tk.Tk()
        self.window.attributes('-alpha', 0.6)
        self.window.attributes('-topmost', True)
        self.window.overrideredirect(True)
        
        self.x1, self.y1 = initial_box['x1'], initial_box['y1']
        self.x2, self.y2 = initial_box['x2'], initial_box['y2']
        width = self.x2 - self.x1
        height = self.y2 - self.y1
        
        self.window.geometry(f"{width}x{height}+{self.x1}+{self.y1}")
        self.window.configure(bg='white')
        
        self.canvas = tk.Canvas(self.window, bg='white', highlightthickness=3, 
                               highlightbackground='black')
        self.canvas.pack(fill='both', expand=True)
        
        self.dragging = False
        self.resizing = False
        self.resize_edge = None
        self.start_x = 0
        self.start_y = 0
        self.start_window_x = 0
        self.start_window_y = 0
        self.resize_threshold = 10
        
        self.canvas.bind('<Button-1>', self.on_mouse_down)
        self.canvas.bind('<B1-Motion>', self.on_mouse_drag)
        self.canvas.bind('<ButtonRelease-1>', self.on_mouse_up)
        self.canvas.bind('<Motion>', self.on_mouse_move)
        
        self.window.bind('<F2>', lambda e: self.close())
        self.window.bind('<Escape>', lambda e: self.close())
        
    def on_mouse_move(self, event):
        x, y = event.x, event.y
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        
        at_left = x < self.resize_threshold
        at_right = x > width - self.resize_threshold
        at_top = y < self.resize_threshold
        at_bottom = y > height - self.resize_threshold
        
        if (at_left and at_top) or (at_right and at_bottom):
            self.canvas.config(cursor='size_nw_se')
        elif (at_right and at_top) or (at_left and at_bottom):
            self.canvas.config(cursor='size_ne_sw')
        elif at_left or at_right:
            self.canvas.config(cursor='size_we')
        elif at_top or at_bottom:
            self.canvas.config(cursor='size_ns')
        else:
            self.canvas.config(cursor='arrow')
    
    def on_mouse_down(self, event):
        self.start_x = event.x
        self.start_y = event.y
        self.start_window_x = self.window.winfo_x()
        self.start_window_y = self.window.winfo_y()
        
        x, y = event.x, event.y
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        
        at_left = x < self.resize_threshold
        at_right = x > width - self.resize_threshold
        at_top = y < self.resize_threshold
        at_bottom = y > height - self.resize_threshold
        
        if at_left or at_right or at_top or at_bottom:
            self.resizing = True
            self.resize_edge = {
                'left': at_left, 'right': at_right,
                'top': at_top, 'bottom': at_bottom
            }
        else:
            self.dragging = True
    
    def on_mouse_drag(self, event):
        if self.dragging:
            dx = event.x - self.start_x
            dy = event.y - self.start_y
            new_x = self.window.winfo_x() + dx
            new_y = self.window.winfo_y() + dy
            self.window.geometry(f"+{new_x}+{new_y}")
            
        elif self.resizing:
            mouse_x = self.window.winfo_pointerx()
            mouse_y = self.window.winfo_pointery()
            
            x = self.window.winfo_x()
            y = self.window.winfo_y()
            width = self.window.winfo_width()
            height = self.window.winfo_height()
            
            new_x = x
            new_y = y
            new_width = width
            new_height = height
            
            if self.resize_edge['left']:
                new_x = mouse_x
                new_width = max(50, (x + width) - mouse_x)
            elif self.resize_edge['right']:
                new_width = max(50, mouse_x - x)
            
            if self.resize_edge['top']:
                new_y = mouse_y
                new_height = max(50, (y + height) - mouse_y)
            elif self.resize_edge['bottom']:
                new_height = max(50, mouse_y - y)
            
            self.window.geometry(f"{int(new_width)}x{int(new_height)}+{int(new_x)}+{int(new_y)}")
    
    def on_mouse_up(self, event):
        self.dragging = False
        self.resizing = False
        self.resize_edge = None
    
    def close(self):
        x1 = self.window.winfo_x()
        y1 = self.window.winfo_y()
        x2 = x1 + self.window.winfo_width()
        y2 = y1 + self.window.winfo_height()
        
        coords = {"x1": x1, "y1": y1, "x2": x2, "y2": y2}
        self.callback(coords)
        self.window.destroy()



class MacroAPI:
    
    def __init__(self):
        self.config_file = Path(_get_macro_settings_path())
        
        self.running = False
        self.fish_count = 0
        self.fruit_count = 0
        self.start_time = None
        self.total_elapsed_time = 0
        self.window = None
        self.stats_overlay = StatsOverlay(self)
        
        self.watchdog = WatchdogMonitor(self)
        
        self.ocr_available = False
        self.init_errors = []
        self.state_start_time = time.time()
        self.current_state = "idle"
        
        self.last_ocr_time = 0
        self.ocr_cooldown = 1.5 # seconds
        self.last_ocr_text = ""
        
        self.last_error = None
        self.last_dark_gray_y = None
        self.last_scan_time = time.time()
        self.is_holding_click = False
        self.last_input_resend_time = time.time()
        self.setting_point = False
        self.setting_point_callback = None
        
        user32 = ctypes.windll.user32
        screen_width = user32.GetSystemMetrics(0)
        screen_height = user32.GetSystemMetrics(1)
        
        self.water_point = {
            "x": int(screen_width * 0.42070),
            "y": int(screen_height * 0.15347)
        }
        
        self.area_box = {
            "x1": int(screen_width * 0.52461),
            "y1": int(screen_height * 0.29167),
            "x2": int(screen_width * 0.68477),
            "y2": int(screen_height * 0.79097)
        }
        
        # Store OCR area as percentages for resolution independence
        self.ocr_area_box_percentages = {
            "x1": 0.3115,
            "y1": 0.0602,
            "x2": 0.6839,
            "y2": 0.2
        }
        
        # Calculate absolute coordinates from percentages
        self.ocr_area_box = {
            "x1": int(screen_width * self.ocr_area_box_percentages["x1"]),
            "y1": int(screen_height * self.ocr_area_box_percentages["y1"]),
            "x2": int(screen_width * self.ocr_area_box_percentages["x2"]),
            "y2": int(screen_height * self.ocr_area_box_percentages["y2"])
        }
        
        self.left_point = {
            "x": int(screen_width * 0.41133),
            "y": int(screen_height * 0.90694)
        }
        self.middle_point = {
            "x": int(screen_width * 0.50078),
            "y": int(screen_height * 0.90556)
        }
        self.right_point = {
            "x": int(screen_width * 0.59023),
            "y": int(screen_height * 0.90486)
        }
        
        self.bait_point = {
            "x": int(screen_width * 0.50078),
            "y": int(screen_height * 0.74028)
        }
        
        self.craft_point_1 = None
        self.craft_point_2 = None
        self.craft_point_3 = None
        self.craft_point_4 = None
        self.leg_bait_point = None
        self.rare_bait_point = None
        
        self.hotkeys = {
            "start_stop": "f1",
            "change_area": "f2",
            "exit": "f3"
        }
        self.rod_hotkey = "1"
        self.anything_else_hotkey = "2"
        
        self.kp = 0.9
        self.kd = 0.3
        self.pd_clamp = 1.0
        self.pd_approaching_damping = 2.0
        self.pd_chasing_damping = 0.5
        
        self.cast_hold_duration = 1.0
        self.recast_timeout = 30.0
        
        self.fish_end_delay = 1.0
        
        self.auto_buy_common_bait = False
        self.auto_select_top_bait = False
        self.auto_store_devil_fruit = False
        self.auto_craft_bait = False
        self.craft_leg_bait = False
        self.craft_rare_bait = False
        
        # Auto Craft Bait timing settings - Configurable navigation path
        self.craft_nav_key_1 = 's'
        self.craft_nav_duration_1 = 0.3
        self.craft_nav_key_2 = 'd'
        self.craft_nav_duration_2 = 3.5
        self.craft_nav_wait_delay = 1.0
        self.craft_t_press_delay = 1.0
        self.craft_click_delay = 1.0
        self.craft_button_delay = 0.5
        self.craft_craft_button_delay = 0.5
        self.craft_sequence_delay = 0.3
        self.craft_exit_delay = 0.5
        
        self.loops_per_purchase = 100
        self.bait_purchase_loop_counter = 0
        
        self.store_fruit_point = None
        self.devil_fruit_hotkey = "3"
        self.store_fruit_hotkey_delay = 1.0
        self.store_fruit_click_delay = 2.0
        self.store_fruit_shift_delay = 0.5
        self.store_fruit_backspace_delay = 1.5
        
        self.webhook_enabled = False
        self.webhook_url = ""
        self.discord_user_id = ""
        self.webhook_notify_devil_fruit = True
        self.webhook_notify_purchase = True
        self.webhook_notify_recovery = True
        
        self.minimize_on_run = False
        self.stay_on_top = True
        
        self.pre_cast_e_delay = 1.5
        self.pre_cast_click_delay = 1.0
        self.pre_cast_type_delay = 1.0
        self.pre_cast_anti_detect_delay = 0.05
        self.auto_select_bait_delay = 0.5
        self.rod_select_delay = 0.5
        self.cursor_anti_detect_delay = 0.05
        self.scan_loop_delay = 0.0
        self.state_resend_interval = 0.1
        self.black_screen_threshold = 0.5
        
        self.gap_tolerance_multiplier = 2.0
        
        self.area_selector_active = False
        self.area_selector = None
        
        self.consecutive_recast_failures = 0
        self.max_recast_failures = 5
        
        self.load_settings()
    
    def deferred_init(self):
        """Run heavy initialization after the window is visible.
        Returns a dict of any errors encountered so the UI can show toasts."""
        errors = []
        
        # Initialize OCR
        try:
            self.initialize_ocr()
            if not self.ocr_available:
                errors.append('OCR failed to initialize — devil fruit detection disabled')
        except Exception as e:
            errors.append(f'OCR error: {str(e)[:100]}')
            self.ocr_available = False
            self.reader = None
        
        self.init_errors = errors
        return {"success": len(errors) == 0, "errors": errors}

    def initialize_ocr(self):
        try:
            # PyInstaller + torch on Windows can fail with WinError 1114 when loading
            # c10.dll due to DLL search path / OpenMP runtime conflicts.
            os.environ.setdefault('KMP_DUPLICATE_LIB_OK', 'TRUE')
            os.environ.setdefault('OMP_NUM_THREADS', '1')

            try:
                # Prefer the extracted PyInstaller location if present; importing torch can
                # fail before we can discover torch.__file__.
                torch_lib_dir = None
                if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
                    candidate = os.path.join(sys._MEIPASS, 'torch', 'lib')
                    if os.path.isdir(candidate):
                        torch_lib_dir = candidate

                # onedir fallback: dist/<app>/_internal/torch/lib
                if torch_lib_dir is None and getattr(sys, 'frozen', False):
                    exe_dir = os.path.dirname(sys.executable)
                    internal_candidate = os.path.join(exe_dir, '_internal', 'torch', 'lib')
                    if os.path.isdir(internal_candidate):
                        torch_lib_dir = internal_candidate

                if torch_lib_dir is None:
                    import torch
                    torch_root = os.path.dirname(torch.__file__)
                    candidate = os.path.join(torch_root, 'lib')
                    if os.path.isdir(candidate):
                        torch_lib_dir = candidate

                if torch_lib_dir:
                    _add_dll_search_dir(torch_lib_dir)

                    # Preload Intel OpenMP runtime if present to reduce init failures.
                    try:
                        import ctypes
                        libiomp = os.path.join(torch_lib_dir, 'libiomp5md.dll')
                        if os.path.isfile(libiomp):
                            ctypes.CDLL(libiomp)
                    except Exception:
                        pass
            except Exception as e:
                print(f"Torch pre-load failed (OCR may not work): {e}")

            import easyocr
            
            print("Initializing EasyOCR...")
            self.reader = easyocr.Reader(
                ['en'], 
                gpu=False,
                verbose=False,
                download_enabled=True
            )
            self.ocr_available = True
            print("EasyOCR ready - text recognition available!")
                
        except ImportError:
            print("EasyOCR not installed - devil fruit detection disabled")
            print("   Run: pip install easyocr")
            self.ocr_available = False
            self.reader = None
        except Exception as e:
            print(f"OCR initialization failed: {str(e)}")
            self.ocr_available = False
            self.reader = None
    
    def preprocess_image_for_ocr(self, img_array):
        """Enhance image for better EasyOCR accuracy - lightweight approach"""
        import cv2
        
        # Resize if too large (faster processing)
        height, width = img_array.shape[:2]
        max_width, max_height = 800, 600
        if width > max_width or height > max_height:
            scale_factor = min(max_width / width, max_height / height)
            new_width = int(width * scale_factor)
            new_height = int(height * scale_factor)
            img_array = cv2.resize(img_array, (new_width, new_height), interpolation=cv2.INTER_LINEAR)
        
        # Convert BGR to RGB if needed
        if len(img_array.shape) == 3:
            img_array = cv2.cvtColor(img_array, cv2.COLOR_BGR2RGB)
        
        # Convert to grayscale
        if len(img_array.shape) == 3:
            img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        
        # Light contrast adjustment
        img_array = cv2.convertScaleAbs(img_array, alpha=1.2, beta=10)
        
        return img_array
    
    def detect_legendary_fruit_drop(self):
        if not self.ocr_available or not self.reader:
            return False
        
        try:
            import mss
            import numpy as np
            
            with mss.mss() as sct:
                drop_region = {
                    'left': self.ocr_area_box['x1'],
                    'top': self.ocr_area_box['y1'],
                    'width': self.ocr_area_box['x2'] - self.ocr_area_box['x1'],
                    'height': self.ocr_area_box['y2'] - self.ocr_area_box['y1']
                }
                
                screenshot = sct.grab(drop_region)
                img_array = np.array(screenshot)
            
            # Preprocess image for better OCR
            processed_img = self.preprocess_image_for_ocr(img_array)
                
            # Use EasyOCR to extract text
            results = self.reader.readtext(processed_img, detail=0, paragraph=True)
            detected_text = ' '.join(results).lower() if results else ""
            
            if not detected_text:
                return False
            
            print(f"📝 EasyOCR detected: {detected_text[:100]}")
            
            # Look for pity counter reset (0/X) which indicates legendary+ fruit
            import re
            
            # Check for "pity: 0" or "pity 0" followed by slash/number (handles OCR errors)
            # Matches: "pity: 0/40", "pity: 0o", "pity 0 /", "pity:0/", etc.
            pity_zero_pattern = re.compile(r'pity[:\s]*0\s*[/o\s]*\d*', re.IGNORECASE)
            if pity_zero_pattern.search(detected_text):
                # Double check it's actually a reset (has "0" right after "pity")
                if re.search(r'pity[:\s]*0', detected_text, re.IGNORECASE):
                    print(f"LEGENDARY FRUIT DETECTED: Pity counter reset to 0!")
                    return True
            
            if 'legendary' in detected_text and re.search(r'\b0\b', detected_text):
                print(f"LEGENDARY FRUIT DETECTED: Found 'legendary' with '0'!")
                return True
            
            return False
            
        except Exception as e:
            print(f"OCR detection error: {str(e)}")
            return False
    
    def detect_devil_fruit_and_legendary(self):
        """Combined OCR scan - checks for devil fruit AND legendary status in one go"""
        if not self.ocr_available or not self.reader:
            return False, False
        
        current_time = time.time()
        if current_time - self.last_ocr_time < self.ocr_cooldown:
            return False, False
        
        try:
            import mss
            import numpy as np
            import re
            import cv2
            
            # Debug: Show scan region
            user32 = ctypes.windll.user32
            screen_width = user32.GetSystemMetrics(0)
            screen_height = user32.GetSystemMetrics(1)
            print(f"🔍 OCR Scan - Resolution: {screen_width}x{screen_height}, Area: ({self.ocr_area_box['x1']},{self.ocr_area_box['y1']}) to ({self.ocr_area_box['x2']},{self.ocr_area_box['y2']})")
            
            with mss.mss() as sct:
                drop_region = {
                    'left': self.ocr_area_box['x1'],
                    'top': self.ocr_area_box['y1'],
                    'width': self.ocr_area_box['x2'] - self.ocr_area_box['x1'],
                    'height': self.ocr_area_box['y2'] - self.ocr_area_box['y1']
                }
                screenshot = sct.grab(drop_region)
                img_array = np.array(screenshot)
            
            # Try OCR with minimal preprocessing first
            # Convert BGRA to RGB
            if img_array.shape[2] == 4:
                img_rgb = cv2.cvtColor(img_array, cv2.COLOR_BGRA2RGB)
            else:
                img_rgb = cv2.cvtColor(img_array, cv2.COLOR_BGR2RGB)
            
            # Try OCR on original image first with aggressive settings
            results = self.reader.readtext(
                img_rgb, 
                detail=0, 
                paragraph=False, 
                batch_size=1,
                text_threshold=0.5,  # Lower threshold for text detection
                low_text=0.3,        # Lower threshold for character detection
                link_threshold=0.3   # More aggressive text linking
            )
            detected_text = ' '.join(results).lower() if results else ""
            
            # If no results, try with preprocessing
            if not detected_text:
                print("⚠️ Trying with preprocessing...")
                processed_img = self.preprocess_image_for_ocr(img_array)
                results = self.reader.readtext(
                    processed_img, 
                    detail=0, 
                    paragraph=False, 
                    batch_size=1,
                    text_threshold=0.5,
                    low_text=0.3,
                    link_threshold=0.3
                )
                detected_text = ' '.join(results).lower() if results else ""
            
            if not detected_text:
                print("❌ OCR detected NO TEXT in scan area")
                self.last_ocr_time = current_time
                return False, False
            
            print(f"📝 EasyOCR detected: {detected_text[:100]}")
            
            # Check for devil fruit keywords - OCR-tolerant matching
            has_fruit = False
            
            # More flexible patterns to handle OCR errors
            flexible_patterns = [
                'drop',      # Always present
                'backpac',   # "backpack" often becomes "backpacr"
                'ruit',      # "fruit" often becomes "eruit" or "ruit"
                'evil',      # "devil" often becomes "devl" or "evil"
                'got',       # Usually readable
                'fish',      # "fished" substring
                'legendar',  # "legendary" substring
                'pity'       # Always with devil fruit notification
            ]
            
            # Count flexible pattern matches
            pattern_matches = sum(1 for pattern in flexible_patterns if pattern in detected_text)
            
            # If we see 2+ patterns, it's likely a devil fruit notification
            if pattern_matches >= 2:
                has_fruit = True
                print(f"✅ Devil fruit detected! (matched {pattern_matches} patterns)")
            else:
                print(f"⚠️ Not enough matches ({pattern_matches} patterns found)")
            
            # Check if legendary (pity counter at 0)
            is_legendary = False
            if has_fruit and 'pity' in detected_text:
                pity_match = re.search(r'pity[:\s]+([0-9ol]+)', detected_text, re.IGNORECASE)
                if pity_match:
                    pity_number = pity_match.group(1)
                    if pity_number[0] in ['0', 'o', 'l'] and len(pity_number) <= 2:
                        is_legendary = True
            
            self.last_ocr_time = current_time
            self.last_ocr_text = detected_text
            
            if has_fruit:
                fruit_type = "LEGENDARY+" if is_legendary else "Common/Rare"
                print(f"🍇 DEVIL FRUIT DETECTED! Type: {fruit_type}")
            else:
                print(f"⚠️ No devil fruit keywords in text: '{detected_text[:80]}'")
            
            return has_fruit, is_legendary
            
        except Exception as e:
            print(f"OCR detection error: {str(e)}")
            return False, False
    
    def detect_any_devil_fruit_drop(self):
        if not self.ocr_available or not self.reader:
            return False
        
        # don't OCR too frequently
        current_time = time.time()
        if current_time - self.last_ocr_time < self.ocr_cooldown:
            return False
        
        try:
            import mss
            import numpy as np
            
            # Try 3 times with delays to catch the message
            for attempt in range(3):
                with mss.mss() as sct:
                    drop_region = {
                        'left': self.ocr_area_box['x1'],
                        'top': self.ocr_area_box['y1'],
                        'width': self.ocr_area_box['x2'] - self.ocr_area_box['x1'],
                        'height': self.ocr_area_box['y2'] - self.ocr_area_box['y1']
                    }
                    
                    screenshot = sct.grab(drop_region)
                    img_array = np.array(screenshot)
                
                # Preprocess image for better OCR
                processed_img = self.preprocess_image_for_ocr(img_array)
                    
                # Use EasyOCR to extract text
                results = self.reader.readtext(processed_img, detail=0, paragraph=True)
                detected_text = ' '.join(results).lower() if results else ""
                
                if not detected_text:
                    if attempt < 2:
                        time.sleep(0.5)  # Longer delay between attempts
                        continue
                    break
                
                devil_fruit_keywords = ['devil', 'fruit', 'backpack', 'drop', 'got', 'fished']
                devil_fruit_phrases = [
                    'devil fruit',
                    'fished up a devil',
                    'got a devil fruit',
                    'devil fruit drop',
                    'check your backpack'
                ]
                
                for phrase in devil_fruit_phrases:
                    if phrase in detected_text:
                        print(f"🍇 Devil fruit detected: '{phrase}' found!")
                        self.last_ocr_time = current_time  # Update cooldown
                        self.last_ocr_text = detected_text
                        return True
                
                keyword_matches = sum(1 for keyword in devil_fruit_keywords if keyword in detected_text)
                if keyword_matches >= 2:
                    print(f"🍇 Devil fruit detected: {keyword_matches} keyword matches!")
                    print(f"   Text: {detected_text[:100]}")
                    self.last_ocr_time = current_time  # Update cooldown
                    self.last_ocr_text = detected_text
                    return True
                
                # If no match on this attempt, wait and try again
                if attempt < 2:
                    time.sleep(0.5)
            
            # Update cooldown even on failure to prevent spam
            self.last_ocr_time = current_time
            return False
            
        except Exception as e:
            print(f"OCR detection error: {str(e)}")
            return False
    
    def load_settings(self):
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    
                    # Load OCR area percentages first
                    if 'ocr_area_box_percentages' in data:
                        self.ocr_area_box_percentages = data['ocr_area_box_percentages']
                        # Recalculate absolute coordinates for current screen resolution
                        user32 = ctypes.windll.user32
                        screen_width = user32.GetSystemMetrics(0)
                        screen_height = user32.GetSystemMetrics(1)
                        self.ocr_area_box = {
                            "x1": int(screen_width * self.ocr_area_box_percentages["x1"]),
                            "y1": int(screen_height * self.ocr_area_box_percentages["y1"]),
                            "x2": int(screen_width * self.ocr_area_box_percentages["x2"]),
                            "y2": int(screen_height * self.ocr_area_box_percentages["y2"])
                        }
                    
                    for key, value in data.items():
                        # Skip ocr_area_box - it's recalculated from percentages
                        if key in ['ocr_area_box', 'ocr_area_box_percentages']:
                            continue
                        if hasattr(self, key):
                            setattr(self, key, value)
                print("Settings loaded successfully")
            except Exception as e:
                print(f"Error loading settings: {e}")
    
    def save_settings(self):
        try:
            try:
                self.config_file.parent.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass

            data = {
                "water_point": self.water_point,
                "area_box": self.area_box,
                "ocr_area_box_percentages": self.ocr_area_box_percentages,
                "left_point": self.left_point,
                "middle_point": self.middle_point,
                "right_point": self.right_point,
                "bait_point": self.bait_point,
                "craft_point_1": self.craft_point_1,
                "craft_point_2": self.craft_point_2,
                "craft_point_3": self.craft_point_3,
                "craft_point_4": self.craft_point_4,
                "leg_bait_point": self.leg_bait_point,
                "rare_bait_point": self.rare_bait_point,
                "hotkeys": self.hotkeys,
                "rod_hotkey": self.rod_hotkey,
                "anything_else_hotkey": self.anything_else_hotkey,
                "kp": self.kp,
                "kd": self.kd,
                "pd_clamp": self.pd_clamp,
                "cast_hold_duration": self.cast_hold_duration,
                "recast_timeout": self.recast_timeout,
                "fish_end_delay": self.fish_end_delay,
                "auto_buy_common_bait": self.auto_buy_common_bait,
                "auto_select_top_bait": self.auto_select_top_bait,
                "auto_store_devil_fruit": self.auto_store_devil_fruit,
                "auto_craft_bait": self.auto_craft_bait,
                "craft_leg_bait": self.craft_leg_bait,
                "craft_rare_bait": self.craft_rare_bait,
                "craft_nav_key_1": self.craft_nav_key_1,
                "craft_nav_duration_1": self.craft_nav_duration_1,
                "craft_nav_key_2": self.craft_nav_key_2,
                "craft_nav_duration_2": self.craft_nav_duration_2,
                "craft_nav_wait_delay": self.craft_nav_wait_delay,
                "craft_t_press_delay": self.craft_t_press_delay,
                "craft_click_delay": self.craft_click_delay,
                "craft_button_delay": self.craft_button_delay,
                "craft_craft_button_delay": self.craft_craft_button_delay,
                "craft_sequence_delay": self.craft_sequence_delay,
                "craft_exit_delay": self.craft_exit_delay,
                "loops_per_purchase": self.loops_per_purchase,
                "store_fruit_point": self.store_fruit_point,
                "devil_fruit_hotkey": self.devil_fruit_hotkey,
                "store_fruit_hotkey_delay": self.store_fruit_hotkey_delay,
                "store_fruit_click_delay": self.store_fruit_click_delay,
                "store_fruit_shift_delay": self.store_fruit_shift_delay,
                "store_fruit_backspace_delay": self.store_fruit_backspace_delay,
                "webhook_enabled": self.webhook_enabled,
                "webhook_url": self.webhook_url,
                "discord_user_id": self.discord_user_id,
                "webhook_notify_devil_fruit": self.webhook_notify_devil_fruit,
                "webhook_notify_purchase": self.webhook_notify_purchase,
                "webhook_notify_recovery": self.webhook_notify_recovery,
                "pre_cast_e_delay": self.pre_cast_e_delay,
                "pre_cast_click_delay": self.pre_cast_click_delay,
                "pre_cast_type_delay": self.pre_cast_type_delay,
                "pre_cast_anti_detect_delay": self.pre_cast_anti_detect_delay,
                "auto_select_bait_delay": self.auto_select_bait_delay,
                "rod_select_delay": self.rod_select_delay,
                "cursor_anti_detect_delay": self.cursor_anti_detect_delay,
                "scan_loop_delay": self.scan_loop_delay,
                "pd_approaching_damping": self.pd_approaching_damping,
                "pd_chasing_damping": self.pd_chasing_damping,
                "gap_tolerance_multiplier": self.gap_tolerance_multiplier,
                "minimize_on_run": self.minimize_on_run,
                "stay_on_top": self.stay_on_top
            }
            with open(self.config_file, 'w') as f:
                json.dump(data, f, indent=4)
            print("Settings saved successfully")
        except Exception as e:
            print(f"Error saving settings: {e}")
        
    def start_macro(self):
        if self.running:
            return {"status": "already_running"}
        
        if not self.water_point or self.water_point.get("x") is None:
            return {"status": "error", "message": "Please set water point first (Controls tab)"}
        
        if not self.area_box or self.area_box.get("x1") is None:
            return {"status": "error", "message": "Please set fishing area first (press F2)"}
        
        self.running = True
        if self.start_time is None:
            self.start_time = time.time()
        else:
            self.start_time = time.time() - self.total_elapsed_time
        if self.auto_buy_common_bait:
            self.bait_purchase_loop_counter = self.loops_per_purchase
        else:
            self.bait_purchase_loop_counter = 0
        
        self.state_start_time = time.time()
        self.current_state = "idle"
        
        self.watchdog.start()
        
        if self.window and self.minimize_on_run:
            self.window.minimize()
        
        # Show stats overlay window
        try:
            print("Attempting to show stats overlay...")
            self.stats_overlay.show()
            print("Stats overlay show() completed")
        except Exception as e:
            import traceback
            print(f"Failed to show stats overlay: {e}")
            print(traceback.format_exc())
        
        threading.Thread(target=self._macro_loop, daemon=True).start()
        
        return {"status": "started", "message": "Macro started!"}
    
    def stop_macro(self):
        self.running = False
        
        if self.start_time:
            self.total_elapsed_time = int(time.time() - self.start_time)
        
        threading.Thread(target=self.watchdog.stop, daemon=True).start()
        
        # Hide stats overlay window
        try:
            self.stats_overlay.hide()
        except Exception as e:
            print(f"Failed to hide stats overlay: {e}")
        
        if self.window:
            self.window.restore()
        
        if self.is_holding_click:
            ctypes.windll.user32.mouse_event(4, 0, 0, 0, 0)
    
    def cleanup(self):
        self.running = False
        
        # Hide stats overlay window
        try:
            self.stats_overlay.hide()
        except Exception as e:
            print(f"Failed to hide stats overlay: {e}")
        
        self.watchdog.active = False
        
        try:
            if self.is_holding_click:
                ctypes.windll.user32.mouse_event(4, 0, 0, 0, 0)
                self.is_holding_click = False
        except:
            pass
        
        try:
            keyboard.unhook_all()
        except:
            pass
    
    def _macro_loop(self):
        print("Macro loop started...")
        while self.running:
            try:
                self.watchdog.update_heartbeat()
                
                self.current_state = "pre_cast"
                self.state_start_time = time.time()
                if not self.pre_cast():
                    break
                
                self.current_state = "waiting"
                self.state_start_time = time.time()
                if not self.waiting():
                    break
                
                self.current_state = "fishing"
                self.state_start_time = time.time()
                if not self.fishing():
                    break
                
                self.fish_count += 1
                self.bait_purchase_loop_counter += 1
                print(f"Fish caught! Total: {self.fish_count}")
                
                self.watchdog.reset_recovery_count()
                
                if self.auto_store_devil_fruit and self.ocr_available:
                    time.sleep(0.1)  # Wait for notification to appear
                    
                    # Single OCR scan - checks both fruit and legendary status
                    has_fruit, is_legendary = self.detect_devil_fruit_and_legendary()
                    
                    if has_fruit:
                        print("Devil fruit detected! Starting storage sequence...")
                        self.fruit_count += 1
                        
                        if is_legendary:
                            print("LEGENDARY FRUIT confirmed! Capturing screenshot...")
                            self.store_devil_fruit(capture_legendary=True)
                            if self.webhook_enabled and self.webhook_url:
                                self.send_devil_fruit_webhook()
                        else:
                            self.store_devil_fruit(capture_legendary=False)
                
                time.sleep(self.fish_end_delay)
                
            except Exception as e:
                print(f"Error in macro loop: {e}")
                time.sleep(1)
    
    def pre_cast(self):
        if not self.running:
            return False
        
        if self.auto_buy_common_bait:
            if self.bait_purchase_loop_counter >= self.loops_per_purchase:
                print(f"Auto buying bait (loop {self.bait_purchase_loop_counter})...")
                self.bait_purchase_loop_counter = 0
                
                keyboard.press_and_release('e')
                time.sleep(self.pre_cast_e_delay)
                if not self.running:
                    return False
                
                ctypes.windll.user32.SetCursorPos(self.left_point['x'], self.left_point['y'])
                time.sleep(self.pre_cast_anti_detect_delay)
                ctypes.windll.user32.mouse_event(0x0001, 0, 1, 0, 0)
                time.sleep(self.pre_cast_anti_detect_delay)
                pyautogui.click()
                time.sleep(self.pre_cast_click_delay)
                if not self.running:
                    return False
                
                ctypes.windll.user32.SetCursorPos(self.middle_point['x'], self.middle_point['y'])
                time.sleep(self.pre_cast_anti_detect_delay)
                ctypes.windll.user32.mouse_event(0x0001, 0, 1, 0, 0)
                time.sleep(self.pre_cast_anti_detect_delay)
                pyautogui.click()
                time.sleep(self.pre_cast_click_delay)
                if not self.running:
                    return False
                
                keyboard.write(str(self.loops_per_purchase))
                time.sleep(self.pre_cast_type_delay)
                if not self.running:
                    return False
                
                ctypes.windll.user32.SetCursorPos(self.left_point['x'], self.left_point['y'])
                time.sleep(self.pre_cast_anti_detect_delay)
                ctypes.windll.user32.mouse_event(0x0001, 0, 1, 0, 0)
                time.sleep(self.pre_cast_anti_detect_delay)
                pyautogui.click()
                time.sleep(self.pre_cast_click_delay)
                if not self.running:
                    return False
                
                ctypes.windll.user32.SetCursorPos(self.right_point['x'], self.right_point['y'])
                time.sleep(self.pre_cast_anti_detect_delay)
                ctypes.windll.user32.mouse_event(0x0001, 0, 1, 0, 0)
                time.sleep(self.pre_cast_anti_detect_delay)
                pyautogui.click()
                time.sleep(self.pre_cast_click_delay)
                if not self.running:
                    return False
                
                ctypes.windll.user32.SetCursorPos(self.middle_point['x'], self.middle_point['y'])
                time.sleep(self.pre_cast_anti_detect_delay)
                ctypes.windll.user32.mouse_event(0x0001, 0, 1, 0, 0)
                time.sleep(self.pre_cast_anti_detect_delay)
                pyautogui.click()
                time.sleep(self.pre_cast_click_delay)
                if not self.running:
                    return False
                
                print("Bait purchase complete")
                self.send_purchase_webhook(self.loops_per_purchase)
                
                # Auto craft baits after purchase
                if self.auto_craft_bait:
                    print("Auto crafting bait after purchase...")
                    if not self.craft_bait():
                        return False
        
        return True
    
    def reliable_click(self, x, y, delay=None):
        """Perform a reliable click with cursor positioning and micro-movement"""
        ctypes.windll.user32.SetCursorPos(x, y)
        time.sleep(self.cursor_anti_detect_delay)
        ctypes.windll.user32.mouse_event(0x0001, 0, 1, 0, 0)
        time.sleep(self.cursor_anti_detect_delay)
        pyautogui.click()
        if delay:
            time.sleep(delay)
    
    def craft_bait(self):
        """Execute bait crafting sequence based on user settings"""
        if not self.running:
            return False
        
        # Check if all craft points are set
        if not all([self.craft_point_1, self.craft_point_2, self.craft_point_3, 
                    self.craft_point_4]):
            print("⚠️ All craft points must be set to use auto craft bait")
            return False
        
        # Check if at least one bait type is selected and has point set
        leg_bait_ready = self.craft_leg_bait and self.leg_bait_point
        rare_bait_ready = self.craft_rare_bait and self.rare_bait_point
        
        print(f"Debug - craft_leg_bait: {self.craft_leg_bait}, leg_bait_point: {self.leg_bait_point is not None}")
        print(f"Debug - craft_rare_bait: {self.craft_rare_bait}, rare_bait_point: {self.rare_bait_point is not None}")
        
        if not leg_bait_ready and not rare_bait_ready:
            print("⚠️ Select at least one bait type and set its point")
            return False
        
        # Check if left and middle points are set (needed for navigation)
        if not self.left_point or not self.middle_point:
            print("⚠️ Left and Middle points must be set in Auto Buy Common Bait")
            return False
        
        print(f"🔧 Crafting baits - Legendary: {leg_bait_ready}, Rare: {rare_bait_ready}")
        
        try:
            # Set state to crafting and reset timer
            self.current_state = "crafting"
            self.state_start_time = time.time()
            
            # Enable shift lock for navigation
            keyboard.press_and_release('shift')
            time.sleep(0.1)
            
            # Update watchdog - starting craft sequence
            if hasattr(self, 'watchdog') and self.watchdog:
                self.watchdog.update_heartbeat()
            
            # Navigate to crafting area - First movement
            keyboard.press(self.craft_nav_key_1)
            time.sleep(self.craft_nav_duration_1)
            keyboard.release(self.craft_nav_key_1)
            
            if not self.running:
                return False
            
            # Wait
            time.sleep(self.craft_nav_wait_delay)
            
            # Second movement
            keyboard.press(self.craft_nav_key_2)
            time.sleep(self.craft_nav_duration_2)
            keyboard.release(self.craft_nav_key_2)
            
            if not self.running:
                return False
            
            # Wait
            time.sleep(self.craft_nav_wait_delay)
            
            # Disable shift lock before pressing T
            keyboard.press_and_release('shift')
            time.sleep(0.1)
            
            # Update watchdog - finished navigation
            if hasattr(self, 'watchdog') and self.watchdog:
                self.watchdog.update_heartbeat()
            
            # Press 'T' once
            keyboard.press('t')
            keyboard.release('t')
            
            # Wait
            time.sleep(self.craft_t_press_delay)
            
            if not self.running:
                return False
            
            # Click left point
            self.reliable_click(self.left_point["x"], self.left_point["y"], self.craft_click_delay)
            
            # Click middle point
            self.reliable_click(self.middle_point["x"], self.middle_point["y"], self.craft_click_delay)
            
            if not self.running:
                return False
            
            # Craft Legendary Bait if enabled
            if leg_bait_ready:
                # Update watchdog - starting leg bait craft
                if hasattr(self, 'watchdog') and self.watchdog:
                    self.watchdog.update_heartbeat()
                
                print("🔧 Crafting Legendary Fish Bait...")
                # Click leg bait point to select it
                self.reliable_click(self.leg_bait_point["x"], self.leg_bait_point["y"], self.craft_click_delay)
                # Extra wait to ensure menu selection registers
                time.sleep(0.3)
                
                # Repeat crafting sequence 5 times
                for i in range(5):
                    if not self.running:
                        return False
                    
                    # Update watchdog every iteration
                    if hasattr(self, 'watchdog') and self.watchdog:
                        self.watchdog.update_heartbeat()
                    
                    # Click + button (craft_point_1)
                    self.reliable_click(self.craft_point_1["x"], self.craft_point_1["y"], self.craft_button_delay)
                    
                    # Click fish button (craft_point_2)
                    self.reliable_click(self.craft_point_2["x"], self.craft_point_2["y"], self.craft_button_delay)
                    
                    # Click craft button (craft_point_3) 15 times
                    for j in range(15):
                        if not self.running:
                            return False
                        self.reliable_click(self.craft_point_3["x"], self.craft_point_3["y"], self.craft_craft_button_delay)
                    
                    time.sleep(self.craft_sequence_delay)
                
                print("✅ Legendary Fish Bait crafted")
            
            # Craft Rare Bait if enabled
            if rare_bait_ready:
                if not self.running:
                    return False
                
                # Add delay between crafting different bait types
                if leg_bait_ready:
                    time.sleep(0.5)
                
                # Update watchdog - starting rare bait craft
                if hasattr(self, 'watchdog') and self.watchdog:
                    self.watchdog.update_heartbeat()
                
                print("🔧 Crafting Rare Fish Bait...")
                # Click rare bait point to select it
                self.reliable_click(self.rare_bait_point["x"], self.rare_bait_point["y"], self.craft_click_delay)
                # Extra wait to ensure menu selection registers
                time.sleep(0.3)
                
                # Repeat crafting sequence 5 times
                for i in range(5):
                    if not self.running:
                        return False
                    
                    # Update watchdog every iteration
                    if hasattr(self, 'watchdog') and self.watchdog:
                        self.watchdog.update_heartbeat()
                    
                    # Click + button (craft_point_1)
                    self.reliable_click(self.craft_point_1["x"], self.craft_point_1["y"], self.craft_button_delay)
                    
                    # Click fish button (craft_point_2)
                    self.reliable_click(self.craft_point_2["x"], self.craft_point_2["y"], self.craft_button_delay)
                    
                    # Click craft button (craft_point_3) 15 times
                    for j in range(15):
                        if not self.running:
                            return False
                        self.reliable_click(self.craft_point_3["x"], self.craft_point_3["y"], self.craft_craft_button_delay)
                    
                    time.sleep(self.craft_sequence_delay)
                
                print("✅ Rare Fish Bait crafted")
            
            if not self.running:
                return False
            
            # Exit crafting menu
            self.reliable_click(self.craft_point_4["x"], self.craft_point_4["y"], self.craft_exit_delay)
            
            if not self.running:
                return False
            
            # Enable shift lock for return navigation
            keyboard.press_and_release('shift')
            time.sleep(0.1)
            
            # Update watchdog - starting return navigation
            if hasattr(self, 'watchdog') and self.watchdog:
                self.watchdog.update_heartbeat()
            
            # Navigate back to original position - reverse Step 2
            opposite_keys = {'w': 's', 's': 'w', 'a': 'd', 'd': 'a'}
            return_key_2 = opposite_keys.get(self.craft_nav_key_2, 's')
            keyboard.press(return_key_2)
            time.sleep(self.craft_nav_duration_2)
            keyboard.release(return_key_2)
            
            if not self.running:
                return False
            
            # Wait
            time.sleep(self.craft_nav_wait_delay)
            
            # Reverse Step 1
            return_key_1 = opposite_keys.get(self.craft_nav_key_1, 'a')
            keyboard.press(return_key_1)
            time.sleep(self.craft_nav_duration_1)
            keyboard.release(return_key_1)
            
            # Disable shift lock
            keyboard.press_and_release('shift')
            time.sleep(0.1)
            
            print("✅ Bait crafting completed successfully")
            
            # Reset recast failure counter after successful craft
            self.consecutive_recast_failures = 0
            
            # Restore state to pre_cast
            self.current_state = "pre_cast"
            self.state_start_time = time.time()
            
            return True
            
        except Exception as e:
            print(f"❌ Error during bait crafting: {e}")
            
            # Restore state to pre_cast
            self.current_state = "pre_cast"
            self.state_start_time = time.time()
            
            return False
        # 3. Click craft points in sequence
        # 4. Confirm crafting
        # 5. Exit menu
        
        print("✅ Bait crafting complete")
        return True
    
    def capture_legendary_fruit_screenshot(self):
        """Rotate camera 180°, capture fruit screenshot, rotate back"""
        try:
            import mss
            import numpy as np
            import cv2
            
            # Helper functions for SendInput
            def send_mouse_move(dx, dy):
                extra = ctypes.c_ulong(0)
                ii_ = INPUT()
                ii_.type = INPUT_MOUSE
                ii_._input.mi = MOUSEINPUT(dx, dy, 0, MOUSEEVENTF_MOVE, 0, ctypes.pointer(extra))
                ctypes.windll.user32.SendInput(1, ctypes.pointer(ii_), ctypes.sizeof(ii_))
            
            def send_mouse_button(down=True):
                extra = ctypes.c_ulong(0)
                ii_ = INPUT()
                ii_.type = INPUT_MOUSE
                flag = MOUSEEVENTF_RIGHTDOWN if down else MOUSEEVENTF_RIGHTUP
                ii_._input.mi = MOUSEINPUT(0, 0, 0, flag, 0, ctypes.pointer(extra))
                ctypes.windll.user32.SendInput(1, ctypes.pointer(ii_), ctypes.sizeof(ii_))
            
            # Get screen center for camera rotation
            screen_width, screen_height = pyautogui.size()
            center_x = screen_width // 2
            center_y = screen_height // 2
            
            # Press shift twice before rotating camera
            keyboard.press_and_release('shift')
            time.sleep(self.store_fruit_shift_delay)
            keyboard.press_and_release('shift')
            time.sleep(self.store_fruit_shift_delay)
            
            # Move to center
            print("Rotating camera 180°...")
            ctypes.windll.user32.SetCursorPos(center_x, center_y)
            time.sleep(0.2)
            
            # Send right mouse button DOWN
            send_mouse_button(down=True)
            time.sleep(0.1)
            
            # Calculate rotation distance based on resolution
            if screen_width <= 1920:
                rotation_multiplier = 0.6
            else:
                rotation_multiplier = 0.4
            
            rotation_distance = int(screen_width * rotation_multiplier)
            
            # Send smooth mouse movement using SendInput
            steps = 50
            for i in range(steps):
                dx = rotation_distance // steps
                send_mouse_move(dx, 0)
                time.sleep(0.005)
            
            time.sleep(0.1)
            
            # Release right button
            send_mouse_button(down=False)
            time.sleep(0.3)
            
            # Capture screenshot from center of screen
            print("Capturing fruit screenshot...")
            screenshot_box = {
                'left': int(screen_width * 0.35),
                'top': int(screen_height * 0.30),
                'width': int(screen_width * 0.30),
                'height': int(screen_height * 0.40)
            }
            
            with mss.mss() as sct:
                screenshot = sct.grab(screenshot_box)
                img_array = np.array(screenshot)
                # mss captures in BGRA format, cv2 expects BGR
                # Convert BGRA to BGR by removing alpha channel
                img_bgr = cv2.cvtColor(img_array, cv2.COLOR_BGRA2BGR)
                
                # Encode to PNG using cv2
                success, encoded_img = cv2.imencode('.png', img_bgr)
                if success:
                    self.legendary_fruit_screenshot = encoded_img.tobytes()
                else:
                    self.legendary_fruit_screenshot = None
            
            print("Rotating camera back...")
            # Rotate camera back
            ctypes.windll.user32.SetCursorPos(center_x, center_y)
            time.sleep(0.2)
            
            send_mouse_button(down=True)
            time.sleep(0.1)
            
            # Send movement back (negative dx)
            for i in range(steps):
                dx = -(rotation_distance // steps)
                send_mouse_move(dx, 0)
                time.sleep(0.005)
            
            send_mouse_button(down=False)
            time.sleep(0.2)
            
            print("Screenshot captured successfully!")
            
        except Exception as e:
            print(f"Error capturing legendary fruit screenshot: {e}")
            self.legendary_fruit_screenshot = None
    
    def store_devil_fruit(self, capture_legendary=False):
        if not self.store_fruit_point:
            print("Warning: Auto Store Devil Fruit enabled but Store Fruit Point not set!")
            return False
        
        try:
            keyboard.press_and_release(self.devil_fruit_hotkey)
            time.sleep(self.store_fruit_hotkey_delay)
            if not self.running:
                return False
            
            # If legendary, rotate camera and capture screenshot
            if capture_legendary:
                self.capture_legendary_fruit_screenshot()
            
            ctypes.windll.user32.SetCursorPos(self.store_fruit_point['x'], self.store_fruit_point['y'])
            time.sleep(self.pre_cast_anti_detect_delay)
            ctypes.windll.user32.mouse_event(0x0001, 0, 1, 0, 0)
            pyautogui.click()
            time.sleep(self.store_fruit_click_delay)
            if not self.running:
                return False
            
            keyboard.press_and_release('shift')
            time.sleep(self.store_fruit_shift_delay)
            if not self.running:
                return False
            
            keyboard.press_and_release('backspace')
            time.sleep(self.store_fruit_backspace_delay)
            if not self.running:
                return False
            
            keyboard.press_and_release('shift')
            time.sleep(self.store_fruit_shift_delay)
            if not self.running:
                return False
            
            return True
            
        except Exception as e:
            print(f"Error storing devil fruit: {e}")
            return False
    
    def waiting(self):
        pyautogui.rightClick()
        time.sleep(0.1)
        if not self.running:
            return False
        
        keyboard.press_and_release(self.anything_else_hotkey)
        time.sleep(self.rod_select_delay)
        if not self.running:
            return False
        keyboard.press_and_release(self.rod_hotkey)
        time.sleep(self.rod_select_delay)
        if not self.running:
            return False
        
        if self.auto_select_top_bait:
            ctypes.windll.user32.SetCursorPos(self.bait_point['x'], self.bait_point['y'])
            time.sleep(self.cursor_anti_detect_delay)
            if not self.running:
                return False
            ctypes.windll.user32.mouse_event(0x0001, 0, 1, 0, 0)
            pyautogui.click()
            time.sleep(self.auto_select_bait_delay)
            if not self.running:
                return False
        
        ctypes.windll.user32.SetCursorPos(self.water_point['x'], self.water_point['y'])
        time.sleep(self.cursor_anti_detect_delay)
        if not self.running:
            return False
        ctypes.windll.user32.mouse_event(0x0001, 0, 1, 0, 0)
        
        pyautogui.mouseDown()
        time.sleep(self.cast_hold_duration)
        if not self.running:
            pyautogui.mouseUp()
            return False
        pyautogui.mouseUp()
        
        start_time = time.time()
        target_blue = np.array([85, 170, 255])
        target_white = np.array([255, 255, 255])
        target_dark_gray = np.array([25, 25, 25])
        
        while self.running and (time.time() - start_time) < self.recast_timeout:
            with mss.mss() as sct:
                monitor = {
                    "left": self.area_box['x1'],
                    "top": self.area_box['y1'],
                    "width": self.area_box['x2'] - self.area_box['x1'],
                    "height": self.area_box['y2'] - self.area_box['y1']
                }
                img = np.array(sct.grab(monitor))
            
            blue_mask = (
                (img[:, :, 2] == target_blue[0]) &
                (img[:, :, 1] == target_blue[1]) &
                (img[:, :, 0] == target_blue[2])
            )
            white_mask = (
                (img[:, :, 2] == target_white[0]) &
                (img[:, :, 1] == target_white[1]) &
                (img[:, :, 0] == target_white[2])
            )
            dark_gray_mask = (
                (img[:, :, 2] == target_dark_gray[0]) &
                (img[:, :, 1] == target_dark_gray[1]) &
                (img[:, :, 0] == target_dark_gray[2])
            )
            
            if np.any(blue_mask) and np.any(white_mask) and np.any(dark_gray_mask):
                print("All colors detected - fish has bitten!")
                self.consecutive_recast_failures = 0
                return True
            
            self.watchdog.update_heartbeat()
            
            time.sleep(self.scan_loop_delay)
        
        self.consecutive_recast_failures += 1
        print(f"Recast timeout - no bite detected ({self.consecutive_recast_failures}/{self.max_recast_failures})")
        
        if self.consecutive_recast_failures >= self.max_recast_failures:
            print(f"🛑 STOPPING: {self.max_recast_failures} consecutive recasts without minigame")
            if self.webhook_enabled and self.webhook_url and self.webhook_notify_recovery:
                self.send_recast_failure_webhook()
            self.stop_macro()
            return False
        
        return True
    
    def fishing(self):
        self.last_error = None
        self.last_dark_gray_y = None
        
        if self.is_holding_click:
            ctypes.windll.user32.mouse_event(4, 0, 0, 0, 0)
            self.is_holding_click = False
        
        target_blue = np.array([85, 170, 255])
        target_white = np.array([255, 255, 255])
        target_dark_gray = np.array([25, 25, 25])
        fishing_start_time = time.time()
        
        while self.running:
            with mss.mss() as sct:
                monitor = {
                    "left": self.area_box['x1'],
                    "top": self.area_box['y1'],
                    "width": self.area_box['x2'] - self.area_box['x1'],
                    "height": self.area_box['y2'] - self.area_box['y1']
                }
                img = np.array(sct.grab(monitor))
            
            blue_mask = (
                (img[:, :, 2] == target_blue[0]) &
                (img[:, :, 1] == target_blue[1]) &
                (img[:, :, 0] == target_blue[2])
            )
            
            if np.any(blue_mask):
                y_coords, x_coords = np.where(blue_mask)
                middle_x = int(np.mean(x_coords))
                
                cropped_slice = img[:, middle_x:middle_x+1, :]
                
                target_gray = np.array([25, 25, 25])
                gray_mask = (
                    (cropped_slice[:, 0, 2] == target_gray[0]) &
                    (cropped_slice[:, 0, 1] == target_gray[1]) &
                    (cropped_slice[:, 0, 0] == target_gray[2])
                )
                
                if np.any(gray_mask):
                    gray_y_coords = np.where(gray_mask)[0]
                    top_gray_y = gray_y_coords[0]
                    bottom_gray_y = gray_y_coords[-1]
                    
                    final_slice = cropped_slice[top_gray_y:bottom_gray_y+1, :, :]
                    
                    target_white_slice = np.array([255, 255, 255])
                    white_mask = (
                        (final_slice[:, 0, 2] == target_white_slice[0]) &
                        (final_slice[:, 0, 1] == target_white_slice[1]) &
                        (final_slice[:, 0, 0] == target_white_slice[2])
                    )
                    
                    target_dark_gray_slice = np.array([25, 25, 25])
                    dark_gray_mask = (
                        (final_slice[:, 0, 2] == target_dark_gray_slice[0]) &
                        (final_slice[:, 0, 1] == target_dark_gray_slice[1]) &
                        (final_slice[:, 0, 0] == target_dark_gray_slice[2])
                    )
                    
                    if np.any(dark_gray_mask):
                        dark_gray_y_coords = np.where(dark_gray_mask)[0]
                        
                        if np.any(white_mask):
                            white_y_coords = np.where(white_mask)[0]
                            top_white_y_relative = white_y_coords[0]
                            bottom_white_y_relative = white_y_coords[-1]
                            white_height = bottom_white_y_relative - top_white_y_relative + 1
                            
                            middle_white_y_screen = self.area_box["y1"] + top_gray_y + (top_white_y_relative + bottom_white_y_relative) // 2
                        else:
                            top_white_y_relative = 0
                            bottom_white_y_relative = max(5, len(final_slice) // 10)
                            white_height = bottom_white_y_relative - top_white_y_relative + 1
                            middle_white_y_screen = self.area_box["y1"] + top_gray_y + (top_white_y_relative + bottom_white_y_relative) // 2
                        
                        if True:
                            dark_gray_y_coords = np.where(dark_gray_mask)[0]
                            
                            gap_tolerance = white_height * self.gap_tolerance_multiplier
                            groups = []
                            current_group = [dark_gray_y_coords[0]]
                            
                            for i in range(1, len(dark_gray_y_coords)):
                                if dark_gray_y_coords[i] - dark_gray_y_coords[i-1] <= gap_tolerance:
                                    current_group.append(dark_gray_y_coords[i])
                                else:
                                    groups.append(current_group)
                                    current_group = [dark_gray_y_coords[i]]
                            groups.append(current_group)
                            
                            biggest_group = max(groups, key=len)
                            biggest_group_middle = (biggest_group[0] + biggest_group[-1]) // 2
                            
                            biggest_group_middle_y_screen = self.area_box["y1"] + top_gray_y + biggest_group_middle
                            
                            kp = self.kp
                            kd = self.kd
                            pd_clamp = self.pd_clamp
                            
                            error = middle_white_y_screen - biggest_group_middle_y_screen
                            
                            p_term = kp * error
                            
                            d_term = 0.0
                            current_time = time.time()
                            time_delta = current_time - self.last_scan_time
                            
                            if self.last_error is not None and self.last_dark_gray_y is not None and time_delta > 0.001:
                                dark_gray_velocity = (biggest_group_middle_y_screen - self.last_dark_gray_y) / time_delta
                                
                                error_magnitude_decreasing = abs(error) < abs(self.last_error)
                                
                                bar_moving_toward_target = (dark_gray_velocity > 0 and error > 0) or (dark_gray_velocity < 0 and error < 0)
                                
                                if error_magnitude_decreasing and bar_moving_toward_target:
                                    damping_multiplier = self.pd_approaching_damping
                                    d_term = -kd * damping_multiplier * dark_gray_velocity
                                else:
                                    damping_multiplier = self.pd_chasing_damping
                                    d_term = -kd * damping_multiplier * dark_gray_velocity
                            
                            control_signal = p_term + d_term
                            control_signal = max(-pd_clamp, min(pd_clamp, control_signal))
                            
                            should_hold = control_signal <= 0
                            
                            if should_hold and not self.is_holding_click:
                                ctypes.windll.user32.mouse_event(2, 0, 0, 0, 0)
                                self.is_holding_click = True
                                self.last_input_resend_time = current_time
                            elif not should_hold and self.is_holding_click:
                                ctypes.windll.user32.mouse_event(4, 0, 0, 0, 0)
                                self.is_holding_click = False
                                self.last_input_resend_time = current_time
                            else:
                                time_since_last_resend = current_time - self.last_input_resend_time
                                if time_since_last_resend >= self.state_resend_interval:
                                    if self.is_holding_click:
                                        ctypes.windll.user32.mouse_event(2, 0, 0, 0, 0)
                                    else:
                                        ctypes.windll.user32.mouse_event(4, 0, 0, 0, 0)
                                    self.last_input_resend_time = current_time
                            
                            self.last_error = error
                            self.last_dark_gray_y = biggest_group_middle_y_screen
                            self.last_scan_time = current_time
                            
                            self.watchdog.update_heartbeat()
            else:
                if self.is_holding_click:
                    ctypes.windll.user32.mouse_event(4, 0, 0, 0, 0)
                    self.is_holding_click = False
                
                if time.time() - fishing_start_time > 3.0:
                    if self.check_black_screen():
                        self.handle_anti_macro_screen()
                    
                    return True
            
            time.sleep(self.scan_loop_delay)
        
        if self.is_holding_click:
            ctypes.windll.user32.mouse_event(4, 0, 0, 0, 0)
            self.is_holding_click = False
        return False
    
    def check_black_screen(self):
        try:
            with mss.mss() as sct:
                monitor = {
                    "top": self.area_box["y1"],
                    "left": self.area_box["x1"],
                    "width": self.area_box["x2"] - self.area_box["x1"],
                    "height": self.area_box["y2"] - self.area_box["y1"]
                }
                img = np.array(sct.grab(monitor))
            
            black_mask = (img[:, :, 2] == 0) & (img[:, :, 1] == 0) & (img[:, :, 0] == 0)
            black_pixels = np.sum(black_mask)
            total_pixels = img.shape[0] * img.shape[1]
            black_ratio = black_pixels / total_pixels
            
            if black_ratio > self.black_screen_threshold:
                print(f"Black screen detected! ({black_ratio*100:.1f}% black pixels)")
                return True
            return False
        except Exception as e:
            print(f"Error checking black screen: {e}")
            return False
    
    def handle_anti_macro_screen(self):
        print("Handling anti-macro screen...")
        keyboard.press_and_release('space')
        time.sleep(0.5)
        keyboard.press_and_release('space')
        time.sleep(1.0)
        print("Anti-macro screen cleared")
    
    def get_state(self):
        elapsed_time = 0
        fish_per_hour = 0.0
        
        if self.start_time:
            elapsed_time = int(time.time() - self.start_time)
            if elapsed_time > 0:
                fish_per_hour = (self.fish_count / elapsed_time) * 3600
        
        hours = elapsed_time // 3600
        minutes = (elapsed_time % 3600) // 60
        seconds = elapsed_time % 60
        
        return {
            "running": self.running,
            "fish_count": self.fish_count,
            "fruit_count": self.fruit_count,
            "time_elapsed": f"{hours}:{minutes:02d}:{seconds:02d}",
            "fish_per_hour": round(fish_per_hour, 1),
            "water_point": self.water_point,
            "area_box": self.area_box,
            "ocr_area_box": self.ocr_area_box,
            "left_point": self.left_point,
            "middle_point": self.middle_point,
            "right_point": self.right_point,
            "bait_point": self.bait_point,
            "store_fruit_point": self.store_fruit_point,
            "craft_point_1": self.craft_point_1,
            "craft_point_2": self.craft_point_2,
            "craft_point_3": self.craft_point_3,
            "craft_point_4": self.craft_point_4,
            "leg_bait_point": self.leg_bait_point,
            "rare_bait_point": self.rare_bait_point,
            "hotkeys": self.hotkeys,
            "auto_buy_common_bait": self.auto_buy_common_bait,
            "auto_select_top_bait": self.auto_select_top_bait,
            "auto_store_devil_fruit": self.auto_store_devil_fruit,
            "auto_craft_bait": self.auto_craft_bait,
            "craft_leg_bait": self.craft_leg_bait,
            "craft_rare_bait": self.craft_rare_bait,
            "craft_nav_key_1": self.craft_nav_key_1,
            "craft_nav_duration_1": self.craft_nav_duration_1,
            "craft_nav_key_2": self.craft_nav_key_2,
            "craft_nav_duration_2": self.craft_nav_duration_2,
            "craft_nav_wait_delay": self.craft_nav_wait_delay,
            "craft_t_press_delay": self.craft_t_press_delay,
            "craft_click_delay": self.craft_click_delay,
            "craft_button_delay": self.craft_button_delay,
            "craft_craft_button_delay": self.craft_craft_button_delay,
            "craft_sequence_delay": self.craft_sequence_delay,
            "craft_exit_delay": self.craft_exit_delay,
            "devil_fruit_hotkey": self.devil_fruit_hotkey,
            "webhook_enabled": self.webhook_enabled,
            "webhook_url": self.webhook_url,
            "discord_user_id": self.discord_user_id,
            "webhook_notify_devil_fruit": getattr(self, 'webhook_notify_devil_fruit', True),
            "webhook_notify_purchase": getattr(self, 'webhook_notify_purchase', True),
            "webhook_notify_recovery": getattr(self, 'webhook_notify_recovery', True),
            "watchdog_recoveries": self.watchdog.recovery_count if hasattr(self, 'watchdog') else 0,
            "cast_hold_duration": self.cast_hold_duration,
            "recast_timeout": self.recast_timeout,
            "fish_end_delay": self.fish_end_delay,
            "kp": self.kp,
            "kd": self.kd,
            "pd_clamp": self.pd_clamp,
            "loops_per_purchase": self.loops_per_purchase,
            "pre_cast_e_delay": self.pre_cast_e_delay,
            "pre_cast_click_delay": self.pre_cast_click_delay,
            "pre_cast_type_delay": self.pre_cast_type_delay,
            "pre_cast_anti_detect_delay": self.pre_cast_anti_detect_delay,
            "auto_select_bait_delay": self.auto_select_bait_delay,
            "store_fruit_hotkey_delay": self.store_fruit_hotkey_delay,
            "store_fruit_click_delay": self.store_fruit_click_delay,
            "store_fruit_shift_delay": self.store_fruit_shift_delay,
            "store_fruit_backspace_delay": self.store_fruit_backspace_delay,
            "rod_select_delay": self.rod_select_delay,
            "cursor_anti_detect_delay": self.cursor_anti_detect_delay,
            "scan_loop_delay": self.scan_loop_delay,
            "pd_approaching_damping": self.pd_approaching_damping,
            "pd_chasing_damping": self.pd_chasing_damping,
            "gap_tolerance_multiplier": self.gap_tolerance_multiplier,
            "minimize_on_run": self.minimize_on_run,
            "rod_hotkey": self.rod_hotkey,
            "anything_else_hotkey": self.anything_else_hotkey,
            "stay_on_top": self.stay_on_top
        }
    
    def set_water_point(self):
        return self._start_point_setting('water_point')
    
    def set_left_point(self):
        return self._start_point_setting('left_point')
    
    def set_middle_point(self):
        return self._start_point_setting('middle_point')
    
    def set_right_point(self):
        return self._start_point_setting('right_point')
    
    def set_bait_point(self):
        return self._start_point_setting('bait_point')
    
    def set_store_fruit_point(self):
        return self._start_point_setting('store_fruit_point')
    
    def _start_point_setting(self, point_name):
        self.setting_point = True
        self.setting_point_callback = point_name
        
        def wait_for_click():
            VK_LBUTTON = 0x01
            while self.setting_point:
                if ctypes.windll.user32.GetAsyncKeyState(VK_LBUTTON) & 0x8000:
                    pos = pyautogui.position()
                    setattr(self, point_name, {"x": pos.x, "y": pos.y})
                    self.setting_point = False
                    self.save_settings()
                    time.sleep(0.2)
                    break
                time.sleep(0.01)
        
        threading.Thread(target=wait_for_click, daemon=True).start()
        return {"status": "waiting", "message": "Move mouse and LEFT CLICK"}
    
    def update_pd_params(self, kp, kd, pd_clamp):
        self.kp = float(kp)
        self.kd = float(kd)
        self.pd_clamp = float(pd_clamp)
        self.save_settings()
        return {"status": "success"}
    
    def update_cast_timing(self, cast_hold, recast_timeout):
        self.cast_hold_duration = float(cast_hold)
        self.recast_timeout = float(recast_timeout)
        self.save_settings()
        return {"status": "success"}
    
    def update_fish_timing(self, fish_end_delay):
        self.fish_end_delay = float(fish_end_delay)
        self.save_settings()
        return {"status": "success"}
    
    def update_rod_hotkey(self, hotkey):
        self.rod_hotkey = str(hotkey)
        self.save_settings()
        return {"status": "success"}
    
    def update_anything_else_hotkey(self, hotkey):
        self.anything_else_hotkey = str(hotkey)
        self.save_settings()
        return {"status": "success"}
    
    def toggle_auto_buy_bait(self, enabled):
        self.auto_buy_common_bait = bool(enabled)
        self.save_settings()
        return {"status": "success", "enabled": self.auto_buy_common_bait}
    
    def toggle_auto_select_bait(self, enabled):
        self.auto_select_top_bait = bool(enabled)
        self.save_settings()
        return {"status": "success", "enabled": self.auto_select_top_bait}
    
    def toggle_auto_store_fruit(self, enabled):
        self.auto_store_devil_fruit = bool(enabled)
        self.save_settings()
        return {"status": "success", "enabled": self.auto_store_devil_fruit}
    
    def toggle_auto_craft_bait(self, enabled):
        self.auto_craft_bait = bool(enabled)
        self.save_settings()
        return {"status": "success", "enabled": self.auto_craft_bait}
    
    def set_craft_point_1(self):
        return self._start_point_setting('craft_point_1')
    
    def set_craft_point_2(self):
        return self._start_point_setting('craft_point_2')
    
    def set_craft_point_3(self):
        return self._start_point_setting('craft_point_3')
    
    def set_craft_point_4(self):
        return self._start_point_setting('craft_point_4')
    
    def set_leg_bait_point(self):
        return self._start_point_setting('leg_bait_point')
    
    def set_rare_bait_point(self):
        return self._start_point_setting('rare_bait_point')
    
    def toggle_craft_leg_bait(self, enabled):
        self.craft_leg_bait = bool(enabled)
        self.save_settings()
        return {"status": "success"}
    
    def toggle_craft_rare_bait(self, enabled):
        self.craft_rare_bait = bool(enabled)
        self.save_settings()
        return {"status": "success"}
    
    def update_devil_fruit_hotkey(self, hotkey):
        self.devil_fruit_hotkey = str(hotkey)
        self.save_settings()
        return {"status": "success"}
    
    def update_loops_per_purchase(self, loops):
        self.loops_per_purchase = int(loops)
        self.save_settings()
        return {"status": "success"}
    
    def update_advanced_timing(self, params):
        for key, value in params.items():
            if hasattr(self, key):
                # Keep craft_nav_key fields as strings, convert others to float
                if 'craft_nav_key' in key:
                    setattr(self, key, str(value).lower())
                else:
                    setattr(self, key, float(value))
        self.save_settings()
        return {"status": "success"}
    
    def set_area_box(self, x1, y1, x2, y2):
        self.area_box = {"x1": int(x1), "y1": int(y1), "x2": int(x2), "y2": int(y2)}
        self.save_settings()
        return {"status": "success"}
    
    def change_area(self):
        if self.area_selector_active and self.area_selector:
            try:
                self.area_selector.close()
            except:
                pass
            self.area_selector = None
            self.area_selector_active = False
            return {"status": "closed", "message": "Area selector closed"}
        
        self.area_selector_active = True
        
        def show_selector():
            def on_area_selected(coords):
                self.area_box = coords
                self.save_settings()
                self.area_selector_active = False
                self.area_selector = None
                print(f"Area saved: {coords}")
            
            self.area_selector = AreaSelector(self.area_box, on_area_selected)
            self.area_selector.window.mainloop()
        
        threading.Thread(target=show_selector, daemon=True).start()
        return {"status": "showing", "message": "Drag to move, resize corners, press F2 to save"}
    
    def rebind_hotkey(self, key_name, new_key):
        self.hotkeys[key_name] = new_key
        return {"status": "success", "message": f"Hotkey {key_name} set to {new_key}"}
    
    def send_devil_fruit_webhook(self):
        if not self.webhook_url or not self.webhook_enabled or not self.webhook_notify_devil_fruit:
            return
        
        try:
            import requests
            from datetime import datetime, timezone
            
            embed = {
                "title": "🌟 Legendary+ Fruit Caught!",
                "description": "Pity counter was used! Legendary+ fruit detected and stored automatically!",
                "color": 0xFFD700,
                "fields": [
                    {"name": "Total Fish Caught", "value": str(self.fish_count), "inline": True}
                ],
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Add image if screenshot was captured
            if hasattr(self, 'legendary_fruit_screenshot') and self.legendary_fruit_screenshot:
                embed["image"] = {"url": "attachment://legendary_fruit.png"}
            
            payload = {"embeds": [embed], "username": "haiku"}
            if self.discord_user_id:
                payload["content"] = f"<@{self.discord_user_id}>"
            
            # Send with image attachment if available
            if hasattr(self, 'legendary_fruit_screenshot') and self.legendary_fruit_screenshot:
                files = {'file': ('legendary_fruit.png', self.legendary_fruit_screenshot, 'image/png')}
                response = requests.post(self.webhook_url, data={'payload_json': requests.compat.json.dumps(payload)}, files=files, timeout=10)
                self.legendary_fruit_screenshot = None  # Clear after sending
            else:
                response = requests.post(self.webhook_url, json=payload, timeout=10)
            
            if response.status_code == 204:
                print("✅ Devil fruit webhook sent successfully!")
            else:
                print(f"❌ Devil fruit webhook failed: HTTP {response.status_code} - {response.text[:100]}")
        except requests.exceptions.Timeout:
            print("❌ Devil fruit webhook error: Request timed out (check your internet connection)")
        except requests.exceptions.RequestException as e:
            print(f"❌ Devil fruit webhook error: {str(e)}")
        except Exception as e:
            print(f"❌ Devil fruit webhook error: {str(e)}")
    
    def minimize_window(self):
        if self.window:
            self.window.minimize()
            return {"status": "success"}
        return {"status": "error"}
    
    def toggle_maximize(self):
        if self.window:
            self.window.toggle_fullscreen()
            return {"status": "success"}
        return {"status": "error"}
    
    def close_window(self):
        if self.window:
            self.cleanup()
            self.window.destroy()
            return {"status": "success"}
        return {"status": "error"}
    
    def get_window_position(self):
        if self.window:
            return {"x": self.window.x, "y": self.window.y}
        return {"x": 0, "y": 0}
    
    def set_window_position(self, x, y):
        if self.window:
            self.window.move(int(x), int(y))
            return {"status": "success"}
        return {"status": "error"}
    
    def toggle_webhook_logging(self, enabled):
        self.webhook_enabled = bool(enabled)
        self.save_settings()
        return {"status": "success"}
    
    def set_webhook_option(self, option, enabled):
        if option == 'devil_fruit':
            self.webhook_notify_devil_fruit = enabled
        elif option == 'purchase':
            self.webhook_notify_purchase = enabled
        elif option == 'recovery':
            self.webhook_notify_recovery = enabled
        self.save_settings()
        return {"success": True, "message": f"Webhook notification updated"}
    
    def set_minimize_on_run(self, enabled):
        self.minimize_on_run = enabled
        self.save_settings()
        return {"success": True, "message": f"Minimize on run updated"}
    
    def set_stay_on_top(self, enabled):
        self.stay_on_top = enabled
        self.save_settings()
        return {"success": True, "message": f"Stay on top will apply on next restart"}
    
    def reset_to_defaults(self):
        """Reset only advanced settings (timing, PD controller, delays) to their default values.
        Feature toggles, points, webhooks, and hotkeys are preserved."""
        try:
            # Reset PD Controller parameters
            self.kp = 0.9
            self.kd = 0.3
            self.pd_clamp = 1.0
            self.pd_approaching_damping = 2.0
            self.pd_chasing_damping = 0.5
            
            # Reset fishing loop timing
            self.cast_hold_duration = 1.0
            self.recast_timeout = 30.0
            self.fish_end_delay = 0.2
            
            # Reset craft navigation path (timing and keys)
            self.craft_nav_key_1 = 's'
            self.craft_nav_duration_1 = 0.3
            self.craft_nav_key_2 = 'd'
            self.craft_nav_duration_2 = 3.5
            self.craft_nav_wait_delay = 1.0
            self.craft_t_press_delay = 1.0
            self.craft_click_delay = 1.0
            self.craft_button_delay = 0.5
            self.craft_craft_button_delay = 0.5
            self.craft_sequence_delay = 0.3
            self.craft_exit_delay = 0.5
            
            # Reset loop intervals
            self.loops_per_purchase = 100
            
            # Reset store fruit timing delays
            self.store_fruit_hotkey_delay = 1.0
            self.store_fruit_click_delay = 2.0
            self.store_fruit_shift_delay = 0.5
            self.store_fruit_backspace_delay = 1.5
            
            # Reset pre-cast and other advanced delays
            self.pre_cast_e_delay = 1.5
            self.pre_cast_click_delay = 1.0
            self.pre_cast_type_delay = 1.0
            self.pre_cast_anti_detect_delay = 0.05
            self.auto_select_bait_delay = 0.5
            self.rod_select_delay = 0.5
            self.cursor_anti_detect_delay = 0.05
            self.scan_loop_delay = 0.0
            self.state_resend_interval = 0.1
            self.black_screen_threshold = 0.5
            
            # Reset gap tolerance
            self.gap_tolerance_multiplier = 2.0
            
            # Save the reset settings
            self.save_settings()
            
            return {"success": True, "message": "Advanced settings reset to defaults"}
        except Exception as e:
            print(f"Error resetting to defaults: {e}")
            return {"success": False, "message": str(e)}
    
    def update_webhook_url(self, url):
        url = str(url).strip()
        
        # Validate webhook URL format
        if url and not url.startswith('https://'):
            return {"status": "error", "message": "Webhook URL must start with https://"}
        
        if url and 'discord.com/api/webhooks/' not in url and 'discordapp.com/api/webhooks/' not in url:
            return {"status": "error", "message": "Invalid Discord webhook URL format"}
        
        self.webhook_url = url
        # Automatically enable webhooks when a valid URL is provided, disable when cleared
        self.webhook_enabled = bool(url)
        self.save_settings()
        return {"status": "success"}
    
    def update_discord_user_id(self, user_id):
        self.discord_user_id = str(user_id)
        self.save_settings()
        return {"status": "success"}
    
    def test_webhook(self):
        if not self.webhook_url:
            return {"success": False, "message": "No webhook URL configured"}
        
        try:
            import requests
            
            embed = {
                "title": "🧪 Webhook Test",
                "description": "Your webhook is working correctly!",
                "color": 3447003,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
            }
            
            payload = {"embeds": [embed]}
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            
            if response.status_code == 204:
                return {"success": True, "message": "Test successful! Webhook is working."}
            elif response.status_code == 404:
                return {"success": False, "message": "❌ Webhook not found (404). Check your webhook URL - it may have been deleted or is invalid."}
            elif response.status_code == 401:
                return {"success": False, "message": "❌ Unauthorized (401). Webhook URL is invalid or expired."}
            elif response.status_code == 429:
                return {"success": False, "message": "❌ Rate limited (429). Discord is blocking requests. Wait a few minutes and try again."}
            else:
                return {"success": False, "message": f"❌ HTTP {response.status_code}: {response.text[:100]}"}
        except requests.exceptions.Timeout:
            return {"success": False, "message": "❌ Request timed out. Check your internet connection."}
        except requests.exceptions.ConnectionError:
            return {"success": False, "message": "❌ Connection error. Check your internet connection or firewall."}
        except requests.exceptions.RequestException as e:
            return {"success": False, "message": f"❌ Request error: {str(e)[:100]}"}
        except Exception as e:
            return {"success": False, "message": f"❌ Error: {str(e)[:100]}"}
    
    def send_purchase_webhook(self, quantity):
        if not self.webhook_enabled or not self.webhook_url or not self.webhook_notify_purchase:
            return
        
        try:
            import requests
            from datetime import datetime, timezone
            
            embed = {
                "title": "Bait Purchased",
                "description": f"Successfully bought **{quantity}** common bait",
                "color": 0x3498db,
                "fields": [
                    {"name": "Total Fish", "value": str(self.fish_count), "inline": True},
                    {"name": "Time", "value": f"<t:{int(datetime.now().timestamp())}:R>", "inline": True}
                ],
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            payload = {"embeds": [embed], "username": "haiku"}
            response = requests.post(self.webhook_url, json=payload, timeout=5)
            
            if response.status_code == 204:
                print("✅ Purchase webhook sent successfully!")
            else:
                print(f"❌ Purchase webhook failed: HTTP {response.status_code} - {response.text[:100]}")
        except requests.exceptions.Timeout:
            print("❌ Purchase webhook error: Request timed out (check your internet connection)")
        except requests.exceptions.RequestException as e:
            print(f"❌ Purchase webhook error: {str(e)}")
        except Exception as e:
            print(f"❌ Purchase webhook error: {str(e)}")
    
    def send_recovery_webhook(self, recovery_count):
        if not self.webhook_enabled or not self.webhook_url or not self.webhook_notify_recovery:
            return
        
        try:
            import requests
            from datetime import datetime, timezone
            
            embed = {
                "title": "🔄 Watchdog Recovery",
                "description": "Fishing loop was stuck and has been restarted",
                "color": 0xe67e22,
                "fields": [
                    {"name": "Recovery #", "value": str(recovery_count), "inline": True},
                    {"name": "Fish Count", "value": str(self.fish_count), "inline": True},
                    {"name": "Time", "value": f"<t:{int(datetime.now().timestamp())}:R>", "inline": True}
                ],
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            payload = {"embeds": [embed], "username": "haiku"}
            if self.discord_user_id:
                payload["content"] = f"<@{self.discord_user_id}>"
            response = requests.post(self.webhook_url, json=payload, timeout=5)
            
            if response.status_code == 204:
                print("✅ Recovery webhook sent successfully!")
            else:
                print(f"❌ Recovery webhook failed: HTTP {response.status_code} - {response.text[:100]}")
        except requests.exceptions.Timeout:
            print("❌ Recovery webhook error: Request timed out (check your internet connection)")
        except requests.exceptions.RequestException as e:
            print(f"❌ Recovery webhook error: {str(e)}")
        except Exception as e:
            print(f"❌ Recovery webhook error: {str(e)}")
    
    def send_recast_failure_webhook(self):
        if not self.webhook_enabled or not self.webhook_url or not self.webhook_notify_recovery:
            return
        
        try:
            import requests
            from datetime import datetime, timezone
            
            embed = {
                "title": "⚠️ Macro Stopped - No Minigame Detected",
                "description": f"Macro stopped after {self.max_recast_failures} consecutive recasts without detecting a minigame. You may not be near water or the game might have issues.",
                "color": 0xef4444,
                "fields": [
                    {"name": "Failed Recasts", "value": str(self.max_recast_failures), "inline": True},
                    {"name": "Total Fish Caught", "value": str(self.fish_count), "inline": True},
                    {"name": "Time", "value": f"<t:{int(datetime.now().timestamp())}:R>", "inline": True}
                ],
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            payload = {"embeds": [embed], "username": "haiku"}
            if self.discord_user_id:
                payload["content"] = f"<@{self.discord_user_id}>"
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            
            if response.status_code == 204:
                print("✅ Recast failure webhook sent successfully!")
            else:
                print(f"❌ Recast failure webhook failed: HTTP {response.status_code} - {response.text[:100]}")
        except requests.exceptions.Timeout:
            print("❌ Recast failure webhook error: Request timed out (check your internet connection)")
        except requests.exceptions.RequestException as e:
            print(f"❌ Recast failure webhook error: {str(e)}")
        except Exception as e:
            print(f"❌ Recast failure webhook error: {str(e)}")

def setup_hotkeys(api, window):
    def toggle_macro():
        if api.running:
            api.stop_macro()
        else:
            api.start_macro()
        window.evaluate_js('updateUI()')
    
    def change_area():
        window.evaluate_js('changeArea()')
    
    keyboard.add_hotkey(api.hotkeys['start_stop'], toggle_macro)
    keyboard.add_hotkey(api.hotkeys['change_area'], change_area)

def main():
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = Path(__file__).parent.parent
    
    web_path = os.path.join(base_path, 'web', 'index.html')
    
    api = MacroAPI()
    
    try:
        window = webview.create_window(
            'Haiku Fishing',
            web_path,
            js_api=api,
            width=800,
            height=520,
            resizable=True,
            frameless=True,
            background_color='#0f0f11',
            on_top=api.stay_on_top
        )
    except Exception as e:
        print('ERROR: UI backend failed to initialize.')
        print(f'  Details: {e}')
        print('')
        print('This app uses pywebview. On Windows 10/11, it typically requires')
        print('Microsoft Edge WebView2 Runtime to be installed.')
        print('Install it here: https://developer.microsoft.com/microsoft-edge/webview2/')
        raise SystemExit(1)
    
    def on_loaded():
        api.window = window
        setup_hotkeys(api, window)
        # Run heavy init in background thread so UI stays responsive
        import threading
        def _update_status(msg):
            try:
                window.evaluate_js(f"updateLoadingStatus('{msg}')")
            except Exception:
                pass
        def _deferred():
            _update_status('Loading settings...')
            import time as _t; _t.sleep(0.1)  # let UI render
            
            _update_status('Initializing OCR engine...')
            result = api.deferred_init()
            
            _update_status('Almost ready...')
            _t.sleep(0.3)
            
            # Notify the UI that init is complete
            try:
                errors_js = str(result.get('errors', [])).replace("'", "\\'")
                window.evaluate_js(f"onBackendReady({str(result['success']).lower()}, '{errors_js}')")
            except Exception:
                pass
        threading.Thread(target=_deferred, daemon=True).start()

    
    def on_closing():
        api.cleanup()
    
    window.events.loaded += on_loaded
    window.events.closing += on_closing

    try:
        webview.start(debug=False)
    except KeyboardInterrupt:
        try:
            api.cleanup()
        except Exception:
            pass
    except Exception as e:
        print('ERROR: UI failed while starting.')
        print(f'  Details: {e}')
        print('')
        print('If the UI does not open on a new PC, install Microsoft Edge WebView2 Runtime:')
        print('  https://developer.microsoft.com/microsoft-edge/webview2/')
        raise SystemExit(1)

if __name__ == '__main__':
    main()

