"""
模块加载器~ 负责自动扫描并加载所有小模块！(๑•̀ㅂ•́)و✧
现在不需要手动配置啦，把 .py 文件丢进 modules/ 目录就会自动加载~
"""
import importlib
import logging
import os
from typing import Dict, List, Optional
from telegram.ext import Application

from .base_module import BaseModule

logger = logging.getLogger(__name__)

# 不自动加载的基础文件
EXCLUDED_MODULES = {
    "__init__",
    "base_module",
    "module_loader",
    "anime_logger",
    "data_manager",
    "helpers",
    "net_helpers",
    "third_party_parser",
    # modules/start.py 曾是一份根目录启动器的陈旧副本，不是功能模块：
    # 它没有模块类、导入即抛 ImportError，所以名字留在这里防止再被当成模块
    "start",
}

# 不可缺失模块（加载失败会阻止机器人启动）
# 这些是用户端必须有的核心功能模块
ESSENTIAL_MODULES = set()


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
        "sticker": "StickerModule",
        "girlfriend": "GirlfriendModule",
    }
    
    if name in special_cases:
        return special_cases[name]
    
    # 默认转换：下划线分割，每个单词首字母大写
    return "".join(word.capitalize() for word in name.split("_"))


def _scan_modules() -> List[str]:
    """
    自动扫描 modules/ 目录下的所有模块文件~
    
    Returns:
        List[str]: 模块名称列表（不含 .py 后缀）
    """
    modules_dir = os.path.dirname(os.path.abspath(__file__))
    module_names = []
    
    for filename in os.listdir(modules_dir):
        if filename.endswith(".py"):
            name = filename[:-3]  # 去掉 .py
            if name not in EXCLUDED_MODULES:
                module_names.append(name)
    
    # 排序，让加载顺序稳定
    module_names.sort()
    return module_names


class ModuleLoader:
    """模块加载器~ 负责自动扫描、加载和管理所有小模块！"""
    
    def __init__(self):
        self.modules: Dict[str, BaseModule] = {}
    
    def load_modules(self, application: Application) -> List[str]:
        """
        自动扫描并加载所有小模块~
        把 .py 文件丢进 modules/ 目录就会自动加载哦！
        
        Args:
            application: telegram.ext.Application 实例
            
        Returns:
            List[str]: 成功加载的模块名称列表
        """
        loaded_modules = []
        failed_modules = []
        module_names = _scan_modules()
        
        logger.info(f"🔍 在 modules/ 目录下发现了 {len(module_names)} 个模块文件~")
        
        for module_name in module_names:
            try:
                # 动态导入模块
                module_path = f"modules.{module_name}"
                module = importlib.import_module(module_path)
                
                # 查找模块类
                class_name = _snake_to_pascal(module_name)
                
                if not hasattr(module, class_name):
                    error_msg = f"没找到类 '{class_name}'"
                    if module_name in ESSENTIAL_MODULES:
                        logger.error(f"❌ 不可缺失模块 '{module_name}' 加载失败，机器人无法启动！")
                        raise RuntimeError(f"不可缺失模块 '{module_name}' 加载失败：{error_msg}")
                    logger.warning(f"⏭️ 跳过 '{module_name}'：{error_msg}")
                    failed_modules.append((module_name, error_msg))
                    continue
                
                module_class = getattr(module, class_name)
                module_instance = module_class(bot_app=self)
                
                # 注册处理器
                module_instance.register_handlers(application)
                
                self.modules[module_name] = module_instance
                loaded_modules.append(module_name)
                logger.info(f"✅ 模块 '{module_name}' 加载成功~ ✨")
                
            except Exception as e:
                # exc_info=True：模块加载失败时，只打一行 str(e) 根本看不出是哪一行炸的。
                # 之前排查过"模块整块静默失效"，就是因为这里没留堆栈。
                logger.error(f"❌ 加载模块 '{module_name}' 失败啦: {e}", exc_info=True)
                failed_modules.append((module_name, str(e)))
                if module_name in ESSENTIAL_MODULES:
                    raise RuntimeError(f"不可缺失模块 '{module_name}' 加载失败，机器人无法启动！{e}")
        
        # 汇总失败项，避免"看起来启动成功、其实功能整块缺失"
        if failed_modules:
            logger.warning("=" * 55)
            logger.warning(f"⚠️ 有 {len(failed_modules)} 个模块未能加载，相关命令将不可用：")
            for name, reason in failed_modules:
                logger.warning(f"   ├─ {name}: {reason}")
            logger.warning("   └─ 机器人会继续运行，但以上模块的功能是缺失的~")
            logger.warning("=" * 55)
        
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
