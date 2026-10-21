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
import re
from urllib.parse import quote

import aiohttp

from config import (
    LINK_THIRD_PARTY_ENABLED, LINK_THIRD_PARTY_API,
    LINK_THIRD_PARTY_PLATFORMS, LINK_THIRD_PARTY_TIMEOUT,
)
from .net_helpers import get_proxy_url_async

logger = logging.getLogger(__name__)

# 响应体上限~
# 对方返回一个 500MB 的 JSON，"先读进来再判断"就已经 OOM 了，所以必须
# 边读边计数、超了立刻放弃。JSON 接口给 4MB（正常响应只有几百字节），
# 抖音的 HTML 页面给 4MB（分享页一般 100~300KB）。
MAX_RESPONSE_BYTES = 4 * 1024 * 1024
MAX_HTML_BYTES = 4 * 1024 * 1024

# 接口超时的兜底值 / 下限（配置被写成 None、0、"30s" 时用默认值）
_DEFAULT_TIMEOUT = 30
_MIN_TIMEOUT = 5


class ResponseTooLarge(Exception):
    """对方返回的响应体超过上限"""


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


def _safe_int(value, default: int) -> int:
    """把配置值安全地转成 int~（手写成 "30s" / None 时回落到默认值）"""
    if isinstance(value, bool):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _client_timeout() -> aiohttp.ClientTimeout:
    """
    构造带总超时的 ClientTimeout~

    `total` 覆盖**整个请求**（连接 + 等响应头 + 读完 body），不是只管连接；
    只设 connect 的话，对方慢慢吐 body 可以一直挂着。
    配置被改成 0/负数/字符串时 aiohttp 会直接抛异常（每次请求都超时），
    所以这里先归一成合理的整数。
    """
    total = max(_MIN_TIMEOUT, _safe_int(LINK_THIRD_PARTY_TIMEOUT, _DEFAULT_TIMEOUT))
    return aiohttp.ClientTimeout(total=total, connect=min(15, total))


async def _read_body_capped(resp, max_bytes: int = MAX_RESPONSE_BYTES) -> bytes:
    """
    读完响应体，超过上限立刻放弃（抛 ResponseTooLarge）~

    为什么不能直接 `await resp.text()` / `await resp.json()`？
      aiohttp 只会按"耗时"超时，不管"体积"。对方返回一个巨大的 JSON 时，
      这行代码会先把几 GB 读进内存，然后才轮到我们判断 —— 结果是 OOM。
      Content-Length 也不一定给（chunked），所以必须按**实际读到的字节数**卡。
    """
    length = resp.headers.get("Content-Length")
    if length and length.isdigit() and int(length) > max_bytes:
        raise ResponseTooLarge(f"Content-Length {int(length)} 超过上限 {max_bytes}")

    chunks = []
    total = 0
    async for chunk in resp.content.iter_chunked(65536):
        total += len(chunk)
        if total > max_bytes:
            # 已经读到的部分直接丢掉，别继续往内存里堆
            raise ResponseTooLarge(f"响应体超过上限 {max_bytes} 字节")
        chunks.append(chunk)
    return b"".join(chunks)


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
    # 大多数服务把数据塞在 data 里。
    # 但有的服务直接返回**顶层数组**（ [{"play": "..."}] ），甚至返回字符串/数字。
    # 原来这里无条件 raw.get("data")，遇到数组就抛 AttributeError，
    # 整条第三方解析路径直接崩掉（上层只看到一句"解析异常"）。
    if isinstance(raw, dict):
        payload = raw.get("data") if isinstance(raw.get("data"), (dict, list)) else raw
    elif isinstance(raw, list):
        payload = raw
    else:
        logger.info(f"第三方接口返回的结构无法解析（{type(raw).__name__}），按空结果处理")
        payload = {}
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


def _is_success_code(code) -> bool:
    """
    判断接口返回的业务码是不是"成功"~

    为什么不能写成 `code not in (None, 0, "0", 200, "200", True)`？
      Python 里 `1 == True`、`False == 0`，元组包含判断走的是 ==，
      所以真正的错误码 **1 会命中 True** 被当成成功处理 —— 接口给的
      错误提示（msg）就这么丢了，上层只剩一句含糊的"接口没有返回媒体地址"，
      用户根本看不出是链接失效还是服务挂了。
    这里按**类型**分支判断，不让 bool 和 int 隐式相等。

    ⚠️ None 一律算**失败**。
      调用方只应该在"**键根本不存在**"时跳过判断（用 _MISSING 哨兵），
      而不是把 None 当"没有错误码"。实测有的服务失败时返回
          {"code": null, "msg": "失败"}
      —— 以前它被当成成功，于是 msg 被丢掉、继续拿残缺的 data 去发媒体。
    """
    if code is None:
        return False
    if isinstance(code, bool):
        # bool 是 int 的子类，这个分支必须排在 int 前面
        return code is True
    if isinstance(code, (int, float)):
        return code in (0, 200)
    if isinstance(code, str):
        return code.strip() in ("", "0", "200")
    return False


