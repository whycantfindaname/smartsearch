[CmdletBinding()]
param(
    [ValidateSet("x64", "arm64")]
    [string] $Architecture = "x64",
    [ValidateSet("Debug", "Release")]
    [string] $Configuration = "Release",
    [string] $PythonPath = "python",
    [string] $OutputRoot = ".desktop-artifacts",
    [ValidateSet("Auto", "Required", "Skip")]
    [string] $InstallerMode = "Auto",
    [string] $InnoSetupPath,
    [switch] $BootstrapInnoSetup,
    [ValidateSet("Required", "Skip")]
    [string] $SigningMode = "Skip"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repositoryRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
. (Join-Path $PSScriptRoot 'Windows-Signing.ps1')
$signingEnabled = $SigningMode -eq 'Required'
$signatures = @()
$signingCertificate = $null
if ($signingEnabled) {
    $signingCertificate = Get-ExpectedSigningCertificate (Join-Path $PSScriptRoot '../packaging/windows/smart-search.cer')
    Assert-SigningCertificate $signingCertificate $signingCertificate
    $identityPath = "Cert:/CurrentUser/My/$($signingCertificate.Thumbprint)"
    if (-not (Test-Path -LiteralPath $identityPath) -or -not (Get-Item -LiteralPath $identityPath).HasPrivateKey) {
        throw 'Required signing identity is missing. Import the pinned PFX before building; no unsigned fallback.'
    }
    $null = Get-WindowsSignTool
}

function Resolve-ExecutablePath([string] $Candidate) {
    if (Test-Path -LiteralPath $Candidate -PathType Leaf) {
        return [System.IO.Path]::GetFullPath($Candidate)
    }
    return (Get-Command -Name $Candidate -CommandType Application -ErrorAction Stop | Select-Object -First 1).Source
}

function Resolve-RepositoryPath([string] $Candidate) {
    if ([System.IO.Path]::IsPathRooted($Candidate)) {
        return [System.IO.Path]::GetFullPath($Candidate)
    }
    return [System.IO.Path]::GetFullPath((Join-Path $repositoryRoot $Candidate))
}

function Get-PythonArchitecture([string] $PythonExecutable) {
    $reported = [string] (& $PythonExecutable -c "import platform; print(platform.machine())")
    if ($LASTEXITCODE -ne 0) {
        throw "Could not determine the selected Python architecture."
    }
    switch ($reported.Trim().ToLowerInvariant()) {
        "amd64" { return "x64" }
        "x86_64" { return "x64" }
        "arm64" { return "arm64" }
        "aarch64" { return "arm64" }
        default { throw "Unsupported Python architecture for PyInstaller: $reported" }
    }
}

function New-RunDirectory([string] $BaseDirectory, [string] $Prefix) {
    if (-not (Test-Path -LiteralPath $BaseDirectory)) {
        New-Item -ItemType Directory -Path $BaseDirectory | Out-Null
    }
    $stamp = [DateTime]::UtcNow.ToString("yyyyMMddTHHmmssZ")
    $suffix = [guid]::NewGuid().ToString("N").Substring(0, 8)
    $directory = Join-Path $BaseDirectory "$Prefix-$stamp-$PID-$suffix"
    if (Test-Path -LiteralPath $directory) {
        throw "Refusing to reuse build directory: $directory"
    }
    New-Item -ItemType Directory -Path $directory | Out-Null
    return $directory
}

function Copy-WindowsProjectSource([string] $SourceDirectory, [string] $DestinationDirectory) {
    if (Test-Path -LiteralPath $DestinationDirectory) {
        throw "Refusing to reuse staged project directory: $DestinationDirectory"
    }
    New-Item -ItemType Directory -Path $DestinationDirectory | Out-Null
    Get-ChildItem -LiteralPath $SourceDirectory -Recurse -File -Force | ForEach-Object {
        $relativePath = [System.IO.Path]::GetRelativePath($SourceDirectory, $_.FullName)
        if ($relativePath -match '(^|[\\/])(bin|obj|\.desktop-artifacts)([\\/]|$)') {
            return
        }
        $target = Join-Path $DestinationDirectory $relativePath
        $targetParent = Split-Path $target -Parent
        if (-not (Test-Path -LiteralPath $targetParent)) {
            New-Item -ItemType Directory -Path $targetParent | Out-Null
        }
        Copy-Item -LiteralPath $_.FullName -Destination $target
    }
}

function Get-ProjectVersion([string] $ProjectRoot) {
    $versionLine = Select-String -LiteralPath (Join-Path $ProjectRoot "pyproject.toml") -Pattern '^\s*version\s*=\s*"([^"]+)"' | Select-Object -First 1
    if ($null -eq $versionLine -or $versionLine.Line -notmatch '^\s*version\s*=\s*"([^"]+)"') {
        throw "Could not read the project version from pyproject.toml."
    }
    return $Matches[1]
}

function Find-InnoSetup([string] $ExplicitPath) {
    if ($ExplicitPath) {
        if (-not (Test-Path -LiteralPath $ExplicitPath -PathType Leaf)) {
            throw "The requested Inno Setup compiler does not exist: $ExplicitPath"
        }
        return [System.IO.Path]::GetFullPath($ExplicitPath)
    }
    $command = Get-Command -Name "ISCC.exe" -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -ne $command) {
        return $command.Source
    }
    $locations = @(
        (Join-Path ([Environment]::GetFolderPath([Environment+SpecialFolder]::ProgramFilesX86)) "Inno Setup 6\ISCC.exe"),
        (Join-Path ([Environment]::GetFolderPath([Environment+SpecialFolder]::ProgramFiles)) "Inno Setup 6\ISCC.exe")
    )
    return $locations | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
}

