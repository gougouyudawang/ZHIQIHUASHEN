param([int]$PortOffset = 0)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$logDir = Join-Path $root 'local_store\bootstrap_logs'
$services = @(
    @{ Name = 'TP'; Port = (8111 + $PortOffset); Module = 'app.tp_app:app' },
    @{ Name = 'AP'; Port = (8112 + $PortOffset); Module = 'app.ap_app:app' },
    @{ Name = 'User'; Port = (8110 + $PortOffset); Module = 'app.experience_app:app' }
)

foreach ($item in $services) {
    $pidFile = Join-Path $logDir "$($item.Name)-$($item.Port).pid"
    if (-not (Test-Path -LiteralPath $pidFile)) { continue }
    $savedPid = [int](Get-Content -LiteralPath $pidFile -Raw).Trim()
    $process = Get-CimInstance Win32_Process -Filter "ProcessId=$savedPid" -ErrorAction SilentlyContinue
    if ($process) {
        $commandLine = [string]$process.CommandLine
        $executable = [string]$process.ExecutablePath
        $sameProject = $executable.StartsWith($root + '\', [StringComparison]::OrdinalIgnoreCase) -and $executable.EndsWith('\Scripts\python.exe', [StringComparison]::OrdinalIgnoreCase)
        if ($sameProject -and $commandLine.Contains($item.Module) -and $commandLine.Contains("--port $($item.Port)")) {
            Stop-Process -Id $savedPid
            Write-Host "$($item.Name) 已停止。"
        } else {
            Write-Warning "跳过 $($item.Name)：PID 已被其他进程使用。"
        }
    }
    Remove-Item -LiteralPath $pidFile -ErrorAction SilentlyContinue
}
