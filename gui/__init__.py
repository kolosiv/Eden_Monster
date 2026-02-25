"""GUI module for Eden Analytics Pro."""

try:
    from gui.main_window_pro import EdenMainWindowPro, run_gui_pro
    EdenMainWindow = EdenMainWindowPro
    run_gui = run_gui_pro
except ImportError:
    from gui.main_window import EdenMainWindow, run_gui

__all__ = ['EdenMainWindow', 'run_gui']
