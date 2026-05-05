#define MyAppName "TLAMATINI"
#define MyAppVersion "5.2.2"
#define MyAppPublisher "TLAMATINI"
#define MyAppExeName "TLAMATINI.exe"

[Setup]
AppId={{C8C4B0F1-7A55-4E62-8B7A-A7EF9D9F6D31}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\TLAMATINI
DefaultGroupName=TLAMATINI
DisableProgramGroupPage=yes
OutputDir=..\..\dist
OutputBaseFilename=TLAMATINI-Windows-Instalador-Full
SetupIconFile=..\..\assets\app_icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Files]
Source: "..\..\dist\tlamatini_full\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\TLAMATINI"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\TLAMATINI"; Filename: "{app}\{#MyAppExeName}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Iniciar TLAMATINI"; Flags: nowait postinstall skipifsilent
