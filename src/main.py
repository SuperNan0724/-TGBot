"""
小南专属TGbot - 主程序入口
一只可可爱爱的 Telegram 机器人，支持 DeepSeek AI 对话~ ✨
"""
import logging
import sys
import os


def _setup_console_encoding():
    """
    把控制台输出强制切成 UTF-8~

    中文 Windows 上 Python 默认用 GBK 编码输出，而本项目的日志和
    启动横幅里全是 emoji（🐱 ✨ ♥ 等），一打印就会抛：

        UnicodeEncodeError: 'gbk' codec can't encode character '\\U0001f431'

    原来的 start.py 靠 `chcp 65001` 绕过这个问题，但那只在走启动器
    时有效；直接运行 `python src/main.py` 必然崩溃。
    所以在这里从程序内部修掉，不再依赖外部命令~

    必须在任何 print() 之前调用。
    """
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is None:
            continue
        try:
            # errors="replace"：万一终端真的编码不了某个字符，
            # 也只是显示成 ? 而不是让整个程序崩掉
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError):
            # 某些环境（例如被重定向到管道、或非标准流对象）不支持 reconfigure，
            # 这种情况下忽略即可，不影响功能
            pass


_setup_console_encoding()


def _coerce_env_value(raw: str, current):
    """
    把环境变量字符串转成和默认值同类型的对象~

    配置文件里全是 Python 字面量（bool / int / tuple），而环境变量天生是字符串。
    直接覆盖会出两种事故：
      • `if DISABLE_THINKING:` 对非空字符串永远为真 → 开关反了
      • 整数项变成 "8080" 这样的字符串，后面拿去做运算/绑端口就 TypeError
    所以必须按默认值的类型转换。
    """
    if isinstance(current, bool):
        return raw.strip().lower() in ("1", "true", "yes", "on")
    if isinstance(current, int):
        return int(raw)
    if isinstance(current, float):
        return float(raw)
    if isinstance(current, tuple):
        return tuple(part.strip() for part in raw.split(",") if part.strip())
    if current is None:
        # BOT_OWNER_ID 这种默认是 None 的项：能当数字就当数字
        try:
            return int(raw)
        except ValueError:
            return raw
    return raw


def _apply_env_overrides(config) -> list:
    """
    用同名环境变量覆盖配置项（容器 / 云平台 / systemd 部署用）~

    12-factor 风格：容器里不必再挂一份 config.py，`TELEGRAM_BOT_TOKEN=xxx`
    这种环境变量优先级最高。转换失败的值会被忽略（不会因为写错一个环境变量
    就起不来），最终生效的键名会打到日志里，方便核对。
    """
    overridden = []
    for name in dir(config):
        if not name.isupper():
            continue
        raw = os.environ.get(name)
        if raw is None or raw == "":
            continue
        try:
            value = _coerce_env_value(raw, getattr(config, name))
        except (TypeError, ValueError):
            continue
        setattr(config, name, value)
        overridden.append(name)
    return overridden


