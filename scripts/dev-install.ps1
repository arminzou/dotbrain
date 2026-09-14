# install.ps1 - fresh-machine setup for dotbrain on native Windows.
#
# Installs uv, Beads (bd), and the dotbrain CLI.
#
# Usage:
#   .\install.ps1
#
# After this script completes, run:
#   dotbrain bootstrap
#
# Requires Windows Developer Mode enabled (Settings > Privacy & security > For developers) so
# `dotbrain wire` can create real directory symlinks.

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# The tool checkout to install from: always this script's own directory, never the
# $DOTBRAIN_HOME data-home override (a user's data home has no pyproject.toml to install).
$DotbrainCheckout = $PSScriptRoot

function Write-Log($Message)  { Write-Host "[install] $Message" }
function Write-Warn($Message) { Write-Warning "[install] $Message" }
function Write-Die($Message)  { Write-Host "[install] error: $Message" -ForegroundColor Red; exit 1 }

function Add-ProcessPath($Directory) {
    if (-not $Directory) { return }
    $entries = $env:Path -split [IO.Path]::PathSeparator
    if ($entries -notcontains $Directory) {
        $env:Path = "$Directory$([IO.Path]::PathSeparator)$env:Path"
    }
}

function Get-BdInstallDirectories {
    $directories = [System.Collections.Generic.List[string]]::new()

    # Beads records the exact binary path for release, Go, and source installs.
    $recorded = Get-Variable -Scope Script -Name LastInstallPath -ErrorAction SilentlyContinue
    if ($recorded -and $recorded.Value) {
        $directories.Add((Split-Path -Parent $recorded.Value))
    }

    $directories.Add((Join-Path $env:LOCALAPPDATA "Programs\bd"))

    # Its release download can fall back to `go install`, which writes to GOBIN or GOPATH\bin.
    if (Get-Command go -ErrorAction SilentlyContinue) {
        $goBin = (& go env GOBIN 2>$null | Select-Object -First 1)
        if ($goBin -and $goBin.Trim()) {
            $directories.Add($goBin.Trim())
        } else {
            $goPath = (& go env GOPATH 2>$null | Select-Object -First 1)
            foreach ($entry in ($goPath -split [IO.Path]::PathSeparator)) {
                if ($entry.Trim()) {
                    $directories.Add((Join-Path $entry.Trim() "bin"))
                }
            }
        }
    }

    return $directories | Select-Object -Unique
}

# Install uv if not already available.
function Ensure-Uv {
    $existing = Get-Command uv -ErrorAction SilentlyContinue
    if ($existing) {
        $version = (& uv --version 2>$null | Select-Object -First 1)
        Write-Log "uv $version already installed"
        return
    }

    Write-Log "uv not found; installing uv"
    Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression

    $uvBin = Join-Path $env:USERPROFILE ".local\bin"
    if (($env:Path -split ";") -notcontains $uvBin) {
        $env:Path = "$uvBin;$env:Path"
    }

    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
        Write-Die "uv install succeeded but uv is not on PATH; open a new shell and re-run"
    }
    $version = (& uv --version 2>$null | Select-Object -First 1)
    Write-Log "uv installed: $version"
}

# Install Beads if not already available. Delegates to beads' own Windows installer, which
# already knows the correct release-asset name and architecture-selection logic for Windows
# (mirrors install.sh's delegation to beads' scripts/install.sh via curl | bash).
function Ensure-Bd {
    $existing = Get-Command bd -ErrorAction SilentlyContinue
    if ($existing) {
        $version = (& bd --version 2>$null | Select-Object -First 1)
        Write-Log "bd $version already installed"
        return
    }

    Write-Log "bd not found; installing Beads"
    Invoke-RestMethod https://raw.githubusercontent.com/gastownhall/beads/main/install.ps1 | Invoke-Expression

    foreach ($bdBin in Get-BdInstallDirectories) {
        if (Test-Path (Join-Path $bdBin "bd.exe")) {
            Add-ProcessPath $bdBin
            break
        }
    }

    if (-not (Get-Command bd -ErrorAction SilentlyContinue)) {
        Write-Die "Beads install succeeded but bd is not on PATH; open a new shell and re-run"
    }
    $version = (& bd --version 2>$null | Select-Object -First 1)
    Write-Log "bd installed: $version"
}

# Install or upgrade dotbrain CLI.
function Install-Dotbrain {
    Write-Log "installing/upgrading dotbrain CLI from $DotbrainCheckout"
    & uv tool install --editable --force $DotbrainCheckout
    if ($LASTEXITCODE -ne 0) {
        Write-Die "uv tool install failed with exit code $LASTEXITCODE"
    }

    $dotbrainCmd = Get-Command dotbrain -ErrorAction SilentlyContinue
    if (-not $dotbrainCmd) {
        Write-Warn "dotbrain not found in current PATH after uv tool install"
        Write-Warn "ensure uv's tool bin directory is on PATH, then run: dotbrain bootstrap"
        return
    }
    Write-Log "dotbrain installed: $($dotbrainCmd.Source)"
}

Write-Log "dotbrain checkout: $DotbrainCheckout"
Ensure-Uv
Ensure-Bd
Install-Dotbrain
Write-Host ""
Write-Log "done. Next step:"
Write-Host "    dotbrain bootstrap"
