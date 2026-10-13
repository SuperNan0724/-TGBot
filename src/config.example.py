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
