"""
🧩 第三方解析模块 —— 补 yt-dlp 的短板

为什么需要它？
──────────────
yt-dlp 覆盖上千站点，但抖音/快手/小红书这类国内平台有强反爬，它的提取器
取不到播放流（yt-dlp 官方 issue 也承认 Douyin extractor 目前不可用）。
这些平台改用第三方解析服务。

为什么不用 KuKuTool？
────────────────────
扒过它的前端：调用链是「先拿 authKey → AES 加密 payload（带 IV）→
POST /api/parse」，而且依赖 same-origin Cookie。直接明文请求会得到：

    HTTP 426  {"reason":"parse_v2_disabled","primaryVersion":"3"}

要接入必须完整复现它的客户端加密，属于**逆向私有接口** —— 对方改个参数
就失效，没法保证长期可用。所以改用返回标准 JSON 的公开接口。

设计要点
────────
响应归一化用**递归找键名**而不是硬编码路径：
  不同服务返回结构差别很大（data.video.play / data.play / data.video_url…），
  写死路径的话换个服务就得改代码。递归找键名可以让配置里换个 URL 就能用。
"""
import json
import logging
from urllib.parse import quote

import aiohttp

from config import (
    LINK_THIRD_PARTY_ENABLED, LINK_THIRD_PARTY_API,
    LINK_THIRD_PARTY_PLATFORMS, LINK_THIRD_PARTY_TIMEOUT,
)
from .net_helpers import get_proxy_url

logger = logging.getLogger(__name__)

# 键名候选表：不同解析服务用的字段名不一样，这里列出常见的几种。
# 顺序有意义，靠前的优先。
# ⚠️ 而且要注意：同名键的值可能是**字典**而不是字符串。
#    比如抖音接口的 "author" 是 {unique_id, nickname, ...}，
#    所以 nickname 必须排在 author 前面，否则会返回整个对象。
VIDEO_URL_KEYS = ("play", "video_url", "videoUrl", "nwm_video_url", "hdplay",
                  "play_addr", "download_url", "url")
COVER_KEYS = ("cover", "origin_cover", "dynamic_cover", "poster", "thumbnail",
              "cover_url")
TITLE_KEYS = ("title", "desc", "description", "text")
AUTHOR_KEYS = ("nickname", "author_name", "uploader", "unique_id", "name", "author")
DURATION_KEYS = ("duration", "duration_ms", "length")
MUSIC_KEYS = ("music", "music_info", "audio")
IMAGES_KEYS = ("images", "image_list", "imgs", "image_urls")


def _is_usable_url(value) -> bool:
    """判断是不是一个能直接请求的 http(s) 地址~"""
    return isinstance(value, str) and value.startswith(("http://", "https://"))


def _deep_find_text(obj, keys, max_depth=8):
    """
    按 key 递归找**字符串**值~

    TITLE_KEYS / AUTHOR_KEYS 这些语义上都是文本字段，但同名键的值可能是
    字典 —— 抖音接口的 "author" 就是 {unique_id, nickname, ...}。
    曾经想用一张 STRING_ONLY_KEYS 名单逐个标记，结果漏了 "author" 本身，
    导致返回整个字典（踩过）。所以这里不靠名单，直接**只接受字符串**：
    非字符串就继续往下找，反正这些字段本来就该是文本。
    """
    if max_depth <= 0 or obj is None:
        return None
    if isinstance(obj, dict):
        # 第一轮：直接命中且是字符串就返回
        for k in keys:
            v = obj.get(k) if k in obj else None
            if isinstance(v, str) and v.strip():
                return v
        # 第二轮：在候选键的值里继续找
        for k in keys:
            if k in obj and isinstance(obj[k], (dict, list)):
                found = _deep_find_text(obj[k], keys, max_depth - 1)
                if found:
                    return found
        # 第三轮：兜底翻所有子值（数据可能被包在别的键下面）
        for v in obj.values():
            if isinstance(v, (dict, list)):
                found = _deep_find_text(v, keys, max_depth - 1)
                if found:
                    return found
    elif isinstance(obj, list):
        for item in obj[:5]:
            found = _deep_find_text(item, keys, max_depth - 1)
            if found:
                return found
    return None


