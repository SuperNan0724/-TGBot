@echo off
setlocal EnableDelayedExpansion
title 配置抖音 Cookie

rem ============================================================
rem  抖音 Cookie 配置工具
rem
rem  用法：双击本文件，按提示粘贴 cookie
rem
rem  【维护须知】本文件必须保持 GBK 编码 + CRLF 行尾！
rem    cmd.exe 按字节解析 .bat，且不要在里面调 chcp。
rem ============================================================

cd /d "%~dp0"

echo.
echo   ============================================
echo      抖音 Cookie 配置工具
echo   ============================================
echo.
echo   请先在 Edge/Chrome 里登录抖音，然后按下面步骤拿 cookie：
echo.
echo     1. 打开 https://www.douyin.com 并登录
echo     2. 按 F12 打开开发者工具
echo     3. 切到 Network（网络）标签，刷新页面
echo     4. 点任意一个 douyin.com 的请求
echo     5. 在 Request Headers 里找到 Cookie: 那一行
echo     6. 复制它整行的值（不含开头的 "Cookie: "）
echo.
echo   准备好后按任意键继续，然后粘贴 cookie 并回车。
echo.
pause >nul

if not exist ".venv\Scripts\python.exe" (
    echo   [错误] 找不到 .venv\Scripts\python.exe
    echo          请先在项目根目录运行 start.bat 初始化环境。
    echo.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" "setup_douyin_cookie.py"
set "RC=%ERRORLEVEL%"

echo.
if "%RC%"=="0" (
    echo   配置完成。可以给机器人发抖音链接试试了。
) else if "%RC%"=="2" (
    echo   cookie 已保存，但实测未通过 —— 请看上面的原因。
) else (
    echo   未完成，请按上面的提示修正后重试。
)
echo.
pause
exit /b %RC%
