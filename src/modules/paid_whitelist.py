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

from config import PAID_WHITELIST_FILE, PRODUCTS_FILE, CALLBACK_HOST, CALLBACK_PORT, CALLBACK_SECRET
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


def _quarantine_broken_file(path: str):
    """读不出来的数据文件先改名留档，免得下一次保存把它彻底覆盖掉~"""
    try:
        broken = f"{path}.broken-{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        os.replace(path, broken)
        logger.warning(f"⚠️ 数据文件无法解析，已备份到 {broken}（请人工检查）")
    except Exception as e:
        logger.error(f"备份损坏的数据文件失败: {e}")


# 主线程（命令）和回调服务器线程都会写这两个 JSON，串行化避免互相踩踏~
_SAVE_LOCK = threading.Lock()


def _write_json_atomic(path: str, data: dict):
    """原子写 JSON：先写临时文件再整体替换，避免中途崩溃留下半个文件~"""
    parent = os.path.dirname(path)
    with _SAVE_LOCK:
        if parent:
            os.makedirs(parent, exist_ok=True)
        tmp_path = f"{path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)


def _load_paid_data() -> dict:
    """加载付费白名单数据~"""
    if os.path.exists(PAID_WHITELIST_FILE):
        try:
            with open(PAID_WHITELIST_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                # 先补齐缺失字段，再校验容器类型：手改成列表/字符串时重置，
                # 免得后面的 .append / .get 直接把命令炸掉
                if not isinstance(data.setdefault("codes", []), list):
                    logger.warning("⚠️ 付费白名单数据里的 codes 不是列表，已重置为空")
                    data["codes"] = []
                if not isinstance(data.setdefault("paid_users", {}), dict):
                    logger.warning("⚠️ 付费白名单数据里的 paid_users 不是对象，已重置为空")
                    data["paid_users"] = {}
                return data
            logger.error(f"付费白名单数据格式不对（顶层应为对象）: {type(data).__name__}")
        except Exception as e:
            logger.error(f"加载付费白名单数据失败: {e}")
        _quarantine_broken_file(PAID_WHITELIST_FILE)
    return {"codes": [], "paid_users": {}}


def _save_paid_data(data: dict):
    """保存付费白名单数据~"""
    try:
        _write_json_atomic(PAID_WHITELIST_FILE, data)
        return True
    except Exception as e:
        logger.error(f"保存付费白名单数据失败: {e}")
        return False


def _normalise_products(data: dict) -> dict:
    """补齐商品条目的默认字段：手改 products.json 少了 name/price 也不能让列表挂掉~"""
    raw = data.get("products")
    if not isinstance(raw, list):
        if raw is not None:
            logger.warning("⚠️ 商品配置里的 products 不是列表，已按空列表处理")
        data["products"] = []
        return data

    products = []
    for idx, prod in enumerate(raw):
        if not isinstance(prod, dict):
            logger.warning(f"⚠️ 商品配置里第 {idx + 1} 项不是对象，已跳过")
            continue
        prod = dict(prod)
        if not prod.get("id"):
            prod["id"] = f"product_{idx + 1}"
        if not prod.get("name"):
            prod["name"] = f"商品 {prod['id']}"
        prod.setdefault("duration_days", DEFAULT_DURATION_DAYS)
        prod.setdefault("description", "")
        prod.setdefault("enabled", True)
        products.append(prod)
    data["products"] = products
    return data


def _load_products() -> dict:
    """加载商品配置~"""
    if os.path.exists(PRODUCTS_FILE):
        try:
            with open(PRODUCTS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return _normalise_products(data)
            logger.error(f"商品配置格式不对（顶层应为对象）: {type(data).__name__}")
        except Exception as e:
            logger.error(f"加载商品配置失败: {e}")
        _quarantine_broken_file(PRODUCTS_FILE)
    return {"products": []}


def _save_products(data: dict):
    """保存商品配置~"""
    try:
        _write_json_atomic(PRODUCTS_FILE, data)
        return True
    except Exception as e:
        logger.error(f"保存商品配置失败: {e}")
        return False


def _price_text(prod) -> str:
    """安全取价格文案：商品缺 price / price_display 时也不能把 /buy 弄炸~"""
    if not isinstance(prod, dict):
        return "价格未设置"
    price_display = prod.get("price_display")
    if price_display not in (None, ""):
        return str(price_display)
    price = prod.get("price")
    if price not in (None, ""):
        return f"{price} 元"
    return "价格未设置"


def _parse_user_id(user_key) -> Optional[int]:
    """把 paid_users 的键转成 int；非数字键跳过并记日志，别让整条命令跟着炸~"""
    try:
        return int(user_key)
    except (TypeError, ValueError):
        logger.warning(f"⚠️ paid_users 里有非数字的用户键 {user_key!r}，已跳过（请手动检查数据文件）")
        return None


def _activated_sort_key(item) -> str:
    """按激活时间倒序排付费用户~

    坏记录（值是 null / 字符串）直接排在最后，不能在这里抛 AttributeError，
    否则 /paid_users 会因为一条脏数据整个用不了。
    """
    value = item[1] if isinstance(item, tuple) and len(item) == 2 else None
    if isinstance(value, dict):
        activated = value.get("activated_at")
        if isinstance(activated, str):
            return activated
    return ""


def _safe_days(value, default: int = 0) -> int:
    """把 duration_days 转成 int~

    products.json / 激活码里手写成 "30 天" 这种字符串时，timedelta(days=...)
    会抛 TypeError，把整个购买/兑换流程打断。转换失败按 0 天处理（等于没加时长），
    并记日志提醒去检查数据，而不是凭空多送几天。
    """
    try:
        return int(value)
    except (TypeError, ValueError):
        logger.warning(f"⚠️ 时长字段不是数字：{value!r}，按 0 天处理（请检查数据文件）")
        return default


def _extend_expiry(existing, duration_days: int, now: Optional[datetime] = None) -> datetime:
    """算新的到期时间：还在有效期内就在原到期时间上叠加天数，过期/没记录就从现在算~"""
    now = now or datetime.now()
    base = now
    if isinstance(existing, dict):
        expires_str = existing.get("expires_at")
        if expires_str:
            try:
                old_expiry = datetime.fromisoformat(expires_str)
                if old_expiry > now:
                    base = old_expiry
            except (TypeError, ValueError):
                pass
    return base + timedelta(days=_safe_days(duration_days))


def _prune_expired_users(data: dict, dm: "DataManager") -> list:
    """清理过期付费用户（启动清理和 /clean_expired 共用这一套逻辑）~

    返回被清理的用户ID列表；非数字键跳过并记日志，单条删失败也不影响其它记录~
    """
    paid_users = data.get("paid_users")
    if not isinstance(paid_users, dict):
        logger.warning("⚠️ 付费白名单数据里的 paid_users 不是对象，跳过过期清理")
        return []

    now = datetime.now()
    expired = []
    for user_key, info in list(paid_users.items()):
        if not isinstance(info, dict):
            logger.warning(f"⚠️ 付费用户 {user_key!r} 的记录不是对象，已跳过")
            continue
        expires_str = info.get("expires_at")
        if not expires_str:
            continue
        try:
            is_expired = now > datetime.fromisoformat(expires_str)
        except (TypeError, ValueError):
            # 到期时间读不出来的记录按过期处理，否则会永远卡在文件里清不掉
            is_expired = True
        if not is_expired:
            continue
        user_id = _parse_user_id(user_key)
        if user_id is None:
            continue
        expired.append((user_key, user_id))

    cleaned = []
    for user_key, user_id in expired:
        try:
            dm.del_user(user_id)
        except Exception as e:
            # 白名单没删干净就先保留记录，下次清理再试，避免两边数据对不上
            logger.error(f"移除付费用户 {user_id} 的白名单失败，本次跳过: {e}")
            continue
        paid_users.pop(user_key, None)
        cleaned.append(user_id)
        logger.info(f"⏰ 付费用户 {user_id} 已过期，已自动从白名单移除")

    if cleaned:
        data["paid_users"] = paid_users
        _save_paid_data(data)
    return cleaned


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
        record = self._data.get("paid_users", {}).get(user_key)
        # 手改 / 老格式的 paid_users 里可能存着 null 或字符串，
        # 直接 .get 会 AttributeError，把 /redeem、/check_expiry 一起带崩
        if isinstance(record, dict):
            expires_str = record.get("expires_at")
            if expires_str:
                try:
                    return datetime.fromisoformat(expires_str)
                except (TypeError, ValueError):
                    pass
        return None

    def _is_user_expired(self, user_id: int) -> bool:
        expires_at = self._get_user_expiry(user_id)
        if expires_at is None:
            return False
        return datetime.now() > expires_at

    def _clean_expired_users(self):
        """清理过期付费用户~（与启动清理共用 _prune_expired_users 同一套逻辑）"""
        return _prune_expired_users(self._data, self.dm)

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

        # 启动时清理已过期的付费用户（和 /clean_expired 走同一套逻辑，过期记录不会留在文件里）
        auto_cleanup(self)

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
            price = _price_text(prod)
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

        self._data["codes"][found]["used"] = True
        self._data["codes"][found]["used_by"] = user_id
        self._data["codes"][found]["used_at"] = activated_at.isoformat()

        user_key = str(user_id)
        # /redeem 一般会拒绝未过期的用户，但白名单和付费记录不同步时（比如白名单被手动删掉）
        # 还是会走到这里，同样要叠加剩余天数，不能把剩下的时间清零
        existing = self._data.get("paid_users", {}).get(user_key)
        expires_at = _extend_expiry(existing, duration_days, activated_at)
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
                "⚠️ 这个激活码已被使用！强行撤销不会影响已用用户，但会标记无效。确认吗？",
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

        for user_key, info in sorted(paid_users.items(), key=_activated_sort_key, reverse=True):
            user_id = _parse_user_id(user_key)
            if user_id is None:
                continue
            # info 在坏数据里可能是 null / 字符串，统一先规整成 dict 再取字段
            if not isinstance(info, dict):
                info = {}
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
                f"  价格：{_price_text(p)}\n"
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
            # 确认按钮可能出现在群里/被转发，点的人不一定是主人，这里必须重新校验
            if not self.dm.is_owner(update.effective_user.id):
                await query.edit_message_text("呜… 只有主人才能撤销激活码哦！")
                return
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

            price = _price_text(prod)
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

        # user_id 必须能转成数字：以前是先把购买记录写进 JSON、再在
        # dm.add_user(int(user_id)) 时才炸，结果"钱付了、订单存了、白名单没加上"，
        # 而且平台只收到 500。现在在写任何数据之前就挡掉。
        try:
            user_id = int(user_id)
        except (TypeError, ValueError):
            logger.warning(f"⚠️ 回调里的 user_id 不是数字：{user_id!r}，已拒绝")
            return web.json_response({"code": 1, "message": "user_id 必须是数字"}, status=400)

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

        # 记录付费用户（续费时在原到期时间上叠加，不能把剩余天数清零~）
        if "paid_users" not in data:
            data["paid_users"] = {}
        user_key = str(user_id)
        expires_at = _extend_expiry(data["paid_users"].get(user_key), duration_days, activated_at)
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

        # 安全闸门：密钥没配就跑回调服务 = 任何人都能伪造"支付成功"白拿激活码
        from config import DISABLE_CALLBACK_SERVER_IF_UNSET
        if CALLBACK_SECRET in ("", "CHANGE_ME_TO_A_RANDOM_SECRET") and DISABLE_CALLBACK_SERVER_IF_UNSET:
            logger.warning(
                "🔒 回调服务器未启动：CALLBACK_SECRET 还是占位值\n"
                "   ├─ 原因：该密钥是回调接口的唯一凭据，用默认值等于没有防护\n"
                "   ├─ 风险：任何人 POST 一个 completed 回调就能给自己发激活码\n"
                "   └─ 解决：在 config.py 里把 CALLBACK_SECRET 改成一串随机字符"
            )
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
def auto_cleanup(module=None):
    """启动时清理过期付费用户~（传入模块实例就清理它内存里的数据，和 /clean_expired 共用一套逻辑）"""
    try:
        dm = DataManager()
        data = module._data if module is not None else _load_paid_data()
        cleaned = _prune_expired_users(data, dm)
        if cleaned:
            logger.info(f"⏰ 启动时自动清理了 {len(cleaned)} 个过期付费用户")
    except Exception as e:
        logger.error(f"自动清理过期用户失败: {e}")
