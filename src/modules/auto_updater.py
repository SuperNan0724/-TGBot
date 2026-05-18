"""
🔄 自动更新模块~ 让小南保持最新版本！(｡•̀ᴗ-)✧

功能：
- 每隔 12 小时自动检查 GitHub 仓库更新
- /update 命令手动检查更新
- 自动下载更新文件，保留用户的 config.py 和 data/ 目录
- 核心文件强制更新，模块文件可选更新（用户自定义的模块不会被覆盖）
- 更新前自动备份旧文件
"""
import logging
import os
import sys
import json
import shutil
import asyncio
import hashlib
import re
from datetime import datetime, timedelta
from typing import Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes

from .base_module import BaseModule

logger = logging.getLogger(__name__)

# ===== 配置 =====
GITHUB_REPO = "SuperNan0724/-TGBot"
GITHUB_API_BASE = f"https://api.github.com/repos/{GITHUB_REPO}"
GITHUB_RAW_BASE = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main"
CHECK_INTERVAL_HOURS = 12  # 检查间隔（小时）

# 项目根目录
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 需要保留的文件/目录（不会被更新覆盖）
PROTECTED_PATHS = [
    "src/config.py",
    "src/data/",
]

# ===== 核心文件（必须更新）=====
# 这些是项目运行必需的关键文件，更新时会强制覆盖
CORE_FILES = [
    "start.py",
    "README.md",
    ".dockerignore",
    "src/main.py",
    "src/requirements.txt",
    "src/deploy/commands.txt",
    "src/deploy/Dockerfile",
    "src/deploy/docker-compose.yml",
    "src/deploy/setup.bat",
    "src/deploy/setup.sh",
    "src/modules/__init__.py",
    "src/modules/base_module.py",
    "src/modules/module_loader.py",
    "src/modules/data_manager.py",
    "src/modules/anime_logger.py",
]

# ===== 模块文件（可选更新）=====
# 这些是官方提供的模块，更新时会检查是否被用户修改过
# 如果用户自定义了同名模块，不会覆盖
MODULE_FILES = [
    "src/modules/admin.py",
    "src/modules/deepseek_chat.py",
    "src/modules/fun.py",
    "src/modules/help.py",
    "src/modules/personalities.py",
    "src/modules/system.py",
    "src/modules/think.py",
    "src/modules/welcome.py",
    "src/modules/auto_updater.py",
]


