#!/bin/bash
# ============================================
#   🐱 小南专属TGbot - 一键部署安装脚本
#   适用于 Linux / macOS / WSL
# ============================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
PINK='\033[38;5;205m'
NC='\033[0m' # No Color

# 获取项目根目录（脚本所在目录的上级）
DEPLOY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$DEPLOY_DIR/.." && pwd)"

cd "$PROJECT_DIR"

echo -e "${PINK}"
echo "============================================"
echo "    🐱 小南专属TGbot - 一键部署安装程序"
echo "============================================"
echo -e "${NC}"
echo -e "${CYAN}📂 项目目录：${PROJECT_DIR}${NC}"
echo ""

# 检测源文件位置（优先 src 目录，其次根目录）
if [ -f "$PROJECT_DIR/src/main.py" ]; then
    SRC_DIR="$PROJECT_DIR/src"
    echo -e "${CYAN}📁 检测到 src 目录结构~${NC}"
else
    SRC_DIR="$PROJECT_DIR"
    echo -e "${CYAN}📁 检测到根目录结构~${NC}"
fi
echo ""

# 检查 Python
echo -e "${BLUE}🔍 正在检查 Python...${NC}"
if command -v python3 &> /dev/null; then
    PYTHON=python3
elif command -v python &> /dev/null; then
    PYTHON=python
else
    echo -e "${RED}❌ 错误：未检测到 Python！${NC}"
    echo ""
    echo "请安装 Python 3.8 或更高版本："
    echo "  • Ubuntu/Debian: sudo apt install python3 python3-pip"
    echo "  • macOS: brew install python3"
    echo "  • CentOS/RHEL: sudo yum install python3 python3-pip"
    echo ""
    exit 1
fi

PYTHON_VERSION=$($PYTHON --version 2>&1)
echo -e "${GREEN}✅ Python 检测成功！${NC}"
echo -e "   ${PYTHON_VERSION}"
echo ""

# 检查 pip
echo -e "${BLUE}🔍 正在检查 pip...${NC}"
if command -v pip3 &> /dev/null; then
    PIP=pip3
elif command -v pip &> /dev/null; then
    PIP=pip
else
    echo -e "${RED}❌ 错误：未检测到 pip！${NC}"
    echo "请安装 python3-pip 包"
    exit 1
fi

PIP_VERSION=$($PIP --version 2>&1)
echo -e "${GREEN}✅ pip 检测成功！${NC}"
echo -e "   ${PIP_VERSION}"
echo ""

# 检查是否为虚拟环境
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${YELLOW}💡 建议在虚拟环境中运行~${NC}"
    echo -e "   创建虚拟环境：${CYAN}$PYTHON -m venv venv${NC}"
    echo -e "   激活虚拟环境：${CYAN}source venv/bin/activate${NC}"
    echo ""
    read -p "是否继续使用系统环境？(y/n，默认n): " USE_SYSTEM
    if [ "$USE_SYSTEM" != "y" ] && [ "$USE_SYSTEM" != "Y" ]; then
        echo -e "${CYAN}正在创建虚拟环境...${NC}"
        $PYTHON -m venv venv
        source venv/bin/activate
        echo -e "${GREEN}✅ 虚拟环境已创建并激活！${NC}"
        echo ""
    fi
fi

# 安装依赖
echo -e "${BLUE}📦 正在安装依赖包...${NC}"
echo ""
$PIP install -r "$SRC_DIR/requirements.txt"
echo ""
echo -e "${GREEN}✅ 依赖安装成功！${NC}"
echo ""

# ============================================
#  配置向导
# ============================================
echo -e "${PINK}============================================"
echo "    📝 配置向导"
echo -e "============================================${NC}"
echo ""
echo -e "${YELLOW}接下来需要配置一些信息~${NC}"
echo -e "${YELLOW}如果已经有 config.py 配置好了，可以直接跳过~${NC}"
echo ""

read -p "是否跳过配置？(y/n，默认n): " SKIP_CONFIG
if [ "$SKIP_CONFIG" = "y" ] || [ "$SKIP_CONFIG" = "Y" ]; then
    echo ""
    echo -e "${BLUE}🔍 正在检查配置文件...${NC}"
    echo ""
    check_config
    exit 0
