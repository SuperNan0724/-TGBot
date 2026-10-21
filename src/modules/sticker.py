"""
🎨 贴纸模块~ 让小南也能玩贴纸！(｡♥‿♥｡)

功能：
- 接收贴纸消息，识别贴纸信息
- 回复贴纸相关的可爱消息
- /add_sticker 主人命令 - 添加贴纸到收藏库
- /sticker_list 查看收藏的贴纸
- /del_sticker 删除收藏的贴纸
- 自动回复贴纸消息（随机从收藏库中选择）
"""
import logging
import json
import os
import re
import random
import hashlib
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

from .base_module import BaseModule
from .data_manager import DataManager

logger = logging.getLogger(__name__)

# 贴纸收藏数据文件
STICKER_FILE = "data/stickers.json"

# 收藏库总量上限~
#
# 为什么要有上限：以前谁都能一直 /add_sticker、一直导入贴纸集，stickers.json
# 只增不减——文件越长，每次 /sticker_list、每个贴纸消息的 random.choice 前
# 都要把整份 JSON 读进内存解析一遍；/sticker_list 的翻页也会翻到几万页，
# 删除菜单更是每页都要重读一遍。收藏库是主人一个人的（命令仅主人可用），
# 所以"每人上限"就等于"总量上限"。
#
# 500 这个数是怎么来的：Telegram 一个满编静态贴纸集是 120 张（动态/视频集 50 张），
# 500 张够放 4 个满编集，日常够用；按每条约 250 字节算文件最大约 150KB，
# 读一次仍然是毫秒级，/sticker_list 也才 100 页（每页 5 个）。
MAX_STICKERS_TOTAL = 500

# callback_data 里用的稳定标识：file_id 的短哈希（10 位十六进制 = 40 bit）
# Telegram 规定 callback_data ≤ 64 字节，而 file_id 本身就有 60~80 字节，塞不进去。
_SID_RE = re.compile(r"^[0-9a-f]{10}$")


def _sticker_sid(file_id) -> str:
    """给一张贴纸算稳定短标识，专门用来在按钮里指认"是哪一张"~

    为什么不用"全局索引"：索引只是"当前列表里的第几个"。两个窗口/两个人先后
    打开同一个删除页时，中间只要有人增删过贴纸，同一个索引就指向了另一张，
    点"删除 #3"会删掉第 3 个位置上的**别的**贴纸——删错东西，且删掉就没了。
    短哈希是内容标识：按钮永远只对应"这一张"，它已经被删掉时只会提示
    "已经不存在了"，绝不会误删别的贴纸。

    40 bit 够不够：收藏库上限 500 张，两两碰撞概率约 500²/2^41 ≈ 6e-8，
    实际等于不会发生；真撞了也只是可能删掉哈希相同的另一张，概率可忽略。
    """
    return hashlib.sha1(str(file_id).encode("utf-8")).hexdigest()[:10]


def _make_sticker(sticker, fallback_set_name: str = "未知") -> dict:
    """把一张 Telegram 贴纸规整成字段齐全的字典~

    导入路径和 /add_sticker 以前各自手拼字典，漏字段（比如 set_name）时，
    以后 /sticker_list 或随机回复里就是 KeyError；file_id 不是字符串时
    `s["file_id"][:20]` 还会直接 TypeError。所有写入路径统一走这里，
    拿不到 file_id 就返回 {}，让调用方跳过、不写进收藏库喵~
    """
    file_id = getattr(sticker, "file_id", None)
    if not isinstance(file_id, str) or not file_id:
        return {}

    set_name = getattr(sticker, "set_name", None)
    if not isinstance(set_name, str) or not set_name:
        set_name = fallback_set_name

    emoji = getattr(sticker, "emoji", None)
    if not isinstance(emoji, str):
        emoji = ""

    def _int_attr(name: str) -> int:
        value = getattr(sticker, name, 0)
        return value if isinstance(value, int) else 0

    return {
        "file_id": file_id,
        "sid": _sticker_sid(file_id),
        "set_name": set_name,
        "emoji": emoji,
        "width": _int_attr("width"),
        "height": _int_attr("height"),
        "is_animated": bool(getattr(sticker, "is_animated", False)),
        "is_video": bool(getattr(sticker, "is_video", False)),
        "added_at": datetime.now().isoformat(),
    }


def _entry_sid(entry: dict) -> str:
    """取一条已收藏贴纸的短标识（老数据没有 sid 字段就用 file_id 现算）~"""
    sid = entry.get("sid")
    if isinstance(sid, str) and _SID_RE.match(sid):
        return sid
    return _sticker_sid(entry.get("file_id", ""))


def _short_set_name(name, limit: int = 40) -> str:
    """贴纸集名字的显示版~

    正常贴纸集名是 Telegram 给的、很短；但数据文件被手改过（或者老版本写进来的）
    可能是超长字符串，10 个条目一拼就能把 /sticker_list、删除菜单顶过 4096 字的
    Telegram 单条上限，整条消息被拒。这里统一截断。
    """
    text = name if isinstance(name, str) and name else "未知"
    return text if len(text) <= limit else text[:limit] + "…"


