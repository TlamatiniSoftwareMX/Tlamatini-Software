$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
. (Join-Path $root 'scripts/INSTALAR-TLAMATINI-EDICIONES.ps1') -Edicion sin-ia

function Assert-True { param([bool]$Condition, [string]$Message) if (-not $Condition) { throw $Message } }
function Expected { param([string]$Path) return @{ size_bytes = (Get-Item $Path).Length; sha256 = (Get-FileHash $Path -Algorithm SHA256).Hash.ToLowerInvariant() } }
$data = Get-Content (Join-Path $root 'installer/ediciones.json') -Raw | ConvertFrom-Json
foreach ($name in @('sin-ia', 'ia-4gb', 'ia-8gb')) {
    $item = Get-SelectedEdition -Data $data -Name $name
    Assert-True ($item.edition -eq $name) 'Incorrect edition selected'
    Assert-True ($item.platform -eq 'windows') 'Incorrect platform selected'
}
Assert-True ($null -eq (Get-SelectedEdition $data 'sin-ia').model) 'No-AI model should be empty'
Assert-True ((Get-SelectedEdition $data 'ia-4gb').model -eq 'Gemma 3 1B Q4_K_M') '4 GB model incorrect'
Assert-True ((Get-SelectedEdition $data 'ia-8gb').ram_recommended_gib -eq 8) '8 GB profile incorrect'

$temporary = Join-Path $env:TEMP ([Guid]::NewGuid().ToString())
New-Item -ItemType Directory $temporary | Out-Null
try {
    $part1 = Join-Path $temporary 'first'
    $part2 = Join-Path $temporary 'second'
    $output = Join-Path $temporary 'installer.exe'
    [IO.File]::WriteAllBytes($part1, [Text.Encoding]::UTF8.GetBytes('first-'))
    [IO.File]::WriteAllBytes($part2, [Text.Encoding]::UTF8.GetBytes('second'))
    $fixture = Join-Path $temporary 'expected'
    [IO.File]::WriteAllBytes($fixture, [Text.Encoding]::UTF8.GetBytes('first-second'))
    $expected = Expected $fixture
    Join-InstallerParts -Paths @($part1, $part2) -Output $output -Expected $expected
    Assert-True (Test-InstallerFile $output $expected) 'Final installer checksum failed'
    [IO.File]::WriteAllBytes($output, [Text.Encoding]::UTF8.GetBytes('tampered'))
    Assert-True (-not (Test-InstallerFile $output $expected)) 'Corruption was accepted'

    $global:FixtureBytes = [Text.Encoding]::UTF8.GetBytes('first-second')
    $global:DownloadCalls = 0
    function Start-BitsTransfer {
        param($Source, $Destination, $Priority, $ErrorAction)
        $global:DownloadCalls++
        [IO.File]::WriteAllBytes($Destination, $global:FixtureBytes)
    }
    $item = @{ size_bytes = $expected.size_bytes; sha256 = $expected.sha256; url = 'https://example.invalid/fixture' }
    Get-InstallerFile -Item $item -Path $output
    Assert-True (Test-InstallerFile $output $expected) 'Downloaded fixture failed verification'
    Get-InstallerFile -Item $item -Path $output
    Assert-True ($global:DownloadCalls -eq 1) 'Verified download was not reused'

    $global:FixtureBytes = [Text.Encoding]::UTF8.GetBytes('bad')
    Remove-Item -LiteralPath $output
    $rejected = $false
    try { Get-InstallerFile -Item $item -Path $output } catch { $rejected = $true }
    Assert-True $rejected 'Corrupted download was not rejected'
    Assert-True (-not (Test-Path $output)) 'Corrupted installer became available for execution'
    Assert-True (-not (Test-Path "$output.download")) 'Corrupted temporary download was retained'
    Write-Host 'Windows installer tests passed: selection, joining, SHA-256, resume and corruption rejection.'
}
finally { Remove-Item -LiteralPath $temporary -Recurse -Force }
