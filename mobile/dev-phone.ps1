# Run this branch's TEMPO on a USB-connected Android phone in the "TEMPO Dev" app (mobile/README.md).
# Starts the Python backend (port 8000) and serves the frontend on port 5173 in their own windows,
# forwards the phone's localhost:5173 to this PC over USB, and opens TEMPO Dev on the phone.
#
# By default the frontend is built and rebuilt on every save (two small files): reopen the page on the
# phone to see a change. -HotReload uses the Vite dev server instead, which updates the phone by itself
# but sends dozens of files at once, which can jam the USB connection and leave a blank screen.
param(
    [string]$Adb = "",
    # A copy of the demo database, so testing never changes backend/tempo_demo.sqlite in the repo.
    [string]$Database = (Join-Path $env:TEMP "tempo-mobile-dev.sqlite"),
    [switch]$HotReload
)
$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
$frontend = Join-Path $repo "frontend"

if (-not $Adb) {
    $found = Get-Command adb -ErrorAction SilentlyContinue
    $Adb = if ($found) { $found.Source } else { Join-Path $env:USERPROFILE "AndroidDev\sdk\platform-tools\adb.exe" }
}
if (-not (Test-Path $Adb)) { throw "adb not found. Pass -Adb <path to adb.exe>." }

$devices = & $Adb devices | Select-Object -Skip 1 | Where-Object { $_ -match "\tdevice$" }
if (-not $devices) { throw "No phone found. Plug it in by USB, allow USB debugging on the phone, and run this again." }

if (-not (Test-Path $Database)) { Copy-Item (Join-Path $repo "backend\tempo_demo.sqlite") $Database }

function Test-Port($port) { [bool](Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) }
function Start-Window($title, $directory, $command) {
    Start-Process powershell -WorkingDirectory $directory -ArgumentList "-NoExit", "-Command",
        "`$host.UI.RawUI.WindowTitle='$title'; $command"
}

if (-not (Test-Port 8000)) {
    Start-Window "TEMPO backend" $repo "python -m backend.web --database '$Database'"
}
if (Test-Port 5173) {
    Write-Host "Port 5173 is already in use; keeping what runs there. Close that window first to switch modes."
} elseif ($HotReload) {
    Start-Window "TEMPO dev server" $frontend "npx vite --host 127.0.0.1 --port 5173 --strictPort"
} else {
    Write-Host "Building the frontend..."
    Push-Location $frontend
    try { npx vite build --logLevel warn; if ($LASTEXITCODE) { throw "The frontend build failed." } } finally { Pop-Location }
    Start-Window "TEMPO rebuild on save" $frontend "npx vite build --watch"
    Start-Window "TEMPO phone server" $frontend "npx vite preview --host 127.0.0.1 --port 5173 --strictPort"
}

Write-Host "Waiting for port 5173..."
for ($i = 0; $i -lt 60 -and -not (Test-Port 5173); $i++) { Start-Sleep -Seconds 1 }
if (-not (Test-Port 5173)) { throw "Nothing started on port 5173. Check the TEMPO windows for errors." }

# A fresh forward each run: a jammed one stays jammed until it is removed.
$ErrorActionPreference = "Continue"   # adb writes ordinary progress to stderr
& $Adb reverse --remove-all | Out-Null
& $Adb reverse tcp:5173 tcp:5173 | Out-Null
& $Adb shell am force-stop com.tempo.chessdemo.dev
& $Adb shell monkey -p com.tempo.chessdemo.dev -c android.intent.category.LAUNCHER 1 2>&1 | Out-Null
if ($HotReload) {
    Write-Host "TEMPO Dev is open. Edits in frontend/src update the phone by themselves."
    Write-Host "If the screen stays blank, run this script again: it resets the USB connection."
} else {
    Write-Host "TEMPO Dev is open. After saving a change, wait for 'built in' in the rebuild window,"
    Write-Host "then run this script again: it keeps the servers running and reopens the app with your change."
}
