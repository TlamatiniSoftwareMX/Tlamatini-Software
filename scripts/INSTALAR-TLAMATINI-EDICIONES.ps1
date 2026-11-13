param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('sin-ia', 'ia-4gb', 'ia-8gb')]
    [string]$Edicion,
    [string]$Catalogo = 'https://github.com/TlamatiniSoftwareMX/Tlamatini-Software/releases/download/ediciones-2026-11-13/INSTALADORES-SEIS-EDICIONES.json',
    [string]$Carpeta = '',
    [switch]$SoloDescargar,
    [switch]$Verificar
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

function Test-InstallerFile {
    param([string]$Path, $Expected)
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $false }
    if ((Get-Item -LiteralPath $Path).Length -ne [long]$Expected.size_bytes) { return $false }
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant() -eq $Expected.sha256
}

function Get-InstallerFile {
    param($Item, [string]$Path)
    if (Test-InstallerFile -Path $Path -Expected $Item) {
        Write-Host "Ya descargado y verificado: $([IO.Path]::GetFileName($Path))"
        return
    }
    $temporary = "$Path.download"
    try {
        try {
            Start-BitsTransfer -Source $Item.url -Destination $temporary -Priority Foreground -ErrorAction Stop
        }
        catch {
            Invoke-WebRequest -UseBasicParsing -Uri $Item.url -OutFile $temporary
        }
        if (-not (Test-InstallerFile -Path $temporary -Expected $Item)) {
            throw "La descarga no paso la verificacion SHA-256: $([IO.Path]::GetFileName($Path))"
        }
        Move-Item -LiteralPath $temporary -Destination $Path -Force
    }
    finally {
        Remove-Item -LiteralPath $temporary -Force -ErrorAction SilentlyContinue
    }
}

function Join-InstallerParts {
    param([string[]]$Paths, [string]$Output, $Expected)
    if (Test-InstallerFile -Path $Output -Expected $Expected) { return }
    $temporary = "$Output.assembling"
    try {
        $destination = [IO.File]::Create($temporary)
        try {
            foreach ($path in $Paths) {
                $source = [IO.File]::OpenRead($path)
                try { $source.CopyTo($destination, 1048576) }
                finally { $source.Dispose() }
            }
        }
        finally { $destination.Dispose() }
        if (-not (Test-InstallerFile -Path $temporary -Expected $Expected)) {
            throw 'El instalador unido no paso la verificacion SHA-256.'
        }
        Move-Item -LiteralPath $temporary -Destination $Output -Force
    }
    finally {
        Remove-Item -LiteralPath $temporary -Force -ErrorAction SilentlyContinue
    }
}

function Get-SelectedEdition {
    param($Data, [string]$Name)
    if ($Data.schema_version -ne 1) { throw 'El catalogo de instalacion no es compatible.' }
    $property = $Data.editions.PSObject.Properties["windows-$Name"]
    if (-not $property) { throw 'No se encontro la edicion solicitada.' }
    $item = $property.Value
    if ($item.platform -ne 'windows' -or -not $item.filename.EndsWith('.exe')) {
        throw 'El catalogo no corresponde a Windows.'
    }
    foreach ($filename in @($item.filename) + @($item.downloads | ForEach-Object { $_.name })) {
        if ([IO.Path]::GetFileName($filename) -ne $filename -or $filename -in @('.', '..')) {
            throw 'Nombre de archivo invalido en el catalogo.'
        }
    }
    $total = ($item.downloads | Measure-Object -Property size_bytes -Sum).Sum
    if (@($item.downloads).Count -eq 0 -or [long]$total -ne [long]$item.size_bytes) {
        throw 'La lista de descargas esta incompleta.'
    }
    return $item
}

function Invoke-TlamatiniInstaller {
    if ($Catalogo.StartsWith('https://')) {
        $data = Invoke-RestMethod -Uri $Catalogo
    }
    else {
        $data = Get-Content -LiteralPath $Catalogo -Raw | ConvertFrom-Json
    }
    $item = Get-SelectedEdition -Data $data -Name $Edicion
    $model = if ($null -eq $item.model) { 'Sin IA' } else { $item.model }
    Write-Host "TLAMATINI $($item.version) | Windows 64 bits | $model"
    if ($item.ram_recommended_gib) { Write-Host "RAM recomendada: $($item.ram_recommended_gib) GB" }
    if ($Verificar) {
        Write-Host "Catalogo verificado: $(@($item.downloads).Count) archivo(s); $($item.size_bytes) bytes."
        return
    }
    if (-not [Environment]::Is64BitOperatingSystem) { throw 'Esta edicion necesita Windows de 64 bits.' }
    $folder = if ($Carpeta) { $Carpeta } else { Join-Path $env:USERPROFILE "Downloads\TLAMATINI\$Edicion" }
    New-Item -ItemType Directory -Path $folder -Force | Out-Null
    $output = Join-Path $folder $item.filename
    if (-not (Test-InstallerFile -Path $output -Expected $item)) {
        if (@($item.downloads).Count -eq 1) {
            Get-InstallerFile -Item $item.downloads[0] -Path $output
        }
        else {
            $partsDir = Join-Path $folder '_partes'
            New-Item -ItemType Directory -Path $partsDir -Force | Out-Null
            $paths = @()
            $number = 0
            foreach ($part in $item.downloads) {
                $number++
                Write-Host "Descargando $number/$(@($item.downloads).Count)..."
                $path = Join-Path $partsDir $part.name
                Get-InstallerFile -Item $part -Path $path
                $paths += $path
            }
            Write-Host 'Preparando el instalador completo...'
            Join-InstallerParts -Paths $paths -Output $output -Expected $item
        }
    }
    if (@($item.downloads).Count -gt 1) {
        $partsDir = Join-Path $folder '_partes'
        foreach ($part in $item.downloads) {
            Remove-Item -LiteralPath (Join-Path $partsDir $part.name) -Force -ErrorAction SilentlyContinue
        }
        if ((Test-Path -LiteralPath $partsDir) -and @(Get-ChildItem -LiteralPath $partsDir -Force).Count -eq 0) {
            Remove-Item -LiteralPath $partsDir -Force
        }
    }
    Write-Host "Instalador completo y verificado: $output" -ForegroundColor Green
    if (-not $SoloDescargar) {
        Write-Host 'Windows solicitara permiso para instalar TLAMATINI.'
        $process = Start-Process -FilePath $output -Wait -PassThru
        if ($process.ExitCode -ne 0) { throw "El instalador termino con codigo $($process.ExitCode)." }
        Write-Host 'Instalacion terminada. Abre TLAMATINI desde el menu Inicio.' -ForegroundColor Green
    }
}

if ($MyInvocation.InvocationName -ne '.') {
    try { Invoke-TlamatiniInstaller }
    catch {
        Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host 'Vuelve a ejecutar el mismo comando para reanudar los archivos ya verificados.'
        exit 1
    }
}
