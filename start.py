#!/usr/bin/env python3
"""
🐱 小南专属TGbot - 跨平台启动器
自动检测操作系统，调用合适的部署方式~
支持 Windows / Linux / macOS / Docker
"""
import os
import sys
import platform
import subprocess
import shutil


# 颜色代码（兼容 Windows）
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    PINK = "\033[95m"
    CYAN = "\033[96m"


def print_color(text: str, color: str = ""):
    """打印彩色文字（自动检测终端支持）"""
    if platform.system() == "Windows":
        # Windows 10+ 支持 ANSI
        os.system("")  # 启用 ANSI 转义
    print(f"{color}{text}{Colors.RESET}")


def get_project_root() -> str:
    """获取项目根目录"""
    return os.path.dirname(os.path.abspath(__file__))


def detect_system() -> dict:
    """检测系统环境信息"""
    system = platform.system()
    machine = platform.machine()
    python_version = sys.version
    
    info = {
        "system": system,
        "machine": machine,
        "python_version": python_version,
        "is_windows": system == "Windows",
        "is_linux": system == "Linux",
        "is_macos": system == "Darwin",
        "has_docker": shutil.which("docker") is not None,
        "has_docker_compose": shutil.which("docker-compose") is not None or shutil.which("docker") is not None,
        "has_python": True,
        "has_git": shutil.which("git") is not None,
    }
    
    # 检查 Docker Compose（新版 Docker 自带）
    if info["has_docker"]:
        try:
            result = subprocess.run(
                ["docker", "compose", "version"],
                capture_output=True, text=True, timeout=5
            )
            info["has_docker_compose"] = result.returncode == 0
        except:
            info["has_docker_compose"] = False
    
    return info


def print_banner():
    """打印启动横幅"""
    banner = f"""
{Colors.PINK}{Colors.BOLD}
    ╔══════════════════════════════════════╗
    ║                                      ║
    ║     🐱 小南专属TGbot ✨              ║
    ║     ✿ 一只可可爱爱的机器人 ✿        ║
    ║                                      ║
    ╚══════════════════════════════════════╝
{Colors.RESET}
{Colors.CYAN}              ~ 跨平台启动器 v1.0 ~{Colors.RESET}
    """
    print(banner)


def print_system_info(info: dict):
    """打印系统信息"""
    print(f"{Colors.BLUE}🔍 系统检测结果：{Colors.RESET}")
    print(f"  • 操作系统：{Colors.CYAN}{info['system']} ({info['machine']}){Colors.RESET}")
    print(f"  • Python版本：{Colors.CYAN}{info['python_version'].split()[0]}{Colors.RESET}")
    docker_status = f"{Colors.GREEN}✓{Colors.RESET} 已安装" if info["has_docker"] else f"{Colors.YELLOW}✗{Colors.RESET} 未安装"
    git_status = f"{Colors.GREEN}✓{Colors.RESET} 已安装" if info["has_git"] else f"{Colors.YELLOW}✗{Colors.RESET} 未安装"
    print(f"  • Docker：{docker_status}")
    print(f"  • Git：{git_status}")
    print()


def check_src_files() -> bool:
    """检查项目源文件是否完整"""
    root = get_project_root()
    src_dir = os.path.join(root, "src")
    
    required_files = [
        "main.py",
        "config.py",
        "requirements.txt",
        os.path.join("modules", "__init__.py"),
        os.path.join("modules", "base_module.py"),
        os.path.join("modules", "module_loader.py"),
        os.path.join("modules", "data_manager.py"),
        os.path.join("modules", "deepseek_chat.py"),
        os.path.join("modules", "admin.py"),
        os.path.join("modules", "help.py"),
        os.path.join("modules", "system.py"),
        os.path.join("modules", "fun.py"),
        os.path.join("modules", "anime_logger.py"),
    ]
    
    missing = []
    for file in required_files:
        file_path = os.path.join(src_dir, file)
        if not os.path.exists(file_path):
            missing.append(file)
    
    if missing:
        print(f"{Colors.RED}❌ 缺少以下源文件：{Colors.RESET}")
        for f in missing:
            print(f"  • {f}")
        return False
    
    return True


