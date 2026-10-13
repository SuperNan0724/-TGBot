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

from telegram import Update
from telegram.ext import Application, ContextTypes

# 确保项目根目录在 Python 路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import TELEGRAM_BOT_TOKEN, BOT_NAME
from modules.module_loader import ModuleLoader
from modules.data_manager import DataManager

# 二次元风格日志
from modules.anime_logger import setup_anime_logging, print_banner, print_module_load, print_separator, Colors

# 设置二次元风格日志
setup_anime_logging()
logger = logging.getLogger(__name__)


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
        
        # 启动回调服务器（发卡平台对接）
        self._start_callback_server(loaded_modules)
    
    def _check_optional_config(self):
        """启动期自检：把可选功能的配置缺失一次性说清楚~"""
        from config import (
            DEEPSEEK_API_KEY, CALLBACK_SECRET,
            DISABLE_CALLBACK_SERVER_IF_UNSET, CALLBACK_PORT,
        )

        # DeepSeek：缺了不影响启动，但 AI 聊天、/think、女友模式都用不了
        if not DEEPSEEK_API_KEY or DEEPSEEK_API_KEY == "YOUR_DEEPSEEK_API_KEY":
            logger.warning(
                "⚠️ DEEPSEEK_API_KEY 未配置\n"
                "   └─ 影响：AI 聊天 / 性格切换 / 思考 / 女友模式 将无法使用\n"
                "      其它命令（游戏、帮助、系统状态）不受影响~"
            )

        # 回调服务器：密钥是唯一凭据，占位值等于对外开放伪造回调
        if CALLBACK_SECRET in ("", "CHANGE_ME_TO_A_RANDOM_SECRET"):
            if DISABLE_CALLBACK_SERVER_IF_UNSET:
                logger.warning(
                    f"🔒 发卡平台回调服务器将不会启动（端口 {CALLBACK_PORT}）\n"
                    "   └─ 原因：CALLBACK_SECRET 还是占位值，用它等于没有防护\n"
                    "      需要接发卡平台时，请在 config.py 里改成一串随机字符~"
                )
            else:
                logger.warning(
                    "⚠️ CALLBACK_SECRET 仍是占位值，但回调服务器被强制开启！\n"
                    "   └─ 风险：任何人都能伪造「支付成功」回调，白拿激活码！\n"
                    "      请立刻在 config.py 里把它改成一串随机字符！"
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

    def _start_callback_server(self, loaded_modules: list):
        """启动发卡平台回调服务器~"""
        if "paid_whitelist" in loaded_modules:
            try:
                paid_module = self.module_loader.get_module("paid_whitelist")
                if paid_module and hasattr(paid_module, 'start_callback_server'):
                    paid_module.start_callback_server()
            except Exception as e:
                logger.error(f"启动回调服务器失败: {e}")
        else:
            logger.info("⏭️ 未加载 paid_whitelist 模块，跳过回调服务器启动")
    
    def get_help_text(self) -> str:
        """获取帮助文本（供模块调用）"""
        return self.module_loader.get_help_text()
    
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
            
            # 检查当前状态
            status = await self._check_bot_status()
            logger.info(f"📊 当前状态检测：{status}")
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
            # 检查当前状态
            status = await self._check_bot_status()
            logger.info(f"📊 当前状态检测：{status}")
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
            # 检查当前状态
            status = await self._check_bot_status()
            logger.info(f"📊 当前状态检测：{status}")
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
            # 检查当前状态
            status = await self._check_bot_status()
            logger.info(f"📊 当前状态检测：{status}")
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
            f"   └─ 已记录到错误日志，可联系开发者查看~"
        )
        
        # 检查当前状态
        status = await self._check_bot_status()
        logger.info(f"📊 当前状态检测：{status}")
        
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "呜… 好像出了点小问题呢(｡•́︿•̀｡)\n"
                "请稍后再试试看吧~ 喵！"
            )
    
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
        this_file = os.path.basename(os.path.abspath(__file__))  # main.py

        # 先收集所有「看起来是机器人」的进程
        candidates = []
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                info = proc.info
                if not (info["name"] or "").lower().startswith("python"):
                    continue
                cmdline = info["cmdline"] or []
                if not any(this_file in str(arg) for arg in cmdline):
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
            # drop_pending_updates=True 清除旧会话冲突
            self.application.run_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True
            )
        finally:
            self._remove_pid_file()
            logger.info("👋 小南已经休息啦~ 下次再见喵！")


def main():
    """主函数~ 一切从这里开始！"""
    bot = BotApp()
    bot.setup()
    bot.run()


if __name__ == "__main__":
    main()