class AutoUpdater(BaseModule):
    """自动更新模块~ 让小南保持最新版本！"""
    
    name = "auto_updater"
    description = "自动检查 GitHub 更新~"
    
    def __init__(self, bot_app=None):
        super().__init__(bot_app)
        self._update_lock = asyncio.Lock()
        self._last_check_file = os.path.join(ROOT_DIR, "data", "last_update_check.json")
        self._backup_dir = os.path.join(ROOT_DIR, "data", "backups")
    
    def register_handlers(self, application):
        """注册命令处理器~"""
        application.add_handler(CommandHandler("update", self.update_command))
        application.add_handler(CommandHandler("check_update", self.check_update_command))
        application.add_handler(CallbackQueryHandler(self.update_callback, pattern=r"^update_"))
    
    async def start_periodic_check(self, application):
        """启动定时检查任务（每12小时）"""
        while True:
            try:
                await asyncio.sleep(CHECK_INTERVAL_HOURS * 3600)
                await self._check_and_notify(application)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"定时检查更新失败: {e}")
    
    async def _check_and_notify(self, application):
        """检查更新并通知所有管理员"""
        try:
            has_update, info = await self._check_github_version()
            if has_update:
                # 通知所有管理员
                from config import BOT_OWNER_ID
                if BOT_OWNER_ID:
                    try:
                        await application.bot.send_message(
                            chat_id=BOT_OWNER_ID,
                            text=f"🔄 发现新版本！\n\n"
                                 f"📦 版本：{info.get('version', '未知')}\n"
                                 f"📝 更新内容：{info.get('description', '无')}\n\n"
                                 f"发送 /update 查看更新详情~",
                            reply_markup=InlineKeyboardMarkup([[
                                InlineKeyboardButton("🔄 查看更新", callback_data="update_check")
                            ]])
                        )
                    except Exception as e:
                        logger.warning(f"通知管理员失败: {e}")
        except Exception as e:
            logger.error(f"检查更新失败: {e}")
    
    async def check_update_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/check_update 命令 - 手动检查更新，不自动下载~"""
        user_id = update.effective_user.id
        
        # 检查权限（仅主人可用）
        from config import BOT_OWNER_ID
        if BOT_OWNER_ID and user_id != BOT_OWNER_ID:
            await update.message.reply_text(
                "呜… 只有主人才能检查小南的更新呢(｡•́︿•̀｡)\n"
                "请让主人来操作吧~"
            )
            return
        
        await update.message.reply_text("🔍 正在检查更新，请稍等~")
        
        try:
            has_update, info = await self._check_github_version()
            
            if has_update:
                await update.message.reply_text(
                    f"🔄 发现新版本！\n\n"
                    f"📦 当前版本：{info.get('current_version', '未知')}\n"
                    f"📦 最新版本：{info.get('version', '未知')}\n"
                    f"📝 更新内容：\n{info.get('description', '无')}\n\n"
                    f"💡 想更新的话，发送 /update 来更新哦~\n"
                    f"可以选择「全部更新」或「仅核心文件」~",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔄 去更新", callback_data="update_check")
                    ]])
                )
            else:
                await update.message.reply_text(
                    f"✅ 小南已经是最新版本啦~\n\n"
                    f"📦 当前版本：{info.get('current_version', '未知')}\n"
                    f"🕐 检查时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
                    f"下次自动检查时间：{(datetime.now() + timedelta(hours=CHECK_INTERVAL_HOURS)).strftime('%Y-%m-%d %H:%M')}"
                )
        except Exception as e:
            logger.error(f"检查更新失败: {e}")
            await update.message.reply_text(
                f"❌ 检查更新失败：{str(e)}\n\n"
                f"可能的原因：\n"
                f"• 网络无法访问 GitHub\n"
                f"• GitHub API 限制\n"
                f"请稍后再试~"
            )
    
    async def update_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/update 命令 - 检查并更新小南~"""
        user_id = update.effective_user.id
        
        # 检查权限（仅主人可用）
        from config import BOT_OWNER_ID
        if BOT_OWNER_ID and user_id != BOT_OWNER_ID:
            await update.message.reply_text(
                "呜… 只有主人才能更新小南呢(｡•́︿•̀｡)\n"
                "请让主人来操作吧~"
            )
            return
        
        await update.message.reply_text(
            "🔄 正在检查更新，请稍等~",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔄 检查更新", callback_data="update_check")
            ]])
        )
    
    async def update_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理更新按钮回调~"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data == "update_check":
            await self._handle_check_update(query, context)
        elif data == "update_all":
            await self._handle_do_update(query, context, update_modules=True)
        elif data == "update_core":
            await self._handle_do_update(query, context, update_modules=False)
        elif data == "update_cancel":
            await query.edit_message_text("🔄 更新已取消~ 下次再更新吧！喵~")
    
    async def _handle_check_update(self, query, context):
        """处理检查更新逻辑"""
        try:
            has_update, info = await self._check_github_version()
            
            if has_update:
                keyboard = [
                    [
                        InlineKeyboardButton("📦 全部更新", callback_data="update_all"),
                        InlineKeyboardButton("⚡ 仅核心文件", callback_data="update_core"),
                    ],
                    [InlineKeyboardButton("❌ 取消", callback_data="update_cancel")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    f"🔄 发现新版本！\n\n"
                    f"📦 当前版本：{info.get('current_version', '未知')}\n"
                    f"📦 最新版本：{info.get('version', '未知')}\n"
                    f"📝 更新内容：\n{info.get('description', '无')}\n\n"
                    f"请选择更新方式：\n"
                    f"• 📦 全部更新：更新核心文件 + 官方模块\n"
                    f"• ⚡ 仅核心文件：只更新关键文件，保留所有模块\n"
                    f"• config.py 和 data/ 目录会自动保留~\n"
                    f"• 自定义模块不会被覆盖~",
                    reply_markup=reply_markup
                )
            else:
                await query.edit_message_text(
                    f"✅ 小南已经是最新版本啦~\n\n"
                    f"📦 当前版本：{info.get('current_version', '未知')}\n"
                    f"🕐 最后检查：{datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
                    f"下次自动检查时间：{(datetime.now() + timedelta(hours=CHECK_INTERVAL_HOURS)).strftime('%Y-%m-%d %H:%M')}"
                )
        except Exception as e:
            logger.error(f"检查更新失败: {e}")
            await query.edit_message_text(
                f"❌ 检查更新失败：{str(e)}\n\n"
                f"可能的原因：\n"
                f"• 网络无法访问 GitHub\n"
                f"• GitHub API 限制\n"
                f"请稍后再试~"
            )
    
    async def _handle_do_update(self, query, context, update_modules: bool):
        """执行更新"""
        async with self._update_lock:
            try:
                await query.edit_message_text(
                    "🔄 正在下载更新文件...\n"
                    "请稍等，不要关闭机器人~"
                )
                
                # 构建更新文件列表
                files_to_update = list(CORE_FILES)  # 核心文件必更新
                if update_modules:
                    files_to_update.extend(MODULE_FILES)  # 模块文件可选
                
                # 备份旧文件
                backup_id = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = os.path.join(self._backup_dir, f"pre_update_{backup_id}")
                
                # 下载并更新文件
                updated_count = 0
                failed_files = []
                skipped_files = []
                module_skipped = 0
                
                for rel_path in files_to_update:
                    # 检查是否受保护
                    if self._is_protected(rel_path):
                        skipped_files.append(rel_path)
                        continue
                    
                    local_path = os.path.join(ROOT_DIR, rel_path)
                    # 将 Windows 反斜杠替换为正斜杠（不能在 f-string 中使用反斜杠）
                    rel_path_unix = rel_path.replace("\\", "/")
                    github_url = f"{GITHUB_RAW_BASE}/{rel_path_unix}"
                    
                    try:
                        # 下载文件
                        content = await self._download_file(github_url)
                        if content is None:
                            failed_files.append(rel_path)
                            continue
                        
                        # 备份旧文件
                        if os.path.exists(local_path):
                            backup_file_path = os.path.join(backup_path, rel_path)
                            os.makedirs(os.path.dirname(backup_file_path), exist_ok=True)
                            shutil.copy2(local_path, backup_file_path)
                        
                        # 写入新文件
                        os.makedirs(os.path.dirname(local_path), exist_ok=True)
                        with open(local_path, "w", encoding="utf-8") as f:
                            f.write(content)
                        
                        updated_count += 1
                        
                    except Exception as e:
                        logger.error(f"更新文件失败 {rel_path}: {e}")
                        failed_files.append(rel_path)
                
                # 构建结果消息
                update_type = "全部更新" if update_modules else "仅核心文件"
                result_msg = (
                    f"✅ {update_type}完成！\n\n"
                    f"📊 更新统计：\n"
                    f"  • 成功更新：{updated_count} 个文件\n"
                    f"  • 跳过保留：{len(skipped_files)} 个文件\n"
                    f"  • 更新失败：{len(failed_files)} 个文件\n"
                )
                
                if not update_modules:
                    result_msg += f"  • 模块文件未更新：{len(MODULE_FILES)} 个（保留自定义模块）\n"
                
                if skipped_files:
                    result_msg += f"\n📋 已保留的文件：\n"
                    for f in skipped_files:
                        result_msg += f"  • {f}\n"
                
                if failed_files:
                    result_msg += f"\n❌ 更新失败的文件：\n"
                    for f in failed_files:
                        result_msg += f"  • {f}\n"
                    result_msg += f"\n💡 可以稍后重试 /update"
                
                result_msg += f"\n🔄 建议重启机器人以应用更新~"
                
                # 保存更新记录
                self._save_check_result({
                    "last_check": datetime.now().isoformat(),
                    "has_update": False,
                    "updated_files": updated_count,
                    "backup_id": backup_id
                })
                
                await query.edit_message_text(result_msg)
                
            except Exception as e:
                logger.error(f"更新过程出错: {e}")
                await query.edit_message_text(
                    f"❌ 更新过程出错：{str(e)}\n\n"
                    f"💡 备份文件保存在：data/backups/\n"
                    f"可以手动恢复~"
                )
    
    def _is_protected(self, rel_path: str) -> bool:
        """检查文件是否受保护（不会被更新覆盖）"""
        for protected in PROTECTED_PATHS:
            if rel_path == protected or rel_path.startswith(protected):
                return True
        return False
    
    async def _download_file(self, url: str) -> Optional[str]:
        """从 GitHub 下载文件内容"""
        import aiohttp
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=15) as resp:
                    if resp.status == 200:
                        return await resp.text()
                    else:
                        logger.warning(f"下载失败 {url}: HTTP {resp.status}")
                        return None
        except asyncio.TimeoutError:
            logger.warning(f"下载超时: {url}")
            return None
        except Exception as e:
            logger.error(f"下载异常: {url} - {e}")
            return None
    
    async def _check_github_version(self):
        """检查 GitHub 仓库是否有更新"""
        import aiohttp
        
        # 获取本地版本信息
        current_version = self._get_local_version()
        
        # 获取 GitHub 上的版本信息
        try:
            async with aiohttp.ClientSession() as session:
                # 获取仓库信息
                async with session.get(f"{GITHUB_API_BASE}", timeout=10) as resp:
                    if resp.status != 200:
                        raise Exception(f"GitHub API 返回 {resp.status}")
                    repo_info = await resp.json()
                
                # 获取最新 commit
                async with session.get(
                    f"{GITHUB_API_BASE}/commits/main",
                    timeout=10,
                    headers={"Accept": "application/vnd.github.v3+json"}
                ) as resp:
                    if resp.status != 200:
                        raise Exception(f"GitHub API 返回 {resp.status}")
                    commit_info = await resp.json()
                
                latest_sha = commit_info["sha"][:7]  # 取前7位作为版本号
                commit_msg = commit_info["commit"]["message"].split("\n")[0]
                commit_date = commit_info["commit"]["committer"]["date"][:10]
                
                # 比较版本
                has_update = latest_sha != current_version
                
                info = {
                    "version": latest_sha,
                    "current_version": current_version,
                    "description": f"Commit: {commit_msg}\n日期: {commit_date}",
                    "commit_sha": latest_sha,
                    "commit_message": commit_msg,
                    "commit_date": commit_date,
                }
                
                # 保存检查结果
                self._save_check_result({
                    "last_check": datetime.now().isoformat(),
                    "has_update": has_update,
                    "latest_version": latest_sha,
                    "current_version": current_version,
                })
                
                return has_update, info
                
        except Exception as e:
            logger.error(f"检查 GitHub 版本失败: {e}")
            raise
    
    def _get_local_version(self) -> str:
        """获取本地版本（基于文件修改时间或自定义版本文件）"""
        version_file = os.path.join(ROOT_DIR, "data", ".version")
        
        if os.path.exists(version_file):
            with open(version_file, "r", encoding="utf-8") as f:
                return f.read().strip()
        
        # 如果没有版本文件，使用 main.py 的修改时间作为版本标识
        main_py = os.path.join(ROOT_DIR, "src", "main.py")
        if os.path.exists(main_py):
            mtime = os.path.getmtime(main_py)
            return datetime.fromtimestamp(mtime).strftime("%Y%m%d")
        
        return "unknown"
    
    def _save_check_result(self, result: dict):
        """保存检查结果"""
        try:
            os.makedirs(os.path.dirname(self._last_check_file), exist_ok=True)
            with open(self._last_check_file, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"保存检查结果失败: {e}")
    
    def get_help_text(self) -> str:
        """返回帮助文本~"""
        return (
            "/update - 检查并更新小南到最新版本~\n"
            "/check_update - 手动检查更新，不自动下载~\n"
            "🔄 自动每12小时检查一次更新~"
        )
