"""
🎬 媒体解析模块 - 让小小南也能"看懂"图片和视频！

发图片或视频给小南，她会用 DeepSeek 的多模态视觉模型看懂内容，
然后用自己的性格语气说给你听~ (｡♥‿♥｡)

技术要点
────────
• 图片：直接以 base64 内联传给 DeepSeek 视觉模型
• 视频：Telegram 上下载后，用 ffmpeg 均匀抽帧，再把多张关键帧一起送进模型
• 人设：复用 personalities.get_prompt + helpers 的时间/常识上下文，回复带小南的性格

⚠️ 视频抽帧依赖 ffmpeg，未安装时会自动降级为"只用视频封面图"。
"""
import asyncio
import base64
import json
import logging
import os
import re
import shutil
import tempfile
import time
from datetime import datetime

import aiohttp
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes, MessageHandler, filters

from config import (
    DEEPSEEK_API_KEY, BOT_NAME_SHORT, DEFAULT_PERSONALITY,
    VISION_MODEL, MEDIA_DATA_DIR,
    MEDIA_CONTEXT_TTL, MEDIA_CONTEXT_MAX_BYTES,
)
from .base_module import BaseModule
from .data_manager import DataManager
from .net_helpers import get_proxy_url, find_ffmpeg, has_ffmpeg, apply_thinking_options
from .personalities import get_prompt
from .helpers import get_time_context, get_common_knowledge

logger = logging.getLogger(__name__)

# DeepSeek 视觉接口的硬限制（来自官方文档）
API_BASE = "https://api.deepseek.com/v1/chat/completions"
MAX_INLINE_IMAGE_BYTES = 32 * 1024 * 1024     # 单图 base64 上限 32 MiB
MAX_REQUEST_BODY_BYTES = 48 * 1024 * 1024     # 请求体上限 48 MiB
SUPPORTED_IMAGE_FORMATS = ("image/jpeg", "image/png", "image/gif", "image/webp")

# Telegram 官方 Bot API 的下载上限（未自建本地 API 服务器时）
TELEGRAM_DOWNLOAD_LIMIT = 20 * 1024 * 1024

# 抽帧参数
DEFAULT_MAX_FRAMES = 6          # 最多抽几帧送进模型
VIDEO_FRAME_SAMPLE_SECONDS = 2  # 每多少秒取一帧（上限内）

# 每用户调用间隔，防止有人连发图片刷爆额度
DEFAULT_COOLDOWN_SECONDS = 15


def _human_size(num_bytes: int) -> str:
    """把字节数变成好看的单位~"""
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.1f} {unit}"
        size /= 1024


def _has_ffmpeg() -> bool:
    """
    检查 ffmpeg 是否可用~

    用 net_helpers 的统一探测（配置 -> PATH -> 用户级注册表 PATH -> 常见位置）。
    不能只用 shutil.which：如果机器人是在装 ffmpeg 之前启动的终端里运行的，
    进程继承的 PATH 里没有它，shutil.which 会误判为"没装"。
    """
    return has_ffmpeg()


def _guess_format(data: bytes) -> str:
    """
    根据文件真实内容判断图片格式~

    DeepSeek 明确说明格式由内容判断而非扩展名，
    所以在发出去之前先自己确认一下，避免把视频容器当图片发。
    """
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return ""


