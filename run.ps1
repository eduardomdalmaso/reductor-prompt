# Script utilitário para executar comandos Python sempre no ambiente Conda do ReductorPrompt
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ScriptArgs
)

$PythonPath = Join-Path $HOME "miniconda3\envs\reductor-prompt\python.exe"
if (-not (Test-Path $PythonPath)) {
    $PythonPath = "C:\Users\hades\miniconda3\envs\reductor-prompt\python.exe"
}

if (-not (Test-Path $PythonPath)) {
    Write-Error "Python do ambiente 'reductor-prompt' não foi encontrado em: $PythonPath"
    exit 1
}

$env:PYTHONIOENCODING = "utf-8"

if ($ScriptArgs.Count -eq 0) {
    & $PythonPath query.py --help
} else {
    & $PythonPath @ScriptArgs
}
