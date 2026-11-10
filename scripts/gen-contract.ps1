# 契约生成：Pydantic 模型 -> openapi.json -> 前端 types.ts
# 用法：npm run gen:contract
$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$apiDir = Join-Path $root 'apps\api'
$python = Join-Path $apiDir '.venv\Scripts\python.exe'
$contract = Join-Path $root 'packages\contract'

$env:PYTHONPATH = (Join-Path $apiDir 'src') + ';' + (Join-Path $root '.pyshim')
$env:PYTHONIOENCODING = 'utf-8'

& $python (Join-Path $apiDir 'scripts\export_openapi.py') (Join-Path $contract 'openapi.json')
if ($LASTEXITCODE -ne 0) { throw '导出 OpenAPI 失败' }

& node (Join-Path $root 'node_modules\openapi-typescript\bin\cli.js') `
    (Join-Path $contract 'openapi.json') `
    '-o' (Join-Path $contract 'src\types.ts')
if ($LASTEXITCODE -ne 0) { throw '生成 TypeScript 类型失败' }

Write-Host '契约已更新：packages/contract/openapi.json + src/types.ts'