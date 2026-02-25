"""Windows Installer Setup for Eden Analytics Pro."""

import os
import sys
import shutil
from pathlib import Path

# PyInstaller spec generation
PYINSTALLER_SPEC = '''
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main_gui.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('gui/assets', 'gui/assets'),
        ('config', 'config'),
        ('localization', 'localization'),
    ],
    hiddenimports=[
        'PyQt6.QtWebEngineWidgets',
        'sklearn.ensemble',
        'sklearn.preprocessing',
        'plotly',
        'yaml',
        'telegram',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='EdenAnalyticsPro',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='gui/assets/logo.ico',
)
'''

INNO_SETUP_SCRIPT = '''
; Eden Analytics Pro Installer Script
; Inno Setup 6.x

#define MyAppName "Eden Analytics Pro"
#define MyAppVersion "2.0.0"
#define MyAppPublisher "Eden Analytics"
#define MyAppURL "https://eden-analytics.com"
#define MyAppExeName "EdenAnalyticsPro.exe"

[Setup]
AppId={{EDEN-ANALYTICS-PRO-2024}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=LICENSE.txt
OutputDir=dist\\installer
OutputBaseFilename=EdenAnalyticsPro_Setup_{#MyAppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
SetupIconFile=gui\\assets\\logo.ico
UninstallDisplayIcon={app}\\{#MyAppExeName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "russian"; MessagesFile: "compiler:Languages\\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode

[Files]
Source: "dist\\EdenAnalyticsPro.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "config\\*"; DestDir: "{app}\\config"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "localization\\*"; DestDir: "{app}\\localization"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "gui\\assets\\*"; DestDir: "{app}\\assets"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\\{#MyAppName}"; Filename: "{app}\\{#MyAppExeName}"
Name: "{group}\\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\\{#MyAppName}"; Filename: "{app}\\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
function InitializeSetup(): Boolean;
begin
  Result := True;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    // Post-installation tasks
  end;
end;
'''

BUILD_SCRIPT_BAT = '''@echo off
echo ========================================
echo Eden Analytics Pro - Build Installer
echo ========================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found!
    exit /b 1
)

REM Install PyInstaller if needed
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo Installing PyInstaller...
    pip install pyinstaller
)

REM Build executable
echo Building executable...
pyinstaller --clean --noconfirm installer/windows/eden.spec

if errorlevel 1 (
    echo ERROR: PyInstaller build failed!
    exit /b 1
)

echo.
echo Executable built successfully!
echo Location: dist/EdenAnalyticsPro.exe
echo.

REM Check for Inno Setup
if exist "%ProgramFiles(x86)%\\Inno Setup 6\\ISCC.exe" (
    echo Building installer...
    "%ProgramFiles(x86)%\\Inno Setup 6\\ISCC.exe" installer/windows/installer.iss
    
    if errorlevel 1 (
        echo ERROR: Inno Setup build failed!
        exit /b 1
    )
    
    echo.
    echo Installer built successfully!
    echo Location: dist/installer/EdenAnalyticsPro_Setup_2.0.0.exe
) else (
    echo WARNING: Inno Setup not found. Installer not created.
    echo Download from: https://jrsoftware.org/isdl.php
)

echo.
echo Build complete!
pause
'''

def create_installer_files():
    """Create all necessary installer files."""
    base_dir = Path(__file__).parent
    
    # Create spec file
    spec_path = base_dir / "eden.spec"
    with open(spec_path, 'w') as f:
        f.write(PYINSTALLER_SPEC)
    print(f"Created: {spec_path}")
    
    # Create Inno Setup script
    iss_path = base_dir / "installer.iss"
    with open(iss_path, 'w') as f:
        f.write(INNO_SETUP_SCRIPT)
    print(f"Created: {iss_path}")
    
    # Create build script
    bat_path = base_dir / "build_installer.bat"
    with open(bat_path, 'w') as f:
        f.write(BUILD_SCRIPT_BAT)
    print(f"Created: {bat_path}")
    
    # Create LICENSE.txt placeholder
    license_path = base_dir.parent.parent / "LICENSE.txt"
    if not license_path.exists():
        with open(license_path, 'w') as f:
            f.write("""Eden Analytics Pro License Agreement

Copyright (c) 2024 Eden Analytics

Permission is hereby granted to use this software for personal and 
commercial purposes, subject to the following conditions:

1. This software is provided "as is", without warranty of any kind.
2. The authors are not liable for any damages arising from the use of this software.
3. Redistribution requires written permission from Eden Analytics.

For licensing inquiries, contact: license@eden-analytics.com
""")
        print(f"Created: {license_path}")
    
    print("\nInstaller files created successfully!")
    print("\nTo build the installer:")
    print("1. Install PyInstaller: pip install pyinstaller")
    print("2. Install Inno Setup 6 from https://jrsoftware.org/isdl.php")
    print("3. Run: build_installer.bat")


if __name__ == "__main__":
    create_installer_files()
