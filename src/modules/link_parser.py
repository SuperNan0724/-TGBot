"""
🔗 链接解析模块 - 自动识别消息里的链接，提取其中的图片/视频并生成简介

发一条链接给小南，她会：
  1. 识别平台（B站/YouTube/抖音/快手/小红书/Twitter/X/微博/直链…）
  2. 用 yt-dlp 提取元数据（标题、作者、时长、播放量…）
  3. 尽量把媒体下载下来发给你（超限则给原始链接）
  4. 再用小南的性格语气写一段简介发出来

技术要点
────────
• 平台覆盖：yt-dlp 支持上千个站点，比手写一堆正则靠谱得多
• 纯直链（.jpg/.mp4）不走 yt-dlp，直接用 aiohttp 下载，更快更稳
• yt-dlp 是同步阻塞的，必须丢进线程池（asyncio.to_thread）否则会卡死事件循环
• 图片理解复用 media_parser 的视觉能力，不重复实现

【踩坑记录】
  1. Telegram Bot 上传文件上限 50MB、下载 20MB。所以下载体积默认限制
     48MB，超限时降级为「发送原始链接」，而不是让整次解析失败。
  2. yt-dlp 下载的媒体 URL 往往带时效签名（B站尤其明显），不能缓存复用，
     每次都要重新提取。
  3. 直链下载必须走代理，而 aiohttp 默认不读系统代理 —— 见 net_helpers。
"""
import asyncio
import ipaddress
import json
import logging
import os
import re
import socket
import tempfile
import time
from urllib.parse import urlparse

import aiohttp
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CommandHandler, ContextTypes, MessageHandler, filters, ApplicationHandlerStop,
)

from config import (
    DEEPSEEK_API_KEY, BOT_NAME_SHORT, DEFAULT_PERSONALITY,
    LINK_PARSER_ENABLED, LINK_MAX_DOWNLOAD_MB, LINK_AI_SUMMARY,
    LINK_COOLDOWN_SECONDS, LINK_MAX_PER_MESSAGE, LINK_EXTRACT_TIMEOUT,
    MEDIA_DATA_DIR,
)
from .base_module import BaseModule
from .data_manager import DataManager
from .net_helpers import get_proxy_url, find_ffmpeg, apply_thinking_options
from .personalities import get_prompt
from .helpers import get_time_context

logger = logging.getLogger(__name__)

# ── 链接匹配 ────────────────────────────────────────────────
URL_PATTERN = re.compile(
    r"https?://[^\s<>\"'\)\]\}]+",
    re.IGNORECASE,
)

# 明显不该解析的后缀（避免把代码/压缩包当媒体抓）
SKIP_EXTENSIONS = (
    ".exe", ".msi", ".zip", ".rar", ".7z", ".tar", ".gz", ".apk",
    ".dmg", ".iso", ".py", ".js", ".ts", ".java", ".c", ".cpp",
    ".json", ".xml", ".csv", ".pdf", ".doc", ".docx", ".xls", ".xlsx",
)

IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".avif")
VIDEO_EXTENSIONS = (".mp4", ".webm", ".mov", ".mkv", ".avi", ".m4v", ".flv")

# ── 平台识别表（用于显示友好名称）──────────────────────────
PLATFORMS = [
    ("bilibili.com", "b23.tv", "B 站"),
    ("youtube.com", "youtu.be", "YouTube"),
    ("douyin.com", "iesdouyin.com", "抖音"),
    ("kuaishou.com", "chenzhongtech.com", "快手"),
    ("xiaohongshu.com", "xhslink.com", "小红书"),
    ("twitter.com", "x.com", "Twitter/X"),
    ("weibo.com", "weibo.cn", "微博"),
    ("zhihu.com", "知乎"),
    ("douban.com", "豆瓣"),
    ("tiktok.com", "TikTok"),
    ("instagram.com", "Instagram"),
    ("v.qq.com", "腾讯视频"),
    ("iqiyi.com", "爱奇艺"),
    ("youku.com", "优酷"),
    ("acfun.cn", "AcFun"),
    ("nicovideo.jp", "niconico"),
    ("twitch.tv", "Twitch"),
    ("github.com", "GitHub"),
    ("mp.weixin.qq.com", "微信公众号"),
]


def _human_size(num_bytes) -> str:
    """字节数转可读单位~"""
    if not num_bytes:
        return "未知"
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.1f} {unit}"
        size /= 1024


def _human_duration(seconds) -> str:
    """秒数转 mm:ss / hh:mm:ss~"""
    if not seconds:
        return ""
    try:
        total = int(float(seconds))
    except (TypeError, ValueError):
        return ""
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def detect_platform(url: str) -> str:
    """识别链接属于哪个平台~"""
    try:
        host = (urlparse(url).hostname or "").lower()
    except Exception:
        return "未知"
    for entry in PLATFORMS:
        *domains, label = entry
        for d in domains:
            if host == d or host.endswith("." + d):
                return label
    return "网页"


# ── 视频标识（"车牌号"）────────────────────────────────────
#
# 从 URL 里抠出平台自己的编号，方便用户复制引用。
# 注意顺序：BV 号要排在 av 号前面，因为 BV 号里可能恰好包含 "av" 字样，
# 先匹配 av 会误判。
ID_PATTERNS = [
    ("BV号", re.compile(r"(BV[0-9A-Za-z]{10})", re.IGNORECASE)),
    ("av号", re.compile(r"/av(\d+)", re.IGNORECASE)),
    ("ep号", re.compile(r"/ep(\d+)", re.IGNORECASE)),
    ("ss号", re.compile(r"/ss(\d+)", re.IGNORECASE)),
    ("直播间", re.compile(r"live\.bilibili\.com/(\d+)")),
    ("UID", re.compile(r"space\.bilibili\.com/(\d+)")),
    ("am号", re.compile(r"/am(\d+)", re.IGNORECASE)),
    ("au号", re.compile(r"/au(\d+)", re.IGNORECASE)),
]