$python = Resolve-ExecutablePath $PythonPath
$dotnet = Resolve-ExecutablePath "dotnet"
$pythonArchitecture = Get-PythonArchitecture $python
if ($pythonArchitecture -ne $Architecture) {
    throw "Requested Windows $Architecture, but the selected Python is $pythonArchitecture. PyInstaller must run under matching architecture Python."
}
$outputBase = Resolve-RepositoryPath $OutputRoot
$runDirectory = New-RunDirectory $outputBase "windows-$Architecture"
$backendManifest = Join-Path $runDirectory "backend.json"
$backendBuilder = Join-Path $PSScriptRoot "build_backend.py"

& $python $backendBuilder --output-root $runDirectory --result-file $backendManifest --smoke
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller backend build failed. Its fresh evidence directory is $runDirectory."
}
$backend = Get-Content -Raw -LiteralPath $backendManifest | ConvertFrom-Json
$backendDirectory = [string] $backend.bundle_directory
if (-not (Test-Path -LiteralPath $backendDirectory -PathType Container)) {
    throw "Backend manifest does not point to a bundle directory: $backendDirectory"
}

$projectSourceDirectory = Join-Path $repositoryRoot "desktop\windows"
$projectSource = Join-Path $projectSourceDirectory "SmartSearch.Desktop.csproj"
if (-not (Test-Path -LiteralPath $projectSource -PathType Leaf)) {
    throw "Windows desktop project is not available: $projectSource"
}
$stagedProjectDirectory = Join-Path $runDirectory "windows-source"
Copy-WindowsProjectSource $projectSourceDirectory $stagedProjectDirectory
$localizationPath = Join-Path $stagedProjectDirectory "messages.json"
Copy-Item -LiteralPath (Join-Path $repositoryRoot "src/smart_search/assets/i18n/messages.json") -Destination $localizationPath
$project = Join-Path $stagedProjectDirectory "SmartSearch.Desktop.csproj"
$publishDirectory = Join-Path $runDirectory "publish"
$platform = if ($Architecture -eq "arm64") { "ARM64" } else { "x64" }
$version = Get-ProjectVersion $repositoryRoot
& $dotnet publish $project --configuration $Configuration --runtime "win-$Architecture" --self-contained true --output $publishDirectory "-p:Platform=$platform" "-p:Version=$version" "-p:LocalizationPath=$localizationPath"
if ($LASTEXITCODE -ne 0) {
    throw "dotnet publish failed. Its fresh evidence directory is $runDirectory."
}

$desktopExecutable = Join-Path $publishDirectory "SmartSearch.Desktop.exe"
if (-not (Test-Path -LiteralPath $desktopExecutable -PathType Leaf)) {
    throw "dotnet publish did not create the expected desktop executable: $desktopExecutable"
}
foreach ($resource in @("App.xbf", "MainWindow.xbf", "SmartSearch.Desktop.pri", "Assets/smart-search.ico", "Assets/smart-search.png")) {
    if (-not (Test-Path -LiteralPath (Join-Path $publishDirectory $resource) -PathType Leaf)) {
        throw "Published Windows app is missing its compiled UI resource: $resource"
    }
}
$backendDestination = Join-Path $publishDirectory "backend"
if (Test-Path -LiteralPath $backendDestination) {
    throw "Refusing to merge backend files into an existing directory: $backendDestination"
}
New-Item -ItemType Directory -Path $backendDestination | Out-Null
Get-ChildItem -LiteralPath $backendDirectory -Force | Copy-Item -Destination $backendDestination -Recurse
$bundledBackend = Join-Path $backendDestination "smart-search.exe"
if (-not (Test-Path -LiteralPath $bundledBackend -PathType Leaf)) {
    throw "Published Windows app is missing backend\smart-search.exe."
}

$ownedFiles = @($desktopExecutable, (Join-Path $publishDirectory 'SmartSearch.Desktop.dll'), $bundledBackend)
$thirdPartyHashes = @{}
if ($signingEnabled) {
    foreach ($file in Get-ChildItem -LiteralPath $publishDirectory -File -Recurse) {
        if ($file.FullName -notin $ownedFiles) {
            $thirdPartyHashes[$file.FullName] = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash
        }
    }
    foreach ($file in $ownedFiles) { $signatures += Invoke-WindowsSigning $file $signingCertificate }
}

