"""
模块基类~ 所有小模块都要继承这个类哦！(◕‿◕✿)
"""
from telegram import Update
from telegram.ext import ContextTypes


class BaseModule:
    """模块基类~ 定义了模块的基本接口喵！"""
    
    # 模块名称
    name = "base"
    
    # 模块描述
    description = "基础模块~"
    
    def __init__(self, bot_app=None):
        self.bot_app = bot_app
    
    def register_handlers(self, application):
        """
        注册模块的处理器~
        子类要重写这个方法，来注册自己的命令和消息处理器哦！
        
        Args:
            application: telegram.ext.Application 实例
        """
        pass
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        处理消息的通用方法（可选重写~）
        
        Args:
            update: Telegram Update 对象
            context: Context 对象
        """
        pass
    
    def get_help_text(self) -> str:
        """
        返回模块的帮助文本~
        
        Returns:
            str: 帮助文本
        """
        return f"/{self.name} - {self.description}"