# 展示时每个标签对应的前缀。
# 显式写出来，不要用 label.replace() 去推——那种写法遇到新标签就会出错
# （比如 "音频au" 去掉"番剧"什么也没去掉，拼出 "音频au12345" 这种鬼东西）。
ID_PREFIX = {
    "BV号": "",
    "av号": "av",
    "ep号": "ep",
    "ss号": "ss",
    "am号": "am",
    "au号": "au",
    "直播间": "直播间 ",
    "UID": "UID ",
}


def _format_id(label: str, value: str) -> str:
    """把 (标签, 值) 拼成好读的展示字符串~"""
    return f"{ID_PREFIX.get(label, '')}{value}"


# ── 裸编号识别 ──────────────────────────────────────────────
#
# 用户经常只发一个编号（比如 BV1Mopn6NEhD），不带完整 URL。
# 这种消息原先完全不会被当成链接，直接掉进普通聊天，机器人只能回
# 「小南还是打不开呢」——用户看着就像"不识别"。
#
# ⚠️ 大小写规则（API 实测得出，和直觉不一样）：
#      前缀 "BV" 大小写**不敏感**：BV / Bv / bV / bv 都能查到
#      后面 10 位 base58 **严格敏感**：BV1Mopn6NEhD 有效，
#                                    BV1mopn6NEhD 就是 -404
#    所以：前缀用 re.IGNORECASE 放宽，但捕获到的串必须**原样**交给 API，
#    绝不做 upper()/lower() 归一化 —— 那会把有效编号改坏。
BARE_ID_PATTERNS = [
    # 不能用 \b：BV 号可能紧跟在中文后面，中文字符也算 \w，\b 会失配
    ("BV号", re.compile(r"(?<![0-9A-Za-z])(BV[0-9A-Za-z]{10})(?![0-9A-Za-z])",
                        re.IGNORECASE)),
    ("av号", re.compile(r"(?<![0-9A-Za-z])av(\d{1,12})(?![0-9A-Za-z])", re.IGNORECASE)),
    ("ep号", re.compile(r"(?<![0-9A-Za-z])ep(\d{1,10})(?![0-9A-Za-z])", re.IGNORECASE)),
    ("ss号", re.compile(r"(?<![0-9A-Za-z])ss(\d{1,10})(?![0-9A-Za-z])", re.IGNORECASE)),
    ("am号", re.compile(r"(?<![0-9A-Za-z])am(\d{1,10})(?![0-9A-Za-z])", re.IGNORECASE)),
]

# 编号 -> 可解析 URL 的模板
ID_URL_TEMPLATES = {
    "BV号": "https://www.bilibili.com/video/{id}",
    "av号": "https://www.bilibili.com/video/av{id}",
    "ep号": "https://www.bilibili.com/bangumi/play/ep{id}",
    "ss号": "https://www.bilibili.com/bangumi/play/ss{id}",
    "am号": "https://www.bilibili.com/audio/am{id}",
}


def _normalize_bv(raw: str) -> str:
    """
    把 BV 号的前缀归一到标准写法 "BV"，payload 部分原样保留~

    为什么必须归一前缀？
      B站 API 对前缀大小写不敏感（Bv / bV / bv 都能查到），
      但 **yt-dlp 的 BiliBili 提取器不行** —— 实测传 Bv1Mopn6NEhD 会报
      「Unable to extract initial state」，报错里 ID 甚至变成了 1Mopn6NEhD
      （前缀被它吞掉了）。所以要在交给 yt-dlp 之前统一成 BV 开头。

    为什么 payload 不能动？
      前 3 位之后是 base58 编码，**严格区分大小写**：
      BV1Mopn6NEhD 有效，BV1mopn6NEhD 就是 -404。
      做 upper()/lower() 归一化会把有效编号改坏。
    """
    if not raw:
        return raw
    return "BV" + raw[2:]


def recover_url_from_id(text: str):
    """
    从纯文本里认出一个裸视频编号，并还原成可解析的 URL~

    只在消息里**没有完整链接**时才该调用它。

    Returns:
        (url, 展示用编号) 或 (None, None)
    """
    if not text or "http" in text.lower():
        return None, None

    for label, pattern in BARE_ID_PATTERNS:
        m = pattern.search(text)
        if not m:
            continue
        template = ID_URL_TEMPLATES.get(label)
        if not template:
            continue
        # 原样使用捕获到的编号，不做大小写归一化（BV 号的 payload 大小写敏感）
        raw = m.group(1)
        value = _normalize_bv(raw) if label == "BV号" else raw
        return template.format(id=value), _format_id(label, value)

    return None, None


def extract_video_id(url: str, info: dict = None) -> str:
    """
    取出视频标识（用户口中的"车牌号"）~

    优先用 yt-dlp 给回来的 id，因为那是**平台自己的权威编号**：
      • 传 av80433022 进去，yt-dlp 的 id 会直接是归一化后的 BV1GJ411x7h7
        —— 等于白送一个 av -> BV 的换算，不用自己复现那套混淆算法。
      • 传 b23.tv 短链进去，拿到的是展开后的真实编号。
    只有拿不到 info 时（比如提取失败、普通网页），才回退到从 URL 里正则抠。

    Returns:
        str: 形如 "BV1GJ411x7h7" 或 "BV1GJ411x7h7（av80433022）"；取不到返回 ""
    """
    yt_id = ""
    if info:
        yt_id = str(info.get("id") or info.get("display_id") or "").strip()

    # URL 里的编号（用于补充显示原始形态，例如用户给的是 av 号）
    url_ids = []
    for label, pattern in ID_PATTERNS:
        m = pattern.search(url or "")
        if not m:
            continue
        value = m.group(1)
        url_ids.append((label, value))

    if yt_id:
        # 用户给的是 av 号、而 yt-dlp 归一成了 BV 号时，两个都显示出来
        for label, value in url_ids:
            if label == "av号" and value not in yt_id:
                return f"{yt_id}（av{value}）"
        return yt_id

    if url_ids:
        label, value = url_ids[0]
        return _format_id(label, value)

    return ""


