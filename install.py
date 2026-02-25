#!/usr/bin/env python3
"""Eden Analytics Pro - Interactive Installation Script.

This script provides an interactive installation experience for Eden Analytics Pro.
It checks system requirements, installs dependencies, and configures the application.
"""

import os
import sys
import subprocess
import platform
import shutil
from pathlib import Path

# Colors for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header():
    """Print the installation header."""
    header = """
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║     🏒  Eden Analytics Pro - Installation Wizard  🏒              ║
║                       Version 2.1.1                               ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
    """
    print(Colors.CYAN + header + Colors.ENDC)

def check_python_version():
    """Check if Python version is compatible."""
    print("\n📋 Checking Python version...")
    
    major, minor = sys.version_info[:2]
    version_str = f"{major}.{minor}.{sys.version_info[2]}"
    
    if major < 3 or (major == 3 and minor < 8):
        print(f"{Colors.FAIL}❌ Python {version_str} detected. Required: 3.8+{Colors.ENDC}")
        print("   Please install Python 3.8 or higher from https://python.org")
        return False
    
    print(f"{Colors.GREEN}✓ Python {version_str} - OK{Colors.ENDC}")
    return True

def check_pip():
    """Check if pip is installed."""
    print("\n📋 Checking pip...")
    
    try:
        import pip
        print(f"{Colors.GREEN}✓ pip {pip.__version__} - OK{Colors.ENDC}")
        return True
    except ImportError:
        print(f"{Colors.FAIL}❌ pip not found{Colors.ENDC}")
        print("   Installing pip...")
        try:
            subprocess.check_call([sys.executable, "-m", "ensurepip", "--upgrade"])
            return True
        except subprocess.CalledProcessError:
            print(f"{Colors.FAIL}❌ Failed to install pip{Colors.ENDC}")
            return False