fi

echo ""
echo -e "${PURPLE}--------------------------------------------"
echo "   🤖 Telegram Bot Token"
echo -e "--------------------------------------------${NC}"
echo "在 Telegram 中搜索 @BotFather"
echo "发送 /newbot 创建新机器人"
echo "拿到你的专属 API Token"
echo ""
read -p "请输入你的 Telegram Bot Token: " TELEGRAM_TOKEN

echo ""
echo -e "${PURPLE}--------------------------------------------"
echo "   🔮 DeepSeek API 配置（可选）"
echo -e "--------------------------------------------${NC}"
echo "如果不想用 AI 对话功能，可以直接回车跳过~"
echo ""
read -p "请输入 DeepSeek API Key（直接回车跳过）: " DEEPSEEK_KEY
read -p "请输入 API 地址（直接回车使用默认）: " DEEPSEEK_URL
read -p "请输入模型名称（直接回车使用 deepseek-chat）: " DEEPSEEK_MODEL

echo ""
echo -e "${PURPLE}--------------------------------------------"
echo "   👤 主人信息"
echo -e "--------------------------------------------${NC}"
echo ""
read -p "请输入你的名字（直接回车使用"主人"）: " OWNER_NAME
read -p "请输入你的 Telegram ID（必填）: " OWNER_ID

echo ""
echo -e "${PURPLE}--------------------------------------------"
echo "   🤖 机器人名称"
echo -e "--------------------------------------------${NC}"
echo ""
read -p "请输入机器人名称（直接回车使用"小南专属TGbot"）: " BOT_NAME

echo ""
echo -e "${BLUE}--------------------------------------------"
echo "   正在生成配置文件..."
echo -e "--------------------------------------------${NC}"

