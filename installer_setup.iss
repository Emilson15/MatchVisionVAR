; installer_setup.iss
; Script de compilacion de instalador para Inno Setup Compiler 6+
; Genera el archivo Setup_MatchVision_VAR_v1.0.exe

[Setup]
AppId={{5E2B9631-017A-4545-9271-9A3E7B6C89D4}
AppName=MatchVision VAR
AppVersion=1.0.0
AppPublisher=MatchVision AI
DefaultDirName={autopf}\MatchVision VAR
DefaultGroupName=MatchVision VAR
AllowNoIcons=yes
OutputDir=installer_output
OutputBaseFilename=Setup_MatchVision_VAR_v1.0
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
DisableProgramGroupPage=yes
SetupIconFile=logo.ico

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Dirs]
Name: "{app}\data"; Permissions: users-full
Name: "{app}\data\escudos"; Permissions: users-full
Name: "{app}\data\raw_videos"; Permissions: users-full
Name: "{app}\data\reportes"; Permissions: users-full

[Files]
; Archivos empaquetados desde la carpeta dist/MatchVision_VAR
Source: "dist\MatchVision_VAR\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "dist\MatchVision_VAR\data\*"; DestDir: "{app}\data"; Flags: ignoreversion recursesubdirs createallsubdirs; Permissions: users-full

[Icons]
Name: "{group}\MatchVision VAR"; Filename: "{app}\MatchVision_VAR.exe"; WorkingDir: "{app}"
Name: "{group}\{cm:UninstallProgram,MatchVision VAR}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\MatchVision VAR"; Filename: "{app}\MatchVision_VAR.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\MatchVision_VAR.exe"; Description: "{cm:LaunchProgram,MatchVision VAR}"; Flags: nowait postinstall skipifsilent