def _load_example_config():
    """把 config.example.py 当成一个普通模块加载出来~"""
    import importlib.util

    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.example.py")
    spec = importlib.util.spec_from_file_location("_config_example", path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _prepare_config():
    """
    准备 config 模块~ 返回 (补齐的键, 被环境变量覆盖的键)

    做三件事，顺序不能乱：
    1. 没有 config.py 时（容器 / 云平台只给环境变量），直接把 config.example.py
       注入成 `config` —— 各模块都是 `from config import X`，没有这个模块
       它们全都会 ImportError。
    2. 用模板补齐 config.py 里缺失的新增配置项（老版本升级路径）。
    3. 用同名环境变量覆盖，方便容器化 / systemd 部署。
    """
    example = _load_example_config()
    if example is None:
        return [], []

    try:
        import config
    except ModuleNotFoundError as exc:
        # 只有"确实没有 config.py"才兜底；config.py 内部缺别的包必须如实报错，
        # 否则用户会以为配置没生效，实际是自己少装了依赖
        if exc.name != "config":
            raise
        config = _load_example_config()
        if config is None:
            return [], []
        sys.modules["config"] = config
    except SyntaxError as exc:
        # config.py 语法错误、或者文件不是 UTF-8，Python 都抛 SyntaxError。
        # 让它冒出去的话，用户看到的是一段指向 import 的 traceback，
        # 根本不知道是自己少了个引号 / 用记事本存成了 ANSI。
        if "codec" in str(exc) or "unicode" in str(exc).lower():
            hint = "编码不是 UTF-8（用记事本另存成了 ANSI/GBK）"
        else:
            hint = "配置里有语法错误"
        print(
            f"\n❌ src/config.py 有问题：{hint}\n"
            f"   位置：第 {exc.lineno} 行  {(exc.text or '').strip()}\n"
            f"   {exc.msg}\n"
            "   处理：用 VS Code / 记事本把 config.py「另存为」→ 编码 UTF-8，"
            "并检查引号、括号是否配对。\n"
        )
        raise SystemExit(1)
    except UnicodeDecodeError:
        # 用记事本把 config.py 另存成 GBK/ANSI 时就是这条路：
        # 直接抛出去的话，用户只看到 Python 的编码 traceback，看不出是"保存编码"的问题
        print(
            "\n❌ src/config.py 不是 UTF-8 编码，Python 读不了它。\n"
            "   原因：用记事本/编辑器另存时选了 ANSI/GBK。\n"
            "   处理：用 VS Code 或记事本「另存为」→ 编码选 UTF-8，再启动一次。\n"
        )
        raise SystemExit(1)

    added = []
    for name in dir(example):
        if not name.isupper() or hasattr(config, name):
            continue
        setattr(config, name, getattr(example, name))
        added.append(name)

    return added, _apply_env_overrides(config)


from telegram import Update
from telegram.ext import Application, ContextTypes

# 确保项目根目录在 Python 路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ⚠️ 必须在下面任何 `from config import ...` 之前完成：
# 没 config.py 时注入模板、缺键补齐、环境变量覆盖，都在这一步做完
try:
    _CONFIG_FILLED, _CONFIG_FROM_ENV = _prepare_config()
except Exception as _exc:  # 兜底层绝不能挡住启动，让后面的真实错误照常暴露
    _CONFIG_FILLED, _CONFIG_FROM_ENV = [], []
    print(f"⚠️ 配置预处理失败（按原样继续）: {_exc}")

from config import TELEGRAM_BOT_TOKEN, BOT_NAME
from modules.module_loader import ModuleLoader
from modules.data_manager import DataManager

# 二次元风格日志
from modules.anime_logger import setup_anime_logging, print_banner, print_module_load, print_separator, Colors

# 设置二次元风格日志
setup_anime_logging()
logger = logging.getLogger(__name__)

if _CONFIG_FROM_ENV:
    logger.info(
        f"🌍 已用环境变量覆盖 {len(_CONFIG_FROM_ENV)} 个配置项："
        f"{', '.join(_CONFIG_FROM_ENV)}"
    )

if _CONFIG_FILLED:
    logger.warning(
        f"⚠️ config.py 缺少 {len(_CONFIG_FILLED)} 个配置项，"
        f"已用 config.example.py 的默认值补齐：\n"
        f"   └─ {', '.join(_CONFIG_FILLED)}\n"
        f"      需要自定义的话，把这些项复制到 config.py 里就好~"
    )


# 代理探测逻辑已抽到 modules/net_helpers.py 共用（media_parser 也要用）
from modules.net_helpers import get_proxy_url as _resolve_proxy


class BotApp:
    """机器人主应用类~ 负责启动和管理所有小模块喵！"""
    
    def __init__(self):
        self.module_loader = ModuleLoader()
        self.application = None
        self.dm = DataManager()
    
    def setup(self):
        """初始化机器人~ 准备启动啦！"""
        # 打印启动横幅
        print_banner()
        print_separator("═", 50)
        
        logger.info(f"🚀 {BOT_NAME} 正在启动...")
        print()
        
        # 检查 Token 是否已配置
        if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN":
            logger.error("呜哇！请在 config.py 中设置 TELEGRAM_BOT_TOKEN 啦！")
            sys.exit(1)
        
        # 检查主人 ID 是否已配置
        from config import BOT_OWNER_ID
        if BOT_OWNER_ID is None:
            logger.warning("⚠️ BOT_OWNER_ID 未设置，主人专属命令将不可用~")
        
        # 可选功能自检：缺东西就一次性说清楚，别等用到才报错
        self._check_optional_config()
        
        # 创建 Application（带上代理配置，否则国内环境连不上 Telegram）
        from telegram.request import HTTPXRequest
        
        proxy_url = _resolve_proxy()
        builder = Application.builder().token(TELEGRAM_BOT_TOKEN)
        
        if proxy_url:
            logger.info(f"🌐 已启用代理：{proxy_url}")
            request = HTTPXRequest(
                proxy=proxy_url,
                connect_timeout=20.0,
                read_timeout=30.0,
                write_timeout=30.0,
                pool_timeout=5.0,
            )
            builder = builder.request(request).get_updates_request(request)
        else:
            logger.warning(
                "🌐 未检测到代理配置，将直连 Telegram\n"
                "   └─ 如果你的网络无法直接访问 Telegram，启动会超时失败。\n"
                "      请在 config.py 里设置 PROXY_URL（例如 http://127.0.0.1:7897）~"
            )
        
        self.application = builder.build()
        
        # 记录 PID，方便启动器/用户干净地停掉本进程
        self._write_pid_file()
        
        # 加载模块
        print()
        logger.info("📦 正在加载模块...")
        loaded_modules = self.module_loader.load_modules(self.application)
        
        print()
        print_separator("─", 40)
        logger.info(f"🎉 成功加载了 {len(loaded_modules)} 个模块:")
        for module_name in loaded_modules:
            print_module_load(module_name)
        print_separator("─", 40)
        print()
        
        # 注册错误处理器
        self.application.add_error_handler(self.error_handler)

    def _check_optional_config(self):
        """启动期自检：把可选功能的配置缺失一次性说清楚~"""
        from config import DEEPSEEK_API_KEY

        # DeepSeek：缺了不影响启动，但 AI 聊天、/think、女友模式都用不了
        if not DEEPSEEK_API_KEY or DEEPSEEK_API_KEY == "YOUR_DEEPSEEK_API_KEY":
            logger.warning(
                "⚠️ DEEPSEEK_API_KEY 未配置\n"
                "   └─ 影响：AI 聊天 / 性格切换 / 思考 / 女友模式 将无法使用\n"
                "      其它命令（游戏、帮助、系统状态）不受影响~"
            )

    def _write_pid_file(self):
        """把当前 PID 写进 data/bot.pid，方便干净地停止本进程~"""
        try:
            from config import DATA_DIR
            os.makedirs(DATA_DIR, exist_ok=True)
            pid_path = os.path.join(DATA_DIR, "bot.pid")
            with open(pid_path, "w", encoding="utf-8") as f:
                f.write(str(os.getpid()))
            logger.info(f"📝 已记录进程号 PID {os.getpid()} 到 {pid_path}")
        except Exception as e:
            logger.warning(f"⚠️ 写入 PID 文件失败：{e}")

    def _remove_pid_file(self):
        """退出时清掉 PID 文件~"""
        try:
            from config import DATA_DIR
            pid_path = os.path.join(DATA_DIR, "bot.pid")
            if os.path.exists(pid_path):
                os.remove(pid_path)
        except Exception:
            pass

    def get_help_text(self) -> str:
        """获取帮助文本（供模块调用）"""
        return self.module_loader.get_help_text()
    
    async def _safe_status_report(self):
        """在错误处理路径里顺便探一下机器人状态~

        这里本身就在处理错误，如果探测再抛异常（网络断、被限流），
        PTB 只会多打一条 "Error while handling error"，把真正的错误埋掉，
        所以异常必须自己吃掉，只留一条 debug 日志。
        """
        try:
            status = await self._check_bot_status()
        except Exception as exc:  # noqa: BLE001
            logger.debug(f"状态检测失败（不影响主流程）: {exc}")
            return
        logger.info(f"📊 当前状态检测：{status}")

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """全局错误处理器~ 出错了也不怕！"""
        error_msg = str(context.error)
        
        # ========== 错误分析与中文提示 ==========
        
        # 1. Conflict 错误：旧会话冲突
        if "Conflict" in error_msg:
            logger.warning(
                "⚠️ 检测到旧会话冲突\n"
                "   ├─ 原因：上一个机器人实例未正常关闭，Telegram 服务器还保留着旧连接\n"
                "   ├─ 影响：新实例无法获取消息，但不会导致崩溃\n"
                "   ├─ 解决：自动杀掉旧的机器人进程，释放连接\n"
                "   └─ 状态：正在等待自动恢复..."
            )
            self._kill_stale_bot_processes()
            
            await self._safe_status_report()
            return
        
        # 2. Timed out 错误：连接超时
        if "Timed out" in error_msg or "timeout" in error_msg.lower():
            logger.warning(
                "⚠️ 连接 Telegram API 超时\n"
                "   ├─ 原因：网络环境无法访问 Telegram 服务器\n"
                "   ├─ 影响：消息发送/接收延迟或失败\n"
                "   ├─ 解决：请确保已开启代理软件（Clash/v2ray/SSR 等）\n"
                "   └─ 状态：机器人会继续尝试重连..."
            )
            await self._safe_status_report()
            return
        
        # 3. NetworkError 错误：网络异常
        if "NetworkError" in error_msg or "Connection" in error_msg:
            logger.warning(
                "⚠️ 网络连接异常\n"
                "   ├─ 原因：与 Telegram 服务器的网络连接中断\n"
                "   ├─ 影响：机器人暂时离线\n"
                "   ├─ 解决：检查网络连接和代理状态\n"
                "   └─ 状态：机器人会自动重连..."
            )
            await self._safe_status_report()
            return
        
        # 4. RetryAfter 错误：请求频率限制
        if "RetryAfter" in error_msg:
            logger.warning(
                "⚠️ 请求过于频繁，被 Telegram 限流\n"
                "   ├─ 原因：短时间内发送了太多请求\n"
                "   ├─ 影响：部分消息可能延迟处理\n"
                "   ├─ 解决：无需操作，Telegram 会自动恢复\n"
                "   └─ 状态：等待限流解除..."
            )
            await self._safe_status_report()
            return
        
        # 5. 其他未知错误
        error_info = {
            "message": error_msg,
            "update_id": update.update_id if update else None,
            "user_id": update.effective_user.id if update and update.effective_user else None,
        }
        self.dm.add_error(error_info)
        
        logger.error(
            f"💔 遇到未知错误\n"
            f"   ├─ 错误信息：{error_msg}\n"
            f"   ├─ 更新 ID：{update.update_id if update else '无'}\n"
            f"   ├─ 用户 ID：{update.effective_user.id if update and update.effective_user else '无'}\n"
            f"   └─ 已记录到错误日志，可联系开发者查看~",
            # 带上完整堆栈：以前只打一行 str(error)，debug 时根本看不出是哪一行炸的
            exc_info=context.error,
        )
        
        # 检查当前状态
        await self._safe_status_report()
        
        if update and update.effective_message:
            # 网络已经不稳定了，这条"出错了"的提示自己再失败也不该再抛出去
            try:
                await update.effective_message.reply_text(
                    "呜… 好像出了点小问题呢(｡•́︿•̀｡)\n"
                    "请稍后再试试看吧~ 喵！"
                )
            except Exception as exc:  # noqa: BLE001
                logger.debug(f"错误提示没能发出去: {exc}")
    
    async def _check_bot_status(self) -> str:
        """检查机器人当前状态，返回中文状态描述"""
        try:
            # 尝试获取 bot 信息来检测连接状态
            bot_user = await self.application.bot.get_me()
            if bot_user:
                return "✅ 机器人运行正常，已成功连接到 Telegram 服务器~"
        except Exception as e:
            error_str = str(e)
            if "Conflict" in error_str:
                return "⏳ 旧会话冲突中，等待 Telegram 释放连接..."
            elif "Timed out" in error_str or "timeout" in error_str.lower():
                return "❌ 无法连接到 Telegram 服务器，请检查代理是否开启~"
            elif "NetworkError" in error_str or "Connection" in error_str:
                return "❌ 网络连接中断，请检查网络状态~"
            else:
                return f"⚠️ 状态检测异常：{error_str}"
        return "❓ 无法获取机器人状态~"
    
    def _kill_stale_bot_processes(self) -> int:
        """
        清理残留的旧机器人进程，释放 Telegram 长轮询连接~

        只杀「命令行里带着本项目 main.py」的 python 进程，
        绝不会碰机器上其它无关的 Python 程序。

        注意：Windows 的 venv 里 `.venv\\Scripts\\python.exe` 是个**转发器**，
        它会再启动一个真正的解释器作为子进程。所以同一个机器人可能表现为
        两个命令行相同的进程（父=转发器，子=真正在轮询的那个）。
        这里会跳过「是其它机器人进程的父进程」的条目——杀转发器没有意义，
        而且会连带影响它下面真正干活的那个进程。

        Returns:
            int: 成功杀掉的进程数
        """
        try:
            import psutil
        except ImportError:
            logger.warning(
                "⚠️ 未安装 psutil，无法自动清理旧进程\n"
                "   └─ 解决：pip install psutil，或手动结束残留的 python 进程"
            )
            return 0

        me = os.getpid()
        this_path = os.path.abspath(__file__)
        this_file = os.path.basename(this_path)  # main.py
        this_dir = os.path.normcase(os.path.dirname(this_path))

        def is_this_bot_arg(proc, arg: str) -> bool:
            """
            这个命令行参数是不是本项目这个 main.py 的路径~

            只比文件名（main.py）会把机器上别的 Python 项目的 main.py 一起杀掉，
            所以要求「文件名一致 + 所在目录就是本项目 src/」。
            相对路径要按对方进程的 cwd 解析，拿不到 cwd 时宁可不杀。
            """
            if os.path.basename(arg) != this_file:
                return False
            if not os.path.isabs(arg):
                try:
                    arg = os.path.join(proc.cwd(), arg)
                except Exception:
                    return False
            return os.path.normcase(os.path.dirname(os.path.abspath(arg))) == this_dir

        # 先收集所有「看起来是机器人」的进程
        candidates = []
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                info = proc.info
                if not (info["name"] or "").lower().startswith("python"):
                    continue
                if not any(is_this_bot_arg(proc, str(arg)) for arg in (info["cmdline"] or [])):
                    continue
                candidates.append(proc)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
            except Exception:
                continue

        # 排除：自己、以及是其它候选进程之父的转发器
        candidate_pids = {p.pid for p in candidates}
        parent_pids = set()
        for proc in candidates:
            try:
                if proc.ppid() in candidate_pids:
                    parent_pids.add(proc.ppid())
            except Exception:
                continue

        killed = 0
        for proc in candidates:
            try:
                if proc.pid == me or proc.pid in parent_pids:
                    continue
                proc.kill()
                proc.wait(timeout=3)
                killed += 1
                logger.info(f"🔫 已清理残留机器人进程 (PID: {proc.pid})")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
            except Exception:
                continue

        if killed:
            logger.info(f"✅ 共清理了 {killed} 个残留进程，连接已释放~")
        else:
            logger.info("✅ 没有发现残留的机器人进程~")
        return killed

    def run(self):
        """运行机器人~ 开始和小可爱们聊天啦！"""
        print()
        logger.info(f"✨ {BOT_NAME} 启动成功！开始轮询消息...")
        print(f"{Colors.PINK}{'♥' * 50}{Colors.RESET}")
        print(f"{Colors.HOT_PINK}{Colors.BOLD}    🐱 小南正在等待小可爱们的消息~ 喵呜！(｡♥‿♥｡){Colors.RESET}")
        print(f"{Colors.PINK}{'♥' * 50}{Colors.RESET}")
        print()
        try:
            # bootstrap_retries 默认是 0 —— 意味着启动时只要连不上 Telegram
            # 就立刻放弃退出。而国内用代理访问 Telegram，代理节点抖动是常态，
            # 于是「明明配置都对，却时好时坏起不来」。
            # 这里给足重试次数，让它自己扛过短暂的网络波动。
            self.application.run_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True,
                bootstrap_retries=5,
            )
        except Exception as e:
            # 启动期网络问题要给用户明确的排查指引，而不是丢一个 traceback
            err = str(e)
            if "TimedOut" in err or "ConnectTimeout" in err or "Timed out" in err:
                logger.error(
                    "💔 启动失败：连不上 Telegram 服务器\n"
                    "   ├─ 原因：网络无法访问 api.telegram.org\n"
                    "   ├─ 检查1：代理软件是否在正常运行（节点可能失效了）\n"
                    "   ├─ 检查2：config.py 里的 PROXY_URL 端口是否与代理软件一致\n"
                    "   ├─ 检查3：浏览器能否打开 https://api.telegram.org\n"
                    "   └─ 提示：网络恢复后重新运行一次即可~"
                )
            else:
                logger.error(f"💔 启动失败：{err}")
            raise
        finally:
            self._remove_pid_file()
            logger.info("👋 小南已经休息啦~ 下次再见喵！")


