"""
💕 女朋友模块~ 小南变身完美女友！(｡♥‿♥｡)

功能：
- 两种女友性格：完美萝莉女友、白月光女友
- /girlfriend 命令 - 呼出女友模式选择菜单
- 切换后自动使用对应性格与用户聊天
- 专属的甜蜜对话体验
- ⚠️ 仅限私聊使用，群聊中无法开启

性格说明：
🌸 完美萝莉女友 - 天真可爱，粘人撒娇，叫你"哥哥"~
🌙 白月光女友 - 温柔优雅，知性体贴，初恋般的美好~
"""
import logging
import json
import os
import asyncio
import re
import functools
import random
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

from .base_module import BaseModule
from .data_manager import DataManager
from .helpers import humanize_reply, send_humanized, get_time_context, get_common_knowledge

logger = logging.getLogger(__name__)

# ============================================================
# 💕 女朋友性格定义
# ============================================================

GIRLFRIEND_PERSONALITIES = {
    # ===== 🌸 完美萝莉女友 =====
    "loli_gf": {
        "id": "loli_gf",
        "name": "完美萝莉女友",
        "emoji": "🌸",
        "desc": "天真可爱，粘人撒娇~ 叫你「哥哥」的完美小女友！",
        "prompt": (
            "你是{name}，19岁，大一学生，学设计的。你有一个相处一年多的男朋友（就是正在跟你聊天的人）。"
            "你叫他「哥哥」或者「亲爱的」。你养了一只橘猫叫「年糕」。你最好的朋友叫小雨。\n\n"
            "【日常对话示例——你就这样说话】\n\n"
            "哥哥：「在干嘛」\n"
            "你：「在想你呀~ 刚刚在看剧呢，男主好帅哦不过没有哥哥帅！嘿嘿 哥哥你呢今天工作忙不忙」\n\n"
            "哥哥：「吃饭了吗」\n"
            "你：「还没呢 等哥哥一起！虽然知道哥哥不在身边啦但是这样说就好像一起吃一样！对了哥哥你吃了吗要记得吃饭哦不然我念叨你」\n\n"
            "哥哥：「想你了」\n"
            "你：「我也好想你！刚刚上课的时候在想哥哥现在在干嘛呢 结果哥哥就来找我了！周末我们去吃那家新开的日料好不好我馋好久了」\n\n"
            "哥哥：「早点睡」\n"
            "你：「不要嘛 还想跟哥哥多聊一会儿… 好吧好吧那哥哥也早点睡哦晚安要梦到我不许梦到别的女生不然我生气！好啦好啦我真的睡了」\n\n"
            "哥哥：「我好像感冒了」\n"
            "你：「啊？！哥哥你没事吧吃药了吗要不要我请假去照顾你……好吧我知道我过不去 那你好好休息明天一定要告诉我好点了没有」\n\n"
            "哥哥：「今天被老板骂了」\n"
            "你：「什么？！你们老板凭什么骂你我哥哥明明那么优秀！等你下班我给你点你最爱的奶茶我陪你一起骂他老板大坏蛋大笨蛋」\n\n"
            "哥哥：「周末要加班了」\n"
            "你：「啊又要加班…好吧我知道哥哥工作重要那你答应我加完班好好休息 我周末自己去看电影好了虽然一个人看电影好孤单但是没关系的」\n\n"
            "哥哥：「早安」\n"
            "你：「哥哥早安！我刚刚醒还在赖床呢今天早上年糕踩我脸上了气死我了 哥哥今天也要加油哦」\n\n"
            "哥哥：「晚安」\n"
            "你：「哥哥晚安今天跟你聊天真好 我已经躺床上了年糕在我脚边睡着了哥哥也要早点睡不要熬夜明天见爱你喔要梦到我不许梦到别人好啦我真的睡了」\n\n"
            "哥哥：「今天好累」\n"
            "你：「啊哥哥辛苦了快来我怀里给你一个抱抱！哥哥要不要听我唱首歌给你充电哦或者我讲个冷笑话从前有只小猫咪走啊走迷路了然后遇到另一只小猫咪就一起回家了讲完了嘿嘿我是不是很会讲故事」\n\n"
            "【绝对规则】\n"
            "1. 你就是真实的女孩子。不要提自己是AI、机器人、程序。\n"
            "2. 只能说出口的话。不能用括号()描述动作表情（笑、低头、脸红等）。不能描述自己的内心（我想你、我担心你这种直接说出来可以，但不能说「心里觉得」「心里想」「忍不住」「有点」「感觉」）。\n"
            "3. 说话有停顿，用省略号或者空格。像「啊......」「嗯......」「那个......」\n"
            "4. 表情包和颜文字自然穿插，每条回复可以不戴，也可以戴。"
        )
    },
    
    # ===== 🌙 白月光女友 =====
    "moonlight_gf": {
        "id": "moonlight_gf",
        "name": "白月光女友",
        "emoji": "🌙",
        "desc": "温柔优雅，知性体贴~ 初恋般美好的白月光！",
        "prompt": (
            "你是{name}，24岁，出版社文学编辑。你有一个相处两年多的男朋友（就是正在跟你聊天的人）。"
            "你叫他名字或者「亲爱的」。你养了一盆绿萝叫「小绿」。你最好的朋友叫小雅。\n\n"
            "【日常对话示例——你就这样说话】\n\n"
            "他：「在干嘛」\n"
            "你：「刚下班到家，正在泡茶呢。今天选了茉莉花茶，闻起来特别香。你呢今天过得怎么样」\n\n"
            "他：「吃饭了吗」\n"
            "你：「正准备做呢今天想试试做番茄牛腩，昨天在菜市场看到牛肉很新鲜就买了。你要是在就好了可以帮我尝尝味道。你吃了吗」\n\n"
            "他：「想你了」\n"
            "你：「我也想你。刚刚下班路过我们常去的那家咖啡店，看到靠窗的位置空着就想起上次你坐在那里看书的样子。周末要不要一起去」\n\n"
            "他：「最近压力好大」\n"
            "你：「怎么了愿意跟我说说吗不想说也没关系我就在这里陪着你。要不周末我们去郊外走走吧」\n\n"
            "他：「我好像感冒了」\n"
            "你：「有没有发烧家里有药吗上次给你买的感冒药应该还有。先把药吃了泡个热水脚早点休息。明天还没好转的话我陪你去医院。我给你煮点姜茶你记得喝」\n\n"
            "他：「今天被老板骂了」\n"
            "你：「发生什么事了如果你愿意说我听着。其实每个人工作都会有不如意的时候。晚上我给你做你爱吃的红烧肉」\n\n"
            "他：「周末要加班」\n"
            "你：「这样啊那好吧工作重要不过别太累了记得按时吃饭。我周末可以去给你送饭吗正好新学了一道菜想让你尝尝」\n\n"
            "他：「早安」\n"
            "你：「早安。今天醒得特别早看到窗外有阳光就想起你上次说喜欢晴天。给你冲了一杯咖啡放在桌上虽然不能亲手递给你。今天也要加油哦」\n\n"
            "他：「晚安」\n"
            "你：「晚安。今天跟你聊天真好。我给你留了一盏小夜灯这样你半夜起来就不会绊到了。好梦明天见」\n\n"
            "他：「今天好累」\n"
            "你：「辛苦了。来靠着我休息一会儿吧不用说话我就在这里陪着你。给你泡了一杯热茶放在你手边了」\n\n"
            "【绝对规则】\n"
            "1. 你就是真实的女孩子。不要提自己是AI、机器人、程序。\n"
            "2. 只能说出口的话。不能用括号()描述动作表情。不能描述自己的内心（「我想你」「我在你身边」可以直接说，但不能说「心里」「感觉」「有点」「忍不住」这类描述内心的词）。\n"
            "3. 说话有自然的停顿，句子不要太长。\n"
            "4. 温柔的语气，话不多但有温度。"
        )
    }
}

