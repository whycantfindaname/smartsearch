[CmdletBinding()]
param([Parameter(Mandatory)][string] $Path, [string] $UninstallerDirectory)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'Windows-Signing.ps1')
$certificate = Get-ExpectedSigningCertificate (Join-Path $PSScriptRoot '../packaging/windows/smart-search.cer')
try {
    Invoke-WindowsSigning $Path $certificate | ConvertTo-Json -Compress | Write-Output
    if ($UninstallerDirectory -and [IO.Path]::GetDirectoryName([IO.Path]::GetFullPath($Path)) -eq [IO.Path]::GetFullPath($UninstallerDirectory)) {
        # Inno deletes its signed uninst.*.tmp after embedding it in Setup.
        $evidence = Join-Path $UninstallerDirectory 'uninstaller.exe'
        if (Test-Path -LiteralPath $evidence) { throw 'Refusing to overwrite signed uninstaller evidence.' }
        Copy-Item -LiteralPath $Path -Destination $evidence
    }
}
finally { $certificate.Dispose() }
