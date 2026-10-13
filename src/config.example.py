"""
配置文件模板~ 请复制成 config.py 再填写你的小秘密哦(｡♥‿♥｡)

使用方法
────────
    Windows:  copy config.example.py config.py
    Linux/Mac: cp config.example.py config.py

然后编辑 config.py，把下面标着【必填】的地方换成你自己的值。

⚠️ config.py 已被 .gitignore 忽略，**永远不要**把它提交到仓库！
   如果密钥曾经被提交过，删掉文件是没用的（git 历史里还在），
   必须去 @BotFather 用 /revoke 换一把新的 Token。
"""
import os

# ══════════════════════════════════════════════
#  🔑 必填项
# ══════════════════════════════════════════════

# 【必填】Telegram Bot Token
# 获取方式：在 Telegram 搜索 @BotFather → 发送 /newbot → 按提示创建 → 复制 Token
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"

# 【必填】你的 Telegram 数字 ID
# 获取方式：在 Telegram 搜索 @userinfobot → 点 START → 它会回复一串数字
# 不填的话，主人专属命令（如收藏贴纸、管理白名单）将不可用
BOT_OWNER_ID = None

# 【可选】DeepSeek API Key
# 获取方式：https://platform.deepseek.com → API Keys → 创建
# 不填的话机器人能正常启动，但 AI 聊天 / 性格切换 / 思考 / 女友模式 不可用
DEEPSEEK_API_KEY = "YOUR_DEEPSEEK_API_KEY"

# ══════════════════════════════════════════════
#  🔮 DeepSeek 接口（一般不用改）
# ══════════════════════════════════════════════
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"

# ══════════════════════════════════════════════
#  🌐 网络代理（国内环境必看！）
# ══════════════════════════════════════════════
# 为什么需要它？
#   python-telegram-bot 底层用 httpx，而 httpx **默认不读取系统代理**。
#   如果你靠代理软件（Clash/v2ray 等）的系统代理模式上网，机器人会绕过
#   代理直连 api.telegram.org，然后超时启动失败：
#       httpx.ConnectTimeout -> telegram.error.TimedOut
#   典型症状：命令行能打开 Telegram 网页，机器人却连不上。
#
# 两种用法：
#   1) 留空 + PROXY_AUTO_DETECT = True  → 自动读取 Windows 系统代理（省事）
#   2) 显式填写 PROXY_URL               → 优先级更高，最稳妥
#
# 例如 Clash 默认端口：
#   PROXY_URL = "http://127.0.0.1:7897"
PROXY_URL = ""
PROXY_AUTO_DETECT = True

# ══════════════════════════════════════════════
#  🤖 机器人外观
# ══════════════════════════════════════════════
BOT_NAME = "小南专属TGbot"        # 机器人的全称（显示在日志里）
BOT_NAME_SHORT = "小南"           # 机器人的简称（对话中显示的名字）
BOT_OWNER_NAME = "主人"           # 主人的名字（显示在欢迎消息等地方）
DEFAULT_PERSONALITY = "default"   # 默认性格 ID（对应 personalities.py 中的 id）
MAX_HISTORY_LENGTH = 10           # 每个用户最多保留的对话历史条数

# ══════════════════════════════════════════════
#  💾 数据文件路径（相对 src/ 目录，一般不用改）
# ══════════════════════════════════════════════
DATA_DIR = "data"
WHITELIST_FILE = "data/whitelist.json"
ADMIN_FILE = "data/admins.json"
USER_DATA_FILE = "data/user_data.json"
ERROR_LOG_FILE = "data/errors.json"
BACKUP_DIR = "data/backups"

# ══════════════════════════════════════════════
#  💰 付费白名单 / 发卡平台
# ══════════════════════════════════════════════
PAID_WHITELIST_FILE = "data/paid_whitelist.json"
PRODUCTS_FILE = "data/products.json"

# ══════════════════════════════════════════════
#  🎬 媒体解析（图片 / 视频理解）
# ══════════════════════════════════════════════
# 让机器人能"看懂"你发的图片和视频~
#
# VISION_MODEL 必须是**支持视觉**的模型：
#   ✅ deepseek-flash                       ← 当前支持视觉的模型（推荐）
#   ❌ deepseek-chat / deepseek-reasoner    ← 纯文本模型，发图片会报错
#
# 计费提醒：deepseek-flash 是推理模型，会先"思考"再回答，
# 思考过程也计入 token，所以看图会消耗额度，请留意用量~
VISION_MODEL = "deepseek-flash"

# 媒体数据目录（存放解析设置等）
MEDIA_DATA_DIR = "data/media"

# 图片上下文保留时间（秒）
# 发图之后，在这个时间窗口内继续追问「图里那个是什么」，
# 机器人还能记得那张图、结合图片回答。超时后自动丢弃。
# 图片只放在内存里，不落盘，重启即失。
MEDIA_CONTEXT_TTL = 600

