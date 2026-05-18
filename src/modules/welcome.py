"""
🎉 进群欢迎模块~ 欢迎新来的小可爱！(｡♥‿♥｡)

功能：
  ✅ 检测新人进群，自动发送欢迎语
  ✅ 40+ 条动态欢迎语，随机选择，不重复
  ✅ 欢迎语发送后 2 分钟自动删除
  ✅ 支持群聊白名单检测
  ✅ 可自定义开启/关闭
"""
import logging
import random
import asyncio
from datetime import datetime

from telegram import Update, ChatMemberUpdated
from telegram.ext import ChatMemberHandler, ContextTypes

from .base_module import BaseModule

logger = logging.getLogger(__name__)

# ===== 欢迎语大全（40+ 条，每条都可爱！）=====
WELCOME_MESSAGES = [
    # 🎀 可爱风格
    "欢迎 {name} 加入~ 快来和小南一起玩吧！(｡♥‿♥｡)",
    "哇！是新的小可爱 {name} 来了！快请坐快请坐~ 🎉",
    "叮咚~ 您的可爱 {name} 已上线！请查收~ 💝",
    "{name} 来啦来啦！小南等你好久了呢~ 喵呜！🐱",
    "欢迎欢迎~ {name} 的到来让这里又热闹了一分！✨",
    "新朋友 {name} 加入啦！撒花撒花~ 🌸🌸🌸",
    "咦？小南闻到了新朋友的味道~ 原来是 {name} 来了！(◕‿◕✿)",
    "欢迎 {name} 加入我们的大家庭~ 以后一起玩呀！🎊",
    "咚咚咚~ 是谁来了呀？原来是可爱的 {name} 呀！🚪💕",
    "新的小伙伴 {name} 出现啦！捕捉成功~ 🎯",

    # 😊 温暖风格
    "欢迎 {name} 加入~ 希望你能在这里玩得开心哦！☀️",
    "每一个新朋友都是礼物~ 欢迎 {name} 的到来！🎁",
    "世界那么大，{name} 却来到了这里~ 一定是特别的缘分！💫",
    "欢迎 {name}~ 这里是一个温暖的小窝，请随意坐~ 🏠",
    "新的旅程开始了~ 欢迎 {name} 和我们一起冒险！🗺️",
    "有朋自远方来~ 欢迎 {name} 加入我们！🎵",
    "欢迎 {name}~ 希望这里能成为你快乐的小天地！🌈",
    "每一个相遇都是奇迹~ 欢迎 {name} 来到我们的世界！🌟",
    "欢迎 {name}~ 以后的日子，请多多指教哦！🙏",
    "因为 {name} 的到来，今天又变成了特别的一天~ 🎀",

    # 😂 搞笑风格
    "警告警告！{name} 正在闯入群聊！请做好准备！🚨",
    "系统提示：{name} 已加入群聊，请开始你的表演！🎭",
    "欢迎 {name}~ 请先交出入群费：一个拥抱！🤗",
    "新的小伙伴 {name} 加入了！大家快藏好小鱼干！🐟",
    "欢迎 {name}~ 本群规矩只有一条：开心最重要！😆",
    "叮！{name} 已加入群聊，群聊活跃度 +100！📈",
    "欢迎 {name}~ 请先做个自我介绍... 算了，先玩再说！🎮",
    "新的受害者 {name} 出现了！咳咳，我是说新朋友~ 😈",
    "欢迎 {name}~ 本群提供免费拥抱和摸摸头服务！🫂",
    "{name} 加入群聊，并发起了一个挑战：谁能比我更可爱！🏆",

    # 💕 二次元风格
    "欢迎 {name}~ 你已经被选为这个群聊的勇者！⚔️",
    "新的角色 {name} 加入了队伍！冒险继续~ 🎮",
    "欢迎 {name}~ 在这个次元里，我们就是一家人啦！🌌",
    "检测到新的羁绊：{name} 已连接！❤️",
    "欢迎 {name}~ 你的冒险日志翻开了新的一页！📖",
    "新的伙伴 {name} 加入了公会！一起打怪升级吧！🎯",
    "欢迎 {name}~ 你的到来让这个世界的色彩又丰富了一分！🎨",
    "系统公告：{name} 已成功传送至本群！🪄",
    "欢迎 {name}~ 在这个故事里，你也是主角哦！⭐",
    "新的魔法使 {name} 加入了！快来一起施展快乐的魔法！🔮",

    # 🐱 猫咪风格
    "欢迎 {name}~ 喵喵喵！小南好开心！🐱💕",
    "新的铲屎官 {name} 出现了！快来摸摸小南~ 🐾",
    "欢迎 {name}~ 小南已经准备好被摸头了！喵~ 🐱",
    "喵~ 是 {name} 来了！小南的尾巴已经翘起来了！🎀",
    "欢迎 {name}~ 小南会好好招待你的，喵嘿嘿~ 😸",
    "新的小伙伴 {name} 来了！小南已经准备好蹭蹭了！🫂",
    "欢迎 {name}~ 小南的猫罐头分你一半！🍯",
    "喵呜！{name} 来啦！小南开心得在地上打滚~ 🌀",
    "欢迎 {name}~ 小南已经记住你的味道了哦！👃💕",
    "喵~ 是 {name} 呀！小南最喜欢新朋友了！(｡♥‿♥｡)",

    # 🌸 文艺风格
    "欢迎 {name}~ 愿你的每一天都如花般绽放！🌸",
    "新的故事开始了~ 欢迎 {name} 成为其中的一页！📚",
    "欢迎 {name}~ 愿你在这里找到属于你的小确幸！🍀",
    "每一颗星星都是特别的~ 欢迎 {name} 这颗新星！⭐",
    "欢迎 {name}~ 愿你的笑容如阳光般温暖这里！☀️",
    "新的旋律加入了~ 欢迎 {name} 和我们一起谱写乐章！🎵",
    "欢迎 {name}~ 愿你的每一天都充满惊喜和美好！🎪",
    "每一朵花都有盛开的理由~ 欢迎 {name} 绽放于此！🌺",
    "欢迎 {name}~ 愿这里成为你心灵的避风港！🏖️",
    "新的色彩加入了画布~ 欢迎 {name} 描绘你的故事！🎨",
]