$installer = [ordered]@{
    status = "skipped"
    path = $null
    note = "Installer packaging was not requested."
}
if ($InstallerMode -ne "Skip") {
    $iscc = Find-InnoSetup $InnoSetupPath
    $compilerOrigin = "existing-local-installation"
    if ($null -eq $iscc -and $BootstrapInnoSetup) {
        $bootstrapManifest = Join-Path $runDirectory "inno-setup.json"
        $bootstrapScript = Join-Path $PSScriptRoot "Get-LocalInnoSetup.ps1"
        & $bootstrapScript -OutputRoot $runDirectory -ResultFile $bootstrapManifest
        if ($LASTEXITCODE -ne 0) {
            throw "Local Inno Setup bootstrap failed. Its fresh evidence directory is $runDirectory."
        }
        $bootstrap = Get-Content -Raw -LiteralPath $bootstrapManifest | ConvertFrom-Json
        $iscc = [string] $bootstrap.compiler_path
        if (-not (Test-Path -LiteralPath $iscc -PathType Leaf)) {
            throw "Local Inno Setup bootstrap did not provide ISCC.exe."
        }
        $compilerOrigin = "official-local-extraction"
    }
    if ($null -eq $iscc) {
        $message = "Inno Setup 6 (ISCC.exe) was not found. No tool was installed; portable publish output remains available at $publishDirectory. Pass -BootstrapInnoSetup to download and locally extract the pinned official compiler inside this build run."
        if ($InstallerMode -eq "Required") {
            throw $message
        }
        Write-Warning $message
        $installer = [ordered]@{ status = "not-built"; path = $null; note = $message }
    }
    else {
        $installerDirectory = Join-Path $runDirectory "installer"
        New-Item -ItemType Directory -Path $installerDirectory | Out-Null
        $installerScript = Join-Path $repositoryRoot "desktop\packaging\windows\SmartSearch.iss"
        if (-not (Test-Path -LiteralPath $installerScript -PathType Leaf)) {
            throw "Inno Setup script is not available: $installerScript"
        }
        $version = Get-ProjectVersion $repositoryRoot
        $allowedArchitectures = if ($Architecture -eq "arm64") { "arm64" } else { "x64compatible" }
        $innoArguments = @(
            "/DSourceDir=$publishDirectory",
            "/DOutputDir=$installerDirectory",
            "/DMyAppVersion=$version",
            "/DMyAppArch=$Architecture",
            "/DAllowedArchitectures=$allowedArchitectures",
            "/DInstallModeArchitectures=$allowedArchitectures",
            $installerScript
        )
        if ($signingEnabled) {
            $uninstallerDirectory = Join-Path $runDirectory 'signed-uninstaller'
            New-Item -ItemType Directory -Path $uninstallerDirectory | Out-Null
            $signCommand = '/Ssmartsearch=$q{0}$q -NoProfile -File $q{1}$q -UninstallerDirectory $q{2}$q -Path $f' -f (Get-Process -Id $PID).Path, (Join-Path $PSScriptRoot 'Sign-WindowsFile.ps1'), $uninstallerDirectory
            $innoArguments = @('/DSignedBuild=1', "/DSignedUninstallerDirectory=$uninstallerDirectory", $signCommand) + $innoArguments
        }
        & $iscc @innoArguments
        if ($LASTEXITCODE -ne 0) {
            throw "Inno Setup compilation failed. Its fresh evidence directory is $runDirectory."
        }
        $installerFile = Get-ChildItem -LiteralPath $installerDirectory -File -Filter "*.exe" | Select-Object -First 1
        if ($null -eq $installerFile) {
            throw "Inno Setup did not create an installer in $installerDirectory."
        }
        $installer = [ordered]@{
            status = if ($signingEnabled) { 'built-self-signed-package' } else { 'built-unsigned-test-package' }
            path = $installerFile.FullName
            note = "Current-user installer only; compiler=$compilerOrigin; it does not modify PATH or remove shared config/results on uninstall."
        }
        if ($signingEnabled) {
            $signatures += Test-WindowsSignature $installerFile.FullName $signingCertificate
            $uninstallers = @(Get-ChildItem -LiteralPath $uninstallerDirectory -File)
            if ($uninstallers.Count -ne 1) { throw 'Expected exactly one signed uninstaller generated by this Inno build.' }
            $signatures += Test-WindowsSignature $uninstallers[0].FullName $signingCertificate
        }
    }
}

if ($signingEnabled) {
    foreach ($file in $thirdPartyHashes.Keys) {
        if ((Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash -ne $thirdPartyHashes[$file]) {
            throw "Signing/packaging changed a file outside the owned signing allowlist: $file"
        }
    }
    $signingCertificate.Dispose()
}

$result = [ordered]@{
    run_directory = $runDirectory
    staged_project_directory = $stagedProjectDirectory
    publish_directory = $publishDirectory
    desktop_executable = $desktopExecutable
    backend = $backend
    installer = $installer
    signing = [ordered]@{
        mode = $SigningMode
        kind = if ($signingEnabled) { 'self-signed' } else { 'unsigned-test' }
        files = $signatures
        unchanged_other_files = $thirdPartyHashes.Count
        user_trust_store_modified = $false
    }
}
$resultPath = Join-Path $runDirectory "result.json"
$result | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $resultPath -Encoding utf8
Write-Output "Windows artifact: $runDirectory"
