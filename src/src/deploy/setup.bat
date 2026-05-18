@echo off
chcp 65001 >nul
title 小南专属TGbot - 一键部署安装程序
color 0A

echo ============================================
echo    🐱 小南专属TGbot - 一键部署安装程序
echo ============================================
echo.

:: 获取项目根目录（setup.bat 所在目录的上级）
set "DEPLOY_DIR=%~dp0"
set "PROJECT_DIR=%DEPLOY_DIR%.."

:: 进入项目根目录
cd /d "%PROJECT_DIR%"

echo 📂 项目目录：%PROJECT_DIR%
echo.

:: 检测源文件位置（优先 src 目录，其次根目录）
if exist "%PROJECT_DIR%\src\main.py" (
    set "SRC_DIR=%PROJECT_DIR%\src"
    echo 📁 检测到 src 目录结构~
) else (
    set "SRC_DIR=%PROJECT_DIR%"
    echo 📁 检测到根目录结构~
)
echo.

:: 检查 Python 是否安装
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 错误：未检测到 Python！
    echo.
    echo 请先安装 Python 3.8 或更高版本~
    echo 下载地址：https://www.python.org/downloads/
    echo.
    echo 💡 安装时请记得勾选 "Add Python to PATH"！
    echo.
    pause
    exit /b 1
)

echo ✅ Python 检测成功！
python --version
echo.

:: 检查 pip 是否可用
pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 错误：未检测到 pip！
    echo 请重新安装 Python 并勾选 "Add Python to PATH"
    pause
    exit /b 1
)

echo ✅ pip 检测成功！
echo.

:: 安装依赖
echo 📦 正在安装依赖包...
echo.
pip install -r "%SRC_DIR%\requirements.txt"
if %errorlevel% neq 0 (
    echo ❌ 依赖安装失败！
    echo 请检查网络连接后重试~
    pause
    exit /b 1
)

echo ✅ 依赖安装成功！
echo.

:: ============================================
::  配置向导
:: ============================================
echo ============================================
echo    📝 配置向导
echo ============================================
echo.
echo 接下来需要配置一些信息~
echo 如果已经有 config.py 配置好了，可以直接跳过~
echo.

set /p SKIP_CONFIG="是否跳过配置？(y/n，默认n): "
if /i "!SKIP_CONFIG!"=="y" goto :CHECK_CONFIG

echo.
echo --------------------------------------------
echo   🤖 Telegram Bot Token
echo --------------------------------------------
echo 在 Telegram 中搜索 @BotFather
echo 发送 /newbot 创建新机器人
echo 拿到你的专属 API Token
echo.
set /p TELEGRAM_TOKEN="请输入你的 Telegram Bot Token: "

echo.
echo --------------------------------------------
echo   🔮 DeepSeek API 配置（可选）
echo --------------------------------------------
echo 如果不想用 AI 对话功能，可以直接回车跳过~
echo.
set /p DEEPSEEK_KEY="请输入 DeepSeek API Key（直接回车跳过）: "
set /p DEEPSEEK_URL="请输入 API 地址（直接回车使用默认）: "
set /p DEEPSEEK_MODEL="请输入模型名称（直接回车使用 deepseek-chat）: "

echo.
echo --------------------------------------------
echo   👤 主人信息
echo --------------------------------------------
echo.
set /p OWNER_NAME="请输入你的名字（直接回车使用"主人"）: "
set /p OWNER_ID="请输入你的 Telegram ID（必填）: "

echo.
echo --------------------------------------------
echo   🤖 机器人名称
echo --------------------------------------------
echo.
set /p BOT_NAME="请输入机器人名称（直接回车使用"小南专属TGbot"）: "

echo.
echo --------------------------------------------
echo   正在生成配置文件...
echo --------------------------------------------

:: 设置默认值
if "%TELEGRAM_TOKEN%"=="" set TELEGRAM_TOKEN=YOUR_TELEGRAM_BOT_TOKEN
if "%DEEPSEEK_KEY%"=="" set DEEPSEEK_KEY=YOUR_DEEPSEEK_API_KEY
if "%DEEPSEEK_URL%"=="" set DEEPSEEK_URL=https://api.deepseek.com/v1/chat/completions
if "%DEEPSEEK_MODEL%"=="" set DEEPSEEK_MODEL=deepseek-chat
if "%OWNER_NAME%"=="" set OWNER_NAME=主人
if "%BOT_NAME%"=="" set BOT_NAME=小南专属TGbot

