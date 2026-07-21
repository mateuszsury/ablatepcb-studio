$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $projectRoot
py -3 -m pip install --upgrade pyinstaller
py -3 -m PyInstaller --noconfirm --clean --windowed --name Gerber2LightBurnPCB `
  --add-data "gerber2lightburn\web;gerber2lightburn\web" app.py
Write-Host "Gotowe: $projectRoot\dist\Gerber2LightBurnPCB\Gerber2LightBurnPCB.exe"