def _load_stickers() -> dict:
    """加载贴纸收藏库~

    这里只保证"返回一个带 stickers 列表的 dict"：文件被手改坏、写到一半、
    或者某些条目不是对象 / 没有 file_id（下载或导入中断时的残留），
    都不该让每个命令在 data["stickers"] 上抛 KeyError / AttributeError 喵~
    """
    data = None
    if os.path.exists(STICKER_FILE):
        try:
            with open(STICKER_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            logger.error(f"加载贴纸数据失败: {e}")
    if not isinstance(data, dict):
        data = {}
    stickers = data.get("stickers")
    if not isinstance(stickers, list):
        stickers = []
    # file_id 必须是**非空字符串**：以前只判断 `s.get("file_id")` 是否为真，
    # 手改成数字 123 也能过关，然后 s["file_id"][:20] 直接 TypeError 炸掉整个列表
    data["stickers"] = [
        s for s in stickers
        if isinstance(s, dict) and isinstance(s.get("file_id"), str) and s["file_id"]
    ]
    return data


def _save_stickers(data: dict):
    """保存贴纸收藏库~

    先写同目录临时文件、再 os.replace 原子替换：
    旧写法 open("w") 会立刻把原文件清空，写到一半断电/进程被杀，stickers.json
    就变成半截 JSON——下次 _load_stickers 解析失败、返回空列表，主人会以为
    "收藏全没了"（其实只是文件坏了）。原子替换下最坏情况是保留上一次的完整内容。
    """
    try:
        parent = os.path.dirname(STICKER_FILE)
        if parent:
            os.makedirs(parent, exist_ok=True)
        tmp_path = f"{STICKER_FILE}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, STICKER_FILE)
        return True
    except Exception as e:
        logger.error(f"保存贴纸数据失败: {e}")
        return False


# ===== 动态回复语生成 =====

# 根据 emoji 分类的回复语
EMOJI_REPLIES = {
    # ❤️ 爱心/喜欢类
    "❤️": ["哇~ 收到爱心贴纸！小南也超喜欢你！(｡♥‿♥｡)", "爱心贴纸~ 好甜呀！", "呜呜收到爱心了！小南好开心！"],
    "💕": ["贴纸好甜~ 小南的心都要化了！", "甜甜的贴纸！小南超爱！"],
    "💖": ["闪闪发光的爱心！小南好喜欢~", "这个爱心贴纸好漂亮！"],
    "💗": ["粉粉嫩嫩的爱心~ 和小南一样可爱！", "爱心贴纸收到！小南也爱你！"],
    "💓": ["心跳加速的贴纸！小南好激动~", "呜呜这个贴纸太甜了！"],
    "💛": ["黄色的爱心~ 暖暖的！", "暖心的贴纸！小南好喜欢！"],
    "💙": ["蓝色的爱心~ 好优雅！", "优雅的爱心贴纸~ 小南收藏啦！"],
    "💚": ["绿色的爱心~ 充满活力！", "活力的爱心贴纸！小南元气满满！"],
    "💜": ["紫色的爱心~ 好神秘！", "神秘的爱心贴纸~ 小南好喜欢！"],
    "🖤": ["黑色的爱心~ 好酷！", "酷酷的爱心贴纸！小南也觉得好帅！"],
    "🤍": ["白色的爱心~ 纯洁又美好！", "纯洁的爱心贴纸~ 小南好感动！"],
    "🤎": ["棕色的爱心~ 好温暖！", "温暖的爱心贴纸！小南收到啦~"],
    
    # 😊 笑脸/开心类
    "😊": ["看到笑脸贴纸~ 小南也开心起来啦！", "笑脸贴纸！今天也是好心情~"],
    "😄": ["大大的笑脸！小南也跟着笑啦~", "好开心的贴纸！小南也超开心！"],
    "😁": ["嘿嘿~ 这个笑脸好有趣！", "笑脸贴纸~ 小南也笑一个！"],
    "😂": ["笑到流泪的贴纸！小南也笑死啦~", "哈哈哈哈这个贴纸太搞笑了！"],
    "🤣": ["笑到打滚的贴纸！小南也笑翻啦~", "笑死啦~ 这个贴纸太有趣了！"],
    "😍": ["哇~ 这个贴纸好可爱！小南也心动了！", "心动的贴纸！小南也好喜欢！"],
    "🥰": ["好甜好甜的贴纸~ 小南被治愈了！", "治愈系贴纸！小南满血复活！", "好可爱的贴纸！小南被萌翻了！", "可爱到犯规的贴纸！小南血条清空！"],
    "😘": ["飞吻贴纸！小南接住啦~ 啾咪！", "收到飞吻~ 小南也亲亲你！"],
    "😋": ["好吃的贴纸~ 小南也想吃！", "看起来好好吃的贴纸！小南馋了~"],
    "😎": ["酷酷的贴纸！小南也觉得好帅！", "帅气的贴纸~ 小南被帅到了！"],
    "🤩": ["闪闪发光的贴纸！小南被闪到了~", "好闪耀的贴纸！小南眼睛都亮了！"],
    "🥳": ["庆祝的贴纸！小南也来一起嗨！", "派对贴纸~ 小南也来跳舞！"],
    "😇": ["天使贴纸~ 小南也觉得好纯洁！", "天使贴纸！小南也被净化了~"],
    
    # 😢 悲伤/哭泣类
    "😢": ["呜呜~ 看到这个贴纸小南也想哭了…", "别难过~ 小南抱抱你！(｡•́︿•̀｡)"],
    "😭": ["哇哇大哭的贴纸！小南也心疼了…", "不哭不哭~ 小南在这里陪着你！"],
    "😞": ["看起来好失落… 小南给你一个抱抱！", "别灰心~ 小南会一直陪着你的！"],
    "😔": ["有点难过的贴纸… 小南陪你一起！", "小南给你加油打气！一切都会好起来的~"],
    "😤": ["生气的贴纸！小南帮你出气！", "别生气啦~ 小南给你顺顺毛！"],
    "😠": ["看起来好生气… 小南躲远一点…", "消消气消消气~ 小南给你扇扇风！"],
    "🤬": ["呜哇好凶的贴纸！小南害怕…", "好凶的贴纸… 小南躲起来了…"],
    
    # 😳 害羞/尴尬类
    "😳": ["害羞的贴纸~ 小南也脸红啦！", "好害羞呀~ 小南也捂脸了！"],
    "🥺": ["可怜巴巴的贴纸~ 小南心都化了！", "呜呜这个眼神太犯规了！小南投降！"],
    "😅": ["尴尬的贴纸~ 小南也挠头了！", "哈哈有点尴尬呢~ 小南也笑了！"],
    "🤭": ["捂嘴笑的贴纸~ 小南也偷偷笑！", "嘿嘿~ 小南也捂住嘴笑了！"],
    "🙈": ["捂眼睛的贴纸！小南也害羞啦~", "不敢看不敢看~ 小南也捂脸了！"],
    
    # 😴 困倦/无聊类
    "😴": ["困困的贴纸~ 小南也打哈欠了！", "好困呀~ 小南也想睡觉了…"],
    "🥱": ["打哈欠的贴纸！小南也被传染了~", "哈欠~ 小南也困了… 晚安！"],
    "😪": ["睡眼惺忪的贴纸~ 小南也想睡了…", "困困的贴纸~ 小南给你唱摇篮曲！"],
    "😑": ["面无表情的贴纸… 小南也面瘫了…", "好淡定的贴纸~ 小南也冷静一下！"],
    "😒": ["嫌弃的贴纸~ 小南也被嫌弃了…", "呜… 这个表情好嫌弃… 小南受伤了…"],
    
    # 😱 惊讶/震惊类
    "😱": ["震惊的贴纸！小南也被吓到了！", "哇！这个贴纸好震撼！小南惊呆了！"],
    "😨": ["害怕的贴纸… 小南也缩成一团了…", "别怕别怕~ 小南保护你！"],
    "😰": ["紧张的贴纸~ 小南也捏了一把汗！", "别紧张~ 小南给你加油！"],
    "🤯": ["脑袋爆炸的贴纸！小南也惊呆了！", "哇塞！这个信息量太大了！小南脑子不够用了！"],
    "😮": ["惊讶的贴纸~ 小南也张大了嘴！", "哇！小南也被惊到了！"],
    "😲": ["目瞪口呆的贴纸！小南也愣住了！", "好惊讶的贴纸~ 小南也吓了一跳！"],
    
    # 🥰 可爱/治愈类
    # 注：🥰 的这两句已并进上面的「笑脸/开心类」同名键，重复键会互相覆盖、悄悄丢数据喵~
    "😻": ["猫咪爱心眼贴纸！小南也喵喵叫~", "好可爱的猫咪贴纸！小南也想养猫了！"],
    "🐱": ["猫咪贴纸！小南的同族！喵呜~", "猫猫贴纸！小南也来蹭蹭！"],
    "🐶": ["狗狗贴纸！好可爱呀~ 汪汪！", "狗狗贴纸！小南也想摸摸头！"],
    "🐰": ["兔兔贴纸！好软好可爱~", "兔兔贴纸！小南也想抱抱！"],
    "🐼": ["熊猫贴纸！圆滚滚的好可爱！", "熊猫贴纸！小南也想滚滚~"],
    "🐻": ["熊熊贴纸！好想抱抱！", "熊贴纸！小南给你一个大大的拥抱！"],
    "🦊": ["狐狸贴纸！好聪明好可爱！", "狐狸贴纸！小南也觉得好帅气！"],
    "🐸": ["青蛙贴纸！好有趣呀~", "青蛙贴纸！小南也呱呱叫！"],
    "🐧": ["企鹅贴纸！摇摇晃晃的好可爱！", "企鹅贴纸！小南也想滑冰！"],
    "🐤": ["小鸡贴纸！叽叽喳喳的好可爱！", "小鸡贴纸！小南也想喂米！"],
    "🦋": ["蝴蝶贴纸！好漂亮呀~", "蝴蝶贴纸！小南也想飞飞！"],
    "🌸": ["花花贴纸！好漂亮呀~ 小南喜欢！", "花朵贴纸！小南也想去赏花！"],
    "🌺": ["花花贴纸！好美呀~", "漂亮的花花贴纸！小南心情都变好了！"],
    "🌻": ["向日葵贴纸！好阳光好温暖！", "向日葵贴纸！小南也充满能量！"],
    "🌹": ["玫瑰花贴纸！好浪漫呀~", "玫瑰贴纸！小南也害羞了！"],
    "🌷": ["郁金香贴纸！好优雅好漂亮！", "郁金香贴纸！小南也想去花园！"],
    "🌈": ["彩虹贴纸！好美好梦幻！", "彩虹贴纸！小南也想许愿！"],
    "⭐": ["星星贴纸！闪闪发光好漂亮！", "星星贴纸！小南也想摘一颗！"],
    "🌟": ["闪耀的星星贴纸！好耀眼！", "星星贴纸！小南的眼睛也亮晶晶！"],
    "✨": ["闪闪发光的贴纸！好梦幻！", "闪亮贴纸！小南也被闪到了！"],
    "🎀": ["蝴蝶结贴纸！好可爱好少女！", "蝴蝶结贴纸！小南也想戴一个！"],
    "🎂": ["蛋糕贴纸！小南想吃蛋糕了！", "蛋糕贴纸！小南也想过生日！"],
    "🍰": ["蛋糕贴纸！好甜好美味~", "蛋糕贴纸！小南流口水了！"],
    "🍦": ["冰淇淋贴纸！小南也想吃！", "冰淇淋贴纸！夏天的最爱！"],
    "🍩": ["甜甜圈贴纸！好诱人呀~", "甜甜圈贴纸！小南也想咬一口！"],
    "🍕": ["披萨贴纸！小南也饿了！", "披萨贴纸！小南也想吃一块！"],
    "🍔": ["汉堡贴纸！好想吃呀~", "汉堡贴纸！小南也馋了！"],
    "🎮": ["游戏贴纸！小南也想玩！", "游戏贴纸！小南是游戏高手！"],
    "🎵": ["音符贴纸！小南也想唱歌！", "音乐贴纸！小南跟着节奏摇摆~"],
    "🎶": ["音乐贴纸！小南也来跳舞！", "音符贴纸！小南哼起了歌~"],
    "🎤": ["麦克风贴纸！小南也想K歌！", "唱歌贴纸！小南是麦霸！"],
    "🎸": ["吉他贴纸！好酷好帅！", "吉他贴纸！小南也想学弹琴！"],
    "🎹": ["钢琴贴纸！好优雅好有气质！", "钢琴贴纸！小南也想弹一曲！"],
    "🎨": ["画板贴纸！小南也想画画！", "艺术贴纸！小南也有艺术细胞！"],
    "📸": ["相机贴纸！小南也想拍照！", "拍照贴纸！小南比个耶！"],
    "🌍": ["地球贴纸！小南想去环游世界！", "地球贴纸！小南也想出去看看！"],
    "🚀": ["火箭贴纸！小南也想飞向太空！", "火箭贴纸！小南也想探索宇宙！"],
    "💪": ["肌肉贴纸！小南也充满力量！", "加油贴纸！小南给你打气！"],
    "🔥": ["火焰贴纸！好燃好热血！", "火焰贴纸！小南也燃起来了！"],
    "💯": ["满分贴纸！小南给你打满分！", "满分贴纸！小南觉得你最棒！"],
    "🎉": ["庆祝贴纸！小南也来撒花！", "派对贴纸！小南也来狂欢！"],
    "🎊": ["彩花贴纸！好热闹好开心！", "庆祝贴纸！小南也来庆祝！"],
    "🎁": ["礼物贴纸！小南也想拆礼物！", "礼物贴纸！小南好期待！"],
    "💡": ["灯泡贴纸！小南也有好主意！", "灵感贴纸！小南灵光一闪！"],
    "🔮": ["水晶球贴纸！好神秘好梦幻！", "魔法贴纸！小南也想学魔法！"],
    "💎": ["钻石贴纸！好闪好耀眼！", "宝石贴纸！小南的眼睛都亮了！"],
    "👑": ["皇冠贴纸！好高贵好优雅！", "皇冠贴纸！小南也想要一个！"],
    "🎪": ["马戏团贴纸！好有趣好欢乐！", "马戏团贴纸！小南也想去看！"],
    "🎭": ["面具贴纸！好神秘好有趣！", "面具贴纸！小南也想变装！"],
    "🎠": ["旋转木马贴纸！好梦幻好浪漫！", "旋转木马贴纸！小南也想坐！"],
    "🎡": ["摩天轮贴纸！好浪漫好美好！", "摩天轮贴纸！小南也想去看风景！"],
    "🏰": ["城堡贴纸！好华丽好梦幻！", "城堡贴纸！小南也想去住！"],
    "🌊": ["海浪贴纸！好清凉好舒服！", "海浪贴纸！小南想去海边！"],
    "☀️": ["太阳贴纸！好温暖好阳光！", "太阳贴纸！小南也充满能量！"],
    "🌙": ["月亮贴纸！好温柔好宁静！", "月亮贴纸！小南也想赏月！"],
    "☁️": ["云朵贴纸！好柔软好舒服！", "云朵贴纸！小南也想躺上去！"],
    "❄️": ["雪花贴纸！好漂亮好清凉！", "雪花贴纸！小南也想玩雪！"],
    "⚡": ["闪电贴纸！好酷好帅气！", "闪电贴纸！小南也被电到了！"],
    "☔": ["雨伞贴纸！下雨天要带伞哦~", "雨伞贴纸！小南帮你挡雨！"],
    "🍀": ["四叶草贴纸！好运连连！", "幸运草贴纸！小南祝你幸运！"],
    "🎯": ["靶心贴纸！小南一箭命中！", "目标贴纸！小南精准命中！"],
    "🏆": ["奖杯贴纸！小南为你骄傲！", "冠军贴纸！小南给你颁奖！"],
    "🥇": ["金牌贴纸！小南觉得你最棒！", "金牌贴纸！小南为你喝彩！"],
    "🎲": ["骰子贴纸！小南也想玩游戏！", "骰子贴纸！小南来赌一把！"],
    "♟️": ["棋子贴纸！小南也想下棋！", "国际象棋贴纸！小南是高手！"],
    "🧩": ["拼图贴纸！小南也想拼！", "拼图贴纸！小南来帮忙！"],
    "📚": ["书本贴纸！小南也想学习！", "书本贴纸！小南是好学生！"],
    "✏️": ["铅笔贴纸！小南也想写字！", "铅笔贴纸！小南来记笔记！"],
    "🎓": ["毕业帽贴纸！恭喜毕业！", "毕业贴纸！小南为你庆祝！"],
    "💻": ["电脑贴纸！小南也想编程！", "电脑贴纸！小南是程序员！"],
    "📱": ["手机贴纸！小南也想玩手机！", "手机贴纸！小南来刷一刷！"],
    "⌚": ["手表贴纸！好精致好优雅！", "手表贴纸！小南也想要一个！"],
    "🔑": ["钥匙贴纸！小南帮你开门！", "钥匙贴纸！小南帮你保管！"],
    "🔒": ["锁贴纸！小南帮你保密！", "锁贴纸！小南守口如瓶！"],
    "🔓": ["开锁贴纸！小南帮你打开！", "解锁贴纸！小南来啦！"],
    "💣": ["炸弹贴纸！小南快跑！", "炸弹贴纸！小南躲远点！"],
    "💥": ["爆炸贴纸！好震撼好刺激！", "爆炸贴纸！小南被震到了！"],
    "🎆": ["烟花贴纸！好美好壮观！", "烟花贴纸！小南也想看！"],
    "🎇": ["烟花贴纸！好浪漫好漂亮！", "烟花贴纸！小南许个愿！"],
    "🎑": ["夜景贴纸！好宁静好美好！", "夜景贴纸！小南也想看星星！"],
    "🌄": ["日出贴纸！好壮美好感动！", "日出贴纸！小南也早起看日出！"],
    "🌅": ["日落贴纸！好浪漫好温柔！", "日落贴纸！小南也想看夕阳！"],
    "🌇": ["城市夜景贴纸！好繁华好漂亮！", "城市贴纸！小南也想去逛街！"],
    "🏙️": ["城市贴纸！好现代好繁华！", "城市贴纸！小南也想去看看！"],
    "🌃": ["星空贴纸！好浪漫好梦幻！", "星空贴纸！小南也想数星星！"],
    "🌌": ["银河贴纸！好壮美好神秘！", "银河贴纸！小南也想探索宇宙！"],
}

# 通用回复语（当 emoji 没有匹配时使用）
GENERAL_REPLIES = [
    "哇~ 好可爱的贴纸！(｡♥‿♥｡)",
    "贴纸收到啦~ 喵呜！",
    "这个贴纸好有趣呀！",
    "小南也想要这个贴纸~",
    "贴纸贴纸~ 好开心！",
    "收到贴纸攻击！(๑•̀ㅂ•́)و✧",
    "贴纸好漂亮呀~ 小南超喜欢！",
    "呜哇~ 这个贴纸太可爱了吧！",
    "贴纸+1！小南的收藏又丰富啦~",
    "好耶！是贴纸！ヽ(✿ﾟ▽ﾟ)ノ",
    "贴纸收到~ 小南好开心！",
    "这个贴纸的表情好棒！",
    "贴纸贴纸~ 小南也想发一个！",
    "收到贴纸啦！小南要好好收藏起来~",
    "哇！这个贴纸好适合现在的心情！",
    "小南收到贴纸啦~ 好开心好开心！",
    "贴纸来啦！小南超兴奋！",
    "这个贴纸好有意思~ 小南看了又看！",
    "贴纸贴纸~ 小南的快乐源泉！",
    "收到贴纸！小南今天又是幸福的一天~",
]

# 动态贴纸专用回复语
ANIMATED_REPLIES = [
    "哇~ 是动态贴纸！好酷好炫！(｡♥‿♥｡)",
    "动态贴纸！小南盯着看了好久~",
    "会动的贴纸！好有趣呀！",
    "动态贴纸~ 小南也想动起来！",
    "哇塞！这个贴纸会动！好厉害！",
    "动态贴纸！小南的眼睛都看花了~",
    "会动的贴纸好可爱！小南也想学！",
    "动态贴纸收到！小南跟着一起摇摆~",
    "好炫酷的动态贴纸！小南被帅到了！",
    "动态贴纸！小南看了又看停不下来~",
]


def _get_dynamic_reply(sticker) -> str:
    """根据贴纸信息动态生成回复语~"""
    emoji = sticker.emoji or ""
    is_animated = sticker.is_animated
    
    # 如果是动态贴纸，有一定概率使用动态贴纸专用回复
    if is_animated and random.random() < 0.4:
        return random.choice(ANIMATED_REPLIES)
    
    # 尝试根据 emoji 匹配回复
    if emoji and emoji in EMOJI_REPLIES:
        return random.choice(EMOJI_REPLIES[emoji])
    
    # 尝试匹配 emoji 的变体（比如带肤色修饰符的）
    if emoji:
        # 取 emoji 的基础部分（第一个字符）
        base_emoji = emoji[0]
        if base_emoji in EMOJI_REPLIES:
            return random.choice(EMOJI_REPLIES[base_emoji])
    
    # 没有匹配到，使用通用回复
    return random.choice(GENERAL_REPLIES)


class StickerModule(BaseModule):
    """贴纸模块~ 让小南也能玩贴纸！"""
    
    name = "sticker"
    description = "贴纸收藏和回复~"
    
    def __init__(self, bot_app=None):
        super().__init__(bot_app)
        self.dm = DataManager()
    
    def register_handlers(self, application):
        """注册命令和消息处理器~"""
        # 贴纸消息处理器
        application.add_handler(MessageHandler(filters.Sticker.ALL, self.handle_sticker))
        
        # 贴纸管理命令（仅主人可用）
        application.add_handler(CommandHandler("add_sticker", self.add_sticker_command))
        application.add_handler(CommandHandler("sticker_list", self.sticker_list_command))
        application.add_handler(CommandHandler("del_sticker", self.del_sticker_command))
        
        # 检测贴纸链接消息（处理 /add_sticker 后面没空格直接跟链接的情况）
        application.add_handler(MessageHandler(
            filters.TEXT & filters.Regex(r'(?:^|/)add_sticker\S*|t\.me/addstickers/'),
            self.handle_sticker_link
        ))
        
        # 按钮回调
        application.add_handler(CallbackQueryHandler(self.sticker_callback, pattern=r"^sticker_"))
    
    async def handle_sticker_link(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理贴纸链接消息~ 自动解析并添加贴纸集（仅主人私聊可用）"""
        user_id = update.effective_user.id
        chat_type = update.effective_chat.type
        
        # 仅主人可用，且仅限私聊
        if not self.dm.is_owner(user_id) or chat_type != "private":
            return
        
        text = update.effective_message.text or ""
        
        # 提取贴纸链接
        import re
        match = re.search(r'https?://t\.me/addstickers/(\S+)', text)
        if not match:
            return  # 没有贴纸链接，忽略
        
        set_name = match.group(1)
        
        # 发送处理中的提示
        status_msg = await update.message.reply_text(
            f"🔍 正在解析贴纸集：{set_name}\n"
            f"请稍等~ 小南正在努力加载中… (｡•̀ᴗ-)✧"
        )
        
        try:
            # 通过 Telegram API 获取贴纸集信息
            bot = context.bot
            sticker_set = await bot.get_sticker_set(set_name)
            
            if not sticker_set:
                await status_msg.edit_text(
                    f"❌ 没有找到贴纸集：{set_name}\n"
                    f"请检查链接是否正确哦~"
                )
                return
            
            stickers = sticker_set.stickers
            if not stickers:
                await status_msg.edit_text(
                    f"📦 贴纸集 {set_name} 是空的呢~"
                )
                return
            
            # 加载现有收藏
            stickers_data = _load_stickers()
            existing_ids = {s.get("file_id") for s in stickers_data["stickers"]}

            # 统计信息
            added_count = 0
            skip_count = 0
            over_count = 0
            # 收藏库还剩多少空位（老数据已经超上限时 room=0，一个都不再导入）
            room = max(0, MAX_STICKERS_TOTAL - len(stickers_data["stickers"]))

            for sticker in stickers:
                if sticker.file_id in existing_ids:
                    skip_count += 1
                    continue

                # 上限到了就停下并计数，而不是把整份贴纸集硬塞进文件里
                if added_count >= room:
                    over_count += 1
                    continue

                new_sticker = _make_sticker(sticker, sticker.set_name or set_name)
                if not new_sticker:
                    # 字段不全（拿不到 file_id）的贴纸不写进收藏库，免得以后 KeyError
                    continue

                stickers_data["stickers"].append(new_sticker)
                existing_ids.add(sticker.file_id)
                added_count += 1
            
            if added_count > 0:
                _save_stickers(stickers_data)
            
            # 构建结果消息
            anim_count = sum(1 for s in stickers if s.is_animated)
            static_count = len(stickers) - anim_count
            
            result_msg = (
                f"✅ 贴纸集解析完成！\n\n"
                f"📦 贴纸集：{sticker_set.name}\n"
                f"📊 贴纸集共 {len(stickers)} 个贴纸\n"
                f"   🖼️ 静态：{static_count} 个\n"
                f"   🎬 动态：{anim_count} 个\n\n"
                f"📥 本次新增收藏：{added_count} 个\n"
            )
            
            if skip_count > 0:
                result_msg += f"⏭️ 已存在跳过：{skip_count} 个\n"

            if over_count > 0:
                result_msg += (
                    f"⚠️ 收藏库已满（上限 {MAX_STICKERS_TOTAL} 个），"
                    f"还有 {over_count} 个没能导入~\n"
                    f"先用 /sticker_list → 🗑️ 删除贴纸 腾位置，再重新发链接吧~\n"
                )
            
            result_msg += (
                f"📊 当前共收藏：{len(stickers_data['stickers'])}/{MAX_STICKERS_TOTAL} 个贴纸\n\n"
                f"查看收藏：/sticker_list"
            )
            
            await status_msg.edit_text(result_msg)
            
        except Exception as e:
            logger.error(f"解析贴纸集失败: {e}")
            await status_msg.edit_text(
                "❌ 解析贴纸集失败…\n\n"
                "可能的原因：\n"
                "• 贴纸集不存在或已删除\n"
                "• 贴纸集名称不正确\n"
                "• 网络连接问题\n\n"
                "请检查链接是否正确，或稍后重试~"
            )
    
    async def handle_sticker(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理贴纸消息~ 回复一个收藏的贴纸表情"""
        chat_type = update.effective_chat.type
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        # 私聊：检查用户是否在白名单
        if chat_type == "private":
            if not self.dm.is_user_whitelisted(user_id) and not self.dm.is_owner(user_id):
                return
        
        # 群聊：检查群组是否在白名单，且需要被提及才回复
        elif chat_type in ("group", "supergroup"):
            if not self.dm.is_group_whitelisted(chat_id):
                return
            
            # 检查是否应该回复（和聊天逻辑一致）
            bot_username = context.bot.username
            bot_id = context.bot.id
            message = update.effective_message
            
            # 情况1：被 @ 了
            is_mentioned = bot_username and f"@{bot_username}" in (message.text or "")
            
            # 情况2：回复了机器人的消息
            is_reply_to_bot = False
            if message.reply_to_message and message.reply_to_message.from_user:
                is_reply_to_bot = message.reply_to_message.from_user.id == bot_id
            
            if not is_mentioned and not is_reply_to_bot:
                return  # 既没被@也没回复机器人，忽略
        
        # 从收藏库中随机选一个贴纸回复
        stickers_data = _load_stickers()
        stickers = stickers_data["stickers"]
        
        if stickers:
            # 有收藏的贴纸，随机选一个回复
            chosen = random.choice(stickers)
            try:
                await update.message.reply_sticker(chosen.get("file_id"))
                return
            except Exception as e:
                logger.warning(f"回复贴纸失败（可能已失效），尝试下一个: {e}")
                # 如果失败，换几张试试。这里只再试 3 张：
                # 以前是对整个收藏库逐张重试，库无限增长 + 贴纸全失效时，
                # 一次贴纸消息就会打出一长串失败请求（很快撞上 Telegram 429 限流），
                # 用户还得等半天才收到文字回复。收藏库上限 500 之后同理，不能全试。
                remaining = [
                    s for s in stickers
                    if s.get("file_id") != chosen.get("file_id")
                ][:3]
                for s in remaining:
                    try:
                        await update.message.reply_sticker(s.get("file_id"))
                        return
                    except Exception:
                        continue
        
        # 没有收藏贴纸或所有贴纸都失效时，用文字回复
        reply = _get_dynamic_reply(update.effective_message.sticker)
        await update.message.reply_text(reply)
    
    async def add_sticker_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/add_sticker - 收藏贴纸（主人专属）"""
        if not self._check_owner(update, context):
            return
        
        # 检查参数中是否有贴纸链接
        import re
        sticker_link = None
        if context.args:
            link_text = " ".join(context.args)
            link_match = re.search(r'https?://t\.me/addstickers/(\S+)', link_text)
            if link_match:
                sticker_link = link_match.group(1)
        
        if sticker_link:
            # 私聊里 handle_sticker_link 本来就能整包导入，别再跟主人说「无法下载」啦喵~
            if update.effective_chat.type == "private":
                await self.handle_sticker_link(update, context)
                return
            await update.message.reply_text(
                f"📦 检测到贴纸集链接：{sticker_link}\n\n"
                f"💡 小南能直接导入整个贴纸集哦~ 但只能在私聊里做！\n"
                f"请私聊小南，把链接单独发一条（和命令分开写）：\n"
                f"https://t.me/addstickers/{sticker_link}"
            )
            return
        
        # 检查是否是回复贴纸消息
        reply_to = update.effective_message.reply_to_message
        if not reply_to or not reply_to.sticker:
            await update.message.reply_text(
                "🎨 用法：回复一个贴纸消息，然后发送 /add_sticker\n\n"
                "或者分享贴纸链接：/add_sticker <贴纸链接>\n"
                "例如：/add_sticker https://t.me/addstickers/MyStickerPack"
            )
            return
        
        sticker = reply_to.sticker
        
        # 检查是否已收藏
        stickers_data = _load_stickers()
        for s in stickers_data["stickers"]:
            if s.get("file_id") == sticker.file_id:
                await update.message.reply_text("😅 这个贴纸已经在收藏库里啦~")
                return

        # 上限检查：满了就明确告诉主人，而不是继续往文件里堆
        # （以前没有任何上限，一个人能一直收藏，stickers.json 无限变长）
        if len(stickers_data["stickers"]) >= MAX_STICKERS_TOTAL:
            await update.message.reply_text(
                f"📦 收藏库满啦！最多只能收藏 {MAX_STICKERS_TOTAL} 个贴纸~\n"
                f"📊 当前：{len(stickers_data['stickers'])}/{MAX_STICKERS_TOTAL}\n\n"
                f"先腾个位置吧：/sticker_list → 🗑️ 删除贴纸"
            )
            return

        # 添加到收藏库（字段统一由 _make_sticker 补齐，保证 file_id/sid/set_name 等都在）
        new_sticker = _make_sticker(sticker)
        if not new_sticker:
            await update.message.reply_text("😅 这个贴纸信息不完整，小南存不下呢… 换个贴纸试试？")
            return
        stickers_data["stickers"].append(new_sticker)
        
        if _save_stickers(stickers_data):
            await update.message.reply_text(
                f"✅ 贴纸已收藏！\n"
                f"📦 贴纸集：{new_sticker.get('set_name', '未知')}\n"
                f"📊 当前共收藏 {len(stickers_data['stickers'])}/{MAX_STICKERS_TOTAL} 个贴纸~\n\n"
                f"查看收藏：/sticker_list"
            )
        else:
            await update.message.reply_text("❌ 收藏失败啦… 请检查日志喵~")
    
    async def sticker_list_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/sticker_list - 查看收藏的贴纸（主人专属）"""
        if not self._check_owner(update, context):
            return
        
        stickers_data = _load_stickers()
        stickers = stickers_data["stickers"]
        
        if not stickers:
            # 按钮回调进来的 update 没有 .message，必须用 effective_message 喵~
            await update.effective_message.reply_text(
                "📭 还没有收藏任何贴纸呢~\n"
                "回复贴纸消息发送 /add_sticker 来收藏吧！"
            )
            return
        
        # 分页显示（每页5个）
        # 用 isdecimal 而不是 isdigit：'²'.isdigit() 为 True 但 int('²') 会 ValueError 喵~
        # 另外限一下位数：Python 3.11+ 对超过 4300 位的数字字符串 int() 会抛 ValueError，
        # 而 isdecimal() 对它照样返回 True（/sticker_list 999…9 就能把命令点崩）
        page_arg = context.args[0] if context.args else ""
        page = int(page_arg) - 1 if page_arg.isdecimal() and len(page_arg) <= 6 else 0
        per_page = 5
        total_pages = (len(stickers) + per_page - 1) // per_page
        page = max(0, min(page, total_pages - 1))
        
        start = page * per_page
        end = min(start + per_page, len(stickers))
        page_items = stickers[start:end]
        
        msg = "🎨 小南的贴纸收藏~\n"
        msg += f"📊 共 {len(stickers)}/{MAX_STICKERS_TOTAL} 个贴纸 | 第 {page+1}/{total_pages} 页\n\n"

        for i, s in enumerate(page_items, start + 1):
            emoji = s.get("emoji", "") or ""
            anim = "🎬" if s.get("is_animated") else "🖼️"
            msg += f"{i}. {anim} {emoji} {_short_set_name(s.get('set_name'))}\n"
            msg += f"   🆔 {s.get('file_id', '')[:20]}...\n"
            msg += f"   🕐 {str(s.get('added_at', '未知'))[:10]}\n\n"
        
        # 翻页按钮
        keyboard = []
        nav_row = []
        if page > 0:
            nav_row.append(InlineKeyboardButton("◀ 上一页", callback_data=f"sticker_list_{page-1}"))
        if page < total_pages - 1:
            nav_row.append(InlineKeyboardButton("下一页 ▶", callback_data=f"sticker_list_{page+1}"))
        if nav_row:
            keyboard.append(nav_row)
        
        # 删除按钮
        keyboard.append([
            InlineKeyboardButton("🗑️ 删除贴纸", callback_data="sticker_show_delete")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
        
        await update.effective_message.reply_text(msg, reply_markup=reply_markup)
    
    async def del_sticker_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/del_sticker <编号> - 删除收藏的贴纸（主人专属）"""
        if not self._check_owner(update, context):
            return
        
        if not context.args:
            await update.message.reply_text(
                "用法：/del_sticker <编号>\n"
                "先用 /sticker_list 查看编号哦~"
            )
            return
        
        try:
            index = int(context.args[0]) - 1  # 用户看到的是从1开始
            stickers_data = _load_stickers()
            
            if 0 <= index < len(stickers_data["stickers"]):
                removed = stickers_data["stickers"].pop(index)
                if _save_stickers(stickers_data):
                    await update.message.reply_text(
                        f"✅ 已删除贴纸~\n"
                        f"📦 {removed.get('set_name', '未知')}\n"
                        f"📊 剩余 {len(stickers_data['stickers'])} 个贴纸"
                    )
                else:
                    await update.message.reply_text("❌ 删除失败啦…")
            else:
                await update.message.reply_text("😅 没有找到这个编号的贴纸呢~ 用 /sticker_list 看看吧")
        except ValueError:
            await update.message.reply_text("😅 要输入数字编号哦~")
    
    async def _show_delete_page(self, query, page: int):
        """显示某一页的删除菜单~（每页 10 个，按钮和文字都离 Telegram 上限远远的喵~）"""
        stickers_data = _load_stickers()
        stickers = stickers_data["stickers"]

        if not stickers:
            await query.edit_message_text("📭 还没有收藏任何贴纸呢~")
            return

        per_page = 10
        total_pages = (len(stickers) + per_page - 1) // per_page
        # 删过贴纸之后旧页码可能已经越界了，先夹回有效范围喵~
        page = max(0, min(page, total_pages - 1))

        start = page * per_page
        end = min(start + per_page, len(stickers))
        page_items = stickers[start:end]

        msg = "🗑️ 选择要删除的贴纸~\n"
        msg += f"📊 共 {len(stickers)}/{MAX_STICKERS_TOTAL} 个贴纸 | 第 {page+1}/{total_pages} 页\n\n"
        keyboard = []

        for i, s in enumerate(page_items, start + 1):
            emoji = s.get("emoji", "") or ""
            anim = "🎬" if s.get("is_animated") else "🖼️"
            msg += f"{i}. {anim} {emoji} {_short_set_name(s.get('set_name'))}\n"
            # 按钮带的是这张贴纸的**稳定短标识**（file_id 的短哈希），不是"第几个"。
            # 所以就算两个窗口里的列表已经不一样了，点"删除 #3"删掉的也永远是
            # #3 当时对应的那一张，不会变成别人列表里的第 3 个喵~
            sid = _entry_sid(s)
            keyboard.append([
                InlineKeyboardButton(f"🗑️ 删除 #{i}", callback_data=f"sticker_del_{sid}")
            ])

        # 翻页按钮（和 /sticker_list 一样排成一排）
        nav_row = []
        if page > 0:
            nav_row.append(InlineKeyboardButton("◀ 上一页", callback_data=f"sticker_show_delete_{page-1}"))
        if page < total_pages - 1:
            nav_row.append(InlineKeyboardButton("下一页 ▶", callback_data=f"sticker_show_delete_{page+1}"))
        if nav_row:
            keyboard.append(nav_row)

        keyboard.append([
            InlineKeyboardButton("🔙 返回列表", callback_data="sticker_back_to_list")
        ])

        await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))

    async def sticker_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理贴纸按钮回调~"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        # 翻页
        if data.startswith("sticker_list_"):
            # callback_data 是客户端发上来的，被改造过就是任意字符串，
            # 直接 int() 会 ValueError 冲出 handler，所以先校验再转
            # （位数也要卡：4300 位以上的数字串 isdecimal() 为 True 但 int() 会抛错）
            suffix = data[len("sticker_list_"):]
            if not suffix.isdecimal() or len(suffix) > 6:
                await query.answer("页码不对哦~", show_alert=False)
                return
            page = int(suffix)
            context.args = [str(page + 1)]
            await self.sticker_list_command(update, context)
        
        # 显示删除选择（分页：一页最多 10 个按钮，文字也不会撞上 4096 上限喵~）
        elif data.startswith("sticker_show_delete"):
            # 页码藏在按钮数据里：sticker_show_delete_<页>，取不到就是第一页
            page_suffix = data[len("sticker_show_delete"):]
            page_digits = page_suffix[1:] if page_suffix.startswith("_") else ""
            page = int(page_digits) if page_digits.isdecimal() and len(page_digits) <= 6 else 0
            await self._show_delete_page(query, page)
        
        # 执行删除（按稳定短标识删，不按位置删）
        elif data.startswith("sticker_del_"):
            sid = data[len("sticker_del_"):]
            if not _SID_RE.match(sid):
                # 老消息里的按钮带的是数字编号（升级前的格式），一律当作已失效：
                # 宁可让主人重开一次列表，也不能拿旧编号去删现在这个位置上的贴纸
                await query.edit_message_text(
                    "😅 这个按钮已经过期啦（升级前的旧按钮），"
                    "重新打开 /sticker_list → 🗑️ 删除贴纸 就好~"
                )
                return
            stickers_data = _load_stickers()

            target_index = None
            for idx, s in enumerate(stickers_data["stickers"]):
                if _entry_sid(s) == sid:
                    target_index = idx
                    break

            if target_index is None:
                await query.edit_message_text("😅 这个贴纸已经不在了呢~ 可能刚才已经删掉啦")
                return

            removed = stickers_data["stickers"].pop(target_index)
            if _save_stickers(stickers_data):
                await query.edit_message_text(
                    f"✅ 已删除贴纸~\n"
                    f"📦 {_short_set_name(removed.get('set_name'))}\n"
                    f"📊 剩余 {len(stickers_data['stickers'])}/{MAX_STICKERS_TOTAL} 个贴纸\n\n"
                    f"查看收藏：/sticker_list"
                )
            else:
                await query.edit_message_text("❌ 删除失败啦…")
        
        # 返回列表
        elif data == "sticker_back_to_list":
            context.args = []
            await self.sticker_list_command(update, context)
    
    def _check_owner(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """检查是否是主人~"""
        user_id = update.effective_user.id
        if not self.dm.is_owner(user_id):
            # 优先使用 message，如果没有则使用 callback_query
            if update.message:
                context.application.create_task(
                    update.message.reply_text("呜… 你不是我的主人，不能使用这个命令哦！(｡•́︿•̀｡)")
                )
            elif update.callback_query:
                context.application.create_task(
                    update.callback_query.edit_message_text("呜… 你不是我的主人，不能使用这个命令哦！(｡•́︿•̀｡)")
                )
            return False
        return True
    
    def get_help_text(self) -> str:
        """返回帮助文本~"""
        return (
            "🎨 贴纸模块~\n"
            "发送贴纸给小南，她会识别并回复哦~\n"
            "/add_sticker - 收藏贴纸（主人专属）\n"
            "/sticker_list - 查看收藏的贴纸（主人专属）\n"
            "/del_sticker <编号> - 删除收藏的贴纸（主人专属）"
        )
