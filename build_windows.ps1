$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $projectRoot
py -3 -m pip install --upgrade pyinstaller
py -3 -m PyInstaller --noconfirm --clean --windowed --name AblatePCBStudio `
  --add-data "ablatepcb\web;ablatepcb\web" app.py
Write-Host "Gotowe: $projectRoot\dist\AblatePCBStudio\AblatePCBStudio.exe"
