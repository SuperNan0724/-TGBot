"""
💰 付费白名单模块 - 激活码 + 发卡平台接入 + 商品管理
小南的小钱罐子~ 支持手动发码和发卡平台自动回调！(｡♥‿♥｡)
"""
import asyncio
import json
import logging
import os
import random
import string
import threading
from datetime import datetime, timedelta
from typing import Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes

from config import PAID_WHITELIST_FILE, PRODUCTS_FILE, CALLBACK_HOST, CALLBACK_PORT, CALLBACK_SECRET, TELEGRAM_BOT_TOKEN
from .base_module import BaseModule
from .data_manager import DataManager

# ────────── aiohttp 按需导入（避免没安装就炸） ──────────
try:
    from aiohttp import web
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False

logger = logging.getLogger(__name__)

# 默认激活码有效期（天）
DEFAULT_DURATION_DAYS = 30


def _generate_code(length: int = 8) -> str:
    """生成随机激活码（大写字母+数字，排除易混淆字符）~"""
    chars = string.ascii_uppercase.replace("O", "").replace("I", "") + string.digits.replace("0", "").replace("1", "")
    return "".join(random.choices(chars, k=length))


def _load_paid_data() -> dict:
    """加载付费白名单数据~"""
    if os.path.exists(PAID_WHITELIST_FILE):
        try:
            with open(PAID_WHITELIST_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载付费白名单数据失败: {e}")
    return {"codes": [], "paid_users": {}}


def _save_paid_data(data: dict):
    """保存付费白名单数据~"""
    try:
        os.makedirs(os.path.dirname(PAID_WHITELIST_FILE), exist_ok=True)
        with open(PAID_WHITELIST_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"保存付费白名单数据失败: {e}")
        return False


def _load_products() -> dict:
    """加载商品配置~"""
    if os.path.exists(PRODUCTS_FILE):
        try:
            with open(PRODUCTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载商品配置失败: {e}")
    return {"products": []}


def _save_products(data: dict):
    """保存商品配置~"""
    try:
        os.makedirs(os.path.dirname(PRODUCTS_FILE), exist_ok=True)
        with open(PRODUCTS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"保存商品配置失败: {e}")
        return False


# ===== 全局：用于在回调中发消息 =====
_bot_app_ref = None  # 由 main.py 启动时赋值


class PaidWhitelist(BaseModule):
    """付费白名单模块~ 管理激活码、商品和付费用户！"""

    name = "paid_whitelist"
    description = "激活码兑换、商品购买与付费白名单管理~"

    def __init__(self, bot_app=None):
        super().__init__(bot_app)
        self.dm = DataManager()
        self._data = _load_paid_data()
        self._products = _load_products()

    def _save(self):
        _save_paid_data(self._data)

    def _save_products_data(self):
        _save_products(self._products)

    # ────────── 到期时间工具 ──────────

    def _get_user_expiry(self, user_id: int) -> Optional[datetime]:
        user_key = str(user_id)
        if user_key in self._data.get("paid_users", {}):
            expires_str = self._data["paid_users"][user_key].get("expires_at")
            if expires_str:
                try:
                    return datetime.fromisoformat(expires_str)
                except:
                    pass
        return None

    def _is_user_expired(self, user_id: int) -> bool:
        expires_at = self._get_user_expiry(user_id)
        if expires_at is None:
            return False
        return datetime.now() > expires_at

    def _clean_expired_users(self):
        paid_users = self._data.get("paid_users", {})
        expired_users = []

        for user_key, info in paid_users.items():
            expires_str = info.get("expires_at")
            if expires_str:
                try:
                    expires_at = datetime.fromisoformat(expires_str)
                    if datetime.now() > expires_at:
                        expired_users.append(int(user_key))
                except:
                    expired_users.append(int(user_key))

        for user_id in expired_users:
            self.dm.del_user(user_id)
            logger.info(f"⏰ 付费用户 {user_id} 已过期，已自动从白名单移除")

        for user_key in [str(uid) for uid in expired_users]:
            if user_key in paid_users:
                del paid_users[user_key]

        if expired_users:
            self._data["paid_users"] = paid_users
            self._save()
        return expired_users

    # ────────── 给小南用的私聊发消息工具 ──────────

    # 存一份 application 引用供回调用
    _application = None

    @classmethod
    def set_application(cls, app):
        cls._application = app

    # ────────── 注册命令 ──────────

    def register_handlers(self, application):
        # 所有人可用
        application.add_handler(CommandHandler("buy", self.buy_command))
        application.add_handler(CommandHandler("redeem", self.redeem_command))
        application.add_handler(CommandHandler("check_expiry", self.check_expiry_command))

        # 主人专属
        application.add_handler(CommandHandler("gencode", self.gencode_command))
        application.add_handler(CommandHandler("codes", self.codes_command))
        application.add_handler(CommandHandler("revoke", self.revoke_command))
        application.add_handler(CommandHandler("paid_users", self.paid_users_command))
        application.add_handler(CommandHandler("clean_expired", self.clean_expired_command))

        # 商品管理（主人专属）
        application.add_handler(CommandHandler("add_product", self.add_product_command))
        application.add_handler(CommandHandler("del_product", self.del_product_command))
        application.add_handler(CommandHandler("products", self.products_command))

        # 私聊发送激活码（主人专属）
        application.add_handler(CommandHandler("send_code", self.send_code_command))

        # 回调按钮
        application.add_handler(CallbackQueryHandler(self.callback_handler, pattern=r"^paid_"))

        # 保存 application 供回调服务使用
        self.__class__._application = application

    # ──────────────────────────────────────────
    #  用户端命令
    # ──────────────────────────────────────────

    async def buy_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/buy - 查看商品列表并获取购买方式~"""
        products = self._products.get("products", [])
        enabled = [p for p in products if p.get("enabled", True)]

        if not enabled:
            await update.message.reply_text(
                "😅 目前还没有上架的商品哦~\n"
                "请联系主人看看什么时候开放购买吧！"
            )
            return

        msg = "🛒 **小南的购买菜单~**\n\n"
        msg += "选择你想要的商品，点击按钮获取付款方式~\n"
        msg += "付款后自动发货，激活码会通过机器人私聊发给你哦！\n\n"

        keyboard = []
        for prod in enabled:
            pid = prod["id"]
            name = prod["name"]
            price = prod.get("price_display", f"{prod['price']} 元")
            desc = prod.get("description", "")
            msg += f"**{name}** — {price}\n  {desc}\n\n"
            keyboard.append([
                InlineKeyboardButton(f"💰 {name} {price}", callback_data=f"paid_buy_{pid}")
            ])

        await update.message.reply_text(
            msg,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None
        )

    async def redeem_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/redeem <激活码> - 使用激活码加入白名单~"""
        user_id = update.effective_user.id

        if self.dm.is_user_whitelisted(user_id) or self.dm.is_owner(user_id):
            if self._is_user_expired(user_id):
                pass  # 过期了，允许重新兑换
            else:
                await update.message.reply_text(
                    "😅 你已经可以用小南啦~ 不需要再兑换了哦！\n"
                    "查看有效期：/check_expiry"
                )
                return

        if not context.args:
            await update.message.reply_text(
                "💡 用法：/redeem <激活码>\n"
                "把主人给你的激活码输进来，就能使用小南啦！\n"
                "😺 还没有激活码？用 /buy 购买吧~"
            )
            return

        code = context.args[0].strip().upper()
        found = None
        for i, c in enumerate(self._data.get("codes", [])):
            if c["code"] == code:
                found = i
                break

        if found is None:
            await update.message.reply_text(
                "❌ 这个激活码不存在哦~\n"
                "请检查一下有没有输错吧！(｡•́︿•̀｡)"
            )
            return

        code_data = self._data["codes"][found]
        if code_data.get("used"):
            await update.message.reply_text("❌ 这个激活码已经被用过啦~ 每个激活码只能使用一次哦！")
            return
        if code_data.get("revoked"):
            await update.message.reply_text("❌ 这个激活码已经被主人撤销啦~ 请联系主人获取新的激活码吧！")
            return

        duration_days = code_data.get("duration_days", DEFAULT_DURATION_DAYS)
        activated_at = datetime.now()
        expires_at = activated_at + timedelta(days=duration_days)

        self._data["codes"][found]["used"] = True
        self._data["codes"][found]["used_by"] = user_id
        self._data["codes"][found]["used_at"] = activated_at.isoformat()

        user_key = str(user_id)
        self._data["paid_users"][user_key] = {
            "activated_at": activated_at.isoformat(),
            "expires_at": expires_at.isoformat(),
            "code": code,
            "duration_days": duration_days
        }
        self._save()
        self.dm.add_user(user_id)

        await update.message.reply_text(
            f"🎉 兑换成功！欢迎加入小南的大家庭~\n\n"
            f"📅 有效期：{duration_days} 天\n"
            f"⏰ 到期时间：{expires_at.strftime('%Y年%m月%d日 %H:%M')}\n\n"
            f"现在你可以和我聊天啦！喵呜~ (｡♥‿♥｡)\n\n"
            f"查看有效期：/check_expiry"
        )
        logger.info(f"💰 用户 {user_id} 使用激活码 {code} 兑换成功，有效期 {duration_days} 天")

    async def check_expiry_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/check_expiry - 查看自己的白名单有效期~"""
        user_id = update.effective_user.id

        if self.dm.is_owner(user_id):
            await update.message.reply_text("👑 主人是不需要有效期的哦~ 小南会永远陪着主人的！")
            return

        if self.dm.is_admin(user_id):
            await update.message.reply_text("👑 管理员是不需要有效期的哦~ 只要还在白名单里就能一直用啦~")
            return

        if not self.dm.is_user_whitelisted(user_id):
            await update.message.reply_text(
                "😅 你还不能使用小南哦~\n"
                "需要激活码才能使用呢！用 /buy 购买吧~\n"
                "已经有激活码了？用 /redeem <激活码> 兑换！"
            )
            return

        expires_at = self._get_user_expiry(user_id)
        if expires_at is None:
            await update.message.reply_text(
                "📅 你的账号没有设置有效期呢~\n"
                "可能是被管理员添加的白名单，可以一直用哦！(｡♥‿♥｡)"
            )
            return

        now = datetime.now()
        remaining = expires_at - now
        remaining_days = remaining.days
        remaining_hours = remaining.seconds // 3600

        if remaining_days < 0:
            await update.message.reply_text(
                "⏰ 你的有效期已经过期啦~\n"
                "请联系主人续费哦！用 /buy 可以购买新的~"
            )
            return

        status = "✅ 正常" if remaining_days > 3 else "⚠️ 即将到期"
        msg = (
            f"📅 你的白名单状态~\n\n"
            f"状态：{status}\n"
            f"到期时间：{expires_at.strftime('%Y年%m月%d日 %H:%M')}\n"
            f"剩余时间：{remaining_days} 天 {remaining_hours} 小时\n\n"
        )
        if remaining_days <= 3:
            msg += "💡 快到期了哦~ 记得购买续费呀！用 /buy"
        elif remaining_days <= 7:
            msg += "💡 还有一周左右，可以提前规划续费哦~"
        else:
            msg += "💪 时间还很充裕，尽情和小南聊天吧！"

        await update.message.reply_text(msg)

    # ──────────────────────────────────────────
    #  主人专属命令
    # ──────────────────────────────────────────

    async def send_code_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/send_code <用户ID> [天数] - 私聊发送激活码给指定用户（主人专属）~"""
        if not self.dm.is_owner(update.effective_user.id):
            await update.message.reply_text("呜… 只有主人才能使用这个命令哦！")
            return

        if not context.args:
            await update.message.reply_text(
                "💡 用法：/send_code <用户ID> [天数]\n"
                "直接生成激活码并通过机器人私聊发给用户~\n"
                "示例：/send_code 123456789 30"
            )
            return

        try:
            target_user_id = int(context.args[0])
            days = DEFAULT_DURATION_DAYS
            if len(context.args) > 1:
                days = int(context.args[1])
                if days <= 0:
                    days = DEFAULT_DURATION_DAYS
        except ValueError:
            await update.message.reply_text("😅 参数格式不对哦~ 用户ID和天数都要是数字！")
            return

        # 生成激活码
        code = _generate_code()
        self._data["codes"].append({
            "code": code,
            "created_at": datetime.now().isoformat(),
            "created_by": update.effective_user.id,
            "used": False,
            "used_by": None,
            "used_at": None,
            "duration_days": days,
            "revoked": False
        })
        self._save()

        # 尝试私聊发送给用户
        sent = False
        try:
            if self.__class__._application:
                bot = self.__class__._application.bot
                await bot.send_message(
                    chat_id=target_user_id,
                    text=(
                        f"🎉 主人送了你一张小南的激活码~\n\n"
                        f"🎫 激活码：`{code}`\n"
                        f"📅 有效期：{days} 天\n\n"
                        f"快来和我聊天吧！用 /redeem {code} 兑换~\n"
                        f"或者点击下面按钮快速兑换~"
                    ),
                    parse_mode="Markdown"
                )
                sent = True
        except Exception as e:
            logger.warning(f"私聊发送给 {target_user_id} 失败: {e}")

        # 回复主人
        if sent:
            await update.message.reply_text(
                f"✅ 已生成激活码并私聊发送给用户 {target_user_id}~\n\n"
                f"🎫 激活码：`{code}`\n"
                f"📅 有效期：{days} 天\n\n"
                f"💡 用户兑换后你会收到通知的~",
                parse_mode="Markdown"
            )
            logger.info(f"💰 主人通过 /send_code 发送了激活码 {code} 给用户 {target_user_id}（{days}天）")
        else:
            await update.message.reply_text(
                f"✅ 已生成激活码~\n\n"
                f"🎫 激活码：`{code}`\n"
                f"📅 有效期：{days} 天\n"
                f"⚠️ 但无法私聊发送给用户 {target_user_id}（可能用户没主动和机器人说过话）\n\n"
                f"请手动把激活码发给用户，或用 /chatid 让用户先联系机器人~",
                parse_mode="Markdown"
            )

    async def gencode_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/gencode [天数] [数量] - 生成激活码（主人专属）~"""
        if not self.dm.is_owner(update.effective_user.id):
            await update.message.reply_text("呜… 只有主人才能生成激活码哦！")
            return

        days = DEFAULT_DURATION_DAYS
        count = 1
        if context.args:
            try:
                days = int(context.args[0])
                if days <= 0:
                    days = DEFAULT_DURATION_DAYS
            except:
                pass
        if len(context.args) > 1:
            try:
                count = int(context.args[1])
                if count <= 0:
                    count = 1
                if count > 50:
                    count = 50
            except:
                pass

        generated_codes = []
        for _ in range(count):
            code = _generate_code()
            self._data["codes"].append({
                "code": code,
                "created_at": datetime.now().isoformat(),
                "created_by": update.effective_user.id,
                "used": False,
                "used_by": None,
                "used_at": None,
                "duration_days": days,
                "revoked": False
            })
            generated_codes.append(code)
        self._save()

        if count == 1:
            await update.message.reply_text(
                f"✅ 已生成激活码~\n\n"
                f"🎫 激活码：`{code}`\n"
                f"📅 有效期：{days} 天\n\n"
                f"把这个激活码发给小可爱，让他们用 /redeem {code} 兑换吧！\n\n"
                f"查看所有激活码：/codes\n"
                f"私聊发送给用户：/send_code <用户ID> {days}",
                parse_mode="Markdown"
            )
            logger.info(f"💰 主人生成了激活码 {code}（{days}天）")
        else:
            codes_text = "\n".join([f"• `{c}`" for c in generated_codes])
            await update.message.reply_text(
                f"✅ 已生成 {count} 个激活码~\n\n"
                f"📅 每个有效期：{days} 天\n\n"
                f"{codes_text}\n\n"
                f"💡 私聊发送：/send_code <用户ID> {days}",
                parse_mode="Markdown"
            )
            logger.info(f"💰 主人批量生成了 {count} 个激活码（{days}天）")

    async def codes_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/codes - 查看所有激活码列表（主人专属）~"""
        if not self.dm.is_owner(update.effective_user.id):
            await update.message.reply_text("呜… 只有主人才能查看激活码列表哦！")
            return

        all_codes = self._data.get("codes", [])
        if not all_codes:
            await update.message.reply_text("📋 还没有生成过激活码哦~\n用 /gencode 或 /send_code 生成吧！")
            return

        total = len(all_codes)
        used = sum(1 for c in all_codes if c.get("used"))
        unused = sum(1 for c in all_codes if not c.get("used") and not c.get("revoked"))
        revoked = sum(1 for c in all_codes if c.get("revoked"))

        msg = (
            f"📋 激活码统计~\n\n"
            f"总计：{total} 个\n"
            f"✅ 未使用：{unused} 个\n"
            f"✔️ 已使用：{used} 个\n"
            f"❌ 已撤销：{revoked} 个\n\n"
        )

        recent = all_codes[-20:]
        msg += f"最近 {len(recent)} 个激活码：\n"
        for c in reversed(recent):
            status = "✅" if c.get("used") else ("❌" if c.get("revoked") else "🟢")
            user_info = f"→ 用户 {c.get('used_by', '?')}" if c.get("used") else ""
            msg += f"{status} `{c['code']}` ({c.get('duration_days', 30)}天) {user_info}\n"

        msg += "\n💡 /revoke <激活码> - 撤销\n💡 /send_code <用户ID> [天数] - 私聊发码"
        await update.message.reply_text(msg, parse_mode="Markdown")

    async def revoke_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/revoke <激活码> - 撤销激活码（主人专属）~"""
        if not self.dm.is_owner(update.effective_user.id):
            await update.message.reply_text("呜… 只有主人才能撤销激活码哦！")
            return
        if not context.args:
            await update.message.reply_text("💡 用法：/revoke <激活码>")
            return

        code = context.args[0].strip().upper()
        found = None
        for i, c in enumerate(self._data.get("codes", [])):
            if c["code"] == code:
                found = i
                break

        if found is None:
            await update.message.reply_text("❌ 找不到这个激活码哦~")
            return

        code_data = self._data["codes"][found]
        if code_data.get("revoked"):
            await update.message.reply_text("😅 这个激活码已经被撤销过啦~")
            return
        if code_data.get("used"):
            keyboard = [[
                InlineKeyboardButton("✅ 确认撤销", callback_data=f"paid_revoke_confirm_{code}"),
                InlineKeyboardButton("❌ 取消", callback_data="paid_revoke_cancel")
            ]]
            await update.message.reply_text(
                f"⚠️ 这个激活码已被使用！强行撤销不会影响已用用户，但会标记无效。确认吗？",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return

        self._data["codes"][found]["revoked"] = True
        self._save()
        await update.message.reply_text(f"✅ 已撤销激活码 {code}~")
        logger.info(f"💰 主人撤销了激活码 {code}")

    async def paid_users_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/paid_users - 查看付费用户列表（主人专属）~"""
        if not self.dm.is_owner(update.effective_user.id):
            await update.message.reply_text("呜… 只有主人才能查看付费用户列表哦！")
            return

        paid_users = self._data.get("paid_users", {})
        if not paid_users:
            await update.message.reply_text("📋 还没有付费用户哦~\n用 /gencode 或 /buy 上架商品吸引用户吧！")
            return

        now = datetime.now()
        active = 0
        expired = 0
        msg = f"📋 付费用户列表（共 {len(paid_users)} 人）~\n\n"

        for user_key, info in sorted(paid_users.items(), key=lambda x: x[1].get("activated_at", ""), reverse=True):
            user_id = int(user_key)
            expires_str = info.get("expires_at", "")
            try:
                expires_at = datetime.fromisoformat(expires_str)
                remaining = expires_at - now
                if remaining.days < 0:
                    status = "❌ 已过期"
                    expired += 1
                elif remaining.days <= 3:
                    status = f"⚠️ {remaining.days}天后到期"
                    active += 1
                else:
                    status = f"✅ {remaining.days}天"
                    active += 1
            except:
                status = "❓ 未知"
                expired += 1
            msg += f"👤 {user_id} | {status} | 码: {info.get('code', '?')}\n"

        msg += f"\n📊 活跃：{active} 人 | 过期：{expired} 人\n"
        msg += "\n清理过期用户：/clean_expired"
        await update.message.reply_text(msg[:4000])

    async def clean_expired_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/clean_expired - 手动清理已过期的付费用户（主人专属）~"""
        if not self.dm.is_owner(update.effective_user.id):
            await update.message.reply_text("呜… 只有主人才能清理过期用户哦！")
            return
        expired = self._clean_expired_users()
        if expired:
            await update.message.reply_text(f"✅ 已清理 {len(expired)} 个过期用户~\n移除的用户ID：{', '.join(str(uid) for uid in expired)}")
        else:
            await update.message.reply_text("🎉 目前没有过期的付费用户哦~")

    # ──────────────────────────────────────────
    #  商品管理（主人专属）
    # ──────────────────────────────────────────

    async def add_product_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/add_product <ID> <名称> <价格> <天数> [描述] - 添加/修改商品（主人专属）~"""
        if not self.dm.is_owner(update.effective_user.id):
            await update.message.reply_text("呜… 只有主人才能管理商品哦！")
            return

        if not context.args or len(context.args) < 4:
            await update.message.reply_text(
                "💡 用法：/add_product <ID> <名称> <价格> <天数> [描述]\n\n"
                "参数说明：\n"
                "• ID：商品唯一标识（英文，如 monthly）\n"
                "• 名称：商品显示名称（如 月度会员）\n"
                "• 价格：显示价格（如 9.99）\n"
                "• 天数：有效期天数\n"
                "• 描述：商品简要说明（可选）\n\n"
                "示例：/add_product monthly 月度会员 9.99 30 30天畅享小南陪伴"
            )
            return

        pid = context.args[0]
        name = context.args[1]
        price = context.args[2]
        try:
            days = int(context.args[3])
        except:
            await update.message.reply_text("😅 天数要是数字哦！")
            return
        description = " ".join(context.args[4:]) if len(context.args) > 4 else ""

        products = self._products.get("products", [])
        found = None
        for i, p in enumerate(products):
            if p["id"] == pid:
                found = i
                break

        if found is not None:
            products[found] = {
                "id": pid, "name": name, "price": price,
                "duration_days": days, "description": description, "enabled": True
            }
            self._products["products"] = products
            self._save_products_data()
            await update.message.reply_text(f"✅ 商品 '{name}' 已更新~")
        else:
            products.append({
                "id": pid, "name": name, "price": price,
                "duration_days": days, "description": description, "enabled": True
            })
            self._products["products"] = products
            self._save_products_data()
            await update.message.reply_text(f"✅ 商品 '{name}' 已添加~\n用户现在可以用 /buy 查看了哦！")

        logger.info(f"💰 主人 {'更新' if found is not None else '添加'}了商品: {pid}")

    async def del_product_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/del_product <商品ID> - 删除商品（主人专属）~"""
        if not self.dm.is_owner(update.effective_user.id):
            await update.message.reply_text("呜… 只有主人才能管理商品哦！")
            return
        if not context.args:
            await update.message.reply_text("💡 用法：/del_product <商品ID>\n先用 /products 查看商品ID~")
            return

        pid = context.args[0]
        products = self._products.get("products", [])
        found = None
        for i, p in enumerate(products):
            if p["id"] == pid:
                found = i
                break

        if found is None:
            await update.message.reply_text(f"❌ 找不到商品 '{pid}' 哦~\n用 /products 查看所有商品")
            return

        del products[found]
        self._products["products"] = products
        self._save_products_data()
        await update.message.reply_text(f"✅ 商品 '{pid}' 已删除~")
        logger.info(f"💰 主人删除了商品: {pid}")

    async def products_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/products - 查看所有商品（主人专属）~"""
        if not self.dm.is_owner(update.effective_user.id):
            await update.message.reply_text("呜… 只有主人才能查看商品管理哦！")
            return

        products = self._products.get("products", [])
        if not products:
            await update.message.reply_text(
                "📋 还没有上架任何商品哦~\n"
                "用 /add_product 添加商品吧！\n\n"
                "示例：/add_product monthly 月度会员 9.99 30 30天畅享小南陪伴"
            )
            return

        msg = "📋 **商品管理列表~**\n\n"
        for p in products:
            status = "🟢 上架中" if p.get("enabled", True) else "🔴 已下架"
            msg += (
                f"**{p['name']}**\n"
                f"  ID：{p['id']}\n"
                f"  价格：{p.get('price_display', p['price'])}\n"
                f"  天数：{p['duration_days']} 天\n"
                f"  描述：{p.get('description', '无')}\n"
                f"  状态：{status}\n\n"
            )

        msg += "管理命令：\n"
        msg += "/add_product - 添加/修改商品\n"
        msg += "/del_product <ID> - 删除商品"

        await update.message.reply_text(msg, parse_mode="Markdown")

    # ──────────────────────────────────────────
    #  按钮回调
    # ──────────────────────────────────────────

    async def callback_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        data = query.data

        if data == "paid_revoke_cancel":
            await query.edit_message_text("✅ 已取消撤销操作~")
            return

        if data.startswith("paid_revoke_confirm_"):
            code = data.replace("paid_revoke_confirm_", "")
            found = None
            for i, c in enumerate(self._data.get("codes", [])):
                if c["code"] == code:
                    found = i
                    break
            if found is not None:
                self._data["codes"][found]["revoked"] = True
                self._save()
                await query.edit_message_text(f"✅ 已强行撤销激活码 {code}~\n已使用的用户不受影响。")
                logger.info(f"💰 主人强行撤销了已使用的激活码 {code}")
            else:
                await query.edit_message_text("❌ 找不到这个激活码啦~")
            return

        if data.startswith("paid_buy_"):
            pid = data.replace("paid_buy_", "")
            products = self._products.get("products", [])
            prod = None
            for p in products:
                if p["id"] == pid and p.get("enabled", True):
                    prod = p
                    break

            if not prod:
                await query.edit_message_text("❌ 这个商品已经下架了哦~ 用 /buy 查看最新商品！")
                return

            price = prod.get("price_display", f"{prod['price']} 元")
            name = prod["name"]
            days = prod["duration_days"]

            await query.edit_message_text(
                f"🛒 **{name}** — {price}\n\n"
                f"📅 有效期：{days} 天\n"
                f"📝 说明：{prod.get('description', '无')}\n\n"
                f"━━━━━━━━━━━━━━━━━━\n\n"
                f"💳 **付款方式**\n\n"
                f"请转账到以下账户，付款后自动发货~\n\n"
                f"🏦 **支付宝**\n"
                f"账号：`你的支付宝账号@这里`\n\n"
                f"💴 **微信支付**\n"
                f"扫码支付：联系主人获取收款码~\n\n"
                f"━━━━━━━━━━━━━━━━━━\n\n"
                f"✅ **付款后请等待几秒**，机器人会自动检测到付款\n"
                f"激活码会自动私聊发送给你哦！\n\n"
                f"💡 如果长时间没收到，请联系主人确认~",
                parse_mode="Markdown"
            )
            return

    # ──────────────────────────────────────────
    #  回调 Web 服务器（嵌入运行）
    # ──────────────────────────────────────────

    @staticmethod
    async def _callback_handler(request):
        """处理发卡平台的回调通知~"""
        try:
            body = await request.json()
        except:
            return web.json_response({"code": 1, "message": "无效的 JSON"}, status=400)

        # 验证密钥
        secret = body.get("secret", "")
        if secret != CALLBACK_SECRET:
            logger.warning(f"⚠️ 回调密钥错误: {secret}")
            return web.json_response({"code": 1, "message": "密钥错误"}, status=403)

        # 必须参数
        product_id = body.get("product_id", "")
        user_id = body.get("user_id", 0)
        order_id = body.get("order_id", "")
        status = body.get("status", "")

        if not product_id or not user_id or not order_id:
            return web.json_response({"code": 1, "message": "缺少必要参数"}, status=400)

        logger.info(f"📩 收到回调: 商品={product_id}, 用户={user_id}, 订单={order_id}, 状态={status}")

        # 只处理成功状态
        if status != "completed":
            logger.info(f"⏭️ 忽略非成功状态: {status}")
            return web.json_response({"code": 0, "message": "收到，但不处理非成功状态"})

        # 读取最新数据
        data = _load_paid_data()
        products = _load_products()

        # 查找商品
        prod = None
        for p in products.get("products", []):
            if p["id"] == product_id:
                prod = p
                break

        if not prod:
            logger.warning(f"⚠️ 商品 {product_id} 不存在")
            return web.json_response({"code": 1, "message": "商品不存在"}, status=404)

        duration_days = prod.get("duration_days", DEFAULT_DURATION_DAYS)

        # 检查用户是否已经通过此订单兑换过（防止重复回调）
        for code_entry in data.get("codes", []):
            if code_entry.get("order_id") == order_id:
                logger.info(f"⏭️ 订单 {order_id} 已处理过，跳过")
                return web.json_response({"code": 0, "message": "订单已处理"})

        # 生成激活码
        code = _generate_code()
        activated_at = datetime.now()
        expires_at = activated_at + timedelta(days=duration_days)

        # 添加到激活码列表
        if "codes" not in data:
            data["codes"] = []
        data["codes"].append({
            "code": code,
            "created_at": activated_at.isoformat(),
            "created_by": 0,  # 系统自动生成
            "used": True,
            "used_by": user_id,
            "used_at": activated_at.isoformat(),
            "duration_days": duration_days,
            "revoked": False,
            "order_id": order_id,
            "product_id": product_id
        })

        # 记录付费用户
        if "paid_users" not in data:
            data["paid_users"] = {}
        user_key = str(user_id)
        data["paid_users"][user_key] = {
            "activated_at": activated_at.isoformat(),
            "expires_at": expires_at.isoformat(),
            "code": code,
            "duration_days": duration_days,
            "order_id": order_id,
            "product_id": product_id
        }
        _save_paid_data(data)

        # 加入白名单
        dm = DataManager()
        dm.add_user(int(user_id))

        logger.info(f"💰 回调自动发码成功: 用户 {user_id}, 商品 {product_id}, 码 {code}, 有效期 {duration_days}天")

        # 私聊通知用户
        try:
            if PaidWhitelist._application:
                bot = PaidWhitelist._application.bot
                await bot.send_message(
                    chat_id=int(user_id),
                    text=(
                        f"🎉 **付款成功！自动发货~**\n\n"
                        f"感谢购买 **{prod.get('name', product_id)}**！\n\n"
                        f"🎫 你的激活码：`{code}`\n"
                        f"📅 有效期：{duration_days} 天\n"
                        f"⏰ 到期时间：{expires_at.strftime('%Y年%m月%d日 %H:%M')}\n\n"
                        f"现在可以用 /redeem {code} 激活啦！\n"
                        f"激活后就能和我聊天了哦~ 喵呜！(｡♥‿♥｡)"
                    ),
                    parse_mode="Markdown"
                )
        except Exception as e:
            logger.error(f"回调后私聊通知用户 {user_id} 失败: {e}")

        return web.json_response({"code": 0, "message": "success"})

    @staticmethod
    async def _health_handler(request):
        """健康检查~"""
        return web.json_response({"status": "ok", "service": "小南TGbot回调服务"})

    def start_callback_server(self):
        """启动回调 HTTP 服务器（异步事件循环中运行）~"""
        if not HAS_AIOHTTP:
            logger.warning("⚠️ 未安装 aiohttp，回调服务器无法启动。请执行: pip install aiohttp")
            return

        app = web.Application()
        app.router.add_post("/callback", self._callback_handler)
        app.router.add_get("/health", self._health_handler)

        runner = web.AppRunner(app)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def start():
            await runner.setup()
            site = web.TCPSite(runner, CALLBACK_HOST, CALLBACK_PORT)
            await site.start()
            logger.info(f"🌐 回调服务器已启动: http://{CALLBACK_HOST}:{CALLBACK_PORT}/callback")
            logger.info(f"🔑 回调密钥（请配置到发卡平台）: {CALLBACK_SECRET}")
            # 保持运行
            await asyncio.Event().wait()

        def run():
            loop.run_until_complete(start())

        thread = threading.Thread(target=run, daemon=True, name="callback-server")
        thread.start()
        logger.info(f"🧵 回调服务器线程已启动 (端口 {CALLBACK_PORT})")

    # ──────────────────────────────────────────
    #  帮助文本
    # ──────────────────────────────────────────

    def get_help_text(self) -> str:
        return (
            "/buy - 查看商品并获取购买方式~\n"
            "/redeem <激活码> - 兑换激活码加入白名单~\n"
            "/check_expiry - 查看有效期~"
        )


# ===== 启动时自动清理过期用户 =====
def auto_cleanup():
    try:
        dm = DataManager()
        data = _load_paid_data()
        paid_users = data.get("paid_users", {})
        now = datetime.now()
        cleaned = 0
        for user_key, info in paid_users.items():
            expires_str = info.get("expires_at")
            if expires_str:
                try:
                    expires_at = datetime.fromisoformat(expires_str)
                    if now > expires_at:
                        dm.del_user(int(user_key))
                        cleaned += 1
                except:
                    pass
        if cleaned > 0:
            logger.info(f"⏰ 启动时自动清理了 {cleaned} 个过期付费用户")
    except Exception as e:
        logger.error(f"自动清理过期用户失败: {e}")