# 单张图最多缓存多少字节（超过就不缓存，只是不能追问，不影响首次解析）
# 默认 5MB —— 太大了白占内存，而且视觉接口本身也会缩放
MEDIA_CONTEXT_MAX_BYTES = 5 * 1024 * 1024

# ══════════════════════════════════════════════
#  🧠 思考模式（deepseek-flash 的推理开关）
# ══════════════════════════════════════════════
# deepseek-flash 默认**开启**思考模式，且强度默认 high：
# 回答前先输出一大段思维链，这段内容同样计入 token 计费。
#
# 实测同一张图的看图回答：
#   思考开启 : 4.1秒 / 517 completion tokens
#   思考关闭 : 1.3秒 /  34 completion tokens   ← 回答质量没差别
#
# 而且思考模式有个坑：它会把 max_tokens 额度耗在思考上，
# 导致 content 为空、推理内容反而泄漏成"正文"发给用户。
# 描述图片、写简介、报元数据这类任务不需要推理，关掉更划算。
#
# True = 关闭思考（默认，快且省）
# False = 保留思考（需要模型"想清楚"的复杂任务可以打开）
DISABLE_THINKING = True

# 当 DISABLE_THINKING = False 时的思考强度：low / high / max
# （官方映射：minimal/low→low，medium/high→high，max/ultra→max）
REASONING_EFFORT = "low"

# 说明：思考模式下**不支持 temperature 参数**（传了也不生效、不报错）。
# 本项目里 temperature 只在关闭思考时才真正起作用。

# ══════════════════════════════════════════════
#  🔗 链接解析（自动识别链接里的图片/视频）
# ══════════════════════════════════════════════
# 发一条链接给小南，她会自动识别平台、提取媒体、生成简介~
#
# 覆盖范围：B站 / YouTube / 抖音 / 快手 / 小红书 / Twitter/X / 微博 / 知乎…
#          以及 .jpg/.png/.gif/.mp4/.webm 等直链
#
# 依赖 yt-dlp（已写进 requirements.txt，装依赖时会自动装上）

# 总开关
LINK_PARSER_ENABLED = True

# 视频下载体积上限（MB）
# Telegram Bot 上传文件上限是 50MB，所以默认留出余量设为 48MB。
# 超过这个体积的视频不会下载，改为只发原始链接（省流量省时间）。
LINK_MAX_DOWNLOAD_MB = 48

# 是否用 AI 生成简介（除平台元数据之外的那段小南口吻介绍）
# 关掉就只发平台自带的标题/作者/时长，不消耗 AI 额度
LINK_AI_SUMMARY = True

# 同一用户两次解析之间的间隔（秒）
# 防止有人连发链接刷 AI 额度；主人不受限制
LINK_COOLDOWN_SECONDS = 20

# 单条消息里最多解析几个链接（防止一条消息塞 10 个链接把机器人拖垮）
LINK_MAX_PER_MESSAGE = 2

# yt-dlp 提取信息的超时（秒）
LINK_EXTRACT_TIMEOUT = 45

# ══════════════════════════════════════════════
#  🧩 第三方解析接口（补 yt-dlp 的短板）
# ══════════════════════════════════════════════
# 为什么需要它？
#   yt-dlp 覆盖了上千个站点，但抖音/快手/小红书这类国内平台有强反爬，
#   yt-dlp 的提取器目前取不到播放流（官方 issue 也承认抖音 extractor 不可用）。
#   所以这些平台走第三方解析接口。
#
# 默认用 tikwm.com —— 公开可用、返回标准 JSON、不需要逆向加密。
# （相比之下 KuKuTool 需要复现 AES 加密 + Cookie 会话，属于逆向私有接口，
#   对方一改版就失效，所以没采用。）
#
# 想换服务只改下面的 URL 即可：响应字段会按**键名递归匹配**自动适配，
# 不要求服务商沿用同一套字段名。
LINK_THIRD_PARTY_ENABLED = True

# 接口地址，{url} 会被替换成经过 URL 编码的目标链接
LINK_THIRD_PARTY_API = "https://www.tikwm.com/api/?url={url}"

# 哪些平台走第三方接口（这些平台 yt-dlp 基本取不到流）
LINK_THIRD_PARTY_PLATFORMS = ("抖音", "快手", "小红书", "TikTok", "Instagram")

# 接口超时（秒）
LINK_THIRD_PARTY_TIMEOUT = 30

