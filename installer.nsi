; NSIS 安装脚本
; 备选的安装包制作方案

!define APP_NAME "Swagger API测试工具"
!define APP_VERSION "1.0.0"
!define APP_PUBLISHER "Swagger API Tester Team"
!define APP_URL "https://github.com/your-repo"
!define APP_EXE "SwaggerAPITester.exe"

Name "${APP_NAME}"
OutFile "dist\installer\SwaggerAPITester-${APP_VERSION}-Setup-NSIS.exe"
InstallDir "$PROGRAMFILES64\${APP_NAME}"
RequestExecutionLevel user

Page directory
Page instfiles

Section "MainSection" SEC01
    SetOutPath "$INSTDIR"
    File "dist\SwaggerAPITester.exe"
    File /r "config"
    File /r "templates"
    File /r "assets"
    File "README.md"
    
    CreateDirectory "$SMPROGRAMS\${APP_NAME}"
    CreateShortCut "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" "$INSTDIR\${APP_EXE}"
    CreateShortCut "$DESKTOP\${APP_NAME}.lnk" "$INSTDIR\${APP_EXE}"
    
    WriteUninstaller "$INSTDIR\Uninstall.exe"
SectionEnd

Section "Uninstall"
    Delete "$INSTDIR\*.*"
    RMDir /r "$INSTDIR"
    Delete "$SMPROGRAMS\${APP_NAME}\*.*"
    RMDir "$SMPROGRAMS\${APP_NAME}"
    Delete "$DESKTOP\${APP_NAME}.lnk"
SectionEnd