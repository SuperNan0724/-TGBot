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
import random
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

from .base_module import BaseModule
from .data_manager import DataManager

logger = logging.getLogger(__name__)

# 贴纸收藏数据文件
STICKER_FILE = "data/stickers.json"


def _load_stickers() -> dict:
    """加载贴纸收藏库~"""
    if os.path.exists(STICKER_FILE):
        try:
            with open(STICKER_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载贴纸数据失败: {e}")
    return {"stickers": []}


def _save_stickers(data: dict):
    """保存贴纸收藏库~"""
    try:
        os.makedirs(os.path.dirname(STICKER_FILE), exist_ok=True)
        with open(STICKER_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
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
    "🥰": ["好甜好甜的贴纸~ 小南被治愈了！", "治愈系贴纸！小南满血复活！"],
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
    "🥰": ["好可爱的贴纸！小南被萌翻了！", "可爱到犯规的贴纸！小南血条清空！"],
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
        
        # 按钮回调
        application.add_handler(CallbackQueryHandler(self.sticker_callback, pattern=r"^sticker_"))
    
    async def handle_sticker(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理贴纸消息~"""
        chat_type = update.effective_chat.type
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        # 私聊：检查用户是否在白名单
        if chat_type == "private":
            if not self.dm.is_user_whitelisted(user_id) and not self.dm.is_owner(user_id):
                return
        
        # 群聊：检查群组是否在白名单
        elif chat_type in ("group", "supergroup"):
            if not self.dm.is_group_whitelisted(chat_id):
                return
        
        sticker = update.effective_message.sticker
        
        # 获取贴纸信息
        sticker_info = []
        sticker_info.append(f"📦 贴纸集：{sticker.set_name or '未知'}")
        sticker_info.append(f"🆔 文件ID：{sticker.file_id}")
        sticker_info.append(f"📐 尺寸：{sticker.width}x{sticker.height}")
        if sticker.emoji:
            sticker_info.append(f"😊 表情：{sticker.emoji}")
        if sticker.is_animated:
            sticker_info.append(f"🎬 类型：动态贴纸")
        else:
            sticker_info.append(f"🖼️ 类型：静态贴纸")
        
        # 动态生成回复语（根据 emoji 和贴纸类型）
        reply = _get_dynamic_reply(sticker)
        
        # 构建回复消息
        msg = (
            f"{reply}\n\n"
            f"🔍 贴纸信息：\n"
            + "\n".join(sticker_info)
        )
        
        # 添加收藏提示（仅主人可见）
        if self.dm.is_owner(user_id):
            msg += "\n\n💡 主人可以用 /add_sticker 收藏这个贴纸哦~"
        
        await update.message.reply_text(msg)
    
    async def add_sticker_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/add_sticker - 收藏贴纸（主人专属）"""
        if not self._check_owner(update, context):
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
            if s["file_id"] == sticker.file_id:
                await update.message.reply_text("😅 这个贴纸已经在收藏库里啦~")
                return
        
        # 添加到收藏库
        new_sticker = {
            "file_id": sticker.file_id,
            "set_name": sticker.set_name or "未知",
            "emoji": sticker.emoji or "",
            "width": sticker.width,
            "height": sticker.height,
            "is_animated": sticker.is_animated,
            "is_video": sticker.is_video,
            "added_at": datetime.now().isoformat(),
        }
        stickers_data["stickers"].append(new_sticker)
        
        if _save_stickers(stickers_data):
            await update.message.reply_text(
                f"✅ 贴纸已收藏！\n"
                f"📦 贴纸集：{sticker.set_name or '未知'}\n"
                f"📊 当前共收藏 {len(stickers_data['stickers'])} 个贴纸~\n\n"
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
            await update.message.reply_text(
                "📭 还没有收藏任何贴纸呢~\n"
                "回复贴纸消息发送 /add_sticker 来收藏吧！"
            )
            return
        
        # 分页显示（每页5个）
        page = int(context.args[0]) - 1 if context.args and context.args[0].isdigit() else 0
        per_page = 5
        total_pages = (len(stickers) + per_page - 1) // per_page
        page = max(0, min(page, total_pages - 1))
        
        start = page * per_page
        end = min(start + per_page, len(stickers))
        page_items = stickers[start:end]
        
        msg = f"🎨 小南的贴纸收藏~\n"
        msg += f"📊 共 {len(stickers)} 个贴纸 | 第 {page+1}/{total_pages} 页\n\n"
        
        for i, s in enumerate(page_items, start + 1):
            emoji = s.get("emoji", "") or ""
            anim = "🎬" if s.get("is_animated") else "🖼️"
            msg += f"{i}. {anim} {emoji} {s.get('set_name', '未知')}\n"
            msg += f"   🆔 {s['file_id'][:20]}...\n"
            msg += f"   🕐 {s.get('added_at', '未知')[:10]}\n\n"
        
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
        
        await update.message.reply_text(msg, reply_markup=reply_markup)
    
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
    
    async def sticker_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理贴纸按钮回调~"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        # 翻页
        if data.startswith("sticker_list_"):
            page = int(data.replace("sticker_list_", ""))
            context.args = [str(page + 1)]
            await self.sticker_list_command(update, context)
        
        # 显示删除选择
        elif data == "sticker_show_delete":
            stickers_data = _load_stickers()
            stickers = stickers_data["stickers"]
            
            if not stickers:
                await query.edit_message_text("📭 还没有收藏任何贴纸呢~")
                return
            
            # 显示带删除按钮的列表
            msg = "🗑️ 选择要删除的贴纸~\n\n"
            keyboard = []
            
            for i, s in enumerate(stickers, 1):
                emoji = s.get("emoji", "") or ""
                anim = "🎬" if s.get("is_animated") else "🖼️"
                msg += f"{i}. {anim} {emoji} {s.get('set_name', '未知')}\n"
                keyboard.append([
                    InlineKeyboardButton(f"🗑️ 删除 #{i}", callback_data=f"sticker_del_{i-1}")
                ])
            
            keyboard.append([
                InlineKeyboardButton("🔙 返回列表", callback_data="sticker_back_to_list")
            ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(msg, reply_markup=reply_markup)
        
        # 执行删除
        elif data.startswith("sticker_del_"):
            index = int(data.replace("sticker_del_", ""))
            stickers_data = _load_stickers()
            
            if 0 <= index < len(stickers_data["stickers"]):
                removed = stickers_data["stickers"].pop(index)
                if _save_stickers(stickers_data):
                    await query.edit_message_text(
                        f"✅ 已删除贴纸~\n"
                        f"📦 {removed.get('set_name', '未知')}\n"
                        f"📊 剩余 {len(stickers_data['stickers'])} 个贴纸\n\n"
                        f"查看收藏：/sticker_list"
                    )
                else:
                    await query.edit_message_text("❌ 删除失败啦…")
            else:
                await query.edit_message_text("😅 这个贴纸已经不存在了~")
        
        # 返回列表
        elif data == "sticker_back_to_list":
            context.args = []
            await self.sticker_list_command(update, context)
    
    def _check_owner(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """检查是否是主人~"""
        user_id = update.effective_user.id
        if not self.dm.is_owner(user_id):
            context.application.create_task(
                update.message.reply_text("呜… 你不是我的主人，不能使用这个命令哦！(｡•́︿•̀｡)")
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
