"""
二次元风格日志模块~ 让小南的日志也可可爱爱！(｡♥‿♥｡)
"""
import logging
import sys
from datetime import datetime

# ANSI 颜色代码
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    ITALIC = "\033[3m"
    
    # 二次元配色
    PINK = "\033[38;5;205m"       # 粉色 - INFO
    LAVENDER = "\033[38;5;183m"   # 薰衣草紫 - DEBUG
    GOLD = "\033[38;5;220m"       # 金色 - WARNING
    CORAL = "\033[38;5;203m"      # 珊瑚红 - ERROR
    HOT_PINK = "\033[38;5;198m"   # 热粉色 - CRITICAL
    MINT = "\033[38;5;121m"       # 薄荷绿 - 成功
    SKY_BLUE = "\033[38;5;117m"   # 天蓝色 - 信息
    WHITE = "\033[38;5;255m"      # 白色
    GRAY = "\033[38;5;245m"       # 灰色 - 时间戳
    
    # 背景色
    BG_PINK = "\033[48;5;205m"
    BG_PURPLE = "\033[48;5;135m"
    BG_RESET = "\033[49m"

# 二次元颜文字
EMOJI_MAP = {
    "INFO": "✨",
    "DEBUG": "🔍",
    "WARNING": "⚠️",
    "ERROR": "💔",
    "CRITICAL": "💀",
    "SUCCESS": "🎉",
    "START": "🚀",
    "STOP": "🛑",
    "LOAD": "📦",
    "HEART": "💖",
}

# 模块名映射（让日志更可爱）
MODULE_NAMES = {
    "__main__": "小南",
    "modules.module_loader": "模块加载器",
    "modules.data_manager": "数据管家",
    "modules.deepseek_chat": "AI酱",
    "modules.help": "小本本",
    "modules.admin": "管理员",
    "modules.system": "系统酱",
    "modules.fun": "娱乐酱",
    "httpx": "网络酱",
    "telegram.ext.Application": "电报酱",
}


class AnimeFormatter(logging.Formatter):
    """二次元风格日志格式化器~"""
    
    def __init__(self):
        super().__init__()
        self.start_time = datetime.now()
    
    def _get_anime_level(self, levelname: str) -> str:
        """获取二次元风格的等级标签~"""
        level_styles = {
            "INFO": f"{Colors.PINK}{Colors.BOLD}✨ INFO ✨{Colors.RESET}",
            "DEBUG": f"{Colors.LAVENDER}{Colors.ITALIC}🔍 DEBUG 🔍{Colors.RESET}",
            "WARNING": f"{Colors.GOLD}{Colors.BOLD}⚠️ WARNING ⚠️{Colors.RESET}",
            "ERROR": f"{Colors.CORAL}{Colors.BOLD}💔 ERROR 💔{Colors.RESET}",
            "CRITICAL": f"{Colors.HOT_PINK}{Colors.BOLD}💀 CRITICAL 💀{Colors.RESET}",
        }
        return level_styles.get(levelname, levelname)
    
    def _get_cute_module_name(self, name: str) -> str:
        """获取可爱的模块名~"""
        # 精确匹配
        if name in MODULE_NAMES:
            return MODULE_NAMES[name]
        
        # 部分匹配
        for key, value in MODULE_NAMES.items():
            if key in name:
                return value
        
        # 简化模块名
        parts = name.split(".")
        if len(parts) > 1:
            return parts[-1]
        return name
    
    def _get_time_str(self) -> str:
        """获取可爱的时间字符串~"""
        now = datetime.now()
        time_str = now.strftime("%H:%M:%S")
        return f"{Colors.GRAY}{Colors.DIM}🕐 {time_str}{Colors.RESET}"
    
    def _get_uptime(self) -> str:
        """获取运行时间~"""
        elapsed = datetime.now() - self.start_time
        total_seconds = int(elapsed.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        
        if hours > 0:
            return f"⏱ {hours}h{minutes}m{seconds}s"
        elif minutes > 0:
            return f"⏱ {minutes}m{seconds}s"
        else:
            return f"⏱ {seconds}s"
    
    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录~"""
        # 获取原始消息
        message = record.getMessage()
        
        # 获取可爱的模块名
        module_name = self._get_cute_module_name(record.name)
        
        # 获取时间
        time_str = self._get_time_str()
        
        # 获取等级
        level_str = self._get_anime_level(record.levelname)
        
        # 获取运行时间
        uptime = self._get_uptime()
        
        # 特殊消息美化
        if "启动成功" in message:
            message = f"{Colors.MINT}{Colors.BOLD}{message}{Colors.RESET}"
        elif "加载成功" in message:
            message = f"{Colors.MINT}{message}{Colors.RESET}"
        elif "启动" in message and "失败" not in message:
            message = f"{Colors.SKY_BLUE}{message}{Colors.RESET}"
        elif "错误" in message or "失败" in message:
            message = f"{Colors.CORAL}{message}{Colors.RESET}"
        elif "HTTP" in message:
            message = f"{Colors.GRAY}{Colors.DIM}{message}{Colors.RESET}"
        else:
            message = f"{Colors.WHITE}{message}{Colors.RESET}"
        
        # 构建二次元风格日志
        anime_log = (
            f"{Colors.PINK}╭─{Colors.RESET} {time_str} {Colors.PINK}✦{Colors.RESET} {uptime}\n"
            f"{Colors.PINK}├─{Colors.RESET} {level_str} {Colors.PINK}✦{Colors.RESET} {Colors.LAVENDER}@{module_name}{Colors.RESET}\n"
            f"{Colors.PINK}╰─{Colors.RESET} {message}"
        )
        
        return anime_log


class AnimeLogger:
    """二次元风格日志管理器~"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._setup_logging()
    
    def _setup_logging(self):
        """设置二次元风格日志~"""
        # 获取根日志器
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        
        # 清除默认处理器
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # 创建控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(AnimeFormatter())
        root_logger.addHandler(console_handler)
        
        # 设置 httpx 日志级别为 WARNING，减少网络日志
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)
        logging.getLogger("telegram").setLevel(logging.WARNING)


# 便捷函数
def setup_anime_logging():
    """一键设置二次元风格日志~"""
    AnimeLogger()


def print_banner():
    """打印启动横幅~"""
    banner = f"""
{Colors.HOT_PINK}{Colors.BOLD}
    ╔══════════════════════════════════════╗
    ║                                      ║
    ║     🐱 小南专属TGbot ✨              ║
    ║     ✿ 一只可可爱爱的机器人 ✿        ║
    ║                                      ║
    ╚══════════════════════════════════════╝
{Colors.RESET}
{Colors.LAVENDER}{Colors.ITALIC}              ~ 喵呜！(｡♥‿♥｡) ~{Colors.RESET}
    """
    print(banner)


def print_module_load(module_name: str, success: bool = True):
    """打印模块加载信息~"""
    if success:
        print(f"  {Colors.MINT}✦ {module_name} 加载成功~ ✨{Colors.RESET}")
    else:
        print(f"  {Colors.CORAL}✧ {module_name} 加载失败… 💔{Colors.RESET}")


def print_separator(char: str = "─", length: int = 50):
    """打印分隔线~"""
    print(f"{Colors.PINK}{char * length}{Colors.RESET}")
