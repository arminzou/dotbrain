$ErrorActionPreference = 'Stop'

dotbrain wire --repo (Get-Location).Path --json
exit $LASTEXITCODE