# 设置默认值
TELEGRAM_TOKEN=${TELEGRAM_TOKEN:-YOUR_TELEGRAM_BOT_TOKEN}
DEEPSEEK_KEY=${DEEPSEEK_KEY:-YOUR_DEEPSEEK_API_KEY}
DEEPSEEK_URL=${DEEPSEEK_URL:-https://api.deepseek.com/v1/chat/completions}
DEEPSEEK_MODEL=${DEEPSEEK_MODEL:-deepseek-chat}
OWNER_NAME=${OWNER_NAME:-主人}
BOT_NAME=${BOT_NAME:-小南专属TGbot}

# 生成 config.py
cat > "$SRC_DIR/config.py" << EOF
"""
配置文件~ 请在这里填写你的小秘密哦(｡♥‿♥｡)
"""
import os

# Telegram Bot 配置
TELEGRAM_BOT_TOKEN = "${TELEGRAM_TOKEN}"  # 从 @BotFather 那里拿到的小钥匙🔑

# DeepSeek API 配置
DEEPSEEK_API_KEY = "${DEEPSEEK_KEY}"      # 从 DeepSeek 平台获取的魔法钥匙✨
DEEPSEEK_API_URL = "${DEEPSEEK_URL}"
DEEPSEEK_MODEL = "${DEEPSEEK_MODEL}"

# 机器人配置
BOT_NAME = "${BOT_NAME}"
BOT_OWNER_NAME = "${OWNER_NAME}"  # 主人的名字（会显示在欢迎消息等地方哦~）
BOT_OWNER_ID = ${OWNER_ID}  # 主人的 Telegram ID（填上才能用主人专属命令哦~）
MAX_HISTORY_LENGTH = 10  # 每个小可爱最多保留的对话历史条数~

# 数据文件路径
DATA_DIR = "data"
WHITELIST_FILE = "data/whitelist.json"
ADMIN_FILE = "data/admins.json"
USER_DATA_FILE = "data/user_data.json"
ERROR_LOG_FILE = "data/errors.json"
BACKUP_DIR = "data/backups"

# 模块配置
ENABLED_MODULES = [
    "deepseek_chat",  # DeepSeek AI 对话模块
    "help",           # 帮助模块
    "admin",          # 管理模块
    "system",         # 系统模块
    "fun",            # 娱乐模块
    # 在这里添加更多模块吧(๑•̀ㅂ•́)و✧
]
EOF

echo -e "${GREEN}✅ 配置文件已生成！${NC}"
echo ""

# 检查配置文件
check_config() {
    if [ ! -f "$SRC_DIR/config.py" ]; then
        echo -e "${RED}❌ 错误：找不到 config.py 配置文件！${NC}"
        exit 1
    fi

    if grep -q "YOUR_TELEGRAM_BOT_TOKEN" "$SRC_DIR/config.py"; then
        echo -e "${YELLOW}⚠️  检测到默认配置！${NC}"
        echo ""
        echo -e "${PINK}============================================"
        echo "    📝 请先配置 config.py 文件！"
        echo -e "============================================${NC}"
        echo ""
        echo "1️⃣  获取 Telegram Bot Token："
        echo "    • 在 Telegram 中搜索 @BotFather"
        echo "    • 发送 /newbot 创建新机器人"
        echo "    • 拿到你的专属 API Token"
        echo ""
        echo "2️⃣  获取 DeepSeek API Key（可选）："
        echo "    • 访问 https://platform.deepseek.com/"
        echo "    • 注册并创建 API Key"
        echo ""
        echo "3️⃣  编辑 config.py 文件："
        echo "    • 将 TELEGRAM_BOT_TOKEN 改为你的 Token"
        echo "    • 将 DEEPSEEK_API_KEY 改为你的 API Key"
        echo "    • 将 BOT_OWNER_ID 改为你的 Telegram ID"
        echo ""
        echo -e "${YELLOW}💡 配置完成后，重新运行 setup.sh 即可！${NC}"
        echo ""
        exit 1
    fi

    echo -e "${GREEN}✅ 配置文件检查通过！${NC}"
    echo ""
}

check_config

# 创建数据目录
echo -e "${BLUE}📁 正在创建数据目录...${NC}"
mkdir -p "$SRC_DIR/data" "$SRC_DIR/data/backups"
echo -e "${GREEN}✅ 数据目录创建成功！${NC}"
echo ""

# 检查 commands.txt
if [ ! -f "$PROJECT_DIR/deploy/commands.txt" ]; then
    echo -e "${YELLOW}⚠️  找不到 commands.txt 指令文件~${NC}"
    echo "正在创建默认指令文件..."
    
    mkdir -p "$PROJECT_DIR/deploy"
    cat > "$PROJECT_DIR/deploy/commands.txt" << 'EOF'
# 小南专属TGbot - 指令列表
# 格式：指令名 - 说明
# 注意：指令名不带 / 哦~
# 分类标签用 [分类名] 格式

[基础命令]
start - 我是混日子的喵～
help - 查看帮助喵～
chat - 和 AI 聊天喵～

[娱乐命令]
dice - 掷骰子喵～
rps - 猜拳喵～
EOF
    
    echo -e "${GREEN}✅ 已创建默认 commands.txt${NC}"
    echo -e "${YELLOW}💡 你可以随时编辑 deploy/commands.txt 来添加/修改指令哦~${NC}"
    echo ""
fi

# 启动机器人
echo -e "${PINK}============================================"
echo "    🚀 准备启动机器人..."
echo -e "============================================${NC}"
echo ""
echo -e "${YELLOW}💡 提示：${NC}"
echo "    • 按 Ctrl+C 可以停止机器人"
echo "    • 关闭终端也会停止机器人"
echo "    • 建议使用 screen 或 tmux 在后台运行"
echo "    • 或者使用: nohup python main.py &"
echo ""
echo -e "${PINK}============================================"
echo "    开始启动 ${BOT_NAME}..."
echo -e "============================================${NC}"
echo ""

cd "$SRC_DIR"
$PYTHON main.py

if [ $? -ne 0 ]; then
    echo ""
    echo -e "${RED}❌ 机器人启动失败！${NC}"
    echo "请检查配置是否正确~"
    exit 1
fi
