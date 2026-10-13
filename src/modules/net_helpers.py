"""
🌐 网络辅助 - 共享的系统代理探测逻辑

为什么需要这个模块？
────────────────────
本项目里有两个地方要发 HTTP 请求：

  1. `main.py`  -> python-telegram-bot（底层 httpx）访问 Telegram API
  2. 各业务模块 -> aiohttp 访问 DeepSeek API

**这两个库默认都不读系统代理**：

  • httpx  ：默认 trust_env 行为与 requests 不同，不自动用系统代理
  • aiohttp：默认 trust_env=False，完全无视 HTTP_PROXY 环境变量

结果就是：命令行 `curl` / PowerShell 能访问 Telegram，机器人却超时。
所以代理必须显式传进去，探测逻辑放在这里共用。

`media_parser.py` 和 `deepseek_chat.py` 都从这里取代理设置~
"""
import logging
import socket
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# 占位值：配置里留空时用它表示"没有显式配置代理"
_PLACEHOLDERS = {"", "YOUR_PROXY_URL", "NONE", "null"}

# 探测结果缓存，避免每条消息都去读一次注册表
_cached_proxy = None
_cache_done = False


def detect_system_proxy() -> str:
    """
    读取 Windows 系统代理设置~

    Returns:
        str: 形如 "http://127.0.0.1:7897" 的代理地址；没配则返回空字符串
    """
    try:
        import winreg
    except ImportError:
        # 非 Windows 平台，退回环境变量
        import os
        for var in ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy"):
            value = os.environ.get(var)
            if value:
                return value
        return ""

    try:
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            enabled = 0
            try:
                enabled, _ = winreg.QueryValueEx(key, "ProxyEnable")
            except FileNotFoundError:
                pass

            try:
                server, _ = winreg.QueryValueEx(key, "ProxyServer")
            except FileNotFoundError:
                server = ""

            if not server:
                return ""

            server = str(server).strip()

            # 多协议写法，例如 "http=127.0.0.1:7897;https=127.0.0.1:7897"
            if "=" in server:
                parts = {}
                for chunk in server.split(";"):
                    if "=" in chunk:
                        proto, _, addr = chunk.partition("=")
                        parts[proto.strip().lower()] = addr.strip()
                server = parts.get("https") or parts.get("http") or ""
                if not server:
                    return ""

            if not server.lower().startswith(("http://", "https://", "socks")):
                server = f"http://{server}"

            # 开关是关的：可能是 TUN 模式（端口还活着），也可能是陈旧残留配置。
            # 不能盲信，先探测端口是否真的在监听，否则会把请求导向一个死代理。
            if not enabled and not is_proxy_alive(server):
                return ""

            return server
    except Exception:
        return ""


def is_proxy_alive(proxy_url: str) -> bool:
    """
    探测代理端口是否真的在监听~

    注册表里可能留着早就关掉的代理软件地址，
    盲目使用会让请求卡在连不上的代理上（比直连还糟）。
    """
    try:
        parsed = urlparse(proxy_url)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
    except Exception:
        return False

    try:
        with socket.create_connection((host, port), timeout=1.5):
            return True
    except OSError:
        return False


def get_proxy_url(use_cache: bool = True) -> str:
    """
    拿到当前应该使用的代理地址~

    优先级：
      1. config.py 里显式配置的 PROXY_URL
      2. 系统代理（当 PROXY_AUTO_DETECT 为 True 时）

    Args:
        use_cache: 是否使用缓存结果（默认 True）。配置热更新后想重新探测就传 False

    Returns:
        str: 代理地址，没有则返回空字符串
    """
    global _cached_proxy, _cache_done

    if use_cache and _cache_done:
        return _cached_proxy

    proxy = ""

    try:
        from config import PROXY_URL, PROXY_AUTO_DETECT
    except ImportError:
        # 老版本 config.py 没有这两项，直接走系统探测
        PROXY_URL, PROXY_AUTO_DETECT = "", True

    explicit = (PROXY_URL or "").strip()
    if explicit and explicit not in _PLACEHOLDERS:
        proxy = explicit
    elif PROXY_AUTO_DETECT:
        proxy = detect_system_proxy()

    _cached_proxy = proxy
    _cache_done = True
    return proxy


def reset_cache():
    """清掉代理探测缓存~（配置改了以后可以调用）"""
    global _cached_proxy, _cache_done
    _cached_proxy = None
    _cache_done = False
