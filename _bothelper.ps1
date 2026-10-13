# 小南专属TGbot - 启动脚本辅助（由 start.bat 调用，不要单独运行）
#
# 参数：
#   run    <python> <main.py> <logdir>   前台启动，输出同时写日志
#   bg     <python> <main.py> <logdir>   后台启动（本脚本负责进程创建）
#   status <pidfile> <srcdir>            检查运行状态
#   stop   <pidfile>                     停止机器人
#
# 为什么用 PowerShell 而不是纯批处理：
#   1. 批处理的 find/findstr 会被 PATH 里 Git 自带的 Unix 工具遮蔽
#      （机器上装了 Git 就会命中 find 的 Unix 版本），导致检测永远失败
#   2. 批处理里用 start 启动带引号参数的命令，容易出现引号嵌套和重复
#      启动的问题，改用 Start-Process 参数传递可靠得多
#   3. 时间戳格式在中文 Windows 上不稳定
#   4. 进程筛选用 CIM 查询比解析 tasklist 文本可靠得多
#
# 【维护须知】本文件必须保存为 **带 BOM 的 UTF-8**！
#   Windows PowerShell 5.1 读取无 BOM 的 .ps1 时会按 ANSI(GBK) 解码，
#   中文字符被解错后会导致引号错位、脚本直接语法报错。

param(
    [Parameter(Mandatory = $true)][string]$Action,
    [string]$Arg1,
    [string]$Arg2,
    [string]$Arg3
)

$ErrorActionPreference = 'Continue'

function Get-BotProcesses {
    # 只返回"最顶层"的机器人实例。
    # 现实里可能出现同一命令行的多个进程（比如父进程被杀后留下的孤儿，
    # 或是手工起了两次），它们其实是同一个机器人的副本，
    # 这里按创建时间排序后只保留最早的那个，避免重复报告和重复停止。
    $all = @(
        Get-CimInstance Win32_Process -Filter "Name LIKE 'python%'" -ErrorAction SilentlyContinue |
            Where-Object { $_.CommandLine -and $_.CommandLine -like "*main.py*" } |
            Sort-Object CreationDate
    )
    if ($all.Count -le 1) { return $all }

    $primary = $all[0]
    $result = @($primary)
    foreach ($p in $all[1..($all.Count - 1)]) {
        # 父进程就是 primary 的属于它的子进程，不算独立实例
        if ($p.ParentProcessId -ne $primary.ProcessId) {
            $result += $p
        }
    }
    return $result
}

function Wait-ForBot {
    # 等机器人真的起来（写出 PID 文件且进程存在）
    param([string]$PidFile, [int]$TimeoutSeconds = 45)

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        Start-Sleep -Milliseconds 800

        if (Test-Path $PidFile) {
            $text = (Get-Content $PidFile -Raw -ErrorAction SilentlyContinue)
            if ($text) { $text = $text.Trim() }
            if ($text -match '^\d+$') {
                $proc = Get-Process -Id ([int]$text) -ErrorAction SilentlyContinue
                if ($proc) {
                    return @{ Ok = $true; Pid = [int]$text }
                }
            }
        }

        # 进程全死光了就再确认一次，然后判定失败
        if (-not (Get-BotProcesses)) {
            Start-Sleep -Seconds 2
            if (-not (Get-BotProcesses)) {
                return @{ Ok = $false; Pid = 0 }
            }
        }
    }
    return @{ Ok = $false; Pid = 0 }
}

