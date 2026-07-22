# Zolla local filters: qwen3.5:9b × 2 workers (needs Ollama NUM_PARALLEL>=2)
$ErrorActionPreference = "Continue"
$env:OLLAMA_NUM_PARALLEL = "2"
$env:OLLAMA_MAX_LOADED_MODELS = "1"
$env:OLLAMA_MODELS = "C:\ollama"
$env:PYTHONUNBUFFERED = "1"
$env:PYTHONIOENCODING = "utf-8"

# ensure ollama up
try {
  Invoke-RestMethod http://127.0.0.1:11434/api/tags | Out-Null
} catch {
  Start-Process -FilePath "C:\Users\1\AppData\Local\Programs\Ollama\ollama.exe" -ArgumentList "serve" -WindowStyle Hidden
  Start-Sleep 5
}

Set-Location "C:\Users\1\OneDrive\Desktop\attr-enrichment-product"
ollama stop gemma4:12b 2>$null
py -3.13 -u filter_pipeline/run_zolla_local_catalog.py --run --model qwen3.5:9b --workers 2 `
  2>&1 | Tee-Object -FilePath portfolio\zolla_filters\local_catalog\full_run.log -Append
