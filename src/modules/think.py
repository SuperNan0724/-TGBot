"""
思考模式模块~ 让小南帮你认真思考问题！(｡•̀ᴗ-)✧
支持 /think 命令和关键词触发（帮我想一下、思考一下、帮我找一下）

✨ 特性：
- 思考时不会被中断（同一用户加锁）
- 超时保护防止 bot 暴死
- 思考过程在内部完成，只输出最终结果
- 与普通聊天互不冲突
"""
import logging
import aiohttp
import asyncio
import re
from datetime import datetime

from telegram import Update
from telegram.ext import CommandHandler, MessageHandler, filters, ContextTypes

from config import DEEPSEEK_API_KEY, DEEPSEEK_API_URL, DEEPSEEK_MODEL
from .base_module import BaseModule
from .data_manager import DataManager

logger = logging.getLogger(__name__)

# 触发关键词
TRIGGER_KEYWORDS = [
    "帮我想一下",
    "思考一下",
    "帮我找一下",
    "帮我查一下",
    "帮我分析",
    "帮我看看",
    "我想知道",
    "你说说",
    "你怎么看",
    "你觉得",
    "有没有",
    "是什么",
    "为什么",
    "怎么办",
    "怎么弄",
    "如何",
    "啥是",
    "啥叫",
]

# 思考模式系统提示词（引导 AI 内部思考，只输出结论）
THINK_SYSTEM_PROMPT = """你是一只聪明又认真的思考型猫咪，名叫小南。
当用户需要你思考问题时，你会进入"认真模式"。

你的思考流程（在内部完成，用户看不到）：
1. 分析问题的关键点和核心需求
2. 分步骤推理，考虑各种可能性
3. 得出结论或给出建议

输出规则：
- 只输出最终的结论或建议，不要展示思考过程
- 用简洁清晰的语言表达
- 开头用 "🤔" 或 "🧐" 表情
- 结论用 "💡" 或 "✨" 标注
- 最后用 "喵~" 结尾
- 保持可爱但专业的语气

记住：用户只关心最终答案，不要输出你的思考步骤！"""