# 哨兵：区分"键不存在"（跳过业务码检查）和"键存在但值是 null"（算失败）
_MISSING = object()


async def parse(url: str, platform_label: str = ""):
    """
    解析链接：抖音走直连（带 Cookie），其它走第三方接口~

    Returns:
        dict: normalize() 的结果；失败返回 None
    """
    # ── 抖音：优先直连（第三方接口对抖音基本无效，实测返回 Url parsing is failed）──
    if "douyin" in url.lower() or platform_label == "抖音":
        try:
            result = await parse_douyin(url)
            if result:
                return result
            logger.info("抖音直连未成功，回退到第三方接口")
        except ThirdPartyError:
            raise
        except Exception as e:
            logger.warning(f"抖音直连异常: {type(e).__name__}: {str(e)[:120]}")

    if not LINK_THIRD_PARTY_ENABLED:
        return None
    if not LINK_THIRD_PARTY_API or "{url}" not in LINK_THIRD_PARTY_API:
        logger.warning(f"LINK_THIRD_PARTY_API 配置有误（缺少 {{url}} 占位符）: "
                       f"{LINK_THIRD_PARTY_API!r}")
        return None

    api_url = LINK_THIRD_PARTY_API.format(url=quote(url, safe=""))
    # async 版本：直接调 get_proxy_url() 重新探测时会同步阻塞 1.5 秒
    proxy = await get_proxy_url_async() or None
    headers = {
        "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/126.0 Safari/537.36"),
        "Accept": "application/json, text/plain, */*",
    }

    try:
        async with aiohttp.ClientSession(timeout=_client_timeout(), trust_env=True) as session:
            async with session.get(api_url, headers=headers, proxy=proxy) as resp:
                if resp.status != 200:
                    logger.warning(f"第三方接口返回 HTTP {resp.status}")
                    return None
                # 体积上限在这里生效：超了直接放弃，不会把巨大 JSON 读进内存
                body = await _read_body_capped(resp)
    except ResponseTooLarge as e:
        logger.warning(f"第三方接口响应过大，已拒绝: {e}")
        return None
    except aiohttp.ClientError as e:
        logger.warning(f"第三方接口请求失败: {type(e).__name__}: {e}")
        return None
    except Exception as e:
        logger.warning(f"第三方接口异常: {type(e).__name__}: {e}")
        return None

    # 非 JSON 响应（风控页/HTML 错误页）在这里被挡掉，不会再抛到上层
    try:
        raw = json.loads(body)
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning(f"第三方接口返回的不是合法 JSON: {e}")
        return None

    # 接口自身的错误码（各家不一样，常见的 code/status/ret）
    if isinstance(raw, dict):
        # 用哨兵而不是默认 None：键不存在 = 跳过检查，
        # 键存在但值是 null = 明确失败（`{"code": null, "msg": "失败"}`）
        code = raw.get("code", raw.get("status", raw.get("ret", _MISSING)))
        if code is not _MISSING and not _is_success_code(code):
            msg = raw.get("msg") or raw.get("message") or raw.get("error") or ""
            logger.info(f"第三方接口返回错误码 {code!r}: {msg}")
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


# ══════════════════════════════════════════════
#  抖音直连解析（带 Cookie）
# ══════════════════════════════════════════════
#
# 为什么不只用第三方接口？
#   实测第三方接口对抖音也返回 "Url parsing is failed!"，因为抖音拦的是
#   发起请求的**设备指纹**，第三方服务同样过不去。
#
# 抖音的风控叫 ArgusSecurityPlugin，不带 cookie 请求它的 API 会得到：
#     HTTP 403  "Blocked by ArgusSecurityPlugin Uifid Not Found"
# 它要的是 Uifid 这类设备指纹 —— 纯 HTTP 请求伪造不出来，必须用真实浏览器
# 登录后拿到的 cookie。

DOUYIN_MOBILE_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
)
AWEME_ID_RE = re.compile(r"/(?:video|note|share/video|share/note)/(\d{6,25})")


def _douyin_cookie() -> str:
    """取配置里的抖音 cookie~"""
    try:
        from config import DOUYIN_COOKIE, DOUYIN_USE_COOKIE
    except ImportError:
        return ""
    if not DOUYIN_USE_COOKIE:
        return ""
    return (DOUYIN_COOKIE or "").strip()


def _douyin_headers() -> dict:
    """构造抖音请求头（带 cookie）~"""
    headers = {
        "User-Agent": DOUYIN_MOBILE_UA,
        "Referer": "https://www.douyin.com/",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9",
    }
    cookie = _douyin_cookie()
    if cookie:
        headers["Cookie"] = cookie
    return headers