def get_src_dir() -> str:
    """获取源文件目录"""
    return os.path.join(get_project_root(), "src")


def check_config() -> bool:
    """检查配置文件是否已配置"""
    root = get_project_root()
    
    # 优先检查 src/config.py，再检查根目录 config.py
    config_paths = [
        os.path.join(root, "src", "config.py"),
        os.path.join(root, "config.py"),
    ]
    
    config_file = None
    for path in config_paths:
        if os.path.exists(path):
            config_file = path
            break
    
    if not config_file:
        print(f"{Colors.RED}❌ 找不到 config.py 配置文件！{Colors.RESET}")
        return False
    
    with open(config_file, "r", encoding="utf-8") as f:
        content = f.read()
    
    if "YOUR_TELEGRAM_BOT_TOKEN" in content:
        print(f"{Colors.YELLOW}⚠️  config.py 还是默认配置哦~{Colors.RESET}")
        print(f"{Colors.YELLOW}   请先编辑 {config_file} 填入你的 Token 和 API Key~{Colors.RESET}")
        print()
        print(f"{Colors.CYAN}💡 也可以运行配置向导来帮你配置~{Colors.RESET}")
        return False
    
    return True


def run_config_wizard():
    """运行配置向导"""
    root = get_project_root()
    
    print(f"\n{Colors.PINK}📝 配置向导启动~{Colors.RESET}")
    print(f"{Colors.CYAN}接下来需要配置一些信息哦！{Colors.RESET}\n")
    
    # 检测 src 目录
    src_dir = os.path.join(root, "src")
    if os.path.exists(os.path.join(src_dir, "main.py")):
        config_path = os.path.join(src_dir, "config.py")
    else:
        config_path = os.path.join(root, "config.py")
    
    print(f"{Colors.BLUE}🤖 Telegram Bot Token{Colors.RESET}")
    print("在 Telegram 中搜索 @BotFather，发送 /newbot 创建机器人~")
    token = input("请输入你的 Telegram Bot Token: ").strip()
    
    print(f"\n{Colors.BLUE}🔮 DeepSeek API Key（可选）{Colors.RESET}")
    api_key = input("请输入 DeepSeek API Key（直接回车跳过）: ").strip()
    
    print(f"\n{Colors.BLUE}👤 主人信息{Colors.RESET}")
    owner_name = input('请输入你的名字（直接回车使用"主人"）: ').strip() or "主人"
    owner_id = input("请输入你的 Telegram ID: ").strip()
    
    print(f"\n{Colors.BLUE}🤖 机器人名称{Colors.RESET}")
    bot_name = input('请输入机器人名称（直接回车使用"小南专属TGbot"）: ').strip() or "小南专属TGbot"
    
    # 生成配置
    config_content = f'''"""
配置文件~ 请在这里填写你的小秘密哦(｡♥‿♥｡)
"""
import os

# Telegram Bot 配置
TELEGRAM_BOT_TOKEN = "{token or 'YOUR_TELEGRAM_BOT_TOKEN'}"  # 从 @BotFather 那里拿到的小钥匙🔑

# DeepSeek API 配置
DEEPSEEK_API_KEY = "{api_key or 'YOUR_DEEPSEEK_API_KEY'}"      # 从 DeepSeek 平台获取的魔法钥匙✨
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"

# 机器人配置
BOT_NAME = "{bot_name}"
BOT_OWNER_NAME = "{owner_name}"  # 主人的名字（会显示在欢迎消息等地方哦~）
BOT_OWNER_ID = {owner_id or 'None'}  # 主人的 Telegram ID（填上才能用主人专属命令哦~）
MAX_HISTORY_LENGTH = 10  # 每个小可爱最多保留的对话历史条数~

# 数据文件路径
DATA_DIR = "data"
WHITELIST_FILE = "data/whitelist.json"
ADMIN_FILE = "data/admins.json"
USER_DATA_FILE = "data/user_data.json"
ERROR_LOG_FILE = "data/errors.json"
BACKUP_DIR = "data/backups"

# 模块配置
ENABLED_MODULES = [
    "deepseek_chat",  # DeepSeek AI 对话模块
    "help",           # 帮助模块
    "admin",          # 管理模块
    "system",         # 系统模块
    "fun",            # 娱乐模块
    # 在这里添加更多模块吧(๑•̀ㅂ•́)و✧
]
'''
    
    with open(config_path, "w", encoding="utf-8") as f:
        f.write(config_content)
    
    print(f"\n{Colors.GREEN}✅ 配置文件已生成！{Colors.RESET}")
    print(f"   保存位置：{config_path}")
    
    return True


