# Refresh partner CSV/HTML while vision run is in progress.
$ErrorActionPreference = "Continue"
$root = "C:\Users\1\OneDrive\Desktop\attr-enrichment-product"
Set-Location $root
while ($true) {
  $stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
  Write-Output "[$stamp] export-only…"
  & py -3.13 filter_pipeline/run_zolla_local_catalog.py --export-only
  $ckpt = Join-Path $root "portfolio\zolla_filters\local_catalog\vision_checkpoint.jsonl"
  $n = 0
  if (Test-Path $ckpt) { $n = (Get-Content $ckpt | Measure-Object -Line).Lines }
  Write-Output "[$stamp] checkpoint_lines=$n"
  Start-Sleep -Seconds 900
}
