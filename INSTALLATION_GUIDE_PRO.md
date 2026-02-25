# Eden Pro Installation Guide

This guide provides comprehensive instructions for installing all dependencies required for Eden Pro, including the ML-based overtime predictor, backtesting module, and PyQt6 GUI application.

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Quick Installation](#quick-installation)
3. [Platform-Specific Instructions](#platform-specific-instructions)
   - [Windows](#windows)
   - [Linux](#linux)
   - [macOS](#macos)
4. [Verification Steps](#verification-steps)
5. [Troubleshooting](#troubleshooting)
6. [Alternative Installation Methods](#alternative-installation-methods)
7. [PyCharm Setup](#pycharm-setup)

---

## System Requirements

- **Python**: 3.8 or higher (3.10+ recommended)
- **RAM**: Minimum 4GB (8GB recommended for ML training)
- **Disk Space**: ~500MB for dependencies
- **Operating System**: Windows 10/11, Linux (Ubuntu 20.04+), or macOS 11+

### Dependencies Overview

| Package | Version | Purpose |
|---------|---------|----------|
| PyQt6 | ≥6.4.0 | GUI Application |
| scikit-learn | ≥1.2.0 | ML Overtime Predictor |
| pandas | ≥1.5.0 | Data Processing |
| matplotlib | ≥3.6.0 | Charts & Reports |
| numpy | ≥1.21.0 | Numerical Calculations |
| requests | ≥2.28.0 | API Calls |
| pydantic | ≥2.0.0 | Data Validation |
| rich | ≥13.0.0 | Console UI |

---

## Quick Installation

For most users, this single command will install everything:

```bash
pip install -r requirements.txt
```

Then verify the installation:

```bash
python test_installation.py
```

---

## Platform-Specific Instructions

### Windows

#### Step 1: Install Python

1. Download Python from [python.org](https://www.python.org/downloads/)
2. Run the installer and **check "Add Python to PATH"**
3. Verify: `python --version`

#### Step 2: Install Dependencies

```cmd
# Open Command Prompt or PowerShell
cd path\to\eden_mvp

# Upgrade pip first
python -m pip install --upgrade pip

# Install all dependencies
pip install -r requirements.txt
```

#### Step 3: Install Visual C++ Redistributable (if needed for PyQt6)

If you encounter DLL errors, install:
- [Visual C++ Redistributable](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist)

---

### Linux

#### Ubuntu/Debian

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install Python and pip
sudo apt install python3 python3-pip python3-venv -y

# Install Qt6 system dependencies (required for PyQt6)
sudo apt install libxcb-xinerama0 libxcb-cursor0 libxkbcommon0 -y
sudo apt install libegl1 libgl1-mesa-glx libxcb-icccm4 libxcb-image0 -y
sudo apt install libxcb-keysyms1 libxcb-randr0 libxcb-render-util0 -y
sudo apt install libxcb-shape0 libxcb-xfixes0 -y

# Optional: Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
cd eden_mvp
pip install --upgrade pip
pip install -r requirements.txt
```

#### Fedora/RHEL/CentOS

```bash
# Install dependencies
sudo dnf install python3 python3-pip qt6-qtbase xcb-util-wm -y

# Install Eden Pro dependencies
cd eden_mvp
pip install -r requirements.txt
```

#### Arch Linux

```bash
sudo pacman -S python python-pip qt6-base
pip install -r requirements.txt
```

---

### macOS

#### Using Homebrew (Recommended)

```bash
# Install Homebrew if not installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python
brew install python@3.11

# Install Qt6 (optional, but can help with some issues)
brew install qt@6

# Install dependencies
cd eden_mvp
pip3 install --upgrade pip
pip3 install -r requirements.txt
```

#### Apple Silicon (M1/M2/M3) Notes

PyQt6 works natively on Apple Silicon. If you encounter issues:

```bash
# Install Rosetta 2 for x86 compatibility
softwareupdate --install-rosetta

# Or use conda (see Alternative Installation Methods)
```

---

## Verification Steps

### Step 1: Run the Test Script

```bash
cd eden_mvp
python test_installation.py
```

Expected output:
```
============================================================
    EDEN PRO - Installation Verification
============================================================

[Testing Imports]
✅ PyQt6 v6.x.x
✅ scikit-learn v1.x.x
✅ pandas v2.x.x
✅ matplotlib v3.x.x
✅ numpy v1.x.x

[Component Tests]
✅ PyQt6 QApplication created successfully
✅ RandomForestClassifier trained and predicted
✅ matplotlib plot created
✅ pandas DataFrame created

============================================================
    ALL TESTS PASSED - Eden Pro is ready!
============================================================
```

### Step 2: Verify GUI Launch (Optional)

```bash
# Test if GUI can start (may require display)
python -c "import os; os.environ['QT_QPA_PLATFORM']='offscreen'; from PyQt6.QtWidgets import QApplication; app = QApplication([]); print('GUI test passed')"
```

### Step 3: Run Eden Pro

```bash
# Console version
python main.py

# GUI version
python main_gui.py
```

---

## Troubleshooting

### PyQt6 Issues (Most Common)

#### Problem: "Could not load the Qt platform plugin"

**Linux Solution:**
```bash
# Install missing Qt dependencies
sudo apt install libxcb-xinerama0 libxcb-cursor0 libxkbcommon-x11-0 -y
sudo apt install libegl1-mesa libgl1-mesa-glx -y

# Set environment variable
export QT_QPA_PLATFORM=xcb
```

**Windows Solution:**
- Install Visual C++ Redistributable (2015-2022)
- Run: `pip uninstall PyQt6 PyQt6-Qt6 PyQt6-sip && pip install PyQt6`

**macOS Solution:**
```bash
brew install qt@6
export PATH="/opt/homebrew/opt/qt@6/bin:$PATH"
```

#### Problem: "No module named 'PyQt6'"

```bash
# Reinstall PyQt6
pip uninstall PyQt6 PyQt6-Qt6 PyQt6-sip
pip install PyQt6>=6.4.0
```

#### Problem: "xcb plugin error" on headless/server Linux

```bash
# Use offscreen platform
export QT_QPA_PLATFORM=offscreen

# Or install virtual framebuffer
sudo apt install xvfb
xvfb-run python main_gui.py
```

---

### scikit-learn Issues

#### Problem: "ImportError: cannot import name 'RandomForestClassifier'"

```bash
pip uninstall scikit-learn
pip install scikit-learn>=1.2.0
```

#### Problem: Slow installation or compile errors

```bash
# Install pre-built wheel
pip install --only-binary :all: scikit-learn
```

---

### matplotlib Issues

#### Problem: "No display" or backend errors

```python
# Add this at the start of your script
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
```

Or set environment variable:
```bash
export MPLBACKEND=Agg
```

---

### General Issues

#### Problem: "pip: command not found"

```bash
# Try with python -m
python -m pip install -r requirements.txt

# Or install pip
python -m ensurepip --upgrade
```

#### Problem: Permission denied errors

```bash
# Use --user flag
pip install --user -r requirements.txt

# Or use virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows
pip install -r requirements.txt
```

#### Problem: Version conflicts

```bash
# Create fresh virtual environment
python -m venv fresh_env
source fresh_env/bin/activate
pip install -r requirements.txt
```

---

## Alternative Installation Methods

### Using Conda (Recommended for Data Science)

```bash
# Create conda environment
conda create -n eden_pro python=3.11 -y
conda activate eden_pro

# Install packages via conda-forge
conda install -c conda-forge pyqt=6 scikit-learn pandas matplotlib numpy -y

# Install remaining packages via pip
pip install requests pydantic pyyaml rich python-dateutil
```

### Using System Packages (Linux)

#### Ubuntu/Debian
```bash
sudo apt install python3-pyqt6 python3-sklearn python3-pandas \
                 python3-matplotlib python3-numpy -y
```

### Docker (For Isolation)

```dockerfile
FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    libxcb-xinerama0 libxcb-cursor0 && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
CMD ["python", "main.py"]
```

---

## PyCharm Setup

### Configure Python Interpreter

1. Open **File → Settings → Project → Python Interpreter**
2. Click the gear icon → **Add Interpreter**
3. Select **Virtualenv Environment** or **System Interpreter**
4. Choose Python 3.8+ installation

### Install Packages in PyCharm

1. Open **View → Tool Windows → Python Packages**
2. Search for each package:
   - PyQt6
   - scikit-learn
   - pandas
   - matplotlib
   - numpy
3. Click **Install Package** for each

### Run Configuration

1. Click **Run → Edit Configurations**
2. Add **Python** configuration
3. Set **Script path** to `main_gui.py`
4. Set **Working directory** to the `eden_mvp` folder

---

## Verified Installation Results

**Date:** February 19, 2026  
**Python Version:** 3.11.6  
**Environment:** Linux (Ubuntu)

### Installed Versions

| Package | Installed Version | Status |
|---------|------------------|--------|
| PyQt6 | 6.10.2 | ✅ Verified |
| scikit-learn | 1.8.0 | ✅ Verified |
| pandas | 2.2.3 | ✅ Verified |
| matplotlib | 3.9.2 | ✅ Verified |
| numpy | 1.26.4 | ✅ Verified |

### Test Results

- ✅ All imports successful
- ✅ PyQt6 QApplication created
- ✅ RandomForestClassifier trained and made predictions
- ✅ matplotlib plot saved to file
- ✅ pandas DataFrame created with correct shape
- ✅ numpy array operations working

---

## Support

If you continue to experience issues:

1. Check Python version: `python --version`
2. List installed packages: `pip list`
3. Run diagnostic: `python test_installation.py`
4. Check system dependencies for PyQt6

For additional help, refer to the official documentation:
- [PyQt6 Documentation](https://doc.qt.io/qtforpython-6/)
- [scikit-learn Installation](https://scikit-learn.org/stable/install.html)
- [pandas Installation](https://pandas.pydata.org/docs/getting_started/install.html)