async def _douyin_resolve_aweme_id(url: str):
    """
    把分享短链展开，取出视频 ID（aweme_id）~

    短链会 302 到形如 https://www.douyin.com/video/7123456789012345678
    """
    headers = _douyin_headers()
    proxy = await get_proxy_url_async() or None
    try:
        async with aiohttp.ClientSession(timeout=_client_timeout(), trust_env=True) as session:
            async with session.get(url, headers=headers, proxy=proxy,
                                   allow_redirects=True) as resp:
                final = str(resp.url)
                # 展开后的 URL 里通常就带 ID
                m = AWEME_ID_RE.search(final)
                if m:
                    return m.group(1)

                # 没带 ID 就翻页面源码找（页面可能几百 KB，同样卡体积上限）
                body = (await _read_body_capped(resp, MAX_HTML_BYTES)).decode("utf-8", "replace")
                m = AWEME_ID_RE.search(body)
                if m:
                    return m.group(1)
                # 有些页面把 ID 放在 aweme_id= 或 itemId=
                m = re.search(r'(?:aweme_id|itemId|item_id)["\']?\s*[:=]\s*["\']?(\d{6,25})', body)
                if m:
                    return m.group(1)

                logger.info(f"抖音短链展开后没找到视频ID，最终URL={final[:120]}")
                return None
    except Exception as e:
        logger.warning(f"抖音短链展开失败: {type(e).__name__}: {str(e)[:120]}")
        return None


async def _douyin_fetch_detail(aweme_id: str):
    """
    调抖音详情接口拿数据~

    需要 cookie 才能过 ArgusSecurityPlugin 风控。
    """
    cookie = _douyin_cookie()
    if not cookie:
        logger.info("未配置 DOUYIN_COOKIE，抖音详情接口大概率会被风控拦截")
        return None

    api = ("https://www.douyin.com/aweme/v1/web/aweme/detail/"
           f"?aweme_id={aweme_id}&device_platform=webapp&aid=6383&channel=channel_pc_web")
    headers = _douyin_headers()
    headers["Accept"] = "application/json, text/plain, */*"
    proxy = await get_proxy_url_async() or None

    try:
        async with aiohttp.ClientSession(timeout=_client_timeout(), trust_env=True) as session:
            async with session.get(api, headers=headers, proxy=proxy) as resp:
                if resp.status != 200:
                    logger.warning(f"抖音详情接口 HTTP {resp.status}")
                    return None
                body = await _read_body_capped(resp, MAX_RESPONSE_BYTES)
                text = body.decode("utf-8", "replace")
                if "ArgusSecurityPlugin" in text or "Uifid Not Found" in text:
                    raise ThirdPartyError(
                        "抖音风控拦截（ArgusSecurityPlugin 要求 Uifid）——"
                        "请在 config.py 里配置 DOUYIN_COOKIE"
                    )
                try:
                    data = json.loads(text)
                except json.JSONDecodeError:
                    logger.warning("抖音详情接口返回的不是 JSON（可能又是风控页）")
                    return None
                return data
    except ThirdPartyError:
        raise
    except Exception as e:
        logger.warning(f"抖音详情接口异常: {type(e).__name__}: {str(e)[:120]}")
        return None


async def parse_douyin(url: str):
    """
    抖音直连解析（优先），失败返回 None 好让上层回退~

    Returns:
        dict: normalize() 的结果 或 None
    """
    aweme_id = await _douyin_resolve_aweme_id(url)
    if not aweme_id:
        return None

    logger.info(f"抖音视频 ID: {aweme_id}")

    data = await _douyin_fetch_detail(aweme_id)
    if not data:
        return None

    # 抖音的详情结构：{"aweme_detail": {...}} 或 {"aweme_list": [{...}]}
    detail = data
    if isinstance(data, dict):
        if isinstance(data.get("aweme_detail"), dict):
            detail = data["aweme_detail"]
        elif isinstance(data.get("aweme_list"), list) and data["aweme_list"]:
            detail = data["aweme_list"][0]

    result = normalize({"data": detail})

    # 抖音的图集结构特殊：images 里每项是 {url_list: [...]}
    if not result.get("images"):
        imgs = _deep_find(detail, IMAGES_KEYS)
        if isinstance(imgs, list):
            urls = []
            for item in imgs:
                u = _extract_url_from_value(item)
                if u:
                    urls.append(u)
            result["images"] = urls

    # 视频直链
    if not result.get("video_url"):
        play = _deep_find(detail, ("play_addr", "play_addr_h264", "play_addr_265"))
        u = _extract_url_from_value(play)
        if u:
            result["video_url"] = u

    if result.get("video_url") or result.get("images"):
        logger.info(
            f"🍪 抖音直连解析成功: 视频={'有' if result['video_url'] else '无'} "
            f"图集={len(result['images'])}张 标题={result['title'][:40]!r}"
        )
        return result

    logger.info("抖音直连拿到数据但没解析出媒体地址")
    return None
