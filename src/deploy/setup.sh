#!/usr/bin/env bash
# ────────────────────────────────────────────────────────────
#  小南专属TGbot —— Linux / macOS / WSL 安装脚本
#
#  用法：
#    ./setup.sh              正常安装（建 .venv + 装依赖 + 建数据目录）
#    ./setup.sh --service    另外安装成 systemd 服务并设置开机自启（需要 sudo）
#    ./setup.sh --mirror     用清华镜像装依赖（国内网络）
#
#  安装完成后用 manage.sh 管理：
#    ./manage.sh start|stop|restart|status|logs
# ────────────────────────────────────────────────────────────
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SRC="$ROOT/src"
VENV="$ROOT/.venv"
PY="$VENV/bin/python"
SERVICE_NAME="telegram-bot"
UNIT_SRC="$SRC/deploy/$SERVICE_NAME.service"
UNIT_DST="/etc/systemd/system/$SERVICE_NAME.service"
ENV_FILE="/etc/$SERVICE_NAME.env"

INSTALL_SERVICE=0
USE_MIRROR=0
for arg in "$@"; do
    case "$arg" in
        --service) INSTALL_SERVICE=1 ;;
        --mirror) USE_MIRROR=1 ;;
        -h|--help)
            sed -n '2,13p' "$0"
            exit 0
            ;;
        *)
            printf '未知参数: %s\n' "$arg" >&2
            exit 1
            ;;
    esac
done

ok()   { printf '  \033[92m✓\033[0m %s\n' "$*"; }
warn() { printf '  \033[93m!\033[0m %s\n' "$*"; }
err()  { printf '  \033[91m✗\033[0m %s\n' "$*" >&2; }
step() { printf '\n\033[96m%s\033[0m\n' "$*"; }

printf '\n\033[95m  小南专属TGbot —— 安装程序\033[0m\n'
printf '  项目目录：%s\n' "$ROOT"

# ── 1. Python ─────────────────────────────────────────────
step '[1/5] 检查 Python'
PYBIN=""
for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1 \
        && "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
        PYBIN="$(command -v "$candidate")"
        break
    fi
done
if [ -z "$PYBIN" ]; then
    err '没有找到 Python 3.10+'
    printf '    Debian/Ubuntu: sudo apt install -y python3 python3-venv python3-pip\n'
    printf '    macOS:         brew install python@3.13\n'
    exit 1
fi
ok "$("$PYBIN" -V 2>&1)  ($PYBIN)"

# ── 2. 虚拟环境 ───────────────────────────────────────────
step '[2/5] 准备虚拟环境 .venv'
if [ -x "$PY" ]; then
    ok '已有 .venv，复用'
else
    if ! "$PYBIN" -m venv "$VENV"; then
        err '创建虚拟环境失败'
        printf '    Debian/Ubuntu 可能缺 venv 组件：sudo apt install -y python3-venv\n'
        exit 1
    fi
    ok '已创建 .venv'
fi

# ── 3. 依赖 ───────────────────────────────────────────────
step '[3/5] 安装 Python 依赖'
MIRROR_ARGS=()
if [ "$USE_MIRROR" -eq 1 ]; then
    MIRROR_ARGS=(-i https://pypi.tuna.tsinghua.edu.cn/simple)
    warn '使用清华镜像'
fi
"$PY" -m pip install -q --upgrade pip "${MIRROR_ARGS[@]}" 2>/dev/null
if ! "$PY" -m pip install -q -r "$SRC/requirements.txt" "${MIRROR_ARGS[@]}"; then
    err '依赖安装失败'
    printf '    国内网络可以加 --mirror 重试： ./setup.sh --mirror\n'
    exit 1
fi
ok '依赖安装完成'

# ── 4. ffmpeg ────────────────────────────────────────────
step '[4/5] 检查 ffmpeg（视频解析需要）'
if command -v ffmpeg >/dev/null 2>&1; then
    ok "ffmpeg 已安装（$(command -v ffmpeg)）"
else
    warn 'ffmpeg 未安装：链接解析只能拿封面图，视频下载不下来'
    printf '    Debian/Ubuntu: sudo apt install -y ffmpeg\n'
    printf '    macOS:         brew install ffmpeg\n'
fi

# ── 5. 配置与数据目录 ────────────────────────────────────
step '[5/5] 准备配置与数据目录'
mkdir -p "$SRC/data" "$SRC/data/backups" "$ROOT/logs"
ok '数据目录已就绪'

if [ -f "$SRC/config.py" ]; then
    ok '检测到 src/config.py'
elif [ -n "${TELEGRAM_BOT_TOKEN:-}" ]; then
    ok '检测到环境变量 TELEGRAM_BOT_TOKEN（不用 config.py 也能跑）'
else
    warn '还没有配置：下面二选一'
    printf '    A) cp %s/config.example.py %s/config.py  然后填 TELEGRAM_BOT_TOKEN\n' "$SRC" "$SRC"
    printf '    B) 用环境变量（systemd 用 /etc/%s.env，Docker 用 .env）\n' "$SERVICE_NAME"
fi

# ── 可选：systemd 服务 ───────────────────────────────────
if [ "$INSTALL_SERVICE" -eq 1 ]; then
    step '[可选] 安装 systemd 服务'
    if [ "$(uname -s)" != "Linux" ]; then
        err '--service 只支持 Linux（macOS 请用 manage.sh）'
        exit 1
    fi
    if ! command -v systemctl >/dev/null 2>&1; then
        err '没有 systemctl，跳过服务安装'
        exit 1
    fi
    if [ ! -f "$UNIT_SRC" ]; then
        err "找不到 $UNIT_SRC"
        exit 1
    fi

    SUDO=""
    if [ "$(id -u)" -ne 0 ]; then
        if command -v sudo >/dev/null 2>&1; then
            SUDO="sudo"
        else
            err '需要 root 权限安装服务（请用 root 或安装 sudo）'
            exit 1
        fi
    fi

    # 把模板里的 /opt/telegram-bot 换成真实安装路径
    TMP_UNIT="$(mktemp)"
    sed "s#/opt/telegram-bot#$ROOT#g" "$UNIT_SRC" > "$TMP_UNIT"
    $SUDO install -m 644 "$TMP_UNIT" "$UNIT_DST"
    rm -f "$TMP_UNIT"
    ok "已写入 $UNIT_DST"

    # 环境变量文件（已存在就不覆盖，免得把用户填好的 Token 冲掉）
    if [ ! -f "$ENV_FILE" ]; then
        if [ -f "$ROOT/.env.example" ]; then
            $SUDO install -m 600 "$ROOT/.env.example" "$ENV_FILE"
            ok "已创建 $ENV_FILE（记得填 Token）"
        fi
    else
        ok "$ENV_FILE 已存在，保留原样"
    fi

    $SUDO systemctl daemon-reload
    $SUDO systemctl enable "$SERVICE_NAME" >/dev/null 2>&1
    ok "已设置开机自启"
fi

printf '\n\033[95m  安装完成\033[0m\n'
if [ "$INSTALL_SERVICE" -eq 1 ]; then
    printf '  启动：sudo systemctl start %s\n' "$SERVICE_NAME"
    printf '  日志：sudo journalctl -u %s -f\n\n' "$SERVICE_NAME"
else
    printf '  前台运行：%s -u %s/main.py\n' "$PY" "$SRC"
    printf '  后台运行：%s start\n' "$SRC/deploy/manage.sh"
    printf '  查看状态：%s status\n' "$SRC/deploy/manage.sh"
    printf '  查看日志：%s logs\n\n' "$SRC/deploy/manage.sh"
fi
