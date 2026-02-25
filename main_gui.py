#!/usr/bin/env python3
"""Eden Analytics Pro - Main GUI Entry Point.

This is the primary entry point for the modern GUI interface.
Launches the new dashboard-style interface with sidebar navigation,
dark/light theme support, and all modern features.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Setup logging
from utils.logger import setup_logger
setup_logger()

from utils.logger import get_logger
logger = get_logger(__name__)


def check_dependencies():
    """Check if required dependencies are installed."""
    missing = []
    
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
    
    return missing


def main():
    """Main entry point for Eden Analytics Pro GUI."""
    # Check dependencies first
    missing = check_dependencies()
    if missing:
        print(f"❌ Missing dependencies: {', '.join(missing)}")
        print("\nPlease run: pip install -r requirements.txt")
        print("Or run: python install.py")
        return 1
    
    try:
        # Import the modern GUI
        from gui.main_window_pro import run_gui_pro
        
        logger.info("Starting Eden Analytics Pro with modern interface")
        print("🚀 Starting Eden Analytics Pro v2.1.1...")
        
        return run_gui_pro()
        
    except ImportError as e:
        logger.warning(f"Could not load modern interface: {e}")
        print(f"⚠️  Note: Some optional features may be unavailable: {e}")
        
        # Fall back to original main window
        try:
            from gui.main_window import run_gui
            logger.info("Falling back to standard interface")
            return run_gui()
        except ImportError as e2:
            logger.error(f"Could not load GUI: {e2}")
            print(f"❌ Error: Could not load GUI: {e2}")
            print("\nPlease ensure all dependencies are installed:")
            print("  pip install -r requirements.txt")
            return 1
            
    except Exception as e:
        logger.exception(f"Error starting application: {e}")
        print(f"❌ Error starting application: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
