param([string]$EdgePath = "${env:ProgramFiles(x86)}/Microsoft/Edge/Application/msedge.exe")
$ErrorActionPreference = 'Stop'
$directory = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../assets/release-evidence'))
if (-not (Test-Path $EdgePath)) { throw "Edge not found: $EdgePath" }
foreach ($name in 'pipeline', 'evaluations', 'tools', 'production') {
    $profile = Join-Path ([IO.Path]::GetTempPath()) ('foundry-evidence-' + [guid]::NewGuid())
    $url = ([uri](Join-Path $directory 'index.html')).AbsoluteUri + '#' + $name
    $output = Join-Path ([IO.Path]::GetTempPath()) ("foundry-$name-" + [guid]::NewGuid() + '.png')
    $arguments = "--headless --disable-gpu --no-first-run --hide-scrollbars --force-device-scale-factor=1 --window-size=1500,1000 --user-data-dir=`"$profile`" --screenshot=`"$output`" `"$url`""
    $process = Start-Process -FilePath $EdgePath -ArgumentList $arguments -Wait -PassThru
    if ($process.ExitCode -ne 0 -or -not (Test-Path $output)) { throw "Capture failed: $name" }
    Move-Item $output (Join-Path $directory "$name.png") -Force
    Write-Output "Captured $name.png"
}