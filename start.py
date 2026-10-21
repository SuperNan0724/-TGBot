#!/usr/bin/env python3
"""
🐱 小南专属TGbot - Windows 启动器
专为 Windows 平台设计~ 自动检测环境并启动机器人！
"""
import os
import re
import sys
import subprocess
import shutil


# 颜色代码
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
    """打印彩色文字"""
    os.system("")  # 启用 ANSI 转义
    print(f"{color}{text}{Colors.RESET}")


def get_project_root() -> str:
    """获取项目根目录"""
    return os.path.dirname(os.path.abspath(__file__))


def detect_system() -> dict:
    """检测系统环境信息"""
    info = {
        "has_docker": shutil.which("docker") is not None,
        "has_docker_compose": shutil.which("docker") is not None,
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
{Colors.CYAN}              ~ Windows 启动器 v1.0 ~{Colors.RESET}
    """
    print(banner)


def print_system_info(info: dict):
    """打印系统信息"""
    print(f"{Colors.BLUE}🔍 环境检测结果：{Colors.RESET}")
    docker_status = f"{Colors.GREEN}✓{Colors.RESET} 已安装" if info["has_docker"] else f"{Colors.YELLOW}✗{Colors.RESET} 未安装"
    git_status = f"{Colors.GREEN}✓{Colors.RESET} 已安装" if info["has_git"] else f"{Colors.YELLOW}✗{Colors.RESET} 未安装"
    print(f"  • Docker：{docker_status}")
    print(f"  • Git：{git_status}")
    print()


def check_src_files() -> bool:
    """检查项目源文件是否完整"""
    root = get_project_root()
    src_dir = os.path.join(root, "src")
    
    # 注意：这里**不能**要求 config.py 存在。
    # 全新克隆的仓库里只有 config.example.py，config.py 是首次运行时
    # 由配置向导（或 start.bat）生成的。以前把 config.py 列进必检清单，
    # 结果第一次运行就报「缺少源文件 config.py」并 exit(1)，永远走不到
    # 生成配置那一步——等于新手拿到项目后根本起不来。
    required_files = [
        "main.py",
        "config.example.py",
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
    
    # 读文件：utf-8-sig 顺便吃掉 BOM（记事本选"UTF-8 带 BOM"很常见，
    # 带 BOM 的源码 Python 能跑，但拿字符串去 compile 会报"非法字符"），
    # 再退回 GBK（另存为 ANSI 的情况）
    try:
        with open(config_file, "r", encoding="utf-8-sig") as f:
            content = f.read()
    except UnicodeDecodeError:
        try:
            with open(config_file, "r", encoding="gbk") as f:
                content = f.read()
        except (UnicodeDecodeError, OSError) as e:
            print(f"{Colors.RED}❌ 读不了 {config_file}：{e}{Colors.RESET}")
            print(f"{Colors.YELLOW}   建议用记事本/VS Code 以 UTF-8 重新保存一次{Colors.RESET}")
            return False
        # 机器人自己是 Python，只认 UTF-8：GBK 的 config.py 会让它一启动就报
        # "codec can't decode"。与其让用户在编码上耗着，这里直接转码并留备份。
        backup_path = config_file + ".bak"
        try:
            shutil.copy2(config_file, backup_path)
            with open(config_file, "w", encoding="utf-8", newline="\n") as f:
                f.write(content)
        except OSError as e:
            print(f"{Colors.RED}❌ config.py 是 GBK 编码，自动转 UTF-8 失败：{e}{Colors.RESET}")
            print(f"{Colors.YELLOW}   请手动另存为 UTF-8 后再启动{Colors.RESET}")
            return False
        print(f"{Colors.GREEN}✅ config.py 是 GBK 编码，已自动转成 UTF-8{Colors.RESET}")
        print(f"{Colors.CYAN}   原文件备份在：{backup_path}{Colors.RESET}")

    # 语法检查：手写配置错一个引号，机器人的报错会指到 import 行，
    # 看起来像"代码坏了"。这里先编译一遍，把出错行号直接摆出来
    try:
        compile(content, config_file, "exec")
    except SyntaxError as e:
        print(f"{Colors.RED}❌ {config_file} 有语法错误，机器人起不来：{Colors.RESET}")
        print(f"{Colors.YELLOW}   第 {e.lineno} 行：{(e.text or '').strip()}{Colors.RESET}")
        print(f"{Colors.YELLOW}   {e.msg}{Colors.RESET}")
        print(f"{Colors.CYAN}💡 常见原因：引号/括号没配对、中文标点（，：“”）写进了字符串外面{Colors.RESET}")
        return False

    if "YOUR_TELEGRAM_BOT_TOKEN" in content:
        print(f"{Colors.YELLOW}⚠️  config.py 还是默认配置哦~{Colors.RESET}")
        print(f"{Colors.YELLOW}   请先编辑 {config_file} 填入你的 Token 和 API Key~{Colors.RESET}")
        print()
        print(f"{Colors.CYAN}💡 也可以运行配置向导来帮你配置~{Colors.RESET}")
        return False

    return True


def run_config_wizard():
    """
    运行配置向导~

    以 config.example.py 为模板生成 config.py，只替换需要填的几项。
    以前这里是整份硬编码写出去的，模板后来新增的配置项（视觉模型、链接解析、
    ffmpeg 路径、代理……）全都不在里面，于是模块里 `from config import X`
    直接 ImportError——用户看到的只是一个看不懂的报错，根本不知道是配置缺字段。
    """
    root = get_project_root()
    src_dir = os.path.join(root, "src")
    if os.path.exists(os.path.join(src_dir, "main.py")):
        config_path = os.path.join(src_dir, "config.py")
        template_path = os.path.join(src_dir, "config.example.py")
    else:
        config_path = os.path.join(root, "config.py")
        template_path = os.path.join(root, "config.example.py")

    print(f"\n{Colors.PINK}📝 配置向导启动~{Colors.RESET}")
    print(f"{Colors.CYAN}接下来需要配置一些信息哦！{Colors.RESET}\n")

    if not os.path.exists(template_path):
        print(f"{Colors.RED}❌ 找不到配置模板：{template_path}{Colors.RESET}")
        print(f"{Colors.YELLOW}   请确认仓库文件完整（config.example.py 是必需的）{Colors.RESET}")
        return False

    with open(template_path, "r", encoding="utf-8") as f:
        template = f.read()

    print(f"{Colors.BLUE}🤖 Telegram Bot Token{Colors.RESET}")
    print("在 Telegram 中搜索 @BotFather，发送 /newbot 创建机器人~")
    token = input("请输入你的 Telegram Bot Token: ").strip()

    print(f"\n{Colors.BLUE}🔮 DeepSeek API Key（可选）{Colors.RESET}")
    api_key = input("请输入 DeepSeek API Key（直接回车跳过）: ").strip()

    print(f"\n{Colors.BLUE}👤 主人信息{Colors.RESET}")
    owner_name = input('请输入你的名字（直接回车使用"主人"）: ').strip() or "主人"
    owner_id_raw = input("请输入你的 Telegram ID（纯数字，直接回车跳过）: ").strip()

    print(f"\n{Colors.BLUE}🤖 机器人名称{Colors.RESET}")
    bot_name = input('请输入机器人名称（直接回车使用"小南专属TGbot"）: ').strip() or "小南专属TGbot"

    # 主人 ID 必须写成数字字面量。以前是直接把你输入的内容拼进去，
    # 填成 @username 就会生成 `BOT_OWNER_ID = @username` —— 非法 Python，
    # 整个 config.py 都导入不了，而报错信息完全看不出是这一行。
    owner_id_text = "None"
    if owner_id_raw:
        if owner_id_raw.isdigit():
            owner_id_text = owner_id_raw
        else:
            print(f"{Colors.YELLOW}⚠️  主人 ID 不是纯数字，已忽略这一项~{Colors.RESET}")
            print(f"{Colors.YELLOW}   在 Telegram 里搜 @userinfobot 就能拿到数字 ID{Colors.RESET}")

    replacements = [
        (r"^TELEGRAM_BOT_TOKEN\s*=.*$", f"TELEGRAM_BOT_TOKEN = {token or 'YOUR_TELEGRAM_BOT_TOKEN'!r}"),
        (r"^DEEPSEEK_API_KEY\s*=.*$", f"DEEPSEEK_API_KEY = {api_key or 'YOUR_DEEPSEEK_API_KEY'!r}"),
        (r"^BOT_OWNER_ID\s*=.*$", f"BOT_OWNER_ID = {owner_id_text}"),
        (r"^BOT_OWNER_NAME\s*=.*$", f"BOT_OWNER_NAME = {owner_name!r}"),
        (r"^BOT_NAME\s*=.*$", f"BOT_NAME = {bot_name!r}"),
    ]

    for pattern, replacement in replacements:
        # 用 lambda 做替换而不是直接当替换串：替换串里的反斜杠会被当成转义
        # （比如名字里带 \1），用函数就不会有这个问题
        template, count = re.subn(pattern, lambda _m, r=replacement: r,
                                  template, count=1, flags=re.M)
        if count == 0:
            print(f"{Colors.YELLOW}⚠️  模板里没有匹配到 {pattern}，这一项未写入{Colors.RESET}")

    # 落盘前先编译一遍：宁可报错退出，也不要留下一个 import 不进来的 config.py
    try:
        compile(template, config_path, "exec")
    except SyntaxError as e:
        print(f"{Colors.RED}❌ 生成的配置有语法错误，已放弃写入：{e}{Colors.RESET}")
        return False

    if os.path.exists(config_path):
        backup_path = config_path + ".bak"
        try:
            shutil.copy2(config_path, backup_path)
            print(f"{Colors.CYAN}💾 原有配置已备份到 {backup_path}{Colors.RESET}")
        except OSError:
            pass

    with open(config_path, "w", encoding="utf-8") as f:
        f.write(template)

    print(f"\n{Colors.GREEN}✅ 配置文件已生成！{Colors.RESET}")
    print(f"   保存位置：{config_path}")

    if not token:
        print(f"{Colors.YELLOW}⚠️  还没填 Token，机器人启动会失败哦~{Colors.RESET}")
    print(f"{Colors.CYAN}💡 国内网络记得在 config.py 里填 PROXY_URL（例如 http://127.0.0.1:7897）{Colors.RESET}")

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

    # 先探一下依赖在不在：已经装好就直接跳过。
    # 以前每次都无条件跑 pip install，离线或 PyPI 抽风时会报一堆红字，
    # 而实际依赖明明是齐的，看着像启动失败了。
    probe = subprocess.run(
        [sys.executable, "-c", "import telegram, aiohttp, psutil, yt_dlp"],
        capture_output=True, text=True
    )
    if probe.returncode == 0:
        print(f"{Colors.GREEN}✅ 依赖已安装，跳过~{Colors.RESET}")
        return True

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
    """
    杀掉**本项目的**旧机器人进程，防止 Conflict 冲突~

    ⚠️ 这里只结束「命令行里带着本项目的 main.py」的进程。
    以前的老实现是 taskkill /F /IM python.exe，那会把机器上
    所有 Python 程序统统杀掉（包括正在运行它的启动器自己），
    所以已经彻底去掉了~
    """
    root = get_project_root()
    src_dir = os.path.join(root, "src")
    main_marker = "main.py"
    bot_dir = src_dir if os.path.exists(os.path.join(src_dir, main_marker)) else root

    killed = 0

    # 优先用 psutil 精确匹配
    try:
        import psutil
    except ImportError:
        psutil = None

    if psutil:
        me = os.getpid()
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                info = proc.info
                if info["pid"] == me:
                    continue
                if not (info["name"] or "").lower().startswith("python"):
                    continue
                cmdline = " ".join(str(a) for a in (info["cmdline"] or []))
                if main_marker not in cmdline:
                    continue
                # 进一步确认路径属于本项目
                if bot_dir.lower() not in cmdline.lower():
                    continue
                proc.kill()
                proc.wait(timeout=3)
                killed += 1
                print(f"{Colors.YELLOW}  🧹 已结束残留进程 PID {info['pid']}{Colors.RESET}")
            except Exception:
                continue
        print(f"{Colors.GREEN}✅ 清理完成，结束了 {killed} 个残留进程~{Colors.RESET}")
        return

    # psutil 不可用时的兜底：只警告，不做危险的全量查杀
    print(f"{Colors.YELLOW}⚠️ 未安装 psutil，跳过自动清理旧进程~{Colors.RESET}")
    print(f"{Colors.YELLOW}   如果出现 Conflict 冲突，请手动结束残留的 python 进程。{Colors.RESET}")
    print(f"{Colors.YELLOW}   安装 psutil 即可自动处理：pip install psutil{Colors.RESET}")


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

    print(f"\n{Colors.BLUE}🐳 使用 Docker 启动...{Colors.RESET}")

    # compose 文件在仓库根目录（构建上下文必须是根目录，
    # 因为 Dockerfile 要 COPY src/。以前它在 src/deploy 下，已经搬走了）
    compose_file = os.path.join(root, "docker-compose.yml")
    if not os.path.exists(compose_file):
        print(f"{Colors.RED}❌ 找不到 docker-compose.yml{Colors.RESET}")
        return False

    # .env 里放 Token；没有的话 compose 会直接报错，先提醒一句
    env_file = os.path.join(root, ".env")
    if not os.path.exists(env_file):
        print(f"{Colors.YELLOW}⚠️  还没有 .env（容器里不带 config.py，配置靠环境变量）{Colors.RESET}")
        print(f"{Colors.YELLOW}   请先复制模板并填 Token：{Colors.RESET}")
        print(f"{Colors.CYAN}     copy .env.example .env{Colors.RESET}")
        return False

    try:
        # 切到仓库根目录再起 compose（相对路径、卷挂载都按根目录算）
        os.chdir(root)
        subprocess.run(["docker", "compose", "up", "-d", "--build"], check=True)

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
            config_ok = run_config_wizard()

    # 没有可用的配置就不要再往下走了：以前这里把 config_ok 直接置 True，
    # 然后照常启动，用户看到的是一堆 ImportError，完全猜不到是没配 Token。
    if not config_ok:
        print(f"\n{Colors.RED}❌ 没有可用的 config.py，机器人没法启动~{Colors.RESET}")
        print(f"{Colors.YELLOW}   请填好 src/config.py（或重新运行本启动器）后再试{Colors.RESET}")
        sys.exit(1)
    
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
        # 安装依赖（装不上就别硬启动，否则用户只会看到满屏 ImportError）
        if not install_dependencies():
            print(f"\n{Colors.RED}❌ 依赖没装齐，机器人跑不起来~{Colors.RESET}")
            print(f"{Colors.YELLOW}   按上面的提示装好依赖后再运行本启动器{Colors.RESET}")
            sys.exit(1)
        
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
