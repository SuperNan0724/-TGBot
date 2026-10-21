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
import os
import re
import shutil
import socket
import time
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# 占位值：配置里留空时用它表示"没有显式配置代理"
_PLACEHOLDERS = {"", "YOUR_PROXY_URL", "NONE", "null"}

# 探测结果缓存，避免每条消息都去读一次注册表。
# ⚠️ 但**不能永久缓存**：代理通常在机器人启动之后才开，
#    永久缓存会让新开的代理永远不生效（症状是"我明明开了代理，机器人还是连不上"）。
#    所以给缓存加个 TTL，过期后重新探测一次。
_CACHE_TTL_SECONDS = 90

_cached_proxy = None
_cache_done = False
_cache_time = 0.0


def _now() -> float:
    """
    取当前单调时钟（秒）~

    单独抽成一个函数是为了让测试能替换时钟，验证 TTL 过期逻辑，
    不影响真实的 time.monotonic()。
    """
    return time.monotonic()


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

    缓存行为：
        探测结果会缓存 **90 秒**（_CACHE_TTL_SECONDS），过期后自动重新探测。
        这样"先启动机器人、后开代理"也能在 90 秒内生效，不用重启机器人。
        想让它立刻重新探测（比如刚改了配置），传 use_cache=False
        或调用 reset_cache()。

    Args:
        use_cache: 是否使用缓存结果（默认 True）。配置热更新后想重新探测就传 False

    Returns:
        str: 代理地址，没有则返回空字符串
    """
    global _cached_proxy, _cache_done, _cache_time

    if use_cache and _cache_done and (_now() - _cache_time) < _CACHE_TTL_SECONDS:
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
    _cache_time = _now()
    return proxy


def reset_cache():
    """清掉代理探测缓存~（配置改了以后可以调用）"""
    global _cached_proxy, _cache_done, _cache_time
    _cached_proxy = None
    _cache_done = False
    _cache_time = 0.0


def _expand_env_path(raw_path: str) -> str:
    """
    展开 Windows 注册表里那种 %VAR% 写法~（不依赖真实环境变量）

    注册表里的 PATH 常写成 %SystemRoot%\\system32;... 这种形式，
    而 os.path.expandvars 只认当前进程的环境变量，所以自己解析一遍。
    """
    def repl(match):
        name = match.group(1) or match.group(2)
        return os.environ.get(name, match.group(0))

    return re.sub(r"%([^%]+)%", repl, raw_path)


def _user_path_dirs() -> list:
    """
    读取「用户级 PATH」里的目录~

    为什么要单独读注册表？
      如果机器人是在装了 ffmpeg **之前**启动的终端里运行的，
      进程继承的 PATH 还是旧的，shutil.which 就找不到 ffmpeg。
      直接读注册表能拿到最新的值，避免用户被这个坑住。
    """
    dirs = []
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
            try:
                raw, _ = winreg.QueryValueEx(key, "Path")
            except FileNotFoundError:
                raw = ""
        if raw:
            for part in str(raw).split(";"):
                part = _expand_env_path(part.strip())
                if part and os.path.isdir(part):
                    dirs.append(part)
    except ImportError:
        # 非 Windows 平台没有 winreg，正常情况
        pass
    except Exception as e:
        # 不要把异常吞得无声无息——否则排查起来极其痛苦
        logger.debug(f"读取用户级 PATH 失败: {e}")
    return dirs


def find_ffmpeg() -> str:
    """
    定位 ffmpeg 可执行文件~

    顺序：
      1. config.py 里显式配置的 FFMPEG_PATH（目录或完整 exe 路径）
      2. 当前进程 PATH
      3. 用户级 PATH（注册表，解决"装了但当前终端不知道"的问题）
      4. 常见安装位置

    Returns:
        str: ffmpeg 可执行文件路径；找不到返回空字符串
    """
    exe_name = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"

    def _check(candidate: str) -> str:
        if not candidate:
            return ""
        # 直接给了 exe
        if os.path.isfile(candidate):
            return candidate
        # 给了目录
        candidate_exe = os.path.join(candidate, exe_name)
        if os.path.isfile(candidate_exe):
            return candidate_exe
        return ""

    # 1. 显式配置
    try:
        from config import FFMPEG_PATH
        found = _check((FFMPEG_PATH or "").strip())
        if found:
            return found
    except ImportError:
        pass

    # 2. 当前 PATH
    found = shutil.which("ffmpeg")
    if found:
        return found

    # 3. 用户级 PATH（注册表里的最新值）
    for d in _user_path_dirs():
        found = _check(d)
        if found:
            return found

    # 4. 常见安装位置
    common = [
        r"C:\ffmpeg\bin",
        r"C:\Program Files\ffmpeg\bin",
        os.path.expanduser(r"~\ffmpeg\bin"),
        os.path.expanduser(r"~\scoop\shims"),
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Links"),
    ]
    for d in common:
        found = _check(d)
        if found:
            return found

    return ""


def has_ffmpeg() -> bool:
    """是否可用 ffmpeg~"""
    return bool(find_ffmpeg())


def apply_thinking_options(payload: dict) -> dict:
    """
    按配置给 DeepSeek 请求体加上"思考模式"相关参数~

    为什么需要这个？
    ────────────────
    deepseek-flash 默认**开启**思考模式且强度为 high，回答前会先输出一大段
    思维链，这段内容同样计费。实测同一张图的看图回答：

        思考开启 : 4.1 秒 / 517 completion tokens
        思考关闭 : 1.3 秒 /  34 completion tokens   ← 回答质量没差别

    更麻烦的是：思考会把 max_tokens 额度吃光，导致 content 为空，
    而推理内容反倒泄漏出来被当成"正文"发给用户（用户会看到
    「让我再想想」「要确保每句最多20字」这种模型内部独白）。

    所以描述图片、写简介这类任务一律关闭思考。

    注意：思考模式下 **temperature 不生效**（官方明确说明，传了不报错也没用），
    所以关闭思考后 temperature 才真正起作用。
    """
    try:
        from config import DISABLE_THINKING, REASONING_EFFORT
    except ImportError:
        DISABLE_THINKING, REASONING_EFFORT = True, "low"

    if DISABLE_THINKING:
        payload["thinking"] = {"type": "disabled"}
    else:
        payload["thinking"] = {"type": "enabled"}
        if REASONING_EFFORT:
            payload["reasoning_effort"] = REASONING_EFFORT
    return payload