:: 生成 config.py
(
echo """
echo 配置文件~ 请在这里填写你的小秘密哦(｡♥‿♥｡)
echo """
echo import os
echo.
echo # Telegram Bot 配置
echo TELEGRAM_BOT_TOKEN = "%TELEGRAM_TOKEN%"  # 从 @BotFather 那里拿到的小钥匙🔑
echo.
echo # DeepSeek API 配置
echo DEEPSEEK_API_KEY = "%DEEPSEEK_KEY%"      # 从 DeepSeek 平台获取的魔法钥匙✨
echo DEEPSEEK_API_URL = "%DEEPSEEK_URL%"
echo DEEPSEEK_MODEL = "%DEEPSEEK_MODEL%"
echo.
echo # 机器人配置
echo BOT_NAME = "%BOT_NAME%"
echo BOT_OWNER_NAME = "%OWNER_NAME%"  # 主人的名字（会显示在欢迎消息等地方哦~）
echo BOT_OWNER_ID = %OWNER_ID%  # 主人的 Telegram ID（填上才能用主人专属命令哦~）
echo MAX_HISTORY_LENGTH = 10  # 每个小可爱最多保留的对话历史条数~
echo.
echo # 数据文件路径
echo DATA_DIR = "data"
echo WHITELIST_FILE = "data/whitelist.json"
echo ADMIN_FILE = "data/admins.json"
echo USER_DATA_FILE = "data/user_data.json"
echo ERROR_LOG_FILE = "data/errors.json"
echo BACKUP_DIR = "data/backups"
echo.
echo # 模块配置
echo ENABLED_MODULES = [
echo     "deepseek_chat",  # DeepSeek AI 对话模块
echo     "help",           # 帮助模块
echo     "admin",          # 管理模块
echo     "system",         # 系统模块
echo     "fun",            # 娱乐模块
echo     # 在这里添加更多模块吧(๑•̀ㅂ•́)و✧
echo ]
) > "%SRC_DIR%\config.py"

echo ✅ 配置文件已生成！
echo.

:CHECK_CONFIG
:: 检查配置文件
echo 🔍 正在检查配置文件...
echo.

if not exist "%SRC_DIR%\config.py" (
    echo ❌ 错误：找不到 config.py 配置文件！
    echo 请确保 config.py 文件存在~
    pause
    exit /b 1
)

:: 检查是否已配置 Token
findstr /C:"YOUR_TELEGRAM_BOT_TOKEN" "%SRC_DIR%\config.py" >nul 2>&1
if %errorlevel% equ 0 (
    echo ⚠️  检测到默认配置！
    echo.
    echo ============================================
    echo    📝 请先配置 config.py 文件！
    echo ============================================
    echo.
    echo 1️⃣  获取 Telegram Bot Token：
    echo    • 在 Telegram 中搜索 @BotFather
    echo    • 发送 /newbot 创建新机器人
    echo    • 拿到你的专属 API Token
    echo.
    echo 2️⃣  获取 DeepSeek API Key（可选）：
    echo    • 访问 https://platform.deepseek.com/
    echo    • 注册并创建 API Key
    echo.
    echo 3️⃣  编辑 config.py 文件：
    echo    • 将 TELEGRAM_BOT_TOKEN 改为你的 Token
    echo    • 将 DEEPSEEK_API_KEY 改为你的 API Key
    echo    • 将 BOT_OWNER_ID 改为你的 Telegram ID
    echo.
    echo 💡 配置完成后，重新运行 setup.bat 即可！
    echo.
    pause
    exit /b 1
)

echo ✅ 配置文件检查通过！
echo.

:: 创建数据目录
echo 📁 正在创建数据目录...
if not exist "%SRC_DIR%\data" mkdir "%SRC_DIR%\data"
if not exist "%SRC_DIR%\data\backups" mkdir "%SRC_DIR%\data\backups"
echo ✅ 数据目录创建成功！
echo.

:: 检查 commands.txt
if not exist "%PROJECT_DIR%\deploy\commands.txt" (
    echo ⚠️  找不到 commands.txt 指令文件~
    echo 正在创建默认指令文件...
    
    if not exist "%PROJECT_DIR%\deploy" mkdir "%PROJECT_DIR%\deploy"
    (
        echo # 小南专属TGbot - 指令列表
        echo # 格式：指令名 - 说明
        echo # 注意：指令名不带 / 哦~
        echo # 分类标签用 [分类名] 格式
        echo.
        echo [基础命令]
        echo start - 我是混日子的喵～
        echo help - 查看帮助喵～
        echo chat - 和 AI 聊天喵～
        echo.
        echo [娱乐命令]
        echo dice - 掷骰子喵～
        echo rps - 猜拳喵～
    ) > "%PROJECT_DIR%\deploy\commands.txt"
    
    echo ✅ 已创建默认 commands.txt
    echo 💡 你可以随时编辑 deploy\commands.txt 来添加/修改指令哦~
    echo.
)

:: 启动机器人
echo ============================================
echo    🚀 准备启动机器人...
echo ============================================
echo.
echo 💡 提示：
echo    • 按 Ctrl+C 可以停止机器人
echo    • 关闭窗口也会停止机器人
echo    • 建议在后台运行哦~
echo.
echo ============================================
echo    开始启动 %BOT_NAME%...
echo ============================================
echo.

cd /d "%SRC_DIR%"
python main.py

if %errorlevel% neq 0 (
    echo.
    echo ❌ 机器人启动失败！
    echo 请检查配置是否正确~
    pause
    exit /b 1
)

pause
