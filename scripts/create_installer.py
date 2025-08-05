#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
创建 Windows 安装包脚本
使用 Inno Setup 创建专业的安装程序
"""

import os
import sys
import subprocess
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from version import __version__, __app_name__
except ImportError:
    # 如果无法导入，使用默认值
    __version__ = "1.0.0"
    __app_name__ = "SwaggerAPITester"

def create_inno_setup_script():
    """创建 Inno Setup 脚本"""
    
    script_content = f'''
; Swagger API Tester 安装脚本
; 使用 Inno Setup 编译器生成

[Setup]
AppName={__app_name__}
AppVersion={__version__}
AppPublisher=Swagger API Tester Team
AppPublisherURL=https://github.com/your-repo
AppSupportURL=https://github.com/your-repo/issues
AppUpdatesURL=https://github.com/your-repo/releases
DefaultDirName={{autopf}}\\{__app_name__}
DefaultGroupName={__app_name__}
AllowNoIcons=yes
LicenseFile=LICENSE
OutputDir=dist\\installer
OutputBaseFilename=SwaggerAPITester-{__version__}-Setup
SetupIconFile=assets\\icon.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "chinesesimplified"; MessagesFile: "compiler:Languages\\ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "{{cm:CreateDesktopIcon}}"; GroupDescription: "{{cm:AdditionalIcons}}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{{cm:CreateQuickLaunchIcon}}"; GroupDescription: "{{cm:AdditionalIcons}}"; Flags: unchecked; OnlyBelowVersion: 6.1

[Files]
; 单文件版本
Source: "dist\\SwaggerAPITester.exe"; DestDir: "{{app}}"; Flags: ignoreversion
; 配置文件
Source: "config\\*"; DestDir: "{{app}}\\config"; Flags: ignoreversion recursesubdirs createallsubdirs
; 模板文件
Source: "templates\\*"; DestDir: "{{app}}\\templates"; Flags: ignoreversion recursesubdirs createallsubdirs
; 资源文件
Source: "assets\\*"; DestDir: "{{app}}\\assets"; Flags: ignoreversion recursesubdirs createallsubdirs
; 文档
Source: "README.md"; DestDir: "{{app}}"; Flags: ignoreversion
Source: "DEPLOYMENT.md"; DestDir: "{{app}}"; Flags: ignoreversion

[Icons]
Name: "{{group}}\\{__app_name__}"; Filename: "{{app}}\\SwaggerAPITester.exe"
Name: "{{group}}\\{{cm:UninstallProgram,{__app_name__}}}"; Filename: "{{uninstallexe}}"
Name: "{{autodesktop}}\\{__app_name__}"; Filename: "{{app}}\\SwaggerAPITester.exe"; Tasks: desktopicon
Name: "{{userappdata}}\\Microsoft\\Internet Explorer\\Quick Launch\\{__app_name__}"; Filename: "{{app}}\\SwaggerAPITester.exe"; Tasks: quicklaunchicon

[Run]
Filename: "{{app}}\\SwaggerAPITester.exe"; Description: "{{cm:LaunchProgram,{__app_name__}}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{{app}}\\config"
Type: filesandordirs; Name: "{{app}}\\logs"
Type: filesandordirs; Name: "{{app}}\\temp"
'''
    
    script_path = Path('installer.iss')
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(script_content.strip())
    
    print(f"Inno Setup script created: {script_path}")
    return script_path

def find_inno_setup():
    """查找 Inno Setup 编译器"""
    possible_paths = [
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
        r"C:\Program Files (x86)\Inno Setup 5\ISCC.exe",
        r"C:\Program Files\Inno Setup 5\ISCC.exe",
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    return None

def create_installer():
    """创建安装包"""
    print("Creating Windows Installer...")
    print("="*50)
    
    # 检查必要文件
    exe_path = Path('dist/SwaggerAPITester.exe')
    if not exe_path.exists():
        print("ERROR: Single file executable not found!")
        print("Please run: python scripts/build_local.py")
        print("And select option 2 (Single file version)")
        return False
    
    # 创建安装包输出目录
    installer_dir = Path('dist/installer')
    installer_dir.mkdir(exist_ok=True)
    
    # 创建 Inno Setup 脚本
    script_path = create_inno_setup_script()
    
    # 查找 Inno Setup 编译器
    iscc_path = find_inno_setup()
    if not iscc_path:
        print("ERROR: Inno Setup not found!")
        print("Please install Inno Setup from: https://jrsoftware.org/isinfo.php")
        print("After installation, run this script again.")
        return False
    
    print(f"Found Inno Setup: {iscc_path}")
    
    # 编译安装包
    try:
        print("Compiling installer...")
        result = subprocess.run([
            iscc_path, str(script_path)
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("SUCCESS: Installer created!")
            
            # 查找生成的安装包
            installer_files = list(installer_dir.glob('*.exe'))
            if installer_files:
                installer_file = installer_files[0]
                size_mb = installer_file.stat().st_size / (1024 * 1024)
                print(f"Installer: {installer_file}")
                print(f"Size: {size_mb:.1f} MB")
                return True
            else:
                print("WARNING: Installer file not found in output directory")
                return False
        else:
            print("ERROR: Installer compilation failed")
            print(result.stderr)
            return False
    
    except Exception as e:
        print(f"ERROR: {e}")
        return False

def create_nsis_script():
    """创建 NSIS 脚本（备选方案）"""
    script_content = f'''
; NSIS 安装脚本
; 备选的安装包制作方案

!define APP_NAME "{__app_name__}"
!define APP_VERSION "{__version__}"
!define APP_PUBLISHER "Swagger API Tester Team"
!define APP_URL "https://github.com/your-repo"
!define APP_EXE "SwaggerAPITester.exe"

Name "${{APP_NAME}}"
OutFile "dist\\installer\\SwaggerAPITester-${{APP_VERSION}}-Setup-NSIS.exe"
InstallDir "$PROGRAMFILES64\\${{APP_NAME}}"
RequestExecutionLevel user

Page directory
Page instfiles

Section "MainSection" SEC01
    SetOutPath "$INSTDIR"
    File "dist\\SwaggerAPITester.exe"
    File /r "config"
    File /r "templates"
    File /r "assets"
    File "README.md"
    
    CreateDirectory "$SMPROGRAMS\\${{APP_NAME}}"
    CreateShortCut "$SMPROGRAMS\\${{APP_NAME}}\\${{APP_NAME}}.lnk" "$INSTDIR\\${{APP_EXE}}"
    CreateShortCut "$DESKTOP\\${{APP_NAME}}.lnk" "$INSTDIR\\${{APP_EXE}}"
    
    WriteUninstaller "$INSTDIR\\Uninstall.exe"
SectionEnd

Section "Uninstall"
    Delete "$INSTDIR\\*.*"
    RMDir /r "$INSTDIR"
    Delete "$SMPROGRAMS\\${{APP_NAME}}\\*.*"
    RMDir "$SMPROGRAMS\\${{APP_NAME}}"
    Delete "$DESKTOP\\${{APP_NAME}}.lnk"
SectionEnd
'''
    
    script_path = Path('installer.nsi')
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(script_content.strip())
    
    print(f"NSIS script created: {script_path}")
    return script_path

def main():
    """主函数"""
    print("Windows Installer Creator")
    print("="*50)
    
    # 检查当前目录
    if not os.path.exists('main.py'):
        print("ERROR: Please run this script from the project root directory")
        return False
    
    success = create_installer()
    
    if not success:
        print("\nAlternative: NSIS Script")
        print("="*30)
        create_nsis_script()
        print("You can use NSIS to compile the installer:")
        print("1. Install NSIS from: https://nsis.sourceforge.io/")
        print("2. Right-click installer.nsi and select 'Compile NSIS Script'")
    
    return success

if __name__ == '__main__':
    main()
