"""
DeepSeek AI 对话模块~ 和小南聊天玩耍！(｡♥‿♥｡)
"""
import logging
import aiohttp
import json
import os
import re
import random
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

from config import DEEPSEEK_API_KEY, DEEPSEEK_API_URL, DEEPSEEK_MODEL, MAX_HISTORY_LENGTH, BOT_NAME_SHORT, DEFAULT_PERSONALITY
from .base_module import BaseModule
from .data_manager import DataManager
from .personalities import PERSONALITIES, PERSONALITY_PROMPTS, PERSONALITY_NAMES, get_prompt, get_personality_name
from .helpers import humanize_reply, send_humanized, get_time_context

logger = logging.getLogger(__name__)

# 记忆数据文件
MEMORY_FILE = "data/memories.json"

# ===== 性格系统 =====
# 从 personalities.py 导入性格数据
# 构建按钮菜单用的列表（带 emoji 和 desc）
PERSONALITY_LIST = [
    {
        "id": p["id"],
        "name": f"{p['emoji']} {p['name']}",
        "desc": p["desc"],
        "prompt": p["prompt"]
    }
    for p in PERSONALITIES
]


def _load_memories():
    """加载所有记忆~"""
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {}


def _save_memories(memories):
    """保存所有记忆~"""
    os.makedirs(os.path.dirname(MEMORY_FILE), exist_ok=True)
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(memories, f, ensure_ascii=False, indent=2)


def _get_user_memories(user_id: int) -> list:
    """获取用户的记忆列表~"""
    memories = _load_memories()
    return memories.get(str(user_id), [])


def _add_memory(user_id: int, content: str):
    """添加一条记忆~"""
    memories = _load_memories()
    user_id_str = str(user_id)
    
    if user_id_str not in memories:
        memories[user_id_str] = []
    
    memories[user_id_str].append({
        "content": content,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M")
    })
    
    # 限制记忆数量，保留最新的50条
    if len(memories[user_id_str]) > 50:
        memories[user_id_str] = memories[user_id_str][-50:]
    
    _save_memories(memories)


def _delete_memory(user_id: int, index: int) -> bool:
    """删除指定索引的记忆~"""
    memories = _load_memories()
    user_id_str = str(user_id)
    
    if user_id_str in memories and 0 <= index < len(memories[user_id_str]):
        del memories[user_id_str][index]
        _save_memories(memories)
        return True
    return False


def _clear_memories(user_id: int):
    """清除用户的所有记忆~"""
    memories = _load_memories()
    user_id_str = str(user_id)
    
    if user_id_str in memories:
        del memories[user_id_str]
        _save_memories(memories)


def _extract_memories_from_text(text: str) -> list:
    """从对话中提取可能的重要信息作为记忆~"""
    extracted = []
    
    # 提取名字信息
    name_patterns = [
        r"(?:我叫|我是|我的名字是|可以叫我|叫我)(.+?)(?:[，。！？\s]|$)",
        r"(?:你叫我|你就叫我|你叫我)(.+?)(?:[，。！？\s]|$)",
        r"(?:称呼我|称呼我为)(.+?)(?:[，。！？\s]|$)"
    ]
    for pattern in name_patterns:
        match = re.search(pattern, text)
        if match:
            name = match.group(1).strip()
            if len(name) <= 10:  # 避免提取太长
                extracted.append(f"对方的名字是{name}")
    
    # 提取喜好信息
    like_patterns = [
        r"(?:我喜欢|我爱|我最爱|我超爱|我特别喜欢|我最喜欢)(.+?)(?:[，。！？\s]|$)",
        r"(?:我讨厌|我不喜欢|我最讨厌)(.+?)(?:[，。！？\s]|$)",
        r"(?:我的爱好是|我的兴趣是|我平时喜欢)(.+?)(?:[，。！？\s]|$)"
    ]
    for pattern in like_patterns:
        match = re.search(pattern, text)
        if match:
            like = match.group(1).strip()
            if len(like) <= 20:
                extracted.append(f"对方{like}")
    
    # 提取职业/身份信息
    identity_patterns = [
        r"(?:我是|我是一名|我是一个|我是做)(.+?)(?:[，。！？\s]|$)",
        r"(?:我在|我从事|我工作在)(.+?)(?:[，。！？\s]|$)"
    ]
    for pattern in identity_patterns:
        match = re.search(pattern, text)
        if match:
            identity = match.group(1).strip()
            if len(identity) <= 20:
                extracted.append(f"对方的身份是{identity}")
    
    return extracted