def install_dependencies():
    """安装 Python 依赖"""
    root = get_project_root()
    
    # 检测 src 目录
    src_dir = os.path.join(root, "src")
    if os.path.exists(os.path.join(src_dir, "requirements.txt")):
        req_path = os.path.join(src_dir, "requirements.txt")
    else:
        req_path = os.path.join(root, "requirements.txt")
    
    print(f"\n{Colors.BLUE}📦 正在安装依赖包...{Colors.RESET}")
    
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", req_path],
            check=True
        )
        print(f"{Colors.GREEN}✅ 依赖安装成功！{Colors.RESET}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"{Colors.RED}❌ 依赖安装失败：{e}{Colors.RESET}")
        return False


def kill_old_bot():
    """一次性杀掉所有旧机器人进程，防止 Conflict 冲突~"""
    system = platform.system()
    
    if system == "Windows":
        # Windows：用 wmic 查所有 python 进程，逐个杀掉
        try:
            # 方法1：taskkill 杀所有 python.exe
            subprocess.run(
                ["taskkill", "/F", "/IM", "python.exe"],
                capture_output=True, text=True, timeout=5
            )
        except:
            pass
        try:
            # 方法2：taskkill 杀所有 pythonw.exe（后台进程）
            subprocess.run(
                ["taskkill", "/F", "/IM", "pythonw.exe"],
                capture_output=True, text=True, timeout=5
            )
        except:
            pass
        try:
            # 方法3：用 wmic 查所有含 main.py 的进程
            result = subprocess.run(
                ["wmic", "process", "where", 'name="python.exe"', "get", "processid"],
                capture_output=True, text=True, timeout=5
            )
            for line in result.stdout.split("\n"):
                pid = line.strip()
                if pid.isdigit():
                    subprocess.run(
                        ["taskkill", "/F", "/PID", pid],
                        capture_output=True, text=True, timeout=3
                    )
        except:
            pass
    else:
        # Linux/macOS：用 pkill 杀所有 python 进程
        try:
            subprocess.run(
                ["pkill", "-9", "-f", "python"],
                capture_output=True, text=True, timeout=5
            )
        except:
            pass


def run_bot():
    """启动机器人"""
    root = get_project_root()
    
    # 检测 src 目录
    src_dir = os.path.join(root, "src")
    if os.path.exists(os.path.join(src_dir, "main.py")):
        main_path = os.path.join(src_dir, "main.py")
        os.chdir(src_dir)
    else:
        main_path = os.path.join(root, "main.py")
    
    # 启动前先杀掉旧进程，防止 Conflict 冲突
    print(f"\n{Colors.YELLOW}🧹 正在清理旧进程...{Colors.RESET}")
    kill_old_bot()
    
    print(f"\n{Colors.PINK}🚀 正在启动机器人...{Colors.RESET}\n")
    
    try:
        subprocess.run([sys.executable, main_path])
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}👋 机器人已停止~{Colors.RESET}")
    except Exception as e:
        print(f"{Colors.RED}❌ 启动失败：{e}{Colors.RESET}")
        return False
    
    return True