def _url_extension(url: str) -> str:
    """取 URL 路径部分的扩展名（小写，带点）~"""
    try:
        path = urlparse(url).path.lower()
    except Exception:
        return ""
    for ext in IMAGE_EXTENSIONS + VIDEO_EXTENSIONS:
        if path.endswith(ext):
            return ext
    return ""


def _is_private_host(url: str) -> bool:
    """
    拒绝内网地址~

    这是个安全措施：如果别人发个 http://192.168.1.1/xxx 或
    http://127.0.0.1:8080/，机器人去请求就等于替人扫描内网。
    """
    try:
        host = urlparse(url).hostname
        if not host:
            return True
        if host.lower() in ("localhost", "127.0.0.1", "::1", "0.0.0.0"):
            return True
        try:
            ip = ipaddress.ip_address(host)
            return ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
        except ValueError:
            # 是域名而不是 IP，放行（不做 DNS 解析，避免额外延迟）
            return False
    except Exception:
        return True


class LinkParser(BaseModule):
    """链接解析模块~ 让小南看懂你发的链接！"""

    name = "link_parser"
    description = "自动识别链接中的图片/视频并生成简介"

    def __init__(self, bot_app=None):
        super().__init__(bot_app)
        self.dm = DataManager()
        self.application = None          # 由 register_handlers 注入
        self.media_parser = None         # 延迟获取（模块按字母序加载，见 _get_media_parser）
        self._last_call = {}
        self._last_reason = ""            # 最近一次失败原因，用于给用户可操作的报错
        self._last_target = {}            # chat_id -> 最近处理过的 URL/编号，供"解析刚才那个"使用
        self._enabled = LINK_PARSER_ENABLED
        self._ensure_dirs()

    def _ensure_dirs(self):
        try:
            os.makedirs(MEDIA_DATA_DIR, exist_ok=True)
        except Exception:
            pass

    def _get_media_parser(self):
        """
        按需获取 media_parser 实例（复用它的视觉/抽帧能力）~

        为什么要延迟获取、而不能在 register_handlers 里拿一次存起来？
          模块是按文件名**字母序**加载的，link_parser 排在 media_parser 之前，
          注册那会儿 media_parser 还没实例化，拿到的永远是 None。
          改成每次用时现拿，就能拿到已经注册好的实例。
          第一次成功拿到后会缓存，避免反复查表。
        """
        if self.media_parser is not None:
            return self.media_parser
        try:
            getter = getattr(self.bot_app, "get_module", None)
            if callable(getter):
                self.media_parser = getter("media_parser")
        except Exception as e:
            logger.debug(f"获取 media_parser 失败: {e}")
        return self.media_parser

    # ──────────────────────────────────────────
    #  注册
    # ──────────────────────────────────────────

    def register_handlers(self, application):
        self.application = application

        # 匹配两类消息：
        #   1. 含完整链接的（Telegram 会给出 url 实体）
        #   2. 只发了裸编号的（比如 BV1Mopn6NEhD）—— 这类没有 url 实体，
        #      只能靠正则认，所以过滤器放宽到所有非命令文本，由处理函数再筛。
        # 不能只依赖 filters.Entity("url")，否则裸编号永远不触发，
        # 用户看到的就是"机器人不识别"。
        application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            self.handle_message,
        ))

        application.add_handler(CommandHandler("link", self.link_command))
        # 英文别名 /parse
        application.add_handler(CommandHandler("parse", self.link_command))

        # 中文别名不能用 CommandHandler！
        # Telegram 只接受 ASCII 小写字母/数字/下划线的命令名，
        # CommandHandler("解析") 会让 PTB 直接抛
        #     Command `解析` is not a valid bot command
        # 那会连带整个模块加载失败（实测踩过：模块数从 13 掉到 12，
        # 链接解析功能整个消失）。所以改用文本正则匹配。
        application.add_handler(MessageHandler(
            filters.Regex(r"^/(?:解析|分析|parse链接)\b"),
            self.link_command,
        ))

        application.add_handler(CommandHandler("link_on", self.link_on_command))
        application.add_handler(CommandHandler("link_off", self.link_off_command))

        logger.info(
            f"🔗 链接解析模块初始化（AI简介: {'开' if LINK_AI_SUMMARY else '关'}, "
            f"下载上限: {LINK_MAX_DOWNLOAD_MB}MB）"
        )

    # ──────────────────────────────────────────
    #  权限 / 限流
    # ──────────────────────────────────────────

    def _can_use(self, user_id: int) -> bool:
        return self.dm.is_owner(user_id) or self.dm.is_user_whitelisted(user_id)

    def _cooldown_left(self, user_id: int) -> int:
        if LINK_COOLDOWN_SECONDS <= 0 or self.dm.is_owner(user_id):
            return 0
        elapsed = time.time() - self._last_call.get(user_id, 0)
        if elapsed >= LINK_COOLDOWN_SECONDS:
            return 0
        return int(LINK_COOLDOWN_SECONDS - elapsed) + 1

    # ──────────────────────────────────────────
    #  消息入口
    # ──────────────────────────────────────────

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """收到含链接的消息~"""
        message = update.effective_message
        user = update.effective_user
        if not message or not user or not message.text:
            return

        # 诊断日志：排查"用户发了连接却毫无反应"这类问题时，
        # 必须先确认 handler 到底有没有被调用（过滤器是否放行）。
        logger.info(
            f"🔗 [link_parser] 收到文本消息: {message.text[:60]!r} "
            f"user={user.id} entities={len(message.entities or [])}"
        )

        if not self._enabled:
            logger.info("🔗 [link_parser] 功能已关闭，跳过")
            return

        if not self._can_use(user.id):
            logger.info(f"🔗 [link_parser] 用户 {user.id} 不在白名单，跳过")
            await message.reply_text(
                "呜… 小南现在还不认识你呢(｡•́︿•̀｡)\n"
                "链接解析要主人允许才能用哦~"
            )
            return

        urls = self._extract_urls(message.text)

        # 没有完整链接时，试试是不是只发了个裸编号（如 BV1Mopn6NEhD）。
        # 这种情况用户以为发了"链接"，但 Telegram 不会给出 url 实体，
        # 不还原成 URL 的话消息就掉进普通聊天，表现为"机器人不识别"。
        recovered_label = ""
        if not urls:
            recovered_url, recovered_label = recover_url_from_id(message.text)
            if recovered_url:
                urls = [recovered_url]

        if not urls:
            logger.info("🔗 [link_parser] 未识别到链接或编号，交给后续 handler")
            return

        logger.info(f"🔗 [link_parser] 识别到目标: {urls}")

        # 记住这个目标，方便用户之后说「解析刚才那个」
        self._last_target[message.chat_id] = urls[0]

        left = self._cooldown_left(user.id)
        if left:
            await message.reply_text(f"慢一点嘛~ 还要等 {left} 秒才能再看一个链接哦(｡•́︿•̀｡)")
            return

        self._last_call[user.id] = time.time()

        if recovered_label:
            status = await message.reply_text(
                f"🔍 认出了 B站编号 {recovered_label}，小南这就去查~"
            )
        else:
            status = await message.reply_text(f"🔗 小南正在看这个链接…（共 {len(urls)} 个）")

        results = []
        for idx, url in enumerate(urls, 1):
            if len(urls) > 1:
                try:
                    await status.edit_text(f"🔗 正在处理第 {idx}/{len(urls)} 个链接…")
                except Exception:
                    pass
            try:
                results.append(await self._process_url(url, user.id, message))
            except Exception as e:
                logger.error(f"链接解析失败 [{url}]: {e}", exc_info=True)
                self.dm.add_error({"message": f"链接解析错误: {e}", "user_id": user.id})
                results.append(f"❌ 这个链接小南看不懂呢：{url}")

        # 汇总多余的文字结果
        notes = [r for r in results if r]
        if notes:
            await status.edit_text("\n\n".join(notes))
        else:
            try:
                await status.delete()
            except Exception:
                pass

        # 关键：必须阻断后续 handler，否则 deepseek_chat 也会回一条，
        # 同一条消息得到两份不相关的回复 —— 用户看到的就是"两个模块抢答"。
        #
        # PTB 源码（Application.process_update）里对 ApplicationHandlerStop 的处理是：
        #     except ApplicationHandlerStop:
        #         break        # 停掉所有后续 handler，含其它 group
        # 官方文档也明确：no further handlers (regardless of the group) will be called
        raise ApplicationHandlerStop

    def _extract_urls(self, text: str) -> list:
        """从文本里提取要解析的链接~"""
        found = []
        for raw in URL_PATTERN.findall(text or ""):
            url = raw.rstrip(".,;:!?、。，；：！？")
            low = url.lower()
            if any(low.endswith(ext) for ext in SKIP_EXTENSIONS):
                continue
            if _is_private_host(url):
                logger.info(f"⏭️ 跳过内网地址: {url}")
                continue
            if url not in found:
                found.append(url)
            if len(found) >= LINK_MAX_PER_MESSAGE:
                break
        return found

    # ──────────────────────────────────────────
    #  核心处理
    # ──────────────────────────────────────────

    async def _process_url(self, url: str, user_id: int, message) -> str:
        """
        处理单个链接~

        Returns:
            str: 需要额外以文字形式回发的说明（空字符串表示不用）
        """
        platform = detect_platform(url)
        ext = _url_extension(url)

        # 用于记录失败原因，让报错能说清楚"为什么打不开"，
        # 而不是笼统一句「小南打不开链接」让用户无从下手。
        self._last_reason = ""

        # 直链的话，用主机名当标签比"网页"清楚得多
        if platform == "网页":
            try:
                host = (urlparse(url).hostname or "").lower()
                if host:
                    platform = host[4:] if host.startswith("www.") else host
            except Exception:
                pass

        # ── 路径 A：直链媒体，不走 yt-dlp ──
        if ext in IMAGE_EXTENSIONS or ext in VIDEO_EXTENSIONS:
            return await self._handle_direct(url, user_id, message, platform, ext)

        # ── 路径 B：平台视频，用 yt-dlp ──
        info = await self._extract_info(url)
        if info:
            return await self._handle_extracted(url, info, user_id, message, platform)

        # ── 路径 C：普通网页，读 Open Graph ──
        return await self._handle_webpage(url, user_id, message, platform)

    # ── 路径 A：直链 ──────────────────────────────

    async def _handle_direct(self, url, user_id, message, platform, ext) -> str:
        """直链媒体：直接下载后发送~"""
        data, content_type, err = await self._http_get(url, max_bytes=LINK_MAX_DOWNLOAD_MB * 1024 * 1024)
        if data is None:
            return f"❌ 这个链接小南拿不到呢（{err}）\n{url}"

        # 图片：交给 media_parser 的视觉能力描述
        if ext in IMAGE_EXTENSIONS or (content_type or "").startswith("image/"):
            caption = f"🖼️ {platform} 图片 · {_human_size(len(data))}"
            await self._send_photo(message, data, caption, url)

            mp = self._get_media_parser()
            if LINK_AI_SUMMARY and mp:
                try:
                    desc = await mp._vision_request(
                        [data],
                        context_note="这是用户分享的一个图片链接里的图片，请用你的语气描述它。",
                        user_id=user_id,
                    )
                    if desc:
                        await message.reply_text(desc)
                except Exception as e:
                    logger.error(f"图片简介生成失败: {e}")
            return ""

        # 视频：直接发文件
        caption = f"🎬 {platform} 视频 · {_human_size(len(data))}"
        sent = await self._send_video(message, data, caption, url)
        if sent:
            return ""
        return f"⚠️ 视频太大发不出来，给你原链接~\n{url}"

    # ── 路径 B：yt-dlp 提取 ───────────────────────

    async def _handle_extracted(self, url, info, user_id, message, platform) -> str:
        """yt-dlp 提取成功：发媒体 + 元数据 + AI 简介~"""
        title = (info.get("title") or "").strip()
        uploader = (info.get("uploader") or info.get("channel") or "").strip()
        duration = _human_duration(info.get("duration"))
        view_count = info.get("view_count")
        like_count = info.get("like_count")
        description = (info.get("description") or "").strip()
        webpage = info.get("webpage_url") or url

        # ── 元数据卡片 ──
        meta_lines = [f"🔗 {platform}" + (f" · {duration}" if duration else "")]

        # 视频标识（"车牌号"）：BV号 / av号 / ep号 等，方便复制引用
        video_id = extract_video_id(url, info)
        if video_id:
            meta_lines.append(f"🆔 {video_id}")

        if title:
            meta_lines.append(f"📌 {title[:120]}")
        if uploader:
            meta_lines.append(f"👤 {uploader}")
        stats = []
        if view_count:
            stats.append(f"播放 {view_count:,}")
        if like_count:
            stats.append(f"点赞 {like_count:,}")
        if stats:
            meta_lines.append("📊 " + " · ".join(stats))
        if description:
            brief = description.replace("\n", " ")[:150]
            meta_lines.append(f"📝 {brief}{'…' if len(description) > 150 else ''}")
        meta_text = "\n".join(meta_lines)

        buttons = InlineKeyboardMarkup([[
            InlineKeyboardButton(f"🔗 打开原链接（{platform}）", url=webpage)
        ]])

        # ── 判断这是图片型还是视频型结果 ──
        is_image = (info.get("ext") or "").lower() in ("jpg", "jpeg", "png", "webp", "gif")
        media_sent = False
        downloaded_bytes = None

        if is_image and info.get("url"):
            data, ctype, err = await self._http_get(info["url"])
            if data:
                await self._send_photo(message, data, meta_text[:1000], webpage, buttons)
                media_sent = True
                downloaded_bytes = data
        else:
            download = await self._download_media(url, info)
            if download:
                path, size = download
                try:
                    with open(path, "rb") as f:
                        data = f.read()
                    ok = await self._send_video(message, data, meta_text[:1000], webpage, buttons)
                    media_sent = ok
                finally:
                    try:
                        os.remove(path)
                    except Exception:
                        pass

        if not media_sent:
            # 下载不了或超限：发纯文字卡片 + 链接按钮
            await message.reply_text(meta_text, reply_markup=buttons, disable_web_page_preview=True)

            # 说明为什么没给文件——否则用户会以为功能坏了。
            # 注意这里的嵌套层级：早先写成 elif 挂在"体积超限"分支下面，
            # 结果下载失败时根本走不到，提示永远不显示。
            if not is_image:
                size_hint = info.get("filesize") or info.get("filesize_approx")
                if size_hint and size_hint > LINK_MAX_DOWNLOAD_MB * 1024 * 1024:
                    await message.reply_text(
                        f"📦 这个视频有 {_human_size(size_hint)}，超过小南的搬运上限"
                        f"（{LINK_MAX_DOWNLOAD_MB}MB），所以只能给你链接啦~"
                    )
                elif self._last_reason:
                    await message.reply_text(
                        f"⚠️ 视频文件没能下载下来：{self._last_reason}\n"
                        "   ├─ 上面已经给出封面和简介\n"
                        "   └─ 可以点按钮直接打开原链接看"
                    )

        # ── AI 简介（第二条消息）──
        if LINK_AI_SUMMARY and DEEPSEEK_API_KEY and DEEPSEEK_API_KEY != "YOUR_DEEPSEEK_API_KEY":
            try:
                cover = None
                thumb = info.get("thumbnail")
                if thumb and self._get_media_parser():
                    cdata, _, _ = await self._http_get(thumb, max_bytes=8 * 1024 * 1024)
                    if cdata:
                        cover = cdata
                summary = await self._ai_summary(info, user_id, cover)
                if summary:
                    await message.reply_text(summary)
            except Exception as e:
                logger.error(f"AI 简介失败: {e}")

        return ""

    async def _download_media(self, url: str, info: dict):
        """
        用 yt-dlp 下载媒体~

        Returns:
            (path, size) 或 None
        """
        cap_bytes = LINK_MAX_DOWNLOAD_MB * 1024 * 1024

        # 已知体积且超限，直接放弃，不浪费带宽
        known = info.get("filesize") or info.get("filesize_approx")
        if known and known > cap_bytes:
            logger.info(f"⏭️ 体积 {_human_size(known)} 超过上限，跳过下载")
            return None

        tmpdir = tempfile.mkdtemp(prefix="nan_link_")
        outtmpl = os.path.join(tmpdir, "media.%(ext)s")

        # 格式选择策略（顺序尝试，越靠前越优先）：
        #   1. 单文件 mp4 —— 无需 ffmpeg 合并，最快最稳
        #   2. 任意单文件（可能不是 mp4，Telegram 多半也能收）
        #   3. 视频+音频分开的最佳组合 —— 靠 ffmpeg 合并
        #   4. 兜底 worst
        #
        # ⚠️ 注意：**不要**在格式串里写 filesize<NNM！
        #    很多站点只给 filesize_approx 甚至完全不给，那种过滤条件会
        #    直接匹配失败并抛 "Requested format is not available"，
        #    结果就是明明能下的视频却下不下来。
        #    体积控制交给 max_filesize 选项 + 下载后二次检查。
        fmt = (
            "best[ext=mp4][vcodec!=none][acodec!=none]/"
            "best[vcodec!=none][acodec!=none]/"
            "bestvideo[ext=mp4]+bestaudio[ext=m4a]/"
            "bestvideo+bestaudio/"
            "best/worst"
        )

        def _run():
            import yt_dlp
            opts = {
                "quiet": True,
                "no_warnings": True,
                "outtmpl": outtmpl,
                "format": fmt,
                "merge_output_format": "mp4",
                "noplaylist": True,
                "socket_timeout": 30,
                "retries": 2,
                "noprogress": True,
                # 超过这个体积就别下了（yt-dlp 支持时会在下载前拒绝）
                "max_filesize": cap_bytes,
            }
            proxy = get_proxy_url()
            if proxy:
                opts["proxy"] = proxy

            # 关键：明确告诉 yt-dlp ffmpeg 在哪。
            # 很多站点（B站就是）没有音视频合一的流，必须靠 ffmpeg 合并，
            # 找不到就直接失败。而且如果机器人是在装 ffmpeg 之前启动的终端里
            # 运行的，进程 PATH 里根本没有它。
            ffmpeg_path = find_ffmpeg()
            if ffmpeg_path:
                opts["ffmpeg_location"] = ffmpeg_path
                logger.debug(f"使用 ffmpeg: {ffmpeg_path}")
            else:
                logger.warning(
                    "⚠️ 未找到 ffmpeg，只能下载音视频合一的流\n"
                    "   └─ 影响：B站等站点无法下载（它们只提供分离的流）\n"
                    "      解决：装 ffmpeg 后在 config.py 里填 FFMPEG_PATH"
                )

            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])

        try:
            await asyncio.to_thread(_run)
        except Exception as e:
            err = str(e)
            logger.warning(f"yt-dlp 下载失败: {err[:200]}")
            # 把失败原因分类记下来，好让用户知道是"没救"还是"等会儿就好了"
            if "No video formats found" in err:
                # B站最常见：播放流接口被风控/需要登录。
                # 元数据还能取到（所以卡片和封面图照常显示），但视频下不下来。
                self._last_reason = (
                    "取不到视频流（B站风控或需要登录 Cookie）"
                )
                logger.warning(
                    "   └─ 取不到播放流。常见原因：\n"
                    "      • 请求太频繁被 B站 风控（等一段时间会自己恢复）\n"
                    "      • 该视频需要登录才能看（大会员/限制内容）\n"
                    "      • yt-dlp 版本落后于站点改动（pip install -U yt-dlp）"
                )
            elif "Requested format is not available" in err:
                self._last_reason = "格式选择器没匹配到可用流"
                logger.warning("   └─ 站点可能改了格式列表")
            elif "HTTP Error 403" in err or "403" in err:
                self._last_reason = "站点返回 403（被风控拦截）"
            else:
                self._last_reason = "视频下载失败"
            return None

        # 找出下载到的文件
        try:
            files = [os.path.join(tmpdir, f) for f in os.listdir(tmpdir)]
            files = [f for f in files if os.path.isfile(f)]
            if not files:
                return None
            # 取最大的那个（可能残留 .part）
            files.sort(key=os.path.getsize, reverse=True)
            path = files[0]
            size = os.path.getsize(path)
            if size == 0 or size > cap_bytes:
                for f in files:
                    try:
                        os.remove(f)
                    except Exception:
                        pass
                os.rmdir(tmpdir)
                return None
            return path, size
        except Exception as e:
            logger.error(f"检查下载结果失败: {e}")
            return None

    async def _extract_info(self, url: str):
        """用 yt-dlp 提取元数据（不下载）~"""
        def _run():
            import yt_dlp
            opts = {
                "quiet": True,
                "no_warnings": True,
                "skip_download": True,
                "noplaylist": True,
                "socket_timeout": 20,
                "extract_flat": False,
            }
            proxy = get_proxy_url()
            if proxy:
                opts["proxy"] = proxy
            with yt_dlp.YoutubeDL(opts) as ydl:
                data = ydl.extract_info(url, download=False)
            # 播放列表/多条目：只取第一个
            if data and data.get("_type") == "playlist" and data.get("entries"):
                entries = [e for e in data["entries"] if e]
                if entries:
                    return entries[0]
            return data

        try:
            return await asyncio.wait_for(
                asyncio.to_thread(_run), timeout=LINK_EXTRACT_TIMEOUT
            )
        except asyncio.TimeoutError:
            logger.warning(f"yt-dlp 提取超时: {url}")
            self._last_reason = "提取超时"
            return None
        except Exception as e:
            msg = str(e)[:180]
            logger.info(f"yt-dlp 无法提取（将回退到网页解析）: {msg}")
            # 记下原因，供最终报错时用
            if "Unsupported URL" in msg:
                self._last_reason = "这个站点不在支持列表里"
            elif "Unable to download webpage" in msg or "Unable to download" in msg:
                self._last_reason = "站点拒绝了访问（可能需要登录或被反爬拦截）"
            else:
                self._last_reason = "站点解析失败"
            return None

    # ── 路径 C：普通网页 Open Graph ────────────────

    async def _handle_webpage(self, url, user_id, message, platform) -> str:
        """普通网页：读 Open Graph 标签~"""
        html, _, err = await self._http_get(url, max_bytes=512 * 1024, as_text=True)
        if not html:
            reason = self._last_reason or err or "请求失败"
            return (
                f"❌ 这个链接小南打不开呢\n"
                f"   ├─ 平台：{platform}\n"
                f"   ├─ 原因：{reason}\n"
                f"   └─ 链接：{url}"
            )

        og = self._parse_open_graph(html)
        title = og.get("title") or og.get("og:title") or ""
        desc = og.get("description") or og.get("og:description") or ""
        image = og.get("og:image") or og.get("image") or ""

        if not (title or desc):
            # 页面能打开但抠不到简介。最常见的两种情况要区分清楚，
            # 否则用户只会看到一句没头没脑的"打不开"。
            head = html[:2000].lower()
            if "<script" in head and "og:" not in head:
                detail = (
                    "这个站点的内容是 JS 动态渲染的，页面里没有可读的简介信息"
                    "（抖音/小红书这类站常见，需要登录态才能解析）"
                )
            else:
                detail = "页面里没有找到简介信息，可能这不是一个内容页"

            lines = [
                f"🔗 {platform} 页面",
                "   ├─ 小南打开了页面，但没能提取到内容简介",
                f"   ├─ 说明：{detail}",
                f"   └─ 链接：{url}",
            ]
            return "\n".join(lines)

        lines = [f"🔗 {platform}"]
        if title:
            lines.append(f"📌 {title[:150]}")
        if desc:
            lines.append(f"📝 {desc[:300]}")
        text = "\n".join(lines)

        buttons = InlineKeyboardMarkup([[
            InlineKeyboardButton("🔗 打开链接", url=url)
        ]])

        # 有 og:image 就先发图（更直观）
        sent_photo = False
        if image and image.startswith("http"):
            data, ctype, _ = await self._http_get(image, max_bytes=8 * 1024 * 1024)
            if data and (ctype or "").startswith("image/"):
                await self._send_photo(message, data, text[:1000], url, buttons)
                sent_photo = True

        if not sent_photo:
            await message.reply_text(text, reply_markup=buttons, disable_web_page_preview=False)

        if LINK_AI_SUMMARY and desc:
            try:
                summary = await self._ai_summary(
                    {"title": title, "description": desc, "webpage_url": url}, user_id
                )
                if summary:
                    await message.reply_text(summary)
            except Exception as e:
                logger.error(f"网页简介失败: {e}")
        return ""

    @staticmethod
    def _parse_open_graph(html: str) -> dict:
        """从 HTML 里抠出 Open Graph / meta 信息~"""
        result = {}
        # <meta property="og:title" content="...">
        for m in re.finditer(
            r'<meta\s+[^>]*?(?:property|name)\s*=\s*["\']([^"\']+)["\'][^>]*?'
            r'content\s*=\s*["\']([^"\']*)["\']',
            html, re.IGNORECASE,
        ):
            key, val = m.group(1).strip().lower(), m.group(2).strip()
            if key not in result:
                result[key] = val
        # content 在前面、property 在后面的写法
        for m in re.finditer(
            r'<meta\s+[^>]*?content\s*=\s*["\']([^"\']*)["\'][^>]*?'
            r'(?:property|name)\s*=\s*["\']([^"\']+)["\']',
            html, re.IGNORECASE,
        ):
            val, key = m.group(1).strip(), m.group(2).strip().lower()
            if key not in result:
                result[key] = val
        # <title>
        if "title" not in result:
            m = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
            if m:
                result["title"] = re.sub(r"\s+", " ", m.group(1)).strip()
        return result

    # ──────────────────────────────────────────
    #  HTTP
    # ──────────────────────────────────────────

    async def _http_get(self, url: str, max_bytes: int = 32 * 1024 * 1024, as_text: bool = False):
        """
        下载 URL 内容~（走代理，带体积上限）

        Returns:
            (data, content_type, error)
        """
        if _is_private_host(url):
            return None, None, "内网地址不允许访问"

        proxy = get_proxy_url() or None
        timeout = aiohttp.ClientTimeout(total=120, connect=30)
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
            ),
            "Accept": "*/*",
        }

        try:
            async with aiohttp.ClientSession(timeout=timeout, trust_env=True) as session:
                async with session.get(url, headers=headers, proxy=proxy) as resp:
                    if resp.status != 200:
                        return None, None, f"HTTP {resp.status}"

                    ctype = (resp.headers.get("Content-Type") or "").lower()

                    # 体积预检
                    length = resp.headers.get("Content-Length")
                    if length and length.isdigit() and int(length) > max_bytes:
                        return None, ctype, f"文件 {_human_size(int(length))} 超过上限"

                    chunks = []
                    total = 0
                    async for chunk in resp.content.iter_chunked(65536):
                        total += len(chunk)
                        if total > max_bytes:
                            return None, ctype, "下载超过体积上限"
                        chunks.append(chunk)

            raw = b"".join(chunks)
            if as_text:
                # 优先用页面声明的编码，失败再用 utf-8
                charset = None
                m = re.search(rb'charset=["\']?([\w-]+)', raw[:4096], re.IGNORECASE)
                if m:
                    charset = m.group(1).decode("ascii", "ignore")
                for enc in filter(None, [charset, "utf-8", "gbk"]):
                    try:
                        return raw.decode(enc), ctype, None
                    except (UnicodeDecodeError, LookupError):
                        continue
                return raw.decode("utf-8", "replace"), ctype, None
            return raw, ctype, None

        except asyncio.TimeoutError:
            return None, None, "请求超时"
        except aiohttp.ClientError as e:
            return None, None, f"网络错误 {type(e).__name__}"
        except Exception as e:
            return None, None, f"{type(e).__name__}"

    # ──────────────────────────────────────────
    #  发送
    # ──────────────────────────────────────────

    async def _send_photo(self, message, data: bytes, caption: str, url: str, buttons=None):
        """发图片~"""
        if buttons is None:
            buttons = InlineKeyboardMarkup([[InlineKeyboardButton("🔗 查看原图", url=url)]])
        try:
            await message.reply_photo(
                photo=data, caption=caption or None, reply_markup=buttons
            )
            return True
        except Exception as e:
            logger.warning(f"发送图片失败: {str(e)[:150]}")
            try:
                await message.reply_text(caption or url, reply_markup=buttons)
                return True
            except Exception:
                return False

    async def _send_video(self, message, data: bytes, caption: str, url: str, buttons=None):
        """发视频~（失败返回 False，由调用方降级为链接）"""
        if buttons is None:
            buttons = InlineKeyboardMarkup([[InlineKeyboardButton("🔗 打开原链接", url=url)]])
        try:
            await message.reply_video(
                video=data,
                caption=caption or None,
                reply_markup=buttons,
                supports_streaming=True,
                read_timeout=180,
                write_timeout=180,
            )
            return True
        except Exception as e:
            logger.warning(f"发送视频失败: {str(e)[:200]}")
            return False

    # ──────────────────────────────────────────
    #  AI 简介
    # ──────────────────────────────────────────

    async def _ai_summary(self, info: dict, user_id: int, cover: bytes = None) -> str:
        """用 DeepSeek 生成小南风格的简介~（有封面图就带图）"""
        import base64

        user_data = self.dm.get_user_data(user_id)
        personality = user_data.get("personality", DEFAULT_PERSONALITY)

        title = info.get("title") or ""
        uploader = info.get("uploader") or info.get("channel") or ""
        duration = _human_duration(info.get("duration"))
        description = (info.get("description") or "")[:800]
        platform = detect_platform(info.get("webpage_url") or "")

        facts = [f"平台：{platform}"]
        if title:
            facts.append(f"标题：{title}")
        if uploader:
            facts.append(f"作者：{uploader}")
        if duration:
            facts.append(f"时长：{duration}")
        if description:
            facts.append(f"原始简介：{description}")

        system = (
            get_prompt(personality, BOT_NAME_SHORT)
            + "\n\n"
            + get_time_context()
            + "\n\n【写简介任务】\n"
            "对方分享了一个链接，你要用两三句话介绍一下这是什么内容。\n"
            "要求：\n"
            "1. 只根据给的信息说，不要编造情节、评价或数据。\n"
            "2. 用你现在的性格语气，像跟朋友安利一样自然。\n"
            "3. 不要用括号描写动作或表情。\n"
            "4. 控制在 80 字以内，不要重复罗列标题和作者。"
        )

        content = [{"type": "text", "text": "链接信息：\n" + "\n".join(facts)}]
        if cover:
            from .media_parser import _guess_format
            fmt = _guess_format(cover)
            if fmt and len(cover) <= 8 * 1024 * 1024:
                b64 = base64.b64encode(cover).decode("ascii")
                content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:{fmt};base64,{b64}", "detail": "low"},
                })

        from config import VISION_MODEL, DEEPSEEK_API_KEY as _KEY, DEEPSEEK_API_URL
        payload = {
            "model": VISION_MODEL,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": content},
            ],
            "max_tokens": 1200,
            "temperature": 1.0,
        }
        # 写简介属于描述型任务，不需要推理；关掉思考更快更省，
        # 也避免思考吃光额度导致正文为空
        apply_thinking_options(payload)
        headers = {
            "Authorization": f"Bearer {_KEY}",
            "Content-Type": "application/json",
        }
        proxy = get_proxy_url() or None
        timeout = aiohttp.ClientTimeout(total=120, connect=30)

        async with aiohttp.ClientSession(timeout=timeout, trust_env=True) as session:
            async with session.post(
                DEEPSEEK_API_URL, headers=headers, json=payload, proxy=proxy
            ) as resp:
                if resp.status != 200:
                    logger.warning(f"AI 简介接口返回 {resp.status}")
                    return ""
                data = await resp.json()

        msg = data["choices"][0]["message"]
        text = (msg.get("content") or "").strip()
        # 不要把 reasoning_content 当正文：那是模型内部独白
        # （详见 media_parser 里同处的说明）
        if not text:
            logger.warning("AI 简介返回空正文（思考可能吃光了 max_tokens）")
        return text

    # ──────────────────────────────────────────
    #  命令
    # ──────────────────────────────────────────

    async def link_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /link、/parse、/解析 —— 手动解析一个链接或编号~

        四种用法：
          1. /link https://...        直接给链接
          2. /link BV1Mopn6NEhD       直接给编号
          3. 回复某条消息发 /link      解析那条消息里的链接/编号
          4. 什么都不带               解析你最近发过的那个

        注意：参数是从**消息文本**里自己抠的，而不是用 context.args。
        因为中文别名 /解析 走的是文本正则（Telegram 不允许中文命令名），
        那种情况下 PTB 不会帮我们切好 args。
        """
        user = update.effective_user
        message = update.effective_message

        if not self._can_use(user.id):
            await message.reply_text("呜… 你不在白名单里，暂时用不了这个功能哦~")
            return

        # 把开头的命令部分（/link、/parse、/解析 …）去掉，剩下的就是参数
        rest = re.sub(r"^/(?:link|parse|解析|分析)\b\s*", "", message.text or "").strip()

        url = None
        source = ""

        # 用法1/2：参数里是链接或编号
        if rest:
            if rest.lower().startswith(("http://", "https://")):
                found = self._extract_urls(rest)
                if found:
                    url = found[0]
            if not url:
                recovered, label = recover_url_from_id(rest)
                if recovered:
                    url = recovered
                    source = f"（识别为 {label}）"

        # 用法3：回复某条消息
        if not url and message.reply_to_message and message.reply_to_message.text:
            replied = message.reply_to_message.text
            found = self._extract_urls(replied)
            if found:
                url = found[0]
            else:
                recovered, label = recover_url_from_id(replied)
                if recovered:
                    url = recovered
                    source = f"（识别为 {label}）"

        # 用法4：什么都没带，用最近提到过的那个
        if not url:
            url = self._last_target.get(message.chat_id)

        if not url:
            await message.reply_text(
                "小南没找到要解析的内容呢(｡•́︿•̀｡)\n\n"
                "可以这样用：\n"
                "  /link https://...      直接给链接\n"
                "  /link BV1Mopn6NEhD     给视频编号\n"
                "  回复某条消息发 /link    解析那条消息\n"
                "  直接把链接或编号发给小南也行~"
            )
            return

        status = await message.reply_text(f"🔗 小南正在看{source}…")
        try:
            note = await self._process_url(url, user.id, message)
            if note:
                await status.edit_text(note)
            else:
                try:
                    await status.delete()
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"链接解析命令失败: {e}", exc_info=True)
            await status.edit_text("呜… 这个链接小南看不懂呢(｡•́︿•̀｡)")

        # 手动命令同样要阻断后续，免得 deepseek_chat 又回一条
        raise ApplicationHandlerStop

    async def link_on_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/link_on - 开启链接解析（仅主人）~"""
        if not self.dm.is_owner(update.effective_user.id):
            await update.message.reply_text("这个命令只有主人能用哦~")
            return
        self._enabled = True
        await update.message.reply_text("✅ 链接解析已开启~ 发个链接试试吧！")

    async def link_off_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/link_off - 关闭链接解析（仅主人）~"""
        if not self.dm.is_owner(update.effective_user.id):
            await update.message.reply_text("这个命令只有主人能用哦~")
            return
        self._enabled = False
        await update.message.reply_text("⛔ 链接解析已关闭~ 小南不会再自动看链接啦。")

    def get_help_text(self) -> str:
        return (
            "/link <链接> - 解析链接里的图片/视频~\n"
            "（直接发链接也行，小南会自动识别并生成简介~）\n"
            "/link_on - 开启链接解析（主人专属）\n"
            "/link_off - 关闭链接解析（主人专属）"
        )
