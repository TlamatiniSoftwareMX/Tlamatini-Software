#ifndef Edition
  #error Debe definir Edition como no-ai o ai-4gb
#endif
#define AppVersion "5.2.6"

[Setup]
AppId={{C8C4B0F1-7A55-4E62-8B7A-A7EF9D9F6D31}
AppName=TLAMATINI ({#Edition})
AppVersion={#AppVersion}
AppPublisher=TLAMATINI
DefaultDirName={autopf}\TLAMATINI
DefaultGroupName=TLAMATINI
DisableProgramGroupPage=yes
OutputDir=..\..\dist
OutputBaseFilename=TLAMATINI-Windows-{#Edition}-5.2.6-Instalador
SetupIconFile=..\..\assets\app_icon.ico
UninstallDisplayIcon={app}\TLAMATINI.exe
Compression=zip
SolidCompression=no
WizardStyle=modern

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Files]
Source: "..\..\dist\{#Edition}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\TLAMATINI"; Filename: "{app}\TLAMATINI.exe"
Name: "{autodesktop}\TLAMATINI"; Filename: "{app}\TLAMATINI.exe"

[Run]
Filename: "{app}\TLAMATINI.exe"; Description: "Iniciar TLAMATINI"; Flags: nowait postinstall skipifsilent
