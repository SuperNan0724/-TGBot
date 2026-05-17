"""
模块加载器~ 负责把各种有趣的小模块都加载进来！(๑•̀ㅂ•́)و✧
"""
import importlib
import logging
from typing import Dict, List, Optional
from telegram.ext import Application

from config import ENABLED_MODULES
from .base_module import BaseModule

logger = logging.getLogger(__name__)


def _snake_to_pascal(name: str) -> str:
    """
    把 snake_case 转成 PascalCase~
    特殊处理 DeepSeek 这种大小写~
    
    Args:
        name: 模块名称（snake_case）
        
    Returns:
        str: 类名（PascalCase）
    """
    # 特殊映射表
    special_cases = {
        "deepseek_chat": "DeepSeekChat",
    }
    
    if name in special_cases:
        return special_cases[name]
    
    # 默认转换：下划线分割，每个单词首字母大写
    return "".join(word.capitalize() for word in name.split("_"))


class ModuleLoader:
    """模块加载器~ 负责加载和管理所有小模块！"""
    
    def __init__(self):
        self.modules: Dict[str, BaseModule] = {}
    
    def load_modules(self, application: Application) -> List[str]:
        """
        加载所有启用的小模块~
        
        Args:
            application: telegram.ext.Application 实例
            
        Returns:
            List[str]: 成功加载的模块名称列表
        """
        loaded_modules = []
        
        for module_name in ENABLED_MODULES:
            try:
                # 动态导入模块
                module_path = f"modules.{module_name}"
                module = importlib.import_module(module_path)
                
                # 查找模块类
                class_name = _snake_to_pascal(module_name)
                
                if hasattr(module, class_name):
                    module_class = getattr(module, class_name)
                    module_instance = module_class(bot_app=self)
                    
                    # 注册处理器
                    module_instance.register_handlers(application)
                    
                    self.modules[module_name] = module_instance
                    loaded_modules.append(module_name)
                    logger.info(f"模块 '{module_name}' 加载成功~ ✨")
                else:
                    logger.warning(f"呜… 模块 '{module_name}' 中没找到类 '{class_name}' 呢(｡•́︿•̀｡)")
                    
            except Exception as e:
                logger.error(f"加载模块 '{module_name}' 失败啦: {e}")
        
        return loaded_modules
    
    def get_module(self, module_name: str) -> Optional[BaseModule]:
        """
        获取指定模块实例~
        
        Args:
            module_name: 模块名称
            
        Returns:
            Optional[BaseModule]: 模块实例，不存在就返回 None 哦
        """
        return self.modules.get(module_name)
    
    def get_all_modules(self) -> Dict[str, BaseModule]:
        """
        获取所有已加载的模块~
        
        Returns:
            Dict[str, BaseModule]: 模块名称到模块实例的映射
        """
        return self.modules
    
    def get_help_text(self) -> str:
        """
        获取所有模块的帮助文本~
        
        Returns:
            str: 帮助文本
        """
        help_lines = ["🤖 小南专属TGbot 可用命令~\n"]
        for module_name, module_instance in self.modules.items():
            help_lines.append(f"  {module_instance.get_help_text()}")
        return "\n".join(help_lines)
