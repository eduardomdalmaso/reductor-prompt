$ErrorActionPreference = "Stop"

Write-Host "=== 1. Checking Ollama & 7B Model ==="
try {
    $models = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 5
    $qwen7b = $models.models | Where-Object { $_.name -like "*7b*" }
    if ($qwen7b) {
        Write-Host " [OK] Ollama is active with 7B model: $($qwen7b.name)"
    } else {
        Write-Host " [WARN] Ollama is active, but 7b model not listed in tags."
    }
} catch {
    Write-Host " [FAIL] Could not connect to Ollama: $_"
}

Write-Host "`n=== 2. Starting PM2 Applications ==="
$pm2Cmd = "C:\Users\hades\AppData\Roaming\npm\pm2.cmd"

# Start apps
& $pm2Cmd start "c:\Users\hades\Documents\HydraForge\ecosystem.config.cjs"
& $pm2Cmd start "c:\Users\hades\Documents\HydraVault\ecosystem.config.cjs"
& $pm2Cmd start "c:\Users\hades\Documents\HydraStream\ecosystem.config.cjs"
& $pm2Cmd start "c:\Users\hades\Documents\reductor-prompt\ecosystem.config.cjs"

# Save state for persistence
& $pm2Cmd save

Write-Host "`n=== 3. PM2 Process Status ==="
& $pm2Cmd list
