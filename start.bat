@echo off
setlocal EnableDelayedExpansion
title 小南专属TGbot 启动器

rem ============================================================
rem  小南专属TGbot - Windows 一键启动脚本
rem
rem  用法：
rem    start.bat            前台运行（关掉窗口即停止）
rem    start.bat --bg       后台运行
rem    start.bat --stop     停止机器人
rem    start.bat --status   查看运行状态
rem
rem  【维护须知】本文件必须保持 GBK 编码 + CRLF 行尾！
rem
rem  1) 编码：cmd.exe 按字节解析 .bat。若文件是 UTF-8 且脚本内调用
rem     chcp 切换代码页，cmd 会把中文字符的字节读错位，导致命令解析
rem     失败。所以这里不调用 chcp，让文件编码与中文 Windows 默认的
rem     代码页 936 保持一致。
rem
rem  2) 行尾：必须是 CRLF。纯 LF 行尾在含中文等多字节内容时会让 cmd
rem     严重错位解析（表现为把半个词当成命令）。
rem
rem  3) 进程检测和后台启动都交给 _bothelper.ps1：
rem     批处理的 find/findstr 会被 PATH 里 Git 自带的 Unix find 遮蔽，
rem     而 start 带引号参数容易引号嵌套和重复启动。
rem ============================================================

set "ROOT=%~dp0"
set "SRC=%ROOT%src"
set "VENV=%ROOT%.venv"
set "PY=%VENV%\Scripts\python.exe"
set "LOGDIR=%ROOT%logs"
set "PIDFILE=%SRC%\data\bot.pid"
set "HELPER=%ROOT%_bothelper.ps1"
set "PS=powershell -NoProfile -ExecutionPolicy Bypass -File"

set "MODE=foreground"
if /i "%~1"=="--bg"     set "MODE=background"
if /i "%~1"=="--stop"   set "MODE=stop"
if /i "%~1"=="--status" set "MODE=status"

echo.
echo   ============================================
echo      小南专属TGbot  启动器
echo   ============================================
echo.

if "%MODE%"=="stop"   goto :do_stop
if "%MODE%"=="status" goto :do_status

rem ============================================================
rem  1. 检查 Python
rem ============================================================
if exist "%PY%" goto :python_ok

echo   [1/5] 检查 Python 环境...
where python >nul 2>&1
if errorlevel 1 (
    echo.
    echo   [错误] 没有找到 Python
    echo.
    echo   请先安装 Python 3.10 或更高版本：
    echo     https://www.python.org/downloads/
    echo.
    echo   注意：安装时务必勾选 "Add Python to PATH"
    echo.
    pause
    exit /b 1
)

echo         正在创建虚拟环境...
python -m venv "%VENV%"
if errorlevel 1 (
    echo   [错误] 虚拟环境创建失败
    pause
    exit /b 1
)
echo         虚拟环境已创建
goto :config_check

:python_ok
echo   [1/5] Python 环境  OK

rem ============================================================
rem  2. 检查配置文件
rem ============================================================
:config_check
echo   [2/5] 检查配置文件...

if exist "%SRC%\config.py" goto :config_exists

if not exist "%SRC%\config.example.py" (
    echo   [错误] 找不到 config.py，也找不到 config.example.py
    pause
    exit /b 1
)

copy "%SRC%\config.example.py" "%SRC%\config.py" >nul
echo.
echo   [首次运行] 已从模板生成 config.py
echo.
echo   请打开下面的文件，填入你的信息：
echo     %SRC%\config.py
echo.
echo   必填项：
echo     TELEGRAM_BOT_TOKEN  - 从 @BotFather 获取
echo     BOT_OWNER_ID        - 从 @userinfobot 获取
echo     PROXY_URL           - 你的代理地址（国内必填）
echo.
pause
exit /b 0

:config_exists
rem 用 findstr 而不是 find（find 会被 Git 的 Unix find 遮蔽）
findstr /C:"YOUR_TELEGRAM_BOT_TOKEN" "%SRC%\config.py" >nul 2>&1
if not errorlevel 1 (
    echo.
    echo   [错误] config.py 里还没有填 Telegram Bot Token
    echo.
    echo   请编辑：%SRC%\config.py
    echo   把 TELEGRAM_BOT_TOKEN 换成 @BotFather 给你的那串字符
    echo.
    pause
    exit /b 1
)

findstr /C:"CHANGE_ME_TO_A_RANDOM_SECRET" "%SRC%\config.py" >nul 2>&1
if not errorlevel 1 (
    echo         [提示] CALLBACK_SECRET 还是默认值
    echo                发卡平台回调服务不会启动（这是安全设计）
    echo                不接发卡平台的话可以忽略
)
echo   [2/5] 配置文件  OK

rem ============================================================
rem  3. 安装依赖
rem ============================================================
echo   [3/5] 检查依赖...

"%PY%" -c "import telegram, aiohttp, psutil, yt_dlp" >nul 2>&1
if not errorlevel 1 (
    echo   [3/5] 依赖  OK
    goto :ffmpeg_check
)

echo         首次运行，正在安装依赖（需要联网，请稍候）...
"%PY%" -m pip install --disable-pip-version-check -q -r "%SRC%\requirements.txt"
if errorlevel 1 (
    echo.
    echo   [错误] 依赖安装失败
    echo.
    echo   如果是网络问题，可以试试国内镜像：
    echo     "%PY%" -m pip install -r "%SRC%\requirements.txt" -i https://pypi.tuna.tsinghua.edu.cn/simple
    echo.
    pause
    exit /b 1
)
echo         依赖安装完成

rem ============================================================
rem  4. 检查 ffmpeg（视频解析需要，可选）
rem ============================================================
:ffmpeg_check
where ffmpeg >nul 2>&1
if errorlevel 1 (
    echo   [4/5] ffmpeg  未安装
    echo         -^> 视频只能看封面图，图片解析不受影响
    echo         -^> 想看懂视频请运行: winget install Gyan.FFmpeg
) else (
    echo   [4/5] ffmpeg  OK
)

rem ============================================================
rem  5. 启动
rem ============================================================
echo   [5/5] 启动中...
echo.

if "%MODE%"=="background" goto :run_background

echo   前台模式：按 Ctrl+C 可以停止
echo.
echo   --------------------------------------------
echo.
%PS% "%HELPER%" run "%PY%" "%SRC%\main.py" "%LOGDIR%"
echo.
echo   --------------------------------------------
echo   机器人已停止
echo.
pause
exit /b 0

rem ============================================================
rem  后台启动
rem ============================================================
:run_background
echo   后台模式：关掉窗口也会继续运行
echo   停止命令：start.bat --stop
echo.
%PS% "%HELPER%" bg "%PY%" "%SRC%\main.py" "%LOGDIR%"
echo.
if errorlevel 1 (
    echo   启动没有成功，请查看上面输出的日志路径
)
echo.
pause
exit /b 0

rem ============================================================
rem  停止
rem ============================================================
:do_stop
echo   正在停止机器人...
echo.
%PS% "%HELPER%" stop "%PIDFILE%"
echo.
pause
exit /b 0

rem ============================================================
rem  状态
rem ============================================================
:do_status
echo   运行状态：
echo.
%PS% "%HELPER%" status "%PIDFILE%" "%SRC%"
echo.
if exist "%LOGDIR%" (
    echo   最近日志：
    for /f "delims=" %%F in ('dir /b /o-d "%LOGDIR%\*.log" 2^>nul') do (
        echo     %%F
        goto :status_end
    )
)
:status_end
echo.
pause
exit /b 0
