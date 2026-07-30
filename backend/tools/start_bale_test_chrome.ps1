param(
    [int]$DebugPort = 9222,
    [string]$ProfilePath = "$env:LOCALAPPDATA\FactoryShift-Bale-Test"
)

$chromeCandidates = @(
    "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
    "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
    "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe"
)
$chromePath = $chromeCandidates |
    Where-Object { Test-Path -LiteralPath $_ } |
    Select-Object -First 1

if (-not $chromePath) {
    throw "Google Chrome was not found."
}

New-Item -ItemType Directory -Path $ProfilePath -Force | Out-Null
$arguments = @(
    "--remote-debugging-port=$DebugPort",
    "--remote-debugging-address=127.0.0.1",
    "--user-data-dir=$ProfilePath",
    "https://web.bale.ai"
)

Start-Process -FilePath $chromePath -ArgumentList $arguments
Write-Output "Bale test Chrome started."
Write-Output "CDP endpoint: http://127.0.0.1:$DebugPort"
Write-Output "Profile: $ProfilePath"
