$ErrorActionPreference = "Stop"

$baseDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $baseDir

$outputName = "TLAMATINI-Windows-Instalador-Full.exe"
$checksumFile = "SHA256-WINDOWS-INSTALADOR.txt"
$parts = @(Get-ChildItem -File "tlamatini-5.2.4-windows-installer.chunk-*-of-*" | Sort-Object Name)

if ($parts.Count -eq 0) {
    Write-Host "No se encontraron las partes del instalador." -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $checksumFile)) {
    Write-Host "Falta $checksumFile." -ForegroundColor Red
    exit 1
}

$expected = ((Get-Content $checksumFile | Select-Object -First 1) -split "\s+")[0].Trim().ToLowerInvariant()
$outputPath = Join-Path $baseDir $outputName
$destination = [System.IO.File]::Create($outputPath)

try {
    foreach ($part in $parts) {
        Write-Host "Procesando $($part.Name)..."
        $source = [System.IO.File]::OpenRead($part.FullName)
        try {
            $source.CopyTo($destination)
        }
        finally {
            $source.Dispose()
        }
    }
}
finally {
    $destination.Dispose()
}

$actual = (Get-FileHash -Algorithm SHA256 $outputPath).Hash.ToLowerInvariant()
if ($actual -ne $expected) {
    Remove-Item $outputPath -Force
    Write-Host "La verificación del instalador falló. Vuelve a descargar las partes." -ForegroundColor Red
    exit 1
}

Write-Host "Instalador verificado correctamente." -ForegroundColor Green
Start-Process -FilePath $outputPath -Wait
