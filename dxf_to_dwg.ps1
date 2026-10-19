# DXF -> DWG (AutoCAD 2018) via ODA File Converter (Windows version of dxf_to_dwg.sh).
# Usage: .\dxf_to_dwg.ps1 -InputDxf <file.dxf> -OutputDir <dir>
# If ODAFileConverter.exe is not on PATH, set the full path first:
#   $env:ODA_CONVERTER = "C:\Program Files\ODA\ODAFileConverter\ODAFileConverter.exe"
param(
    [Parameter(Mandatory = $true)][string]$InputDxf,
    [Parameter(Mandatory = $true)][string]$OutputDir
)
$ErrorActionPreference = 'Stop'

$oda = if ($env:ODA_CONVERTER) { $env:ODA_CONVERTER } else { 'ODAFileConverter.exe' }
$inDir = Join-Path ([IO.Path]::GetTempPath()) ('dxf2dwg_' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $inDir | Out-Null
try {
    Copy-Item -LiteralPath $InputDxf -Destination $inDir
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
    $outAbs = (Resolve-Path -LiteralPath $OutputDir).Path

    & $oda $inDir $outAbs ACAD2018 DWG 0 1
    if ($LASTEXITCODE -ne 0) { throw "ODAFileConverter failed (exit code $LASTEXITCODE)" }

    $dwg = Join-Path $outAbs (([IO.Path]::GetFileNameWithoutExtension($InputDxf)) + '.dwg')
    if (-not (Test-Path -LiteralPath $dwg)) { throw "DWG not created: $dwg" }
    Write-Output $dwg
}
finally {
    Remove-Item -LiteralPath $inDir -Recurse -Force -ErrorAction SilentlyContinue
}
