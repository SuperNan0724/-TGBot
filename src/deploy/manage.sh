#!/usr/bin/env bash
# ────────────────────────────────────────────────────────────
#  小南专属TGbot —— 命令行管理脚本（Linux / macOS / WSL）
#
#  用法：
#    ./manage.sh start     后台启动（日志写到 logs/）
#    ./manage.sh stop      停止（先 SIGINT 优雅退出，15 秒不退才 SIGKILL）
#    ./manage.sh restart
#    ./manage.sh status
#    ./manage.sh logs      跟踪最新日志
#
#  前置：先跑过 src/deploy/setup.sh（它会建好 .venv 并装依赖）
#  这是 Windows 上 start.bat --bg/--stop/--status 的对应物。
# ────────────────────────────────────────────────────────────
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SRC="$ROOT/src"
PY="$ROOT/.venv/bin/python"
PIDFILE="$SRC/data/bot.pid"
LOGDIR="$ROOT/logs"

read_pid() {
    [ -f "$PIDFILE" ] || return 1
    local pid
    pid="$(tr -dc '0-9' < "$PIDFILE" 2>/dev/null)"
    [ -n "$pid" ] || return 1
    printf '%s' "$pid"
}

is_running() {
    local pid
    pid="$(read_pid)" || return 1
    kill -0 "$pid" 2>/dev/null
}

cmd_status() {
    if is_running; then
        printf '  正在运行（PID %s）\n' "$(read_pid)"
        return 0
    fi
    if [ -f "$PIDFILE" ]; then
        printf '  未运行（PID 文件是残留的：%s）\n' "$(cat "$PIDFILE" 2>/dev/null)"
        return 2
    fi
    printf '  未运行（没有 PID 文件）\n'
    return 2
}

cmd_start() {
    if is_running; then
        printf '  已经在跑了（PID %s），不用重复启动\n' "$(read_pid)"
        return 0
    fi
    if [ ! -x "$PY" ]; then
        printf '  [错误] 找不到 %s\n         请先运行 src/deploy/setup.sh 建虚拟环境\n' "$PY" >&2
        return 1
    fi

    mkdir -p "$LOGDIR" "$SRC/data"
    # 顺手清理 7 天前的日志，免得 logs/ 无限增长（systemd 走 journald，不需要这段）
    find "$LOGDIR" -maxdepth 1 -type f -name 'bot_*.log' -mtime +7 -delete 2>/dev/null || true
    local log="$LOGDIR/bot_$(date +%Y%m%d_%H%M%S).log"
    printf '  日志: %s\n' "$log"

    # setsid：脱离当前终端，关掉 SSH 也不影响（macOS 可能没有，退回 nohup）
    if command -v setsid >/dev/null 2>&1; then
        setsid nohup "$PY" -u "$SRC/main.py" >> "$log" 2>&1 < /dev/null &
    else
        nohup "$PY" -u "$SRC/main.py" >> "$log" 2>&1 < /dev/null &
    fi

    # PID 文件是 main.py 启动成功后自己写的，等它出现就等于"真的起来了"
    local i=0
    while [ "$i" -lt 30 ]; do
        sleep 1
        if is_running; then
            printf '  启动成功（PID %s）\n' "$(read_pid)"
            tail -n 5 "$log" 2>/dev/null
            return 0
        fi
        i=$((i + 1))
    done

    printf '  [警告] 30 秒内没等到 PID 文件，可能启动失败了\n' >&2
    tail -n 20 "$log" 2>/dev/null >&2
    return 1
}

cmd_stop() {
    if ! is_running; then
        printf '  没有在运行\n'
        rm -f "$PIDFILE"
        return 2
    fi

    local pid
    pid="$(read_pid)"
    printf '  正在停止 PID %s ...\n' "$pid"

    # SIGINT 会让 PTB 走正常关闭流程（清理 pid 文件、断开连接）
    kill -INT "$pid" 2>/dev/null || kill -TERM "$pid" 2>/dev/null

    local i=0
    while [ "$i" -lt 15 ]; do
        sleep 1
        if ! kill -0 "$pid" 2>/dev/null; then
            printf '  已停止\n'
            rm -f "$PIDFILE"
            return 0
        fi
        i=$((i + 1))
    done

    printf '  15 秒还没停，强制结束\n' >&2
    kill -KILL "$pid" 2>/dev/null
    rm -f "$PIDFILE"
    return 0
}

cmd_logs() {
    local latest
    latest="$(ls -t "$LOGDIR"/*.log 2>/dev/null | head -n 1)"
    if [ -z "$latest" ]; then
        printf '  还没有日志文件（%s）\n' "$LOGDIR" >&2
        return 1
    fi
    printf '  == %s ==\n' "$latest"
    tail -n 50 -f "$latest"
}

case "${1:-}" in
    start) cmd_start ;;
    stop) cmd_stop ;;
    restart) cmd_stop; cmd_start ;;
    status) cmd_status ;;
    logs) cmd_logs ;;
    *)
        printf '用法: %s {start|stop|restart|status|logs}\n' "$0"
        exit 1
        ;;
esac
