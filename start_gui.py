#!/usr/bin/env python3
"""Eden Analytics Pro - GUI Launcher.

Simple launcher for the graphical user interface with dependency checks.
This script launches the modern dashboard interface with:
- Sidebar navigation
- Dark/Light theme support  
- Dashboard with live statistics
- ML Models management
- Arbitrage detection
- History tracking
- Settings panel
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def check_dependencies():
    """Check if required dependencies are installed."""
    missing = []
    optional_missing = []
    
    # Required dependencies
    try:
        import PyQt6
    except ImportError:
        missing.append("PyQt6")
    
    try:
        import yaml
    except ImportError:
        missing.append("pyyaml")
    
    try:
        import pydantic
    except ImportError:
        missing.append("pydantic")
    
    try:
        import requests
    except ImportError:
        missing.append("requests")
    
    # Optional dependencies (for enhanced features)
    try:
        import numpy
    except ImportError:
        optional_missing.append("numpy")
    
    try:
        import pandas
    except ImportError:
        optional_missing.append("pandas")
    
    try:
        import sklearn
    except ImportError:
        optional_missing.append("scikit-learn")
    
    try:
        import plotly
    except ImportError:
        optional_missing.append("plotly")
    
    return missing, optional_missing


def show_splash():
    """Show a simple text splash screen."""
    splash = """
    ╔═══════════════════════════════════════════════════════════════╗
    ║                                                               ║
    ║          🏒  Eden Analytics Pro v2.4.0  🏒                    ║
    ║                                                               ║
    ║              Hockey Arbitrage Analysis System                 ║
    ║                   Modern Dashboard Interface                  ║
    ║         + Belarusian Bookmakers (Betera, Fonbet, etc.)        ║
    ║                                                               ║
    ╚═══════════════════════════════════════════════════════════════╝
    """
    print(splash)


def main():
    """Main launcher function."""
    show_splash()
    
    print("Checking dependencies...")
    
    missing, optional_missing = check_dependencies()
    
    if missing:
        print(f"\n❌ Missing required dependencies: {', '.join(missing)}")
        print("\nPlease run: pip install -r requirements.txt")
        print("Or run: python install.py")
        sys.exit(1)
    
    print("✓ All required dependencies OK")
    
    if optional_missing:
        print(f"⚠️  Optional dependencies not installed: {', '.join(optional_missing)}")
        print("   Some features may be limited. Install with: pip install -r requirements.txt")
    
    print("\n🚀 Starting Eden Analytics Pro...\n")
    print("   Loading modern dashboard interface...")
    
    try:
        # Import and run the modern GUI directly
        from gui.main_window_pro import run_gui_pro
        print("   ✓ Modern interface loaded successfully")
        print("   Launching application...\n")
        run_gui_pro()
        
    except ImportError as e:
        print(f"\n⚠️  Could not load modern interface: {e}")
        print("   Trying standard interface...")
        
        try:
            from gui.main_window import run_gui
            print("   ✓ Standard interface loaded")
            print("   Launching application...\n")
            run_gui()
        except ImportError as e2:
            print(f"\n❌ Error loading GUI: {e2}")
            print("\nPlease ensure all dependencies are installed:")
            print("  pip install -r requirements.txt")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ Error starting application: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