# ══════════════════════════════════════════════
#  🚫 明确不支持的平台
# ══════════════════════════════════════════════
# 这些平台会**直接回复原因**，不再尝试解析（省得白等一轮超时）。
#
# 抖音为什么在列表里？实测结论：
#   抖音的风控叫 ArgusSecurityPlugin，它要求在请求里带 `Uifid`。
#   而 Uifid **不在 cookie 里** —— 它是页面 JS 运行时生成、作为请求头发出去的。
#   实测对比（用的是真实浏览器登录后的完整 cookie）：
#       带 cookie   -> HTTP 403  "Blocked by ArgusSecurityPlugin Uifid Not Found"
#       不带 cookie -> HTTP 403  "Blocked by ArgusSecurityPlugin Uifid Not Found"
#   两者**完全相同**，说明抖音压根没校验 cookie。
#   要过这道风控必须复现它混淆过的 JS + a_bogus 签名算法，
#   成本高且对方一改版就失效，所以不做。
LINK_UNSUPPORTED_PLATFORMS = ("抖音", "快手", "小红书")

# 命中不支持平台时回复的话术
LINK_UNSUPPORTED_REPLY = (
    "🙏 抱歉，{platform}的链接小南解析不了\n"
    "   ├─ 原因：该平台的风控要求在请求里带 JS 运行时生成的设备指纹，\n"
    "   │        普通 HTTP 请求（含配置 Cookie）都会被拦，实测确认\n"
    "   ├─ 支持：B站 / YouTube / 直链图片视频 / 普通网页 都可以~\n"
    "   └─ 链接：{url}"
)

# ══════════════════════════════════════════════
#  🍪 平台 Cookie（抖音等需要登录态的平台）
# ══════════════════════════════════════════════
# 为什么需要它？
#   抖音有 ArgusSecurityPlugin（自家的风控盾）。不带 cookie 直接请求它的 API：
#       HTTP 403  "Blocked by ArgusSecurityPlugin Uifid Not Found"
#   它要的是 Uifid 这类**设备指纹**，纯 HTTP 请求伪造不出来，
#   必须用真实浏览器登录后拿到的 cookie。
#
# 怎么获取（Chrome / Edge）：
#   1. 浏览器打开 https://www.douyin.com 并登录
#   2. F12 打开开发者工具 -> Network 标签 -> 刷新页面
#   3. 点任意一个 douyin.com 的请求 -> Request Headers
#   4. 找到 Cookie: 那一整行，复制它的值
#
# ⚠️ 安全提醒：这个 cookie 等同于你的**登录态**，拿到的人可以操作你的账号。
#    本文件已被 .gitignore 忽略，不要提交、不要外发。
#    cookie 会过期，失效后需要重新获取。
DOUYIN_COOKIE = ""

# 请求抖音时是否带上上面的 cookie
DOUYIN_USE_COOKIE = True

# ══════════════════════════════════════════════
#  🎞️ ffmpeg 路径（自动检测失败时才需要手填）
# ══════════════════════════════════════════════
# 为什么需要它？
#   很多站点（B站就是典型）**不提供音视频合一的流**，必须分别下载视频和
#   音频再用 ffmpeg 合并。找不到 ffmpeg，这些视频就完全下载不下来，
#   只能退化成"发个链接"。
#
#   自动检测顺序：
#     1. 下面这个配置项（目录或 exe 完整路径）
#     2. 当前进程的 PATH
#     3. 用户级 PATH（读注册表，能解决「装了 ffmpeg 但当前终端不知道」）
#     4. 常见安装位置（C:\ffmpeg\bin 等）
#
# 留空即自动检测。如果日志提示找不到 ffmpeg，把 bin 目录填在这里：
#   FFMPEG_PATH = r"C:\ffmpeg\bin"
FFMPEG_PATH = ""

# 发卡平台回调服务器
#
# ⚠️ CALLBACK_SECRET 是回调接口的**唯一凭据**！
#    发卡平台在通知"有人付款成功"时必须带上它才能通过校验。
#    如果这里留成默认值，任何人都能 POST 一个伪造的"支付成功"回调，
#    给自己凭空发激活码、免费进白名单——所以默认配置下回调服务器
#    会直接拒绝启动，直到你把它改成真正的随机字符串。
#
#    改法示例（随便一串随机字符）：
#        CALLBACK_SECRET = "a7f3k9x2m5q8w1e4"
#
#    接发卡平台时，在平台后台把回调地址设为：
#        http://<你的公网地址>:8080/callback
#    并把同一个密钥填到平台的"回调密钥"字段里。
#
#    如果你只是自己用、不接发卡平台，保持原样即可（回调服务不会启动，
#    其它功能完全不受影响）。
CALLBACK_HOST = "127.0.0.1"
CALLBACK_PORT = 8080
CALLBACK_SECRET = "CHANGE_ME_TO_A_RANDOM_SECRET"

# 密钥还是占位值时，是否禁止启动回调服务器（强烈建议保持 True）
DISABLE_CALLBACK_SERVER_IF_UNSET = True

# ══════════════════════════════════════════════
#  🧩 模块配置
# ══════════════════════════════════════════════
# 模块已改为自动扫描加载~
# 把 .py 文件丢进 src/modules/ 目录就会自动加载啦！(๑•̀ㅂ•́)و✧
