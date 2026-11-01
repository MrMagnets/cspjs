# 一键启动开发环境（Windows PowerShell）
# 用法：pwsh ./scripts/dev.ps1
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot

Write-Host '[1/2] 启动后端 http://127.0.0.1:8000 ...' -ForegroundColor Cyan
Start-Process -FilePath 'python' `
  -ArgumentList '-m', 'uvicorn', 'app.main:app', '--reload', '--port', '8000' `
  -WorkingDirectory (Join-Path $root 'backend')

Start-Sleep -Seconds 2

Write-Host '[2/2] 启动前端 http://127.0.0.1:5173 ...' -ForegroundColor Cyan
Start-Process -FilePath 'pnpm' -ArgumentList 'dev' -WorkingDirectory (Join-Path $root 'frontend')

Write-Host ''
Write-Host '后端接口文档：http://127.0.0.1:8000/docs' -ForegroundColor Green
Write-Host '前端页面：    http://127.0.0.1:5173' -ForegroundColor Green
Write-Host '管理员账号：  admin / adminmagnet'