class MediaParser(BaseModule):
    """媒体解析模块~ 让小南看懂图片和视频！"""

    name = "media_parser"
    description = "图片与视频内容解析（多模态视觉）"

    def __init__(self, bot_app=None):
        super().__init__(bot_app)
        self.dm = DataManager()
        self.application = None       # 由 register_handlers 注入，用来下载 Telegram 文件
        self._last_call = {}          # user_id -> 上次调用时间戳
        # 最近一次解析过的图片，供后续追问使用
        #   user_id -> {"data": bytes, "desc": str, "ts": float}
        # 只放内存不落盘：图片是隐私内容，重启即失也更安全
        self._image_context = {}
        self._ffmpeg = _has_ffmpeg()
        self._settings = self._load_settings()
        os.makedirs(MEDIA_DATA_DIR, exist_ok=True)

    # ──────────────────────────────────────────
    #  设置持久化
    # ──────────────────────────────────────────

    def _settings_path(self) -> str:
        return os.path.join(MEDIA_DATA_DIR, "settings.json")

    def _load_settings(self) -> dict:
        path = os.path.join(MEDIA_DATA_DIR, "settings.json")
        default = {
            "enabled": True,
            "max_frames": DEFAULT_MAX_FRAMES,
            "cooldown_seconds": DEFAULT_COOLDOWN_SECONDS,
        }
        try:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    default.update(json.load(f))
        except Exception as e:
            logger.error(f"读取媒体解析设置失败: {e}")
        return default

    def _save_settings(self):
        try:
            os.makedirs(MEDIA_DATA_DIR, exist_ok=True)
            with open(self._settings_path(), "w", encoding="utf-8") as f:
                json.dump(self._settings, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存媒体解析设置失败: {e}")

    # ──────────────────────────────────────────
    #  权限与限流
    # ──────────────────────────────────────────

    def _can_use(self, user_id: int) -> bool:
        """和 deepseek_chat 保持一致：主人或白名单用户才能用 AI 功能~"""
        return self.dm.is_owner(user_id) or self.dm.is_user_whitelisted(user_id)

    def _cooldown_left(self, user_id: int) -> int:
        """距离下次可用还剩几秒~ 主人不受限流影响"""
        cooldown = int(self._settings.get("cooldown_seconds", DEFAULT_COOLDOWN_SECONDS))
        if cooldown <= 0 or self.dm.is_owner(user_id):
            return 0
        last = self._last_call.get(user_id, 0)
        elapsed = time.time() - last
        if elapsed >= cooldown:
            return 0
        return int(cooldown - elapsed) + 1

    # ──────────────────────────────────────────
    #  图片上下文（供追问使用）
    # ──────────────────────────────────────────

    def _remember_image(self, user_id: int, data: bytes, desc: str = ""):
        """
        记住用户最近发的那张图~

        为什么要存？
          用户发图 -> 机器人描述 -> 用户接着问「图里那个是什么」
          如果只把描述当文本丢给 AI，它就看不到图了，只能干瞪眼回
          「我看不到图呀」——这正是用户实际遇到的问题。

        只放内存不落盘。图片属于隐私内容，而且重启后本来也没必要留着。
        """
        try:
            if not data:
                return
            if len(data) > MEDIA_CONTEXT_MAX_BYTES:
                logger.info(
                    f"图片 {_human_size(len(data))} 超过追问缓存上限"
                    f"（{_human_size(MEDIA_CONTEXT_MAX_BYTES)}），不缓存"
                )
                return
            if not _guess_format(data):
                # 不是受支持的图片格式（比如视频首帧以外的数据），不缓存
                return
            self._image_context[user_id] = {
                "data": data,
                "desc": desc or "",
                "ts": time.time(),
            }
        except Exception as e:
            logger.debug(f"缓存图片上下文失败: {e}")

    def get_image_context(self, user_id: int):
        """
        取出该用户最近缓存的图片（过期则返回 None）~

        Returns:
            dict: {"data": bytes, "desc": str}；没有或已过期返回 None
        """
        item = self._image_context.get(user_id)
        if not item:
            return None
        if time.time() - item.get("ts", 0) > MEDIA_CONTEXT_TTL:
            self._image_context.pop(user_id, None)
            return None
        return item

    async def answer_about_last_image(self, user_id: int, question: str) -> str:
        """
        结合用户最近发的那张图回答问题~

        Returns:
            str: 回答；没有可用图片或调用失败时返回空字符串
        """
        ctx = self.get_image_context(user_id)
        if not ctx:
            return ""

        note = (
            f"对方之前发过一张图，你当时是这样描述的：「{ctx['desc'][:200]}」。\n"
            f"现在对方针对这张图追问：{question}\n"
            "请看着图回答这个问题。"
        )
        try:
            return await self._vision_request([ctx["data"]], context_note=note, user_id=user_id)
        except Exception as e:
            logger.error(f"结合图片回答失败: {e}")
            return ""

    # ──────────────────────────────────────────
    #  注册处理器
    # ──────────────────────────────────────────

    def register_handlers(self, application):
        # Application 实例在这里拿得到（bot_app 是 ModuleLoader，没有 bot 属性）
        self.application = application

        logger.info(f"🎬 媒体解析模块初始化（ffmpeg: {'可用' if self._ffmpeg else '未安装'}）")

        application.add_handler(MessageHandler(filters.PHOTO, self.handle_photo))
        application.add_handler(MessageHandler(filters.VIDEO, self.handle_video))
        application.add_handler(MessageHandler(filters.ANIMATION, self.handle_animation))

        application.add_handler(CommandHandler("media", self.media_command))
        application.add_handler(CommandHandler("media_on", self.media_on_command))
        application.add_handler(CommandHandler("media_off", self.media_off_command))

    # ──────────────────────────────────────────
    #  各类媒体的入口
    # ──────────────────────────────────────────

    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """收到照片~"""
        await self._handle_media(update, context, kind="photo")

    async def handle_video(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """收到视频~"""
        await self._handle_media(update, context, kind="video")

    async def handle_animation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """收到 GIF 动图~（属于图片格式，可以直接送进模型）"""
        await self._handle_media(update, context, kind="animation")

    async def _handle_media(self, update: Update, context: ContextTypes.DEFAULT_TYPE, kind: str):
        """统一的媒体处理入口~"""
        message = update.effective_message
        user = update.effective_user
        if not message or not user:
            return

        # 功能总开关
        if not self._settings.get("enabled", True):
            return

        # 权限
        if not self._can_use(user.id):
            await message.reply_text(
                "呜… 小南现在还不认识你呢(｡•́︿•̀｡)\n"
                "图片解析要主人允许才能用哦~"
            )
            return

        # API Key 检查
        if not DEEPSEEK_API_KEY or DEEPSEEK_API_KEY == "YOUR_DEEPSEEK_API_KEY":
            await message.reply_text(
                "呜… 主人还没给小南配 DeepSeek Key 呢，\n"
                "所以小南看不懂图片啦(｡•́︿•̀｡)"
            )
            return

        # 限流
        left = self._cooldown_left(user.id)
        if left:
            await message.reply_text(f"慢一点嘛~ 还要等 {left} 秒才能再看一张哦(｡•́︿•̀｡)")
            return

        # 校验模型是否支持视觉
        if VISION_MODEL.lower() in ("deepseek-chat", "deepseek-reasoner"):
            await message.reply_text(
                f"呜… 当前的模型 `{VISION_MODEL}` 不支持看图呢\n"
                "请在 config.py 里把 VISION_MODEL 改成 `deepseek-flash`~"
            )
            return

        status = await message.reply_text("👀 小南正在看…")
        self._last_call[user.id] = time.time()

        try:
            image_bytes = None
            if kind == "photo":
                # 照片额外把原始字节带出来，存进上下文供后续追问
                result, image_bytes = await self._analyze_photo(message, user.id)
            elif kind == "animation":
                result = await self._analyze_animation(message, user.id)
            else:
                result = await self._analyze_video(message, user.id)

            if result is None:
                await status.edit_text("呜… 这个文件小南拿不到呢(｡•́︿•̀｡)")
                return

            # 先记住图片再发送，保证用户紧接着追问时上下文已经就位
            if image_bytes:
                self._remember_image(user.id, image_bytes, result)

            await self._deliver(status, result, user.id)

        except Exception as e:
            logger.error(f"媒体解析失败: {e}", exc_info=True)
            self.dm.add_error({"message": f"媒体解析错误: {e}", "user_id": user.id})
            await status.edit_text("呜… 小南看不太懂这张呢(｡•́︿•̀｡)\n再试一次好不好~")

    # ──────────────────────────────────────────
    #  分类型处理
    # ──────────────────────────────────────────

    async def _analyze_photo(self, message, user_id: int):
        """
        解析照片：取最大尺寸那张~

        Returns:
            (描述文本, 图片字节) —— 图片字节供调用方缓存，便于后续追问
        """
        photo = message.photo[-1]        # Telegram 已按尺寸升序排列
        data = await self._download_file(photo.file_id)
        if data is None:
            return None, None
        desc = await self._vision_request([data], context_note="这是一张图片", user_id=user_id)
        return desc, data

    async def _analyze_animation(self, message, user_id: int) -> str:
        """解析 GIF 动图：GIF 属于受支持格式，直接送~"""
        animation = message.animation
        data = await self._download_file(animation.file_id)
        if data is None:
            return None

        fmt = _guess_format(data)
        if fmt == "image/gif":
            return await self._vision_request(
                [data], context_note="这是一张 GIF 动图", user_id=user_id
            )

        # 有些"动图"实际是 MP4/WebM 视频，走抽帧
        return await self._video_pipeline(data, "这段动图", user_id)

    async def _analyze_video(self, message, user_id: int) -> str:
        """解析视频：下载后抽帧~"""
        video = message.video

        if video.file_size and video.file_size > TELEGRAM_DOWNLOAD_LIMIT:
            # 官方 Bot API 下不下来，退而求其次用封面图
            if video.thumbnail:
                data = await self._download_file(video.thumbnail.file_id)
                if data:
                    note = (
                        f"这是一段视频的封面图（视频时长 {video.duration or '未知'} 秒，"
                        f"大小 {_human_size(video.file_size)}，"
                        f"超过了 Telegram 的 20MB 下载上限，所以只能看到封面）"
                    )
                    return await self._vision_request([data], context_note=note, user_id=user_id)
            return (
                f"呜… 这个视频有 {_human_size(video.file_size)}，"
                f"超过 Telegram 官方接口 20MB 的下载上限啦，小南拿不到(｡•́︿•̀｡)"
            )

        data = await self._download_file(video.file_id)
        if data is None:
            return None
        return await self._video_pipeline(
            data, f"这段视频（时长 {video.duration or '未知'} 秒）", user_id
        )

    async def _video_pipeline(self, data: bytes, label: str, user_id: int) -> str:
        """视频处理流水线：抽帧 -> 送模型~"""
        if not self._ffmpeg:
            return (
                "呜… 小南的电脑上没装 ffmpeg，\n"
                "所以没办法把视频拆成一帧一帧来看(｡•́︿•̀｡)\n\n"
                "装好 ffmpeg 就能看懂视频啦~ 安装方法：\n"
                "`winget install Gyan.FFmpeg`"
            )

        frames = await self._extract_frames(data)
        if not frames:
            return "呜… 这个视频小南一帧都读不出来呢(｡•́︿•̀｡)"

        note = (
            f"这是从{label}里按时间顺序均匀抽取的 {len(frames)} 张关键帧。"
            "请把它们连起来理解，描述视频里发生了什么。"
        )
        return await self._vision_request(frames, context_note=note, user_id=user_id)

    # ──────────────────────────────────────────
    #  下载与抽帧
    # ──────────────────────────────────────────

    async def _download_file(self, file_id: str):
        """从 Telegram 下载文件~（走和主程序相同的代理连接）"""
        if self.application is None:
            logger.error("Application 未注入，无法下载文件")
            return None
        try:
            tg_file = await self.application.bot.get_file(file_id)
            return bytes(await tg_file.download_as_bytearray())
        except Exception as e:
            logger.error(f"下载文件失败: {e}")
            return None

    async def _extract_frames(self, video_bytes: bytes) -> list:
        """用 ffmpeg 均匀抽帧，返回 JPEG 字节列表~"""
        max_frames = int(self._settings.get("max_frames", DEFAULT_MAX_FRAMES))
        tmpdir = tempfile.mkdtemp(prefix="nan_video_")
        try:
            video_path = os.path.join(tmpdir, "input.mp4")
            with open(video_path, "wb") as f:
                f.write(video_bytes)

            # 先取时长，决定抽帧间隔
            duration = await self._probe_duration(video_path)
            if duration and duration > 0:
                interval = max(1.0, duration / max_frames)
            else:
                interval = VIDEO_FRAME_SAMPLE_SECONDS

            out_pattern = os.path.join(tmpdir, "frame_%02d.jpg")
            # 用解析出来的完整路径，而不是裸 "ffmpeg"：
            # 机器人可能是在装 ffmpeg 之前启动的终端里跑的，PATH 里没有它
            ffmpeg_exe = find_ffmpeg() or "ffmpeg"
            cmd = [
                ffmpeg_exe, "-hide_banner", "-loglevel", "error",
                "-i", video_path,
                "-vf", f"fps=1/{interval:.3f},scale='min(1280,iw)':-2",
                "-frames:v", str(max_frames),
                "-q:v", "4",
                "-y", out_pattern,
            ]
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await asyncio.wait_for(proc.communicate(), timeout=180)
            if proc.returncode != 0:
                logger.error(f"ffmpeg 抽帧失败: {stderr.decode('utf-8', 'replace')[:400]}")
                return []

            frames = []
            for name in sorted(os.listdir(tmpdir)):
                if not name.startswith("frame_"):
                    continue
                with open(os.path.join(tmpdir, name), "rb") as f:
                    frames.append(f.read())
            return frames
        except asyncio.TimeoutError:
            logger.error("ffmpeg 抽帧超时（视频可能过大）")
            return []
        except Exception as e:
            logger.error(f"抽帧过程出错: {e}")
            return []
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    async def _probe_duration(self, video_path: str):
        """用 ffprobe 拿视频时长（秒）~"""
        # 从 ffmpeg 的路径推出同目录下的 ffprobe
        ffmpeg_exe = find_ffmpeg()
        if not ffmpeg_exe:
            return None
        ffprobe = os.path.join(
            os.path.dirname(ffmpeg_exe),
            "ffprobe.exe" if os.name == "nt" else "ffprobe",
        )
        if not os.path.isfile(ffprobe):
            ffprobe = shutil.which("ffprobe")
        if not ffprobe:
            return None
        try:
            proc = await asyncio.create_subprocess_exec(
                ffprobe, "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                video_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
            return float(stdout.decode().strip())
        except Exception:
            return None

    # ──────────────────────────────────────────
    #  调用视觉模型
    # ──────────────────────────────────────────

    def _build_system_prompt(self, user_id: int) -> str:
        """构建带小南人设的系统提示~"""
        user_data = self.dm.get_user_data(user_id)
        personality = user_data.get("personality", DEFAULT_PERSONALITY)

        parts = [
            get_prompt(personality, BOT_NAME_SHORT),
            get_time_context(),
            get_common_knowledge(),
            (
                "\n\n【看图任务】\n"
                "对方发来了一张图片或一段视频，你看懂之后要用自己的语气讲给对方听。\n"
                "要求：\n"
                "1. 先客观说清楚你看到了什么（画面内容、文字、场景），不要编造看不清的细节。\n"
                "2. 然后用你现在的性格语气说出来，像真人聊天一样自然。\n"
                "3. 不要用括号描写动作或表情。\n"
                "4. 长度控制在 200 字以内，别写成流水账。\n"
                "5. 如果图片里有文字，把关键文字念出来。"
            ),
        ]
        return "\n\n".join(p for p in parts if p)

    def _build_user_content(self, images: list, context_note: str) -> list:
        """构建多模态 user 消息内容块~"""
        content = [{"type": "text", "text": context_note}]
        total = 0
        for idx, data in enumerate(images, 1):
            fmt = _guess_format(data)
            if not fmt:
                logger.warning(f"第 {idx} 张图格式无法识别，跳过")
                continue
            if len(data) > MAX_INLINE_IMAGE_BYTES:
                logger.warning(f"第 {idx} 张图 {_human_size(len(data))} 超过 32MiB 上限，跳过")
                continue

            b64 = base64.b64encode(data).decode("ascii")
            total += len(b64)
            if total > MAX_REQUEST_BODY_BYTES:
                logger.warning("图片总量超过 48MiB 请求体上限，截断")
                break

            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:{fmt};base64,{b64}",
                    "detail": "low" if len(images) > 3 else "original",
                },
            })
        return content

    async def _vision_request(self, images: list, context_note: str, user_id: int = 0) -> str:
        """真正调用 DeepSeek 视觉接口~"""
        content = self._build_user_content(images, context_note)
        if len(content) <= 1:
            return "呜… 这些文件小南一个都读不出来呢(｡•́︿•̀｡)"

        payload = {
            "model": VISION_MODEL,
            "messages": [
                {"role": "system", "content": self._build_system_prompt(user_id)},
                {"role": "user", "content": content},
            ],
            # 1600 是留给"万一开了思考"的余量；关掉思考后实际只用几十个 token
            "max_tokens": 1600,
            "temperature": 1.0,
        }
        # 按配置决定是否开启思考（默认关闭，避免思考吃光额度导致正文为空）
        apply_thinking_options(payload)

        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json",
        }

        proxy = get_proxy_url() or None
        timeout = aiohttp.ClientTimeout(total=180, connect=30)

        async with aiohttp.ClientSession(timeout=timeout, trust_env=True) as session:
            async with session.post(
                API_BASE, headers=headers, json=payload, proxy=proxy
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    logger.error(f"视觉接口返回 {resp.status}: {error_text[:500]}")
                    if resp.status == 401:
                        return "呜… DeepSeek Key 好像不对呢，主人检查一下吧(｡•́︿•̀｡)"
                    if resp.status == 429:
                        return "呜… 小南被限流了，等一下下再看好不好~"
                    return "呜… 小南看图片的时候出错了(｡•́︿•̀｡)"

                data = await resp.json()

        message = data["choices"][0]["message"]
        text = (message.get("content") or "").strip()

        # 防御：如果思考模式没关，模型可能把额度全花在 reasoning 上导致 content 为空。
        # 这时**不要**把 reasoning_content 当正文发出去 —— 那是模型的内部独白，
        # 用户会看到「让我再想想」「要确保每句最多20字」这种莫名其妙的内容。
        # 宁可回一句体面的话，也不泄露思考过程。
        if not text:
            finish = data["choices"][0].get("finish_reason")
            reasoning_len = len((message.get("reasoning_content") or ""))
            logger.warning(
                f"模型返回空正文 (finish_reason={finish}, 思考内容 {reasoning_len} 字符)"
                " —— 多半是思考吃光了 max_tokens；"
                "可在 config.py 里设 DISABLE_THINKING = True 避免"
            )
            return "呜… 小南看了半天没看懂，换一张试试好不好~"

        usage = data.get("usage", {})
        logger.info(
            f"👁️ 媒体解析完成 | 图片 {len(content) - 1} 张 | "
            f"prompt={usage.get('prompt_tokens')} completion={usage.get('completion_tokens')}"
        )
        return text

    # ──────────────────────────────────────────
    #  输出
    # ──────────────────────────────────────────

    async def _deliver(self, status_message, text: str, user_id: int):
        """把结果发出去~ 太长就分条，并清理 AI 可能带出的转义符"""
        from .helpers import unescape_text
        text = unescape_text(text).strip()

        # 去掉模型可能加的动作描写括号（项目说话规则禁止括号描写）
        text = re.sub(r"（[^）]{0,20}）", "", text).strip()
        text = re.sub(r"\([^)]{0,20}\)", "", text).strip()
        if not text:
            text = "小南看完了，但不知道该怎么形容呢~"

        if len(text) <= 4000:
            await status_message.edit_text(text)
            return

        # 太长：第一条编辑进去，剩下的分条发
        chunks = [text[i:i + 3500] for i in range(0, len(text), 3500)]
        await status_message.edit_text(chunks[0])
        for chunk in chunks[1:]:
            await status_message.reply_text(chunk)

    # ──────────────────────────────────────────
    #  命令
    # ──────────────────────────────────────────

    async def media_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/media - 查看媒体解析状态~"""
        user_id = update.effective_user.id
        enabled = self._settings.get("enabled", True)
        cooldown = self._settings.get("cooldown_seconds", DEFAULT_COOLDOWN_SECONDS)

        lines = [
            "🎬 媒体解析状态~",
            "",
            f"├─ 功能开关：{'✅ 已开启' if enabled else '⛔ 已关闭'}",
            f"├─ 视觉模型：`{VISION_MODEL}`",
            f"├─ ffmpeg：{'✅ 可用（支持视频抽帧）' if self._ffmpeg else '❌ 未安装（视频只能看封面）'}",
            f"├─ 视频抽帧数：最多 {self._settings.get('max_frames', DEFAULT_MAX_FRAMES)} 帧",
            f"└─ 调用间隔：{cooldown} 秒",
            "",
            "直接发图片或视频给小南就能解析啦~",
        ]

        if not self._can_use(user_id):
            lines.append("\n⚠️ 你目前不在白名单里，暂时用不了这个功能哦~")

        if not self._ffmpeg:
            lines.append("\n💡 想让小南看懂视频，先装 ffmpeg：\n`winget install Gyan.FFmpeg`")

        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

    async def media_on_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/media_on - 开启媒体解析（仅主人）~"""
        if not self.dm.is_owner(update.effective_user.id):
            await update.message.reply_text("这个命令只有主人能用哦~")
            return
        self._settings["enabled"] = True
        self._save_settings()
        await update.message.reply_text("✅ 媒体解析已开启~ 发图片给小南试试吧！")

    async def media_off_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/media_off - 关闭媒体解析（仅主人）~"""
        if not self.dm.is_owner(update.effective_user.id):
            await update.message.reply_text("这个命令只有主人能用哦~")
            return
        self._settings["enabled"] = False
        self._save_settings()
        await update.message.reply_text("⛔ 媒体解析已关闭~ 小南不会再自动看图啦。")

    def get_help_text(self) -> str:
        return (
            "/media - 查看媒体解析状态~\n"
            "（直接发图片或视频，小南就会看懂并讲给你听~）\n"
            "/media_on - 开启媒体解析（主人专属）\n"
            "/media_off - 关闭媒体解析（主人专属）"
        )