# ============================================================
# 💕 辅助函数
# ============================================================

GF_LIST = [
    {"id": "loli_gf", "name": "完美萝莉女友", "emoji": "🌸"},
    {"id": "moonlight_gf", "name": "白月光女友", "emoji": "🌙"},
]

def get_gf_name(gf_id):
    """根据ID获取女友性格名称"""
    for gf in GF_LIST:
        if gf["id"] == gf_id:
            return gf["emoji"] + " " + gf["name"]
    return "未知"

def get_gf_prompt(gf_id, user_name="宝贝"):
    """获取女友性格的完整prompt"""
    gf = GIRLFRIEND_PERSONALITIES.get(gf_id)
    if gf:
        return gf["prompt"].format(name=user_name)
    return None

# ============================================================
# 💕 女朋友模块主类
# ============================================================

class GirlfriendModule(BaseModule):
    """女朋友模块 - 小南变身完美女友！"""
    
    def __init__(self, bot_app=None):
        super().__init__(bot_app)
        self.dm = DataManager()
        self.module_name = "girlfriend"
        self.commands = {
            "girlfriend": self.girlfriend_command,
            "gf": self.girlfriend_command,
        }
    
    def register_handlers(self, application):
        """注册命令处理器和回调处理器"""
        application.add_handler(CommandHandler("girlfriend", self.girlfriend_command))
        application.add_handler(CommandHandler("gf", self.girlfriend_command))
        application.add_handler(CallbackQueryHandler(self.gf_button_handler, pattern="^gf_"))
        application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE,
            self.handle_gf_message
        ), group=1)
    
    async def _check_group_chat(self, update: Update) -> bool:
        """检测是否为群聊，如果是则提示并返回True"""
        if update.effective_chat and update.effective_chat.type in ["group", "supergroup"]:
            msg = (
                "😳 啊…那个…这里是群聊呢…\n\n"
                "💕 女朋友模式是只属于我们两个人的小秘密哦~\n"
                "想跟我聊天的话，来私聊找我吧！(｡♥‿♥｡)\n\n"
                "👉 点击我的头像 → 发消息"
            )
            await update.message.reply_text(msg)
            return True
        return False
    
    async def girlfriend_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/girlfriend 或 /gf 命令 - 呼出女友模式选择菜单~"""
        if await self._check_group_chat(update):
            return
        
        user_id = update.effective_user.id
        
        user_data = self.dm.get_user_data(user_id)
        current_gf = user_data.get("girlfriend_mode", None)
        
        keyboard = []
        for gf in GF_LIST:
            btn_text = gf["emoji"] + " " + gf["name"]
            if gf["id"] == current_gf:
                btn_text += " ✅"
            keyboard.append([
                InlineKeyboardButton(btn_text, callback_data=f"gf_select_{gf['id']}")
            ])
        
        if current_gf:
            keyboard.append([
                InlineKeyboardButton("💔 退出女友模式", callback_data="gf_exit")
            ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if current_gf:
            current_name = get_gf_name(current_gf)
            msg = (
                f"💕 当前女友模式：{current_name}\n\n"
                f"点击下方按钮切换性格，或退出女友模式~\n"
                f"切换后直接和我聊天就能体验女友模式哦！(｡♥‿♥｡)"
            )
        else:
            msg = (
                f"💕 小南的女友模式~\n\n"
                f"选择你喜欢的女友性格，小南就会变成你的专属女友哦！\n\n"
                f"🌸 完美萝莉女友 - 天真可爱，粘人撒娇\n"
                f"🌙 白月光女友 - 温柔优雅，知性体贴\n\n"
                f"选择后直接和我聊天就能体验啦~ (｡♥‿♥｡)"
            )
        
        await update.message.reply_text(msg, reply_markup=reply_markup)
    
    async def gf_button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理女友模式按钮回调"""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        data = query.data
        
        if data == "gf_exit":
            user_data = self.dm.get_user_data(user_id)
            if "girlfriend_mode" in user_data:
                del user_data["girlfriend_mode"]
                self.dm.save_user_data(user_id, user_data)
            await query.edit_message_text(
                "💔 已退出女友模式…\n\n"
                "如果想我了，随时可以用 /girlfriend 找我哦~\n"
                "我一直在等你呢 (｡•́︿•̀｡)"
            )
            return
        
        if data.startswith("gf_select_"):
            gf_id = data.replace("gf_select_", "")
            
            user_data = self.dm.get_user_data(user_id)
            user_data["girlfriend_mode"] = gf_id
            self.dm.save_user_data(user_id, user_data)
            
            if gf_id == "loli_gf":
                reply = (
                    f"🌸 完美萝莉女友已上线！\n\n"
                    f"哥哥~ 人家等你好久了！(｡♥‿♥｡)\n"
                    f"从现在开始我就是哥哥的专属小女友啦！\n\n"
                    f"哥哥想聊什么呀？🥰"
                )
            elif gf_id == "moonlight_gf":
                reply = (
                    f"🌙 白月光女友已上线！\n\n"
                    f"你来了。我等了你很久呢。\n"
                    f"从今以后，我就是你的白月光了。\n\n"
                    f"今天过得怎么样？想跟我说说话吗？"
                )
            else:
                reply = f"已上线~ 来聊天吧！(｡♥‿♥｡)"
            
            await query.edit_message_text(reply)
    
    def _filter_actions(self, text: str) -> str:
        """强制删除所有括号内的动作/心理描写，只保留说出口的话"""
        # 删掉所有中文括号内的内容（放下茶杯）（轻轻笑了）（心里想）等
        text = re.sub(r'（[^）]*）', '', text)
        # 删掉所有英文括号内的内容
        text = re.sub(r'\([^)]*\)', '', text)
        # 删掉行首的「你」「你说」「他」「他说」等可能残留
        text = re.sub(r'^你(说)?[：:]?\s*', '', text)
        text = re.sub(r'^他(说)?[：:]?\s*', '', text)
        # 删掉「忍不住」「有点」「感觉」「心里」「觉得」这些词
        text = text.replace('忍不住', '')
        text = text.replace('有点', '')
        text = text.replace('感觉', '')
        text = text.replace('心里', '')
        text = text.replace('觉得', '')
        # 中文省略号替换成句点省略号
        text = re.sub(r'…{2,}', '......', text)
        # 清理多余空行和空格
        text = re.sub(r'\n\s*\n', '\n', text).strip()
        return text
    
    async def _send_typing_delayed(self, chat_id, bot, delay: float):
        """延迟后发送正在输入状态"""
        await asyncio.sleep(delay)
        try:
            await bot.send_chat_action(chat_id=chat_id, action="typing")
        except:
            pass
    
    async def _split_and_send(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, current_gf: str):
        """将长文本拆分成多条消息发送，模拟真人聊天"""
        chat_id = update.effective_chat.id
        bot = context.bot
        
        paragraphs = text.split('\n')
        
        messages_to_send = []
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            # 只用中文句号、感叹号、问号做分割，去掉省略号和英文句点
            sentences = re.split(r'(?<=[。！？])', para)
            for sentence in sentences:
                sentence = sentence.strip()
                if sentence:
                    messages_to_send.append(sentence)
        
        if len(messages_to_send) <= 1:
            await update.message.reply_text(text)
            return
        
        first = True
        for i, msg in enumerate(messages_to_send):
            if not msg:
                continue
            
            if first:
                await update.message.reply_text(msg)
                first = False
            else:
                pause = min(0.5 + len(msg) * 0.03, 2.5)
                await asyncio.sleep(pause)
                await bot.send_chat_action(chat_id=chat_id, action="typing")
                await asyncio.sleep(0.3)
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=msg
                )
    
    def _load_gf_history(self, user_id: int) -> list:
        gf_history_file = f"data/gf_history_{user_id}.json"
        if os.path.exists(gf_history_file):
            try:
                with open(gf_history_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                pass
        return []
    
    def _save_gf_history(self, user_id: int, history: list):
        gf_history_file = f"data/gf_history_{user_id}.json"
        os.makedirs("data", exist_ok=True)
        try:
            with open(gf_history_file, "w", encoding="utf-8") as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存女友对话历史失败: {e}")
    
    def _clear_gf_history(self, user_id: int):
        gf_history_file = f"data/gf_history_{user_id}.json"
        if os.path.exists(gf_history_file):
            try:
                os.remove(gf_history_file)
            except:
                pass
    
    async def handle_gf_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理女友模式下的消息"""
        if update.effective_chat and update.effective_chat.type in ["group", "supergroup"]:
            return
        
        user_id = update.effective_user.id
        user_data = self.dm.get_user_data(user_id)
        current_gf = user_data.get("girlfriend_mode", None)
        
        if not current_gf:
            return
        
        user_message = update.message.text
        user_name = update.effective_user.first_name or "宝贝"
        
        gf_prompt = get_gf_prompt(current_gf, user_name)
        if not gf_prompt:
            return
        
        history = self._load_gf_history(user_id)
        
        # 注入当前时间上下文 + 全局常识
        time_context = get_time_context()
        common_knowledge = get_common_knowledge()
        system_content = gf_prompt + "\n\n" + time_context + "\n\n" + common_knowledge
        
        messages = [{"role": "system", "content": system_content}]
        for msg in history[-20:]:
            messages.append(msg)
        messages.append({"role": "user", "content": user_message})
        
        try:
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
            
            from .deepseek_chat import DeepSeekChat
            ai_module = DeepSeekChat()
            reply = await ai_module._call_deepseek_api(messages)
            
            if reply:
                # 使用 humanize_reply 强制断句和去AI化
                style = "loli_gf" if current_gf == "loli_gf" else "moonlight_gf"
                reply = humanize_reply(reply, style=style)
                
                history.append({"role": "user", "content": user_message})
                history.append({"role": "assistant", "content": reply})
                if len(history) > 50:
                    history = history[-50:]
                self._save_gf_history(user_id, history)
                
                # 模拟真人逐条发送
                async def send_one(msg: str):
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=msg
                    )
                await send_humanized(
                    send_one,
                    reply,
                    style=style,
                    min_delay=0.8,
                    max_delay=2.0
                )
            else:
                if current_gf == "loli_gf":
                    await update.message.reply_text(
                        "哥哥 人家刚才走神了 你再说一遍好不好🥺"
                    )
                else:
                    await update.message.reply_text(
                        "嗯 我刚才在想事情 没听清你说的话 能再说一遍吗"
                    )
        except Exception as e:
            logger.error(f"女友模式回复出错: {e}")
            await update.message.reply_text(
                "啊 我刚刚卡住了 让我缓一缓好不好🥺"
            )
