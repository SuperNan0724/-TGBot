"""
🔧 辅助函数 - 让人工智能的回复更像真人在聊天
"""
import re
import asyncio
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def get_common_knowledge() -> str:
    """
    获取小南的"常识"——这些是她应该知道的基本信息
    注入到 AI 的 system prompt 中，让所有性格都知道这些事实
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
    获取当前时间的上下文描述，注入到 AI 的 system prompt 中
    让 AI 知道现在是几点、该问什么、该说什么，表现得像真人一样有时间观念
    """
    now = datetime.now()
    hour = now.hour
    weekday = now.weekday()
    date_str = now.strftime("%Y年%m月%d日")

    weekdays_cn = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    weekday_cn = weekdays_cn[weekday]

    if 5 <= hour < 8:
        time_period = "清晨"
        greeting = "早上好/早安"
        suggestion = "可以问问对方昨晚睡得好不好，或者今天有什么计划。适合说'早安'、'睡醒了吗'、'今天天气不错'"
        meal_context = "还没吃早饭"
    elif 8 <= hour < 11:
        time_period = "上午"
        greeting = "早上好/早安"
        suggestion = "可以问问对方在干嘛、今天有什么安排。适合说'在忙吗'、'今天要干嘛呀'"
        meal_context = "刚吃过早饭不久"
    elif 11 <= hour < 13:
        time_period = "中午"
        greeting = "中午好"
        suggestion = "可以问问对方吃饭了没、吃的什么。适合说'吃饭了吗'、'中午吃的什么呀'"
        meal_context = "该吃午饭了"
    elif 13 <= hour < 15:
        time_period = "下午"
        greeting = "下午好"
        suggestion = "可以问问对方下午有什么安排，或者提醒对方休息一下。适合说'下午忙吗'、'困不困呀'"
        meal_context = "刚吃过午饭"
    elif 15 <= hour < 17:
        time_period = "下午"
        greeting = "下午好"
        suggestion = "可以问问对方工作/学习顺不顺利。适合说'在干嘛呢'、'下午过得怎么样'"
        meal_context = "下午茶时间"
    elif 17 <= hour < 19:
        time_period = "傍晚"
        greeting = "晚上好"
        suggestion = "可以问问对方下班/放学了没、晚饭吃的什么。适合说'下班了吗'、'晚饭吃的什么呀'"
        meal_context = "该吃晚饭了"
    elif 19 <= hour < 22:
        time_period = "晚上"
        greeting = "晚上好"
        suggestion = "可以聊聊今天过得怎么样、做了什么事。适合说'今天过得怎么样'、'晚上有什么安排'"
        meal_context = "刚吃过晚饭"
    else:
        time_period = "深夜"
        greeting = "晚上好/晚安"
        suggestion = "可以问问对方怎么还没睡、提醒早点休息。适合说'这么晚还没睡呀'、'早点休息哦'、'熬夜对身体不好'"
        meal_context = "深夜了不适合吃东西"

    if weekday >= 5:
        day_type = "周末"
    else:
        day_type = "工作日"

    return (
        f"【当前时间信息 - 请根据这个时间自然地说话】\n"
        f"现在是：{date_str} {weekday_cn}，{hour}点\n"
        f"时间段：{time_period}\n"
        f"适合说的问候语：{greeting}\n"
        f"这个时间适合聊的话题：{suggestion}\n"
        f"饮食状态：{meal_context}\n"
        f"今天类型：{day_type}\n"
        f"【重要】请自然地融入时间信息，不要生硬地说'现在是几月几号'。"
        f"比如上午可以说'今天起得好早呀'，中午可以说'吃饭了吗'，晚上可以说'今天过得怎么样'。"
        f"如果对方深夜发消息，要表现出惊讶和关心，问对方怎么还不睡。"
    )


def humanize_reply(text: str, style: str = "default") -> str:
    """
    强制断句 + 去AI化
    核心规则：一句话就是一行。不换行就是长句，长句必须被拆开。
    """
    if not text:
        return text

    # === 1. 删除括号动作描写 ===
    text = re.sub(r'[（(][^）)]*[）)]', '', text)

    # === 2. 删除 AI 痕迹词 ===
    text = re.sub(r'忍不住', '', text)
    text = re.sub(r'有点', '', text)
    text = re.sub(r'觉得', '', text)
    text = re.sub(r'心里[^，。！？\n]{0,10}[，。！？]', '', text)
    text = re.sub(r'感觉[^，。！？\n]{0,10}[，。！？]', '', text)

    # === 3. 暴力断句 ===
    lines = []
    raw_sentences = re.split(r'(?<=[。！？])', text)

    for sent in raw_sentences:
        sent = sent.strip()
        if not sent:
            continue
        if len(sent) > 25:
            sub_parts = re.split(r'(?<=[，、；])', sent)
            for sub in sub_parts:
                sub = sub.strip()
                if sub:
                    lines.append(sub)
        else:
            lines.append(sent)

    # === 4. 如果一行太长，强制按字数拆 ===
    final_lines = []
    for line in lines:
        if len(line) > 30:
            chunks = []
            while len(line) > 20:
                cut = 15
                for pos in range(15, min(len(line), 25)):
                    if line[pos] in ' ，、；':
                        cut = pos
                        break
                chunks.append(line[:cut].strip())
                line = line[cut:].strip()
            if line:
                chunks.append(line)
            merged = []
            i = 0
            while i < len(chunks):
                if i + 1 < len(chunks):
                    merged.append(chunks[i] + ' ' + chunks[i+1])
                    i += 2
                else:
                    merged.append(chunks[i])
                    i += 1
            final_lines.extend(merged)
        else:
            final_lines.append(line)

    # === 5. 按风格合并太短的行 ===
    if style == "loli_gf":
        result = _merge_short_lines(final_lines, max_len=40)
    elif style == "moonlight_gf":
        result = final_lines
    else:
        result = final_lines

    # === 6. 清理 ===
    text = '\n'.join(result)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {2,}', ' ', text)
    text = text.strip()

    if not text:
        if style == "loli_gf":
            return "哥哥 人家刚才走神了 你再说一遍好不好🥺"
        elif style == "moonlight_gf":
            return "嗯 我刚才在想事情 没听清你说的话"
        return "嗯？我刚才走神了 能再说一遍吗"

    return text


def _merge_short_lines(lines: list, max_len: int = 40) -> list:
    """把太短的行合并一下"""
    result = []
    buffer = ""
    for line in lines:
        if buffer and len(buffer) + len(line) + 1 <= max_len:
            buffer += ' ' + line
        else:
            if buffer:
                result.append(buffer)
            buffer = line
    if buffer:
        result.append(buffer)
    return result


async def send_humanized(
    reply_func,
    text: str,
    style: str = "default",
    min_delay: float = 0.8,
    max_delay: float = 2.0
):
    """
    模拟真人逐条发送消息
    """
    import random

    lines = text.split('\n')
    lines = [p.strip() for p in lines if p.strip()]

    if len(lines) <= 2:
        await reply_func(text)
        return

    for i, line in enumerate(lines):
        await reply_func(line)
        if i < len(lines) - 1:
            delay = random.uniform(min_delay, max_delay)
            await asyncio.sleep(delay)
