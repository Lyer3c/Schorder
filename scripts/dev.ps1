# 启动开发环境：FastAPI(8000) + Vite(5173)
# 用法：npm run dev   或   pwsh -File scripts/dev.ps1
$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$apiDir = Join-Path $root 'apps\api'
$webDir = Join-Path $root 'apps\web'
$python = Join-Path $apiDir '.venv\Scripts\python.exe'
$vite = Join-Path $root 'node_modules\vite\bin\vite.js'

if (-not (Test-Path $python)) { throw "找不到虚拟环境：$python（见 README 的初始化步骤）" }
if (-not (Test-Path $vite)) { throw "找不到 vite，请先在仓库根执行 npm install" }

# 沙箱兼容垫片：仅在需要时生效；生产环境不需要
$env:PYTHONPATH = (Join-Path $apiDir 'src') + ';' + (Join-Path $root '.pyshim')
$env:PYTHONIOENCODING = 'utf-8'
$env:PIP_CONFIG_FILE = Join-Path $apiDir 'pip.ini'

Write-Host 'API -> http://127.0.0.1:8000/docs'
Write-Host 'Web -> http://127.0.0.1:5173'

$api = Start-Process -FilePath $python `
    -ArgumentList '-m', 'uvicorn', 'schorder.main:app', '--reload', '--port', '8000' `
    -WorkingDirectory $apiDir -NoNewWindow -PassThru

try {
    Push-Location $webDir
    try {
        & node $vite --host 127.0.0.1 --port 5173 --strictPort
    }
    finally { Pop-Location }
}
finally {
    if ($api -and -not $api.HasExited) { Stop-Process -Id $api.Id -Force -ErrorAction SilentlyContinue }
}