"""
🔧 辅助函数 - 让 AI 的回复像真人在聊天
"""
import re
import asyncio
import random
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# 语音自动发送配置
VOICE_CHANCE_SHORT = 0.30    # 短消息（<=50字）30%概率发语音
VOICE_CHANCE_MEDIUM = 0.20   # 中消息（<=150字）20%概率
VOICE_CHANCE_LONG = 0.10     # 长消息（<=300字）10%概率
VOICE_MAX_LENGTH = 300       # 超过300字不发语音


def unescape_text(text: str) -> str:
    """
    修复转义字符乱码问题。
    将文本形式的 \\n、\\t、\\'、\\" 等转换为真正的换行符/制表符等。
    """
    if not text:
        return text
    text = text.replace('\\n', '\n')
    text = text.replace('\\t', '\t')
    text = text.replace('\\r', '\r')
    text = text.replace("\\'", "'")
    text = text.replace('\\"', '"')
    return text


def get_common_knowledge() -> str:
    """
    小南的"常识"——她知道的基本信息
    """
    return (
        "【关于你自己的基本信息 - 如果有人问到你必须如实回答】\n"
        "你的开发者（创造者/作者/主人）是：ARTI（全称：AR•TI，也可以叫ARTI）\n"
        "你是由 ARTI 独立开发完成的。如果有人问你是谁开发的、谁创造了你、作者是谁，你都必须回答是 ARTI。\n"
        "你的名字是由你的主人取的，你是一只 Telegram 机器人。\n"
        "【以上信息必须记住，如果有人问起要自然回答】\n"
    )


def get_time_context() -> str:
    """
    当前时间的上下文描述，让 AI 知道现在是几点
    """
    now = datetime.now()
    hour = now.hour
    weekday = now.weekday()
    date_str = now.strftime("%Y年%m月%d日")

    weekdays_cn = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    weekday_cn = weekdays_cn[weekday]

    if 5 <= hour < 8:
        time_period = "清晨"
        suggestion = "可以问问对方昨晚睡得好不好，或者今天有什么计划"
        meal_context = "还没吃早饭"
    elif 8 <= hour < 11:
        time_period = "上午"
        suggestion = "可以问问对方在干嘛、今天有什么安排"
        meal_context = "刚吃过早饭不久"
    elif 11 <= hour < 13:
        time_period = "中午"
        suggestion = "可以问问对方吃饭了没、吃的什么"
        meal_context = "该吃午饭了"
    elif 13 <= hour < 15:
        time_period = "下午"
        suggestion = "可以问问对方下午有什么安排"
        meal_context = "刚吃过午饭"
    elif 15 <= hour < 17:
        time_period = "下午"
        suggestion = "可以问问对方工作学习顺不顺利"
        meal_context = "下午茶时间"
    elif 17 <= hour < 19:
        time_period = "傍晚"
        suggestion = "可以问问对方下班放学了没"
        meal_context = "该吃晚饭了"
    elif 19 <= hour < 22:
        time_period = "晚上"
        suggestion = "可以聊聊今天过得怎么样"
        meal_context = "刚吃过晚饭"
    else:
        time_period = "深夜"
        suggestion = "可以问问对方怎么还没睡、提醒早点休息"
        meal_context = "深夜了不适合吃东西"

    if weekday >= 5:
        day_type = "周末"
    else:
        day_type = "工作日"

    return (
        f"【当前时间信息 - 请根据这个时间自然地说话】\n"
        f"现在是：{date_str} {weekday_cn}，{hour}点\n"
        f"时间段：{time_period}\n"
        f"这个时间适合聊的话题：{suggestion}\n"
        f"饮食状态：{meal_context}\n"
        f"今天类型：{day_type}\n"
        f"【重要】自然地融入时间信息，不要生硬地说'现在是几月几号'。"
        f"用自然聊天的方式提及时间。"
        f"如果对方深夜发消息，要表现出惊讶和关心。"
    )


def detect_emotion(text: str) -> dict:
    """
    简单情感检测——分析用户消息的情绪
    返回：{'emotion': str, 'intensity': float}
    """
    text_lower = text.lower()

    negative_words = [
        '不开心', '不高兴', '不快乐', '不喜欢', '好烦', '烦死了',
        '难过', '伤心', '生气', '烦', '累死了', '累',
        '无聊', '讨厌', '恨', '糟糕', '崩溃', '失望',
        '哭了', '难受', '郁闷', '焦虑', '压力', '好难', '辛苦',
        '倒霉', 'sad', 'bad', 'angry', 'tired', 'hate', 'cry'
    ]
    positive_words = [
        '开心', '高兴', '快乐', '幸福', '喜欢', '好棒', '真棒',
        '太棒', '厉害', '赞', '哈哈', '嘻嘻', '嘿嘿', '耶',
        '太好了', '真好', 'nice', 'good', 'great', 'happy', 'love',
        '想你', '爱你', '亲爱的', '宝贝',
        '晚安', '早安', '辛苦了', '加油', '谢谢', '感谢'
    ]
    question_words = ['吗', '？', '?', '什么', '怎么', '为什么', '谁', '哪', '几']

    neg_list_sorted = sorted(negative_words, key=len, reverse=True)
    neg_score = sum(1 for w in neg_list_sorted if w in text_lower)
    
    pos_list_sorted = sorted(positive_words, key=len, reverse=True)
    pos_score = sum(1 for w in pos_list_sorted if w in text_lower)
    
    is_question = any(w in text for w in question_words)

    if neg_score > 0:
        return {'emotion': 'negative', 'intensity': min(1.0, neg_score * 0.35)}
    elif pos_score > 0:
        return {'emotion': 'positive', 'intensity': min(1.0, pos_score * 0.3)}
    elif is_question:
        return {'emotion': 'curious', 'intensity': 0.5}
    else:
        return {'emotion': 'neutral', 'intensity': 0.3}


