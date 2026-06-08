# 热点发现平台 - 全栈开发启动脚本
# 同时启动：
# 1. hot-content-bridge daemon (热榜采集)
# 2. FastAPI backend (API 服务)
# 3. Vite frontend (前端开发服务器)

param(
    [switch]$SkipDaemon,
    [switch]$SkipBackend,
    [switch]$SkipFrontend
)

$ErrorActionPreference = "Continue"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

Write-Host "🔥 热点发现平台 - 全栈启动" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan
Write-Host ""

# 创建日志目录
$LogDir = Join-Path $ProjectRoot "logs"
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}

$processes = @()

try {
    # 1. 启动 hot-content-bridge daemon
    if (-not $SkipDaemon) {
        Write-Host "[1/3] 启动 hot-content-bridge daemon..." -ForegroundColor Green
        $daemonLog = Join-Path $LogDir "daemon.log"
        $daemonProcess = Start-Process -FilePath "uv" -ArgumentList "run", "hot-content-bridge", "daemon" -WorkingDirectory $ProjectRoot -RedirectStandardOutput $daemonLog -RedirectStandardError $daemonLog -PassThru -WindowStyle Normal
        $processes += $daemonProcess
        Write-Host "  ✓ hot-content-bridge daemon 已启动 (PID: $($daemonProcess.Id))" -ForegroundColor Gray
        Write-Host "  📝 日志: $daemonLog" -ForegroundColor Gray
        Start-Sleep -Seconds 2
    }

    # 2. 启动 FastAPI backend
    if (-not $SkipBackend) {
        Write-Host "[2/3] 启动 FastAPI backend..." -ForegroundColor Green
        $backendLog = Join-Path $LogDir "backend.log"
        $backendProcess = Start-Process -FilePath "uv" -ArgumentList "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload" -WorkingDirectory $ProjectRoot -RedirectStandardOutput $backendLog -RedirectStandardError $backendLog -PassThru -WindowStyle Normal
        $processes += $backendProcess
        Write-Host "  ✓ FastAPI backend 已启动 (PID: $($backendProcess.Id))" -ForegroundColor Gray
        Write-Host "  📝 日志: $backendLog" -ForegroundColor Gray
        Write-Host "  🌐 API: http://localhost:8000" -ForegroundColor Gray
        Write-Host "  📚 Docs: http://localhost:8000/docs" -ForegroundColor Gray
        Start-Sleep -Seconds 2
    }

    # 3. 启动 Vite frontend
    if (-not $SkipFrontend) {
        Write-Host "[3/3] 启动 Vite frontend..." -ForegroundColor Green
        $frontendLog = Join-Path $LogDir "frontend.log"
        $frontendDir = Join-Path $ProjectRoot "web" | Join-Path -ChildPath "frontend"
        $frontendProcess = Start-Process -FilePath "npm" -ArgumentList "run", "dev" -WorkingDirectory $frontendDir -RedirectStandardOutput $frontendLog -RedirectStandardError $frontendLog -PassThru -WindowStyle Normal
        $processes += $frontendProcess
        Write-Host "  ✓ Vite frontend 已启动 (PID: $($frontendProcess.Id))" -ForegroundColor Gray
        Write-Host "  📝 日志: $frontendLog" -ForegroundColor Gray
        Write-Host "  🌐 Frontend: http://localhost:5173" -ForegroundColor Gray
    }

    Write-Host ""
    Write-Host "✅ 所有服务已启动!" -ForegroundColor Green
    Write-Host ""
    Write-Host "📋 访问地址:" -ForegroundColor Cyan
    Write-Host "  前端: http://localhost:5173" -ForegroundColor White
    Write-Host "  后端 API: http://localhost:8000" -ForegroundColor White
    Write-Host "  API 文档: http://localhost:8000/docs" -ForegroundColor White
    Write-Host ""
    Write-Host "⏹️  按 Ctrl+C 停止所有服务" -ForegroundColor Yellow
    Write-Host ""

    # 等待用户中断
    while ($true) {
        Start-Sleep -Seconds 1
        
        # 检查进程是否还在运行
        $allRunning = $true
        foreach ($proc in $processes) {
            if ($proc.HasExited) {
                Write-Host "⚠️  进程 $($proc.Id) 已退出" -ForegroundColor Red
                $allRunning = $false
            }
        }
        
        if (-not $allRunning) {
            break
        }
    }

}
finally {
    Write-Host ""
    Write-Host "⏹️  正在停止所有服务..." -ForegroundColor Yellow
    
    foreach ($proc in $processes) {
        if (-not $proc.HasExited) {
            try {
                Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
                Write-Host "  ✓ 已停止进程 $($proc.Id)" -ForegroundColor Gray
            }
            catch {
                Write-Host "  ✗ 停止进程 $($proc.Id) 失败" -ForegroundColor Red
            }
        }
    }
    
    Write-Host "👋 再见!" -ForegroundColor Cyan
}