def run_docker():
    """使用 Docker 启动"""
    root = get_project_root()
    deploy_dir = os.path.join(root, "src", "deploy")
    
    print(f"\n{Colors.BLUE}🐳 使用 Docker 启动...{Colors.RESET}")
    
    try:
        # 先检查 docker-compose.yml
        compose_file = os.path.join(deploy_dir, "docker-compose.yml")
        if not os.path.exists(compose_file):
            print(f"{Colors.RED}❌ 找不到 docker-compose.yml{Colors.RESET}")
            return False
        
        # 切换到 deploy 目录
        os.chdir(deploy_dir)
        
        # 启动 Docker Compose
        subprocess.run(["docker", "compose", "up", "-d"], check=True)
        
        print(f"{Colors.GREEN}✅ Docker 容器已启动！{Colors.RESET}")
        print(f"{Colors.CYAN}   查看日志：docker compose logs -f{Colors.RESET}")
        print(f"{Colors.CYAN}   停止：docker compose down{Colors.RESET}")
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"{Colors.RED}❌ Docker 启动失败：{e}{Colors.RESET}")
        return False


def main():
    """主函数~ 自动检测并选择合适的部署方式！"""
    # 设置控制台编码（Windows）
    if platform.system() == "Windows":
        os.system("chcp 65001 >nul 2>&1")
    
    print_banner()
    
    # 检测系统
    system_info = detect_system()
    print_system_info(system_info)
    
    # 检查源文件
    print(f"{Colors.BLUE}🔍 正在检查项目文件...{Colors.RESET}")
    if not check_src_files():
        print(f"\n{Colors.RED}❌ 项目文件不完整！{Colors.RESET}")
        print(f"{Colors.YELLOW}请确保 src 目录包含所有源文件~{Colors.RESET}")
        sys.exit(1)
    print(f"{Colors.GREEN}✅ 项目文件完整！{Colors.RESET}\n")
    
    # 检查配置
    config_ok = check_config()
    
    # 如果配置不完整，询问是否运行配置向导
    if not config_ok:
        print()
        choice = input(f"{Colors.YELLOW}是否运行配置向导？(y/n，默认y): {Colors.RESET}").strip().lower()
        if choice != "n":
            run_config_wizard()
            config_ok = True
    
    # 选择部署方式
    print(f"\n{Colors.PINK}📋 选择部署方式：{Colors.RESET}")
    print(f"  {Colors.CYAN}1.{Colors.RESET} 直接运行（Python）")
    
    if system_info["has_docker_compose"]:
        print(f"  {Colors.CYAN}2.{Colors.RESET} Docker 容器运行")
    
    print(f"  {Colors.CYAN}3.{Colors.RESET} 退出")
    
    choice = input(f"\n{Colors.YELLOW}请选择 (1-3): {Colors.RESET}").strip()
    
    if choice == "2" and system_info["has_docker_compose"]:
        run_docker()
    elif choice == "3":
        print(f"\n{Colors.YELLOW}👋 下次再见~ 喵！{Colors.RESET}")
        sys.exit(0)
    else:
        # 安装依赖
        install_dependencies()
        
        # 创建数据目录
        root = get_project_root()
        src_dir = os.path.join(root, "src")
        if os.path.exists(src_dir):
            data_dir = os.path.join(src_dir, "data")
        else:
            data_dir = os.path.join(root, "data")
        
        os.makedirs(os.path.join(data_dir, "backups"), exist_ok=True)
        
        # 启动机器人
        run_bot()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}👋 下次再见~ 喵！(｡♥‿♥｡){Colors.RESET}")
    except Exception as e:
        print(f"\n{Colors.RED}💔 出错了：{e}{Colors.RESET}")
        sys.exit(1)