class Think(BaseModule):
    """思考模式模块~ 让小南帮你认真思考问题！"""
    
    name = "think"
    description = "让小南帮你思考问题~"
    
    def __init__(self, bot_app=None):
        super().__init__(bot_app)
        self.dm = DataManager()
        # 用户思考锁：{user_id: timestamp}，防止同一用户重复触发
        self._thinking_users: dict = {}
    
    def register_handlers(self, application):
        """注册命令和消息处理器~"""
        application.add_handler(CommandHandler("think", self.think_command))
        # 关键词触发只处理私聊，群聊需要 @ 或回复
        application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE,
            self.handle_private_message
        ))
        application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND & (filters.ChatType.GROUP | filters.ChatType.SUPERGROUP),
            self.handle_group_message
        ))
    
    def _is_thinking(self, user_id: int) -> bool:
        """检查用户是否正在思考中~"""
        if user_id in self._thinking_users:
            # 检查是否超时（超过60秒自动解锁）
            elapsed = (datetime.now() - self._thinking_users[user_id]).total_seconds()
            if elapsed > 60:
                del self._thinking_users[user_id]
                return False
            return True
        return False
    
    def _lock_user(self, user_id: int):
        """锁定用户，开始思考~"""
        self._thinking_users[user_id] = datetime.now()
    
    def _unlock_user(self, user_id: int):
        """解锁用户，思考完成~"""
        if user_id in self._thinking_users:
            del self._thinking_users[user_id]
    
    async def think_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/think 命令 - 让小南帮你思考~"""
        if not context.args:
            await update.message.reply_text(
                "🧐 想让小南帮你想什么呢~\n\n"
                "用法：/think <你的问题>\n"
                "例如：/think 周末去哪里玩比较好\n\n"
                "或者直接说「帮我想一下xxx」「思考一下xxx」\n"
                "小南也会进入思考模式哦！(｡•̀ᴗ-)✧"
            )
            return
        
        question = " ".join(context.args)
        await self._handle_think(update, context, question)
    
    async def handle_private_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理私聊消息，检测关键词触发思考模式~"""
        text = update.effective_message.text
        
        if self._should_think(text):
            await self._handle_think(update, context, text)
    
    async def handle_group_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理群聊消息，检测关键词触发思考模式~"""
        chat_id = update.effective_chat.id
        
        # 检查群组是否在白名单
        if not self.dm.is_group_whitelisted(chat_id):
            return
        
        message = update.effective_message
        bot_username = context.bot.username
        bot_id = context.bot.id
        
        # 检查是否被 @ 或回复机器人
        is_mentioned = bot_username and f"@{bot_username}" in (message.text or "")
        is_reply_to_bot = False
        if message.reply_to_message and message.reply_to_message.from_user:
            is_reply_to_bot = message.reply_to_message.from_user.id == bot_id
        
        if not is_mentioned and not is_reply_to_bot:
            return
        
        text = update.effective_message.text
        
        # 去除 @bot 前缀
        if bot_username:
            text = re.sub(rf"@{bot_username}\s*", "", text).strip()
        
        if self._should_think(text):
            await self._handle_think(update, context, text)
    
    def _should_think(self, text: str) -> bool:
        """判断是否应该进入思考模式~"""
        if not text:
            return False
        
        for keyword in TRIGGER_KEYWORDS:
            if keyword in text:
                return True
        
        return False
    
    async def _handle_think(self, update: Update, context: ContextTypes.DEFAULT_TYPE, question: str):
        """处理思考逻辑（带锁和超时保护）~"""
        user_id = update.effective_user.id
        
        # 检查 API Key
        if not DEEPSEEK_API_KEY or DEEPSEEK_API_KEY == "YOUR_DEEPSEEK_API_KEY":
            await update.message.reply_text(
                "呜… 主人还没有给我配置 AI 能力呢(｡•́︿•̀｡)\n"
                "请主人先在 config.py 里设置 DEEPSEEK_API_KEY 吧~"
            )
            return
        
        # 检查是否正在思考中（防止重复触发）
        if self._is_thinking(user_id):
            await update.message.reply_text(
                "🤔 小南正在思考上一个问题呢~\n"
                "等小南想好了再问下一个吧~ 喵！(｡•́︿•̀｡)"
            )
            return
        
        # 锁定用户
        self._lock_user(user_id)
        
        try:
            # 发送"正在输入"状态
            await update.effective_chat.send_action("typing")
            
            # 用超时保护调用 API
            try:
                response = await asyncio.wait_for(
                    self._call_deepseek_api(question),
                    timeout=25.0  # API 超时 25 秒
                )
            except asyncio.TimeoutError:
                logger.warning(f"思考模式超时: 用户{user_id}")
                await update.message.reply_text(
                    "🤔 这个问题有点难，小南要想久一点...\n"
                    "再问一次试试看吧~ 喵！(｡•́︿•̀｡)"
                )
                return
            
            if response:
                await update.message.reply_text(response)
            else:
                await update.message.reply_text(
                    "呜… 小南的脑子卡住了(｡•́︿•̀｡)\n"
                    "请稍后再试试吧~ 喵！"
                )
        
        except Exception as e:
            logger.error(f"思考模式错误 (用户{user_id}): {e}")
            self.dm.add_error({
                "message": f"思考模式错误: {str(e)}",
                "user_id": user_id,
                "time": datetime.now().isoformat()
            })
            await update.message.reply_text(
                "呜… 好像出了点小问题呢(｡•́︿•̀｡)\n"
                "请稍后再试试看吧~ 喵！"
            )
        
        finally:
            # 无论如何都要解锁
            self._unlock_user(user_id)
    
    async def _call_deepseek_api(self, question: str) -> str:
        """调用 DeepSeek API（思考模式，只返回结论）~"""
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }
        
        messages = [
            {"role": "system", "content": THINK_SYSTEM_PROMPT},
            {"role": "user", "content": question}
        ]
        
        payload = {
            "model": DEEPSEEK_MODEL,
            "messages": messages,
            "temperature": 0.5,  # 思考模式用较低温度，更理性
            "max_tokens": 1000   # 限制输出长度，只保留结论
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=25) as resp:
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
            "/think <问题> - 让小南帮你思考问题~\n"
            "💡 也可以直接说「帮我想一下xxx」「思考一下xxx」"
        )
