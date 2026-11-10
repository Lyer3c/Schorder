# 一键验证：lint -> 类型 -> 测试 -> 契约 -> 前端类型 -> 构建
# 用法：npm run verify   或   pwsh -File scripts/verify.ps1
param([switch]$SkipBuild)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$apiDir = Join-Path $root 'apps\api'
$webDir = Join-Path $root 'apps\web'
$python = Join-Path $apiDir '.venv\Scripts\python.exe'

$env:PYTHONPATH = (Join-Path $apiDir 'src') + ';' + (Join-Path $root '.pyshim')
$env:PYTHONIOENCODING = 'utf-8'
$env:TMP = Join-Path $root '.tmp'
$env:TEMP = Join-Path $root '.tmp'
New-Item -ItemType Directory -Force -Path $env:TMP | Out-Null

function Step([string]$name, [scriptblock]$body) {
    Write-Host ''
    Write-Host "== $name ==" -ForegroundColor Cyan
    & $body
    if ($LASTEXITCODE -ne 0) { throw "步骤失败：$name" }
}

Push-Location $apiDir
try {
    Step 'ruff check'  { & $python -m ruff check . }
    Step 'ruff format' { & $python -m ruff format --check . }
    Step 'mypy'        { & $python -m mypy src }
    Step 'pytest'      { & $python -m pytest -q }
}
finally { Pop-Location }

Step 'contract' { & (Join-Path $PSScriptRoot 'gen-contract.ps1') }

Push-Location $webDir
try {
    Step 'tsc' { & node ..\..\node_modules\typescript\bin\tsc --noEmit -p tsconfig.json }
    if (-not $SkipBuild) {
        Step 'vite build' { & node ..\..\node_modules\vite\bin\vite.js build }
    }
}
finally { Pop-Location }

Write-Host ''
Write-Host '全部通过' -ForegroundColor Green