class DeepSeekChat(BaseModule):
    """DeepSeek AI 对话模块~ 和小南聊天玩耍！"""
    
    name = "deepseek_chat"
    description = "和 DeepSeek AI 聊天~"
    
    def __init__(self, bot_app=None):
        super().__init__(bot_app)
        self.dm = DataManager()
    
    def register_handlers(self, application):
        """注册命令和消息处理器~"""
        application.add_handler(CommandHandler("chat", self.chat_command))
        application.add_handler(CommandHandler("role", self.role_command))
        application.add_handler(CallbackQueryHandler(self.role_callback, pattern=r"^role_"))
        application.add_handler(CommandHandler("remember", self.remember_command))
        application.add_handler(CommandHandler("forget", self.forget_command))
        application.add_handler(CommandHandler("memories", self.memories_command))
        application.add_handler(CommandHandler("clear_memories", self.clear_memories_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
    
    async def chat_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/chat 命令 - 和 AI 聊天~"""
        if not context.args:
            await update.message.reply_text(
                "用法：/chat <你想说的话>\n"
                "或者直接发消息给我也可以哦~ 喵！(｡♥‿♥｡)"
            )
            return
        
        question = " ".join(context.args)
        await self._handle_chat(update, context, question)

    async def role_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/role 命令 - 呼出性格选择菜单（翻页）~"""
        user_id = update.effective_user.id
        user_data = self.dm.get_user_data(user_id)
        current_role = user_data.get("personality", DEFAULT_PERSONALITY)
        current_name = PERSONALITY_NAMES.get(current_role, "🐱 默认 - 可爱猫咪")

        # 保存当前页到 context
        context.user_data["role_page"] = 0

        await self._send_role_page(update.message, context, user_id, current_role)

    async def _send_role_page(self, message, context, user_id, current_role, edit=False):
        """发送性格选择翻页菜单~"""
        page = context.user_data.get("role_page", 0)
        per_page = 9  # 每页9个性格（3行x3列）
        total_pages = (len(PERSONALITY_LIST) + per_page - 1) // per_page
        start = page * per_page
        end = min(start + per_page, len(PERSONALITY_LIST))
        page_items = PERSONALITY_LIST[start:end]
        current_name = PERSONALITY_NAMES.get(current_role, "🐱 默认 - 可爱猫咪")

        # 构建按钮（每行3列）
        keyboard = []
        row = []
        for i, p in enumerate(page_items):
            # 缩短按钮文字：只取 emoji + 短名
            short_name = p["name"]
            # 去掉"少女/少年"等长后缀
            for long_suffix, short_suffix in [("少女/少年", ""), ("少女", ""), ("达人", "")]:
                short_name = short_name.replace(long_suffix, short_suffix)
            if p["id"] == current_role:
                short_name += "✅"
            row.append(InlineKeyboardButton(short_name, callback_data=f"role_{p['id']}"))
            if len(row) == 3:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)

        # 翻页按钮
        nav_row = []
        if page > 0:
            nav_row.append(InlineKeyboardButton("◀ 上一页", callback_data="role_page_prev"))
        nav_row.append(InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="role_page_info"))
        if page < total_pages - 1:
            nav_row.append(InlineKeyboardButton("下一页 ▶", callback_data="role_page_next"))
        if nav_row:
            keyboard.append(nav_row)

        reply_markup = InlineKeyboardMarkup(keyboard)

        msg = (
            f"🎭 小南的性格切换~\n"
            f"当前：{current_name}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"点击下方按钮选择性格~"
        )

        if edit:
            await message.edit_text(msg, reply_markup=reply_markup)
        else:
            await message.reply_text(msg, reply_markup=reply_markup)

    async def role_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理性格选择按钮回调~"""
        query = update.callback_query
        await query.answer()

        data = query.data
        user_id = update.effective_user.id
        user_data = self.dm.get_user_data(user_id)
        current_role = user_data.get("personality", DEFAULT_PERSONALITY)

        # 翻页操作
        if data == "role_page_next":
            context.user_data["role_page"] = context.user_data.get("role_page", 0) + 1
            await self._send_role_page(query.message, context, user_id, current_role, edit=True)
            return
        elif data == "role_page_prev":
            context.user_data["role_page"] = context.user_data.get("role_page", 0) - 1
            await self._send_role_page(query.message, context, user_id, current_role, edit=True)
            return
        elif data == "role_page_info":
            return  # 页码按钮，不做操作

        # 选择性格
        role_id = data.replace("role_", "")
        if role_id in PERSONALITY_PROMPTS:
            user_data["personality"] = role_id
            user_data["last_active"] = datetime.now().isoformat()
            self.dm.save_user_data(user_id, user_data)

            new_name = PERSONALITY_NAMES[role_id]
            p_info = PERSONALITY_LIST[[p['id'] for p in PERSONALITY_LIST].index(role_id)]

            await query.edit_message_text(
                f"🎭 小南的性格已经切换为：\n"
                f"{new_name}\n\n"
                f"现在的小南是这样子的~\n"
                f"{p_info['desc']}\n\n"
                f"来和小南聊天试试吧！(｡♥‿♥｡)"
            )
    
    async def remember_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/remember - 让小南记住一件事~"""
        if not context.args:
            await update.message.reply_text(
                "💭 想让小南记住什么呢~\n"
                "用法：/remember <内容>\n"
                "例如：/remember 我最喜欢吃草莓蛋糕"
            )
            return
        
        content = " ".join(context.args)
        user_id = update.effective_user.id
        
        _add_memory(user_id, content)
        
        await update.message.reply_text(
            f"💭 小南记住啦~\n"
            f"📝 {content}\n"
            f"小南会一直记得的！(｡♥‿♥｡)\n\n"
            f"查看记忆：/memories"
        )
    
    async def forget_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/forget - 让小南忘记一件事~"""
        if not context.args:
            await update.message.reply_text(
                "💭 想让小南忘记哪件事呢~\n"
                "用法：/forget <编号>\n"
                "先用 /memories 查看编号哦~"
            )
            return
        
        try:
            index = int(context.args[0]) - 1  # 用户看到的是从1开始
            user_id = update.effective_user.id
            
            if _delete_memory(user_id, index):
                await update.message.reply_text("💭 小南已经忘记这件事啦~ 🧹")
            else:
                await update.message.reply_text("😅 没有找到这个编号的记忆呢~ 用 /memories 看看吧")
        except ValueError:
            await update.message.reply_text("😅 要输入数字编号哦~ 用 /memories 查看编号")
    
    async def memories_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/memories - 查看小南记得的事情~"""
        user_id = update.effective_user.id
        user_memories = _get_user_memories(user_id)
        
        if not user_memories:
            await update.message.reply_text(
                "💭 小南还没有关于你的记忆呢~\n"
                "用 /remember 让小南记住一些事情吧！\n"
                "或者多和小南聊天，小南会自己记住的~"
            )
            return
        
        msg = f"💭 小南记得关于你的事情~\n\n"
        for i, mem in enumerate(user_memories, 1):
            msg += f"{i}. 📝 {mem['content']}\n"
            msg += f"   🕐 {mem['time']}\n\n"
        
        msg += "忘记某件事：/forget <编号>\n"
        msg += "清除所有：/clear_memories"
        
        await update.message.reply_text(msg)
    
    async def clear_memories_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/clear_memories - 清除所有记忆~"""
        user_id = update.effective_user.id
        _clear_memories(user_id)
        await update.message.reply_text("💭 小南已经清除了所有关于你的记忆~ 🧹")
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理普通消息~"""
        chat_type = update.effective_chat.type
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        # 私聊：检查是否开启了女友模式
        if chat_type == "private":
            user_data = self.dm.get_user_data(user_id)
            if user_data.get("girlfriend_mode"):
                return  # 女友模式已开启，让 girlfriend 模块处理
        
        # 私聊：检查用户是否在白名单
        if chat_type == "private":
            if not self.dm.is_user_whitelisted(user_id) and not self.dm.is_owner(user_id):
                await update.message.reply_text(
                    "呜… 你没有小鱼干呢(｡•́︿•̀｡)\n"
                    "只有主人添加的小可爱才能和我聊天哦~"
                )
                return
        
        # 群聊：检查群组是否在白名单
        elif chat_type in ("group", "supergroup"):
            if not self.dm.is_group_whitelisted(chat_id):
                return  # 群组不在白名单，直接忽略
            
            # 检查是否应该回复
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
        
        question = update.effective_message.text
        
        # 自动提取记忆
        extracted = _extract_memories_from_text(question)
        for memory in extracted:
            _add_memory(user_id, memory)
            if extracted:
                logger.info(f"自动记忆: 用户{user_id} - {memory}")
        
        await self._handle_chat(update, context, question)
    
    async def _handle_chat(self, update: Update, context: ContextTypes.DEFAULT_TYPE, question: str):
        """处理聊天逻辑~"""
        # 检查 API Key
        if not DEEPSEEK_API_KEY or DEEPSEEK_API_KEY == "YOUR_DEEPSEEK_API_KEY":
            await update.message.reply_text(
                "呜… 主人还没有给我配置 AI 能力呢(｡•́︿•̀｡)\n"
                "请主人先在 config.py 里设置 DEEPSEEK_API_KEY 吧~"
            )
            return
        
        user_id = update.effective_user.id
        user_data = self.dm.get_user_data(user_id)
        personality = user_data.get("personality", DEFAULT_PERSONALITY)
        
        # 发送"正在输入"状态
        await update.effective_chat.send_action("typing")
        
        # 构建对话历史（包含记忆）
        messages = self._build_messages(user_data, personality, question, user_id)
        
        try:
            response = await self._call_deepseek_api(messages)
            
            if response:
                # 人性化处理：断句+去AI化
                response = humanize_reply(response, style="default")
                
                # 保存对话历史（保存处理前的原始回复，避免下次对话历史也断句）
                user_data["history"].append({"role": "user", "content": question})
                user_data["history"].append({"role": "assistant", "content": response})
                
                # 限制历史长度
                if len(user_data["history"]) > MAX_HISTORY_LENGTH * 2:
                    user_data["history"] = user_data["history"][-(MAX_HISTORY_LENGTH * 2):]
                
                user_data["last_active"] = datetime.now().isoformat()
                self.dm.save_user_data(user_id, user_data)
                
                # 逐条发送，模拟真人
                async def send_one(msg: str):
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=msg
                    )
                await send_humanized(
                    send_one,
                    response,
                    style="default",
                    min_delay=0.5,
                    max_delay=1.5
                )
            else:
                await update.message.reply_text(
                    "呜… AI 好像走神了(｡•́︿•̀｡)\n"
                    "请稍后再试试吧~ 喵！"
                )
        
        except Exception as e:
            logger.error(f"DeepSeek API 调用失败: {e}")
            self.dm.add_error({"message": f"DeepSeek API 错误: {str(e)}", "user_id": user_id})
            await update.message.reply_text(
                "呜… 好像出了点小问题呢(｡•́︿•̀｡)\n"
                "请稍后再试试看吧~ 喵！"
            )
    
    def _build_messages(self, user_data: dict, personality: str, question: str, user_id: int) -> list:
        """构建消息列表（包含记忆+时间上下文）~"""
        system_prompt = get_prompt(personality, BOT_NAME_SHORT)
        
        # 注入当前时间上下文
        time_context = get_time_context()
        
        # 获取用户的记忆
        user_memories = _get_user_memories(user_id)
        
        # 构建包含记忆和时间信息的系统提示
        memory_prompt = ""
        if user_memories:
            memory_prompt = "\n\n以下是你对这个人的记忆（请记住这些信息）：\n"
            for mem in user_memories:
                memory_prompt += f"- {mem['content']}\n"
        
        full_system_prompt = system_prompt + "\n\n" + time_context + memory_prompt
        
        messages = [
            {"role": "system", "content": full_system_prompt}
        ]
        
        # 添加对话历史
        for msg in user_data.get("history", []):
            messages.append(msg)
        
        # 添加当前问题
        messages.append({"role": "user", "content": question})
        
        return messages
    
    async def _call_deepseek_api(self, messages: list) -> str:
        """调用 DeepSeek API~"""
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": DEEPSEEK_MODEL,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 2000
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=30) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data["choices"][0]["message"]["content"]
                else:
                    error_text = await resp.text()
                    logger.error(f"API 返回错误: {resp.status} - {error_text}")
                    return None
    
    def get_help_text(self) -> str:
        """返回帮助文本~"""
        return (
            "/chat <问题> - 和 AI 聊天~\n"
            "/role - 切换小南的性格（按钮菜单）~\n"
            "/remember <内容> - 让小南记住一件事~\n"
            "/memories - 查看小南记得的事情~\n"
            "/forget <编号> - 让小南忘记一件事~\n"
            "/clear_memories - 清除所有记忆~\n"
            "直接发消息也能和我聊天哦~"
        )
