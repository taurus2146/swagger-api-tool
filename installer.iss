; Swagger API Tester 安装脚本
; 使用 Inno Setup 编译器生成

[Setup]
AppName=Swagger API测试工具
AppVersion=1.0.0
AppPublisher=Swagger API Tester Team
AppPublisherURL=https://github.com/your-repo
AppSupportURL=https://github.com/your-repo/issues
AppUpdatesURL=https://github.com/your-repo/releases
DefaultDirName={autopf}\Swagger API测试工具
DefaultGroupName=Swagger API测试工具
AllowNoIcons=yes
LicenseFile=LICENSE
OutputDir=dist\installer
OutputBaseFilename=SwaggerAPITester-1.0.0-Setup
SetupIconFile=assets\icon.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "chinesesimplified"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1

[Files]
; 单文件版本
Source: "dist\SwaggerAPITester.exe"; DestDir: "{app}"; Flags: ignoreversion
; 配置文件
Source: "config\*"; DestDir: "{app}\config"; Flags: ignoreversion recursesubdirs createallsubdirs
; 模板文件
Source: "templates\*"; DestDir: "{app}\templates"; Flags: ignoreversion recursesubdirs createallsubdirs
; 资源文件
Source: "assets\*"; DestDir: "{app}\assets"; Flags: ignoreversion recursesubdirs createallsubdirs
; 文档
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "DEPLOYMENT.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Swagger API测试工具"; Filename: "{app}\SwaggerAPITester.exe"
Name: "{group}\{cm:UninstallProgram,Swagger API测试工具}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Swagger API测试工具"; Filename: "{app}\SwaggerAPITester.exe"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\Swagger API测试工具"; Filename: "{app}\SwaggerAPITester.exe"; Tasks: quicklaunchicon

[Run]
Filename: "{app}\SwaggerAPITester.exe"; Description: "{cm:LaunchProgram,Swagger API测试工具}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\config"
Type: filesandordirs; Name: "{app}\logs"
Type: filesandordirs; Name: "{app}\temp"