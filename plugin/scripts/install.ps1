# Install the CLI that matches this plugin release on native Windows.

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$DotbrainVersion = "0.2.0"
$DotbrainRef = "git+https://github.com/arminzou/dotbrain@v$DotbrainVersion"

function Write-Die($Message) {
    Write-Host "[dotbrain] error: $Message" -ForegroundColor Red
    exit 1
}

function Ensure-Uv {
    if (Get-Command uv -ErrorAction SilentlyContinue) { return }
    Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
    $uvBin = Join-Path $env:USERPROFILE ".local\bin"
    if (($env:Path -split ";") -notcontains $uvBin) { $env:Path = "$uvBin;$env:Path" }
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) { Write-Die "uv is not on PATH; open a new shell and retry" }
}

function Add-ProcessPath($Directory) {
    if ($Directory -and (($env:Path -split ";") -notcontains $Directory)) {
        $env:Path = "$Directory;$env:Path"
    }
}

function Get-BdInstallDirectories {
    $directories = [System.Collections.Generic.List[string]]::new()
    $recorded = Get-Variable -Scope Script -Name LastInstallPath -ErrorAction SilentlyContinue
    if ($recorded -and $recorded.Value) { $directories.Add((Split-Path -Parent $recorded.Value)) }
    $directories.Add((Join-Path $env:LOCALAPPDATA "Programs\bd"))

    if (Get-Command go -ErrorAction SilentlyContinue) {
        $goBin = (& go env GOBIN 2>$null | Select-Object -First 1)
        if ($goBin -and $goBin.Trim()) {
            $directories.Add($goBin.Trim())
        } else {
            $goPath = (& go env GOPATH 2>$null | Select-Object -First 1)
            foreach ($entry in ($goPath -split [IO.Path]::PathSeparator)) {
                if ($entry.Trim()) { $directories.Add((Join-Path $entry.Trim() "bin")) }
            }
        }
    }

    return $directories | Select-Object -Unique
}

function Ensure-Bd {
    if (Get-Command bd -ErrorAction SilentlyContinue) { return }
    Invoke-RestMethod https://raw.githubusercontent.com/gastownhall/beads/main/install.ps1 | Invoke-Expression
    foreach ($bdBin in Get-BdInstallDirectories) {
        if (Test-Path (Join-Path $bdBin "bd.exe")) {
            Add-ProcessPath $bdBin
            break
        }
    }
    if (-not (Get-Command bd -ErrorAction SilentlyContinue)) { Write-Die "bd is not on PATH; open a new shell and retry" }
}

Ensure-Uv
Ensure-Bd
& uv tool install --force $DotbrainRef
if ($LASTEXITCODE -ne 0) { Write-Die "dotbrain installation failed" }
if (-not (Get-Command dotbrain -ErrorAction SilentlyContinue)) { Write-Die "dotbrain is not on PATH; open a new shell and retry" }
if (((& uv tool list) -join "`n") -notmatch [regex]::Escape("dotbrain v$DotbrainVersion")) {
    Write-Die "installed dotbrain version does not match this plugin"
}
& dotbrain bootstrap
