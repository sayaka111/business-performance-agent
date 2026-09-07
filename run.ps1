param([switch]$Test, [switch]$Json, [switch]$MockLLM, [string]$InputFile, [string]$Question)
$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8 = '1'
$taskPython = $null
# Use an activated environment, the project environment, or PATH Python.
$taskCandidates = @()
if ($env:VIRTUAL_ENV) { $taskCandidates += Join-Path $env:VIRTUAL_ENV 'Scripts\python.exe' }
$taskCandidates += Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
$taskPathPython = Get-Command python -CommandType Application -ErrorAction SilentlyContinue
if ($taskPathPython) { $taskCandidates += $taskPathPython.Source }
foreach ($taskCandidate in $taskCandidates) {
    if (Test-Path -LiteralPath $taskCandidate -PathType Leaf) {
        $taskPython = $taskCandidate
        break
    }
}
if (-not $taskPython) { throw 'Python 3.11+ not found. Follow QUICKSTART.md to create .venv.' }
Push-Location $PSScriptRoot
try {
    if ($Test) { & $taskPython -m unittest discover -s tests -v }
    else {
        $taskArgs = @('-m', 'business_performance_agent')
        if ($Json) { $taskArgs += '--json' }
        if ($MockLLM) { $taskArgs += '--mock-llm' }
        if ($InputFile) { $taskArgs += @('--input', $InputFile) }
        if ($Question) { $taskArgs += @('--question', $Question) }
        & $taskPython @taskArgs
    }
    $taskExit = $LASTEXITCODE
} finally { Pop-Location }
exit $taskExit