switch ($Action) {

    'run' {
        $py = $Arg1
        $main = $Arg2
        $logdir = $Arg3

        if (-not (Test-Path $logdir)) {
            New-Item -ItemType Directory -Force -Path $logdir | Out-Null
        }
        $stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
        $log = Join-Path $logdir "bot_$stamp.log"
        Write-Output "  日志: $log"
        Write-Output ""

        # -u 强制 Python 无缓冲输出，否则重定向到文件时日志会长时间为空
        & $py -u $main 2>&1 | Tee-Object -FilePath $log
    }

    'bg' {
        $py = $Arg1
        $main = $Arg2
        $logdir = $Arg3
        $srcDir = Split-Path $main -Parent
        $pidfile = Join-Path $srcDir 'data\bot.pid'

        if (-not (Test-Path $logdir)) {
            New-Item -ItemType Directory -Force -Path $logdir | Out-Null
        }

        # 清掉可能残留的 PID 文件，避免误判成"启动成功"
        if (Test-Path $pidfile) { Remove-Item $pidfile -Force -ErrorAction SilentlyContinue }

        $stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
        $log = Join-Path $logdir "bot_$stamp.log"
        $errlog = Join-Path $logdir "bot_${stamp}_err.log"

        Write-Output "  日志: $log"
        Write-Output "  等待启动（最多 45 秒）..."

        # Start-Process 是独立的进程创建，不受父控制台影响，
        # 也不会像批处理 start 那样出现引号嵌套或重复启动的问题
        $proc = Start-Process -FilePath $py `
            -ArgumentList @('-u', $main) `
            -WorkingDirectory $srcDir `
            -RedirectStandardOutput $log `
            -RedirectStandardError $errlog `
            -WindowStyle Hidden `
            -PassThru

        $result = Wait-ForBot -PidFile $pidfile -TimeoutSeconds 45

        if ($result.Ok) {
            Write-Output ""
            Write-Output "  机器人已在后台运行（PID $($result.Pid)）"
            Write-Output "  可以关掉这个窗口了"
            Write-Output ""
            Write-Output "  查看状态: start.bat --status"
            Write-Output "  停止运行: start.bat --stop"
            exit 0
        }

        Write-Output ""
        Write-Output "  [警告] 启动失败或超时"
        Write-Output ""
        $alive = @(Get-BotProcesses)
        if ($alive.Count -gt 0) {
            Write-Output "  进程是否还活着: 是（PID $($alive.ProcessId -join ', ')）"
        } else {
            Write-Output "  进程是否还活着: 否"
        }
        Write-Output "  日志文件: $log"

        if ((Test-Path $log) -and (Get-Item $log).Length -gt 0) {
            Write-Output ""
            Write-Output "  --- 日志末尾 ---"
            Get-Content $log -Tail 15 | ForEach-Object { Write-Output "  $_" }
        } elseif ((Test-Path $errlog) -and (Get-Item $errlog).Length -gt 0) {
            Write-Output ""
            Write-Output "  --- 错误输出末尾 ---"
            Get-Content $errlog -Tail 15 | ForEach-Object { Write-Output "  $_" }
        } else {
            Write-Output "  （日志为空，机器人可能还没输出就被终止了）"
        }
        exit 1
    }

    'status' {
        $pidfile = $Arg1
        $srcDir = $Arg2
        $running = $false

        if (Test-Path $pidfile) {
            $pidText = (Get-Content $pidfile -Raw).Trim()
            if ($pidText -match '^\d+$') {
                $proc = Get-Process -Id ([int]$pidText) -ErrorAction SilentlyContinue
                if ($proc) {
                    $secs = [math]::Round(((Get-Date) - $proc.StartTime).TotalSeconds)
                    Write-Output "  正在运行（PID $pidText，已运行 $secs 秒）"
                    $running = $true
                } else {
                    Write-Output "  未运行（PID 文件是残留的：$pidText）"
                }
            } else {
                Write-Output "  未运行（PID 文件内容异常）"
            }
        } else {
            Write-Output "  未运行（没有 PID 文件）"
        }

        # 兜底：PID 文件丢了但进程还在
        if (-not $running) {
            foreach ($p in @(Get-BotProcesses)) {
                Write-Output "  但检测到进程 PID $($p.ProcessId) 仍带着 main.py 在跑"
                $running = $true
            }
        }

        Write-Output ""
        Write-Output "  配置文件: $(Join-Path $srcDir 'config.py')"
        Write-Output "  日志目录: $(Join-Path (Split-Path $srcDir -Parent) 'logs')"

        if ($running) { exit 0 } else { exit 2 }
    }

    'stop' {
        $pidfile = $Arg1
        $stopped = 0

        if (Test-Path $pidfile) {
            $pidText = (Get-Content $pidfile -Raw).Trim()
            if ($pidText -match '^\d+$') {
                $proc = Get-Process -Id ([int]$pidText) -ErrorAction SilentlyContinue
                if ($proc) {
                    Stop-Process -Id ([int]$pidText) -Force -ErrorAction SilentlyContinue
                    Write-Output "  已停止进程 PID $pidText"
                    $stopped = 1
                }
            }
        }

        # 兜底：只结束命令行里带 main.py 的 python 进程。
        # 绝不使用 taskkill /IM python.exe —— 那会杀掉机器上所有 Python 程序
        foreach ($p in @(Get-BotProcesses)) {
            Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
            Write-Output "  已停止残留进程 PID $($p.ProcessId)"
            $stopped = 1
        }

        if (Test-Path $pidfile) { Remove-Item $pidfile -Force -ErrorAction SilentlyContinue }

        if ($stopped -eq 0) {
            Write-Output "  没有发现正在运行的机器人"
            exit 2
        }
        exit 0
    }

    default {
        Write-Output "  [内部错误] 未知的 Action: $Action"
        exit 1
    }
}
