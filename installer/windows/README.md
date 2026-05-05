# Windows Installer

Compilar en Windows con Inno Setup:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build_full_release_windows.ps1
iscc installer\windows\TLAMATINI_full.iss
```

Salida esperada:

- `dist/TLAMATINI-full-windows-x86_64.zip`
- `dist/TLAMATINI-full-windows-installer.exe`
