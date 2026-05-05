param(
    [string]$InstallRoot = "$env:LOCALAPPDATA\TLAMATINI"
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$SourceExe = Join-Path $ScriptDir "TLAMATINI.exe"
if (-not (Test-Path $SourceExe)) {
    $SourceExe = Join-Path $ScriptDir "TLAMATINI"
}
if (-not (Test-Path $SourceExe)) {
    Write-Error "No se encontro el ejecutable Full junto al instalador."
    exit 1
}

$BinDir = Join-Path $InstallRoot "bin"
$TargetExe = Join-Path $BinDir "TLAMATINI.exe"
New-Item -ItemType Directory -Force -Path $BinDir | Out-Null
Copy-Item $SourceExe $TargetExe -Force

$Desktop = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $Desktop "TLAMATINI.lnk"
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $TargetExe
$Shortcut.WorkingDirectory = $BinDir
$IconPath = Join-Path $ScriptDir "tlamatini.ico"
if (Test-Path $IconPath) {
    $Shortcut.IconLocation = $IconPath
}
$Shortcut.Save()

Write-Host "TLAMATINI Full instalado en $TargetExe"
Write-Host "Acceso directo creado en $ShortcutPath"