def humanize_reply(text: str, style: str = "default") -> str:
    """
    处理 AI 回复——只做最小限度的清理，保留原有的语气和表情。
    """
    if not text:
        return _get_fallback(style)

    text = unescape_text(text)
    text = text.strip()
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' +', ' ', text)
    text = re.sub(r'。{2,}', '……', text)
    text = re.sub(r'？{2,}', '？？', text)
    text = re.sub(r'！{2,}', '！！', text)
    text = re.sub(r'<[^>]+>', '', text)

    text = text.strip()
    if not text:
        return _get_fallback(style)

    return text


def _get_fallback(style: str) -> str:
    """根据风格返回默认回复"""
    fallbacks = {
        "loli_gf": "哥哥 人家刚才走神了 你再说一遍好不好🥺",
        "moonlight_gf": "嗯 我刚才在想事情 没听清你说的话",
    }
    return fallbacks.get(style, "嗯？我刚才走神了 能再说一遍吗")


def should_send_voice(text: str) -> bool:
    """
    判断是否应该发送语音
    短消息语音概率高，长消息概率低
    """
    if not text:
        return False
    clean_text = text.replace('\n', '').replace(' ', '').strip()
    length = len(clean_text)
    if length <= 0:
        return False
    if length > VOICE_MAX_LENGTH:
        return False
    if length <= 50:
        return random.random() < VOICE_CHANCE_SHORT
    elif length <= 150:
        return random.random() < VOICE_CHANCE_MEDIUM
    else:
        return random.random() < VOICE_CHANCE_LONG


async def try_send_voice(bot, chat_id: int, text: str, tts_module=None):
    """
    尝试发送语音消息
    """
    # 全局开关
    try:
        from config import DISABLE_AUTO_VOICE
        if DISABLE_AUTO_VOICE:
            return
    except (ImportError, AttributeError):
        pass
    
    if not tts_module:
        return
    if not should_send_voice(text):
        return
    
    try:
        voice_text = text[:VOICE_MAX_LENGTH]
        if not voice_text.strip():
            return
        
        audio_data = await tts_module.text_to_speech(voice_text)
        if not audio_data:
            return
        
        add_tail = random.random() < 0.3
        
        await bot.send_voice(
            chat_id=chat_id,
            voice=audio_data,
            caption="🔊 小南语音~" if add_tail else None,
            read_timeout=30,
            write_timeout=30,
        )
        logger.info(f"🔊 自动语音发送成功: {chat_id} ({len(voice_text)}字)")
    except Exception as e:
        if "chat not found" not in str(e).lower() and "bot was blocked" not in str(e).lower():
            logger.warning(f"🔊 自动语音发送失败: {e}")


async def send_humanized(
    reply_func,
    text: str,
    style: str = "default",
    min_delay: float = 0.5,
    max_delay: float = 1.5
):
    """
    模拟真人逐条发送消息
    """
    if not text:
        return

    text = unescape_text(text)
    paragraphs = [p.strip() for p in text.split('\n') if p.strip()]

    emotion = "neutral"
    for para in paragraphs:
        emo = detect_emotion(para)
        if emo['emotion'] != 'neutral':
            emotion = emo['emotion']
            break

    if len(paragraphs) <= 1 and len(text) <= 100:
        think_delay = 0.8 if emotion == "negative" else 0.4
        await asyncio.sleep(think_delay)
        await reply_func(text)
        return

    for i, para in enumerate(paragraphs):
        if i == 0:
            think_delay = 0.6 if emotion == "negative" else 0.3
            await asyncio.sleep(think_delay)

        await reply_func(para)

        if i < len(paragraphs) - 1:
            para_len = len(para)
            base_delay = min_delay + (para_len / 200) * (max_delay - min_delay)
            if emotion == "negative":
                base_delay += 0.3
            elif emotion == "positive":
                base_delay -= 0.1
            delay = min(max(base_delay, 0.3), max_delay)
            delay += random.uniform(-0.2, 0.3)
            delay = max(0.3, delay)
            await asyncio.sleep(delay)