def _self_check() -> int:
    """
    部署自检：不联网、不启动机器人，只回答"这套配置能不能跑起来"~

    用法：
        python main.py --check          # 本地 / systemd 装完验一下
        docker run --rm -e TELEGRAM_BOT_TOKEN=xxx telegram-bot:local python main.py --check

    返回码：0 = 关键项齐全；1 = 缺少必需配置（会写清楚缺什么）。
    """
    print()
    print("=" * 56)
    print("  小南专属TGbot —— 部署自检")
    print("=" * 56)

    problems = []
    warnings = []

    # 1. Token
    token = (TELEGRAM_BOT_TOKEN or "").strip()
    if not token or token == "YOUR_TELEGRAM_BOT_TOKEN":
        problems.append("TELEGRAM_BOT_TOKEN 还没填（@BotFather 的 /newbot 会给）")
    else:
        # 只显示指纹，别把 Token 打进日志/截图
        print(f"  ✅ Telegram Token：已配置（…{token[-4:]}）")

    # 2. 主人 ID
    try:
        import config as _cfg
        bot_owner = getattr(_cfg, "BOT_OWNER_ID", None)
    except Exception:
        bot_owner = None
    if bot_owner in (None, "", 0):
        warnings.append("BOT_OWNER_ID 未设置：主人专属命令（收藏贴纸、白名单管理）不可用")
    else:
        print(f"  ✅ 主人 ID：{bot_owner}")

    # 3. AI / 代理
    try:
        import config as _cfg
        api_key = (getattr(_cfg, "DEEPSEEK_API_KEY", "") or "").strip()
        proxy_url = (getattr(_cfg, "PROXY_URL", "") or "").strip()
    except Exception:
        api_key, proxy_url = "", ""
    if not api_key or api_key == "YOUR_DEEPSEEK_API_KEY":
        warnings.append("DEEPSEEK_API_KEY 未配置：AI 聊天 / 性格 / 思考 / 女友模式不可用")
    else:
        print("  ✅ DeepSeek Key：已配置")
    print(f"  {'✅' if proxy_url else '·'} 代理：{proxy_url or '未配置（国内网络连不上 Telegram 时必填）'}")

    # 4. 依赖
    try:
        import telegram

        print(f"  ✅ python-telegram-bot：{telegram.__version__}")
    except Exception as exc:  # noqa: BLE001
        problems.append(f"依赖没装好（import telegram 失败）：{exc}")
    try:
        import aiohttp

        print(f"  ✅ aiohttp：{aiohttp.__version__}")
    except Exception as exc:  # noqa: BLE001
        problems.append(f"依赖没装好（import aiohttp 失败）：{exc}")
    try:
        import yt_dlp

        print(f"  ✅ yt-dlp：{yt_dlp.version.__version__}")
    except Exception:
        warnings.append("yt-dlp 未安装：链接解析（视频/图片）不可用")

    # 5. ffmpeg
    try:
        from modules.net_helpers import find_ffmpeg

        ffmpeg = find_ffmpeg()
        if ffmpeg:
            print(f"  ✅ ffmpeg：{ffmpeg}")
        else:
            warnings.append("找不到 ffmpeg：B 站等站点的视频下载不下来（只能发链接）")
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"ffmpeg 检测失败：{exc}")

    # 6. 数据目录可写
    try:
        import config as _cfg

        data_dir = getattr(_cfg, "DATA_DIR", "data")
        os.makedirs(data_dir, exist_ok=True)
        probe = os.path.join(data_dir, ".write_test")
        with open(probe, "w", encoding="utf-8") as f:
            f.write("ok")
        os.remove(probe)
        print(f"  ✅ 数据目录可写：{os.path.abspath(data_dir)}")
    except Exception as exc:  # noqa: BLE001
        problems.append(f"数据目录不可写（{exc}）：白名单/用户数据存不下来")

    # 7. 配置来源
    if _CONFIG_FROM_ENV:
        print(f"  ✅ 环境变量覆盖了 {len(_CONFIG_FROM_ENV)} 项")
    if _CONFIG_FILLED:
        print(f"  ✅ 模板补齐了 {len(_CONFIG_FILLED)} 项（老 config.py 缺新键，正常）")

    print("-" * 56)
    for item in problems:
        print(f"  ❌ {item}")
    for item in warnings:
        print(f"  ⚠️  {item}")
    if not problems and not warnings:
        print("  🎉 全部检查通过，可以直接启动啦~")
    elif not problems:
        print("  ✅ 关键项齐全，上面的告警只影响可选功能")
    print("=" * 56)
    print()

    return 1 if problems else 0


def main():
    """主函数~ 一切从这里开始！"""
    # 配置里的 data/ 路径都是相对 src/ 的，两个启动器也都是先 chdir 到 src/
    # 再拉起本文件；直接 `python src/main.py` 时如果 cwd 是项目根目录，
    # 数据就会写到另一个 data/ 目录（看起来像"数据全丢了"）
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    if "--check" in sys.argv:
        sys.exit(_self_check())

    bot = BotApp()
    try:
        bot.setup()
        bot.run()
    finally:
        # setup() 中途失败时 run() 的 finally 根本不会执行，会留下 data/bot.pid；
        # 而 start.bat --stop/--status 正是照着这个 PID 找进程，PID 被系统
        # 复用之后就可能杀掉无关进程，所以任何退出路径都要清掉
        bot._remove_pid_file()


if __name__ == "__main__":
    main()
