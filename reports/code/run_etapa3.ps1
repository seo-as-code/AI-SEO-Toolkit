# Etapa 3 — pipeline AI completo (GSC mas reciente automatico)
Set-Location $PSScriptRoot\..\..
$gsc = Get-ChildItem ..\data\raw\gsc_oauth*.csv | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $gsc) {
    Write-Error "No hay CSV GSC en ..\data\raw\ — ejecuta Etapa 1 primero."
    exit 1
}
Write-Host "GSC:" $gsc.FullName
py .\scripts\orchestrator\ai_seo_master.py --gsc $gsc.FullName