def _deep_find(obj, keys, max_depth=8):
    """
    在嵌套结构里按**键名**递归查找，返回第一个命中的非空值~

    用于 URL、时长、图集这类值可能是字符串也可能是列表/字典的字段。
    找纯文本字段请用 _deep_find_text()。
    """
    if max_depth <= 0 or obj is None:
        return None
    if isinstance(obj, dict):
        for k in keys:
            if k in obj:
                v = obj[k]
                if v not in (None, "", [], {}):
                    return v
        for v in obj.values():
            found = _deep_find(v, keys, max_depth - 1)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for item in obj[:5]:
            found = _deep_find(item, keys, max_depth - 1)
            if found is not None:
                return found
    return None


def _deep_find_url(obj, keys, max_depth=8):
    """
    递归找第一个像 URL 的值~

    URL 的存放形态比文本字段更杂，实测见过这些：
      "play": "https://..."
      "play_addr": {"url_list": ["https://...", ...]}
      "video": {"play_addr": {"url_list": [{"url": "https://..."}]}}
    所以命中后的值可能是字符串、字符串列表，也可能是嵌套对象，都要能钻进去。
    """
    if max_depth <= 0 or obj is None:
        return None

    if isinstance(obj, dict):
        # 先看候选键
        for k in keys:
            if k in obj:
                found = _extract_url_from_value(obj[k], max_depth - 1)
                if found:
                    return found
        # 再兜底翻所有子值
        for v in obj.values():
            found = _deep_find_url(v, keys, max_depth - 1)
            if found:
                return found
    elif isinstance(obj, list):
        for item in obj[:5]:
            found = _deep_find_url(item, keys, max_depth - 1)
            if found:
                return found
    return None


def _extract_url_from_value(value, max_depth=6):
    """从一个值里掏出 http(s) 地址（可能是字符串/列表/嵌套对象）~"""
    if max_depth <= 0 or value is None:
        return None
    if _is_usable_url(value):
        return value
    if isinstance(value, str):
        return None
    if isinstance(value, list):
        for item in value:
            found = _extract_url_from_value(item, max_depth - 1)
            if found:
                return found
        return None
    if isinstance(value, dict):
        # 优先看常见的 url 字段名
        for k in ("url", "url_list", "play_url", "src", "uri"):
            if k in value:
                found = _extract_url_from_value(value[k], max_depth - 1)
                if found:
                    return found
        for v in value.values():
            found = _extract_url_from_value(v, max_depth - 1)
            if found:
                return found
    return None


def _fk(obj, key, default=None):
    """
    按 key 取，允许 key 的第一个字母大写（有些服务返回大驼峰）~
    例如 _fk(info, "cover") 也能取到 "Cover"
    """
    if not isinstance(obj, dict):
        return default
    for k in (key, key.capitalize(), key.upper()):
        if k in obj and obj[k] not in (None, "", [], {}):
            return obj[k]
    return default