def install_dependencies():
    """Install required dependencies from requirements.txt."""
    print("\n📦 Installing dependencies...")
    print("   This may take a few minutes...\n")
    
    requirements_path = Path(__file__).parent / "requirements.txt"
    
    if not requirements_path.exists():
        print(f"{Colors.FAIL}❌ requirements.txt not found{Colors.ENDC}")
        return False
    
    try:
        # Upgrade pip first
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--upgrade", "pip"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT
        )
        
        # Install requirements
        process = subprocess.Popen(
            [sys.executable, "-m", "pip", "install", "-r", str(requirements_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        
        for line in process.stdout:
            if "Successfully installed" in line or "Requirement already satisfied" in line:
                # Show only important messages
                pkg_name = line.split()[-1] if "installed" in line else ""
                if pkg_name:
                    print(f"   ✓ Installed: {pkg_name}")
        
        process.wait()
        
        if process.returncode == 0:
            print(f"\n{Colors.GREEN}✓ All dependencies installed successfully{Colors.ENDC}")
            return True
        else:
            print(f"\n{Colors.FAIL}❌ Some dependencies failed to install{Colors.ENDC}")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"{Colors.FAIL}❌ Error installing dependencies: {e}{Colors.ENDC}")
        return False

def configure_api_key():
    """Configure API key interactively."""
    print("\n🔑 API Configuration")
    print("="*50)
    
    config_path = Path(__file__).parent / "config" / "config.yaml"
    
    print("\nTo get real odds data, you need an API key from The Odds API.")
    print("Get your free key at: https://the-odds-api.com/")
    print("\n(Free tier: 500 requests/month)")
    
    choice = input("\nDo you want to enter your API key now? (y/n): ").strip().lower()
    
    if choice == 'y':
        api_key = input("Enter your API key: ").strip()
        
        if api_key and len(api_key) > 20:
            try:
                with open(config_path, 'r') as f:
                    content = f.read()
                
                content = content.replace('key: "YOUR_API_KEY_HERE"', f'key: "{api_key}"')
                content = content.replace('demo_mode: true', 'demo_mode: false')
                
                with open(config_path, 'w') as f:
                    f.write(content)
                
                print(f"{Colors.GREEN}✓ API key configured successfully{Colors.ENDC}")
                return True
            except Exception as e:
                print(f"{Colors.WARNING}⚠ Could not save API key: {e}{Colors.ENDC}")
                return False
        else:
            print(f"{Colors.WARNING}⚠ Invalid API key. Using demo mode.{Colors.ENDC}")
            return False
    else:
        print("\n   Using demo mode (no real data)")
        print("   You can configure the API key later in config/config.yaml")
        return False

def initialize_database():
    """Initialize the database."""
    print("\n💾 Initializing database...")
    
    try:
        # Import and initialize database manager
        sys.path.insert(0, str(Path(__file__).parent))
        from database.db_manager import DatabaseManager
        
        db = DatabaseManager()
        print(f"{Colors.GREEN}✓ Database initialized successfully{Colors.ENDC}")
        return True
    except Exception as e:
        print(f"{Colors.WARNING}⚠ Database initialization warning: {e}{Colors.ENDC}")
        return True  # Non-critical

def create_desktop_shortcut():
    """Create desktop shortcut (Windows only)."""
    if platform.system() != "Windows":
        return
    
    print("\n🖥️ Desktop Shortcut")
    
    choice = input("Create desktop shortcut? (y/n): ").strip().lower()
    
    if choice != 'y':
        return
    
    try:
        import winreg
        
        desktop = Path.home() / "Desktop"
        shortcut_path = desktop / "Eden Analytics Pro.lnk"
        
        # Create shortcut using PowerShell
        target = Path(__file__).parent / "main_gui.py"
        
        ps_script = f'''
$WshShell = New-Object -comObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("{shortcut_path}")
$Shortcut.TargetPath = "pythonw.exe"
$Shortcut.Arguments = "\"{target}\""
$Shortcut.WorkingDirectory = "{Path(__file__).parent}"
$Shortcut.Description = "Eden Analytics Pro - Hockey Arbitrage System"
$Shortcut.Save()
        '''
        
        subprocess.run(["powershell", "-Command", ps_script], check=True)
        print(f"{Colors.GREEN}✓ Desktop shortcut created{Colors.ENDC}")
    except Exception as e:
        print(f"{Colors.WARNING}⚠ Could not create shortcut: {e}{Colors.ENDC}")

def train_ml_model():
    """Optionally train the ML model."""
    print("\n🤖 ML Model Training")
    print("="*50)
    print("\nThe ML model improves overtime predictions.")
    print("Training takes about 1-2 minutes.")
    
    choice = input("\nTrain ML model now? (y/n): ").strip().lower()
    
    if choice != 'y':
        print("   Skipped. You can train later with: python -m models.model_trainer")
        return
    
    try:
        print("\n   Training model...")
        
        sys.path.insert(0, str(Path(__file__).parent))
        from models.model_trainer import train_initial_model
        
        result = train_initial_model()
        
        print(f"\n{Colors.GREEN}✓ ML model trained successfully{Colors.ENDC}")
        print(f"   Accuracy: {result.accuracy:.1%}")
    except Exception as e:
        print(f"{Colors.WARNING}⚠ ML training skipped: {e}{Colors.ENDC}")

def print_success():
    """Print installation success message."""
    success_msg = f"""
{Colors.GREEN}
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║         ✅  Installation completed successfully!  ✅              ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
{Colors.ENDC}

{Colors.CYAN}Quick Start:{Colors.ENDC}

  1. Run the GUI:           python main_gui.py
  2. Run the console:       python main.py
  3. Start Telegram bot:    python start_bot.py

{Colors.CYAN}Documentation:{Colors.ENDC}

  • Quick Start Guide:      docs/QUICK_START_GUIDE.md
  • User Manual:            docs/USER_MANUAL.md
  • Telegram Setup:         docs/TELEGRAM_BOT_SETUP.md

{Colors.CYAN}Need help?{Colors.ENDC}

  • Run diagnostics:        python check_system.py
  • Check FAQ:              docs/FAQ.md

    """
    print(success_msg)

def main():
    """Main installation function."""
    print_header()
    
    # Check system requirements
    if not check_python_version():
        sys.exit(1)
    
    if not check_pip():
        sys.exit(1)
    
    # Install dependencies
    if not install_dependencies():
        print(f"\n{Colors.WARNING}⚠ Installation completed with warnings{Colors.ENDC}")
        print("   Some features may not work correctly.")
    
    # Initialize database
    initialize_database()
    
    # Configure API key
    configure_api_key()
    
    # Train ML model (optional)
    train_ml_model()
    
    # Create desktop shortcut (Windows)
    create_desktop_shortcut()
    
    # Print success message
    print_success()

if __name__ == "__main__":
    main()