class Welcome(BaseModule):
    """进群欢迎模块~ 欢迎新来的小可爱！"""
    
    name = "welcome"
    description = "进群欢迎~ 欢迎新来的小可爱！"
    
    def __init__(self, bot_app=None):
        super().__init__(bot_app)
        # 记录已发送过的欢迎语索引，避免重复
        self._used_indices = {}
        # 记录已发送的欢迎消息，用于自动删除
        self._welcome_messages = {}
    
    def register_handlers(self, application):
        """注册处理器~"""
        application.add_handler(ChatMemberHandler(
            self.handle_chat_member,
            chat_member_types=ChatMemberHandler.CHAT_MEMBER
        ))
    
    async def handle_chat_member(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理群成员状态变化~"""
        chat_member = update.chat_member
        chat_id = update.effective_chat.id
        
        # 只处理群组/超级群组
        if update.effective_chat.type not in ("group", "supergroup"):
            return
        
        # 检查群组是否在白名单
        from .data_manager import DataManager
        dm = DataManager()
        if not dm.is_group_whitelisted(chat_id):
            return
        
        # 检测新人加入
        old_status = chat_member.old_chat_member.status
        new_status = chat_member.new_chat_member.status
        
        # 从非成员变为成员（加入群聊）
        if old_status in ("left", "kicked", "restricted") and new_status in ("member", "administrator"):
            new_user = chat_member.new_chat_member.user
            
            # 忽略机器人自己
            if new_user.is_bot:
                return
            
            # 获取用户信息
            name = new_user.full_name or new_user.first_name or "小可爱"
            user_id = new_user.id
            
            # 生成欢迎语
            welcome_text = self._get_welcome_message(chat_id, name)
            
            # 发送欢迎消息
            msg = await update.effective_chat.send_message(welcome_text)
            
            # 记录消息，2分钟后自动删除
            self._welcome_messages[msg.message_id] = {
                "chat_id": chat_id,
                "user_id": user_id,
                "time": datetime.now()
            }
            
            # 2分钟后删除
            asyncio.create_task(self._auto_delete_message(
                context.bot,
                chat_id,
                msg.message_id,
                delay=120  # 2分钟
            ))
            
            logger.info(f"🎉 欢迎 {name}({user_id}) 加入群聊 {chat_id}")
    
    def _get_welcome_message(self, chat_id: int, name: str) -> str:
        """获取一条不重复的欢迎语~"""
        # 获取该群已使用的索引
        if chat_id not in self._used_indices:
            self._used_indices[chat_id] = set()
        
        used = self._used_indices[chat_id]
        
        # 如果所有欢迎语都用过了，重置
        if len(used) >= len(WELCOME_MESSAGES):
            used.clear()
            logger.info(f"🔄 群 {chat_id} 的欢迎语已全部用完，重新开始~")
        
        # 从未使用的欢迎语中随机选一条
        available = [i for i in range(len(WELCOME_MESSAGES)) if i not in used]
        if not available:
            available = list(range(len(WELCOME_MESSAGES)))
        
        idx = random.choice(available)
        used.add(idx)
        
        # 格式化欢迎语
        template = WELCOME_MESSAGES[idx]
        return template.format(name=name)
    
    async def _auto_delete_message(self, bot, chat_id: int, message_id: int, delay: int = 120):
        """自动删除消息~"""
        try:
            await asyncio.sleep(delay)
            await bot.delete_message(chat_id=chat_id, message_id=message_id)
            logger.info(f"🗑️ 已自动删除欢迎消息 {message_id}")
        except Exception as e:
            # 消息可能已经被手动删除，忽略错误
            logger.debug(f"自动删除欢迎消息失败（可能已被手动删除）: {e}")
        finally:
            # 清理记录
            self._welcome_messages.pop(message_id, None)
    
    def get_help_text(self) -> str:
        """返回帮助文本~"""
        return "🎉 进群欢迎 - 欢迎新来的小可爱！"