def normalize(raw: dict) -> dict:
    """
    把各家服务五花八门的响应归一化成统一结构~

    Returns:
        dict: {
            "video_url": str | None,   # 视频文件直链
            "images": list,            # 图集直链（图文作品）
            "cover": str | None,
            "title": str,
            "author": str,
            "duration": int | None,    # 秒
            "music": str | None,
        }
    """
    # 大多数服务把数据塞在 data 里
    payload = raw.get("data") if isinstance(raw.get("data"), (dict, list)) else raw
    if isinstance(payload, list) and payload:
        payload = payload[0]

    title = _deep_find_text(payload, TITLE_KEYS) or ""
    author = _deep_find_text(payload, AUTHOR_KEYS) or ""
    duration = _deep_find(payload, DURATION_KEYS)

    # 时长可能是毫秒
    try:
        duration = int(float(duration)) if duration is not None else None
        if duration and duration > 10000:
            duration = duration // 1000
    except (TypeError, ValueError):
        duration = None

    # 视频直链：优先无水印
    video_url = _deep_find_url(payload, ("play", "video_url", "videoUrl",
                                         "nwm_video_url", "hdplay"))
    if not video_url:
        video_url = _deep_find_url(payload, ("wmplay", "download_url", "play_addr"))

    # 图集（抖音的"图文作品"）
    images = []
    imgs_raw = _deep_find(payload, IMAGES_KEYS)
    if isinstance(imgs_raw, list):
        for item in imgs_raw:
            if _is_usable_url(item):
                images.append(item)
            elif isinstance(item, dict):
                u = _deep_find_url(item, ("url", "url_list", "origin", "image"))
                if u:
                    images.append(u)

    cover = _deep_find_url(payload, COVER_KEYS)
    music = _deep_find_url(payload, MUSIC_KEYS)

    if isinstance(title, str):
        title = title.strip()[:200]
    if isinstance(author, str):
        author = author.strip()[:80]

    return {
        "video_url": video_url,
        "images": images,
        "cover": cover,
        "title": title,
        "author": author,
        "duration": duration,
        "music": music,
    }


def should_use(platform_label: str) -> bool:
    """判断这个平台要不要走第三方接口~"""
    if not LINK_THIRD_PARTY_ENABLED:
        return False
    return platform_label in LINK_THIRD_PARTY_PLATFORMS


async def parse(url: str):
    """
    调用第三方接口解析链接~

    Returns:
        dict: normalize() 的结果；失败返回 None
    """
    if not LINK_THIRD_PARTY_ENABLED:
        return None
    if not LINK_THIRD_PARTY_API or "{url}" not in LINK_THIRD_PARTY_API:
        logger.warning(f"LINK_THIRD_PARTY_API 配置有误（缺少 {{url}} 占位符）: "
                       f"{LINK_THIRD_PARTY_API!r}")
        return None

    api_url = LINK_THIRD_PARTY_API.format(url=quote(url, safe=""))
    proxy = get_proxy_url() or None
    headers = {
        "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/126.0 Safari/537.36"),
        "Accept": "application/json, text/plain, */*",
    }
    timeout = aiohttp.ClientTimeout(total=LINK_THIRD_PARTY_TIMEOUT, connect=15)

    try:
        async with aiohttp.ClientSession(timeout=timeout, trust_env=True) as session:
            async with session.get(api_url, headers=headers, proxy=proxy) as resp:
                if resp.status != 200:
                    logger.warning(f"第三方接口返回 HTTP {resp.status}")
                    return None
                raw = await resp.json(content_type=None)
    except aiohttp.ClientError as e:
        logger.warning(f"第三方接口请求失败: {type(e).__name__}: {e}")
        return None
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning(f"第三方接口返回的不是合法 JSON: {e}")
        return None
    except Exception as e:
        logger.warning(f"第三方接口异常: {type(e).__name__}: {e}")
        return None

    # 接口自身的错误码（各家不一样，常见的 code/status/ret）
    if isinstance(raw, dict):
        code = raw.get("code", raw.get("status", raw.get("ret")))
        if code not in (None, 0, "0", 200, "200", True):
            msg = raw.get("msg") or raw.get("message") or raw.get("error") or ""
            logger.info(f"第三方接口返回错误码 {code}: {msg}")
            # 把接口的原始提示带出去，方便用户判断是链接失效还是服务挂了
            raise ThirdPartyError(str(msg) or f"接口返回 code={code}")

    result = normalize(raw)
    if not result.get("video_url") and not result.get("images"):
        logger.info("第三方接口没有返回可用的媒体地址")
        raise ThirdPartyError("接口没有返回媒体地址（可能是链接失效或内容受限）")

    logger.info(
        f"🧩 第三方解析成功: 视频={'有' if result['video_url'] else '无'} "
        f"图集={len(result['images'])} 张 标题={result['title'][:40]!r}"
    )
    return result


class ThirdPartyError(Exception):
    """第三方接口明确返回了错误（区别于网络故障）"""
