param(
    [string]$Repository = "TlamatiniSoftwareMX/Tlamatini-Software"
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$workDir = Join-Path $env:TEMP "TLAMATINI-instalar-windows"
$outputName = "TLAMATINI-Windows-Instalador-Full.exe"

function Get-RemoteFile {
    param([string]$Uri, [string]$Destination)

    $temporary = "$Destination.download"
    Remove-Item -Force $temporary -ErrorAction SilentlyContinue
    try {
        Start-BitsTransfer -Source $Uri -Destination $temporary -Priority Foreground -ErrorAction Stop
    }
    catch {
        Invoke-WebRequest -UseBasicParsing -Uri $Uri -OutFile $temporary
    }
    Move-Item -Force $temporary $Destination
}

function Get-ChecksumTable {
    param([string]$Path)

    $checksums = @{}
    foreach ($line in Get-Content -LiteralPath $Path) {
        if ($line -match '^([A-Fa-f0-9]{64})\s+(.+)$') {
            $checksums[$Matches[2].Trim()] = $Matches[1].ToLowerInvariant()
        }
    }
    return $checksums
}

function Test-Checksum {
    param([string]$Path, [string]$Expected)

    if (-not (Test-Path -LiteralPath $Path)) { return $false }
    return ((Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant() -eq $Expected)
}

try {
    if ([Environment]::Is64BitOperatingSystem -eq $false) { throw "TLAMATINI requiere Windows de 64 bits." }
    New-Item -ItemType Directory -Force -Path $workDir | Out-Null

    Write-Host "Consultando la ultima version de TLAMATINI..." -ForegroundColor Cyan
    $headers = @{ "User-Agent" = "TLAMATINI-Windows-Installer"; "Accept" = "application/vnd.github+json" }
    $release = Invoke-RestMethod -Headers $headers -Uri "https://api.github.com/repos/$Repository/releases/latest"
    $assets = @($release.assets)
    $partAssets = @($assets | Where-Object { $_.name -match '^tlamatini-.*-windows-installer\.chunk-\d{3}-of-\d{3}$' } | Sort-Object name)
    $partsChecksum = $assets | Where-Object { $_.name -eq "SHA256-WINDOWS-PARTES.txt" } | Select-Object -First 1
    $installerChecksum = $assets | Where-Object { $_.name -eq "SHA256-WINDOWS-INSTALADOR.txt" } | Select-Object -First 1
    if ($partAssets.Count -eq 0 -or -not $partsChecksum -or -not $installerChecksum) {
        throw "La release $($release.tag_name) no contiene todos los archivos de instalacion para Windows."
    }

    $partChecksumPath = Join-Path $workDir $partsChecksum.name
    Get-RemoteFile -Uri $partsChecksum.browser_download_url -Destination $partChecksumPath
    $checksums = Get-ChecksumTable -Path $partChecksumPath
    if ($checksums.Count -ne $partAssets.Count) { throw "La lista de comprobacion de las partes no coincide con la release." }

    Write-Host "Descargando TLAMATINI $($release.tag_name) ($($partAssets.Count) partes)..." -ForegroundColor Cyan
    $index = 0
    foreach ($asset in $partAssets) {
        $index++
        if (-not $checksums.ContainsKey($asset.name)) { throw "Falta la comprobacion para $($asset.name)." }
        $destination = Join-Path $workDir $asset.name
        if (Test-Checksum -Path $destination -Expected $checksums[$asset.name]) {
            Write-Host "[$index/$($partAssets.Count)] Ya descargado."
            continue
        }
        Remove-Item -Force $destination -ErrorAction SilentlyContinue
        Write-Host "[$index/$($partAssets.Count)] Descargando TLAMATINI..."
        Get-RemoteFile -Uri $asset.browser_download_url -Destination $destination
        if (-not (Test-Checksum -Path $destination -Expected $checksums[$asset.name])) {
            Remove-Item -Force $destination -ErrorAction SilentlyContinue
            throw "La comprobacion de $($asset.name) fallo. Ejecuta el instalador nuevamente."
        }
    }

    $installerChecksumPath = Join-Path $workDir $installerChecksum.name
    Get-RemoteFile -Uri $installerChecksum.browser_download_url -Destination $installerChecksumPath
    $expectedInstaller = (Get-ChecksumTable -Path $installerChecksumPath)[$outputName]
    if (-not $expectedInstaller) { throw "No se encontro la comprobacion del instalador final." }

    $installerPath = Join-Path $workDir $outputName
    if (-not (Test-Checksum -Path $installerPath -Expected $expectedInstaller)) {
        Write-Host "Preparando el instalador..." -ForegroundColor Cyan
        Remove-Item -Force $installerPath -ErrorAction SilentlyContinue
        $destination = [System.IO.File]::Create($installerPath)
        try {
            foreach ($asset in $partAssets) {
                $source = [System.IO.File]::OpenRead((Join-Path $workDir $asset.name))
                try { $source.CopyTo($destination) } finally { $source.Dispose() }
            }
        }
        finally { $destination.Dispose() }
    }

    if (-not (Test-Checksum -Path $installerPath -Expected $expectedInstaller)) {
        Remove-Item -Force $installerPath -ErrorAction SilentlyContinue
        throw "La comprobacion del instalador final fallo. Ejecuta el instalador nuevamente."
    }

    Write-Host "Descarga verificada. Windows solicitara permiso para instalar TLAMATINI." -ForegroundColor Green
    $process = Start-Process -FilePath $installerPath -Wait -PassThru
    if ($process.ExitCode -ne 0) { throw "El instalador finalizo con codigo $($process.ExitCode)." }
    Remove-Item -Force -Recurse $workDir -ErrorAction SilentlyContinue
    Write-Host "TLAMATINI se instalo correctamente." -ForegroundColor Green
}
catch {
    Write-Host ""
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Puedes volver a ejecutar este mismo archivo: las partes verificadas se conservaran para reanudar la descarga." -ForegroundColor Yellow
    exit 1
}
