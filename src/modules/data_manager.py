"""
数据管理模块~ 负责管理所有小数据！(｡･ω･｡)ﾉ♡
"""
import functools
import json
import os
import shutil
import tempfile
import threading
import time
import logging
from datetime import datetime
from typing import Optional, Any

from config import (
    WHITELIST_FILE, ADMIN_FILE, USER_DATA_FILE, 
    ERROR_LOG_FILE, BACKUP_DIR, DATA_DIR
)

logger = logging.getLogger(__name__)

# 备份目录最多保留多少份（超出后从最旧的开始删）
MAX_BACKUPS = 20
# user_data 最多保留多少条用户记录（超出后淘汰最久没活跃的普通用户）
MAX_USER_RECORDS = 5000
# 单个用户的历史条数硬上限：各模块自己也会裁（deepseek 用 MAX_HISTORY_LENGTH），
# 这里是最后一道保险，防止某个模块忘了裁就把 user_data.json 写成无限大
MAX_HISTORY_ENTRIES = 200


def _synchronized(method):
    """给 DataManager 的读写方法加同一把可重入锁~

    主事件循环和别的写盘路径（例如某些模块起的后台线程）会同时操作这个单例：
    以前没有锁，一个线程 json.dump 正在遍历 user_data 时另一个线程
    往里加 key，就会抛 RuntimeError: dictionary changed size during iteration，
    这一次保存整体失败（用户刚说完的话直接没了），日志里只留一行看不出所以然~
    """
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        with self._lock:
            return method(self, *args, **kwargs)
    return wrapper


class DataManager:
    """数据管理器~ 所有数据都归我管！喵！"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        # 锁必须先建：下面的 _ensure_dirs / _load_all_data 都可能被其它线程撞上
        self._lock = threading.RLock()
        self._initialized = True
        self._ensure_dirs()
        self._data_cache = {}
        self._load_all_data()
    
    def _ensure_dirs(self):
        """确保数据目录存在~"""
        os.makedirs(DATA_DIR, exist_ok=True)
        os.makedirs(BACKUP_DIR, exist_ok=True)
    
    def _load_all_data(self):
        """加载所有数据~"""
        self._data_cache = {
            "whitelist": self._load_json(WHITELIST_FILE, {"users": [], "groups": []}),
            "admins": self._load_json(ADMIN_FILE, {"admins": []}),
            "user_data": self._load_json(USER_DATA_FILE, {}),
            "errors": self._load_json(ERROR_LOG_FILE, {"errors": []}),
        }
    
    def _load_json(self, filepath: str, default: Any) -> Any:
        """加载 JSON 文件~"""
        if not os.path.exists(filepath):
            return default
        try:
            # utf-8-sig：记事本另存为「UTF-8 带 BOM」时，json.load 会报
            # Unexpected UTF-8 BOM，整个文件被当成不存在、数据全丢
            with open(filepath, "r", encoding="utf-8-sig") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载 {filepath} 失败啦: {e}")
            # 损坏的文件先改名留底，否则下一次保存会直接把它覆盖掉，
            # 用户的白名单/对话历史就再也找不回来了
            try:
                broken = f"{filepath}.broken-{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                os.replace(filepath, broken)
                logger.error(f"💾 已保留损坏的文件为 {broken}，可手动检查后恢复~")
            except Exception as e2:
                logger.error(f"保留损坏文件失败: {e2}")
        return default

    @_synchronized
    def _save_json(self, filepath: str, data: Any):
        """保存 JSON 文件~（整段持锁：序列化期间别的线程不能改缓存）"""
        try:
            dirname = os.path.dirname(filepath)
            if dirname:
                os.makedirs(dirname, exist_ok=True)
            # 先写同目录下的临时文件，再 os.replace 原子替换：
            # 1) 写到一半崩溃/断电不会把原文件毁掉（旧写法 open("w") 会立刻清空文件）
            # 2) 多个写盘路径可能同时保存，用唯一临时文件
            #    才不会互相踩到对方写了一半的内容
            fd, tmp_path = tempfile.mkstemp(
                dir=dirname or ".", prefix=os.path.basename(filepath) + ".", suffix=".tmp"
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                    f.flush()
                    os.fsync(f.fileno())
                # Windows 上目标文件可能正好被读线程打开着，这时 os.replace
                # 会抛 PermissionError，等一下重试即可
                for attempt in range(5):
                    try:
                        os.replace(tmp_path, filepath)
                        break
                    except PermissionError:
                        if attempt == 4:
                            raise
                        time.sleep(0.05)
            finally:
                if os.path.exists(tmp_path):
                    try:
                        os.remove(tmp_path)
                    except OSError:
                        pass
            return True
        except Exception as e:
            logger.error(f"保存 {filepath} 失败啦: {e}")
            return False
    
    def _save_all(self):
        """保存所有数据~"""
        self._save_json(WHITELIST_FILE, self._data_cache["whitelist"])
        self._save_json(ADMIN_FILE, self._data_cache["admins"])
        self._save_json(USER_DATA_FILE, self._data_cache["user_data"])
        self._save_json(ERROR_LOG_FILE, self._data_cache["errors"])
    
    # ===== 白名单管理 =====
    
    def is_user_whitelisted(self, user_id: int) -> bool:
        """检查用户是否在白名单~"""
        return user_id in self._data_cache["whitelist"]["users"]
    
    def is_group_whitelisted(self, group_id: int) -> bool:
        """检查群组是否在白名单~"""
        return group_id in self._data_cache["whitelist"]["groups"]
    
    @_synchronized
    def add_user(self, user_id: int) -> bool:
        """添加用户到白名单~"""
        if user_id not in self._data_cache["whitelist"]["users"]:
            self._data_cache["whitelist"]["users"].append(user_id)
            self._save_json(WHITELIST_FILE, self._data_cache["whitelist"])
            return True
        return False
    
    @_synchronized
    def add_group(self, group_id: int) -> bool:
        """添加群组到白名单~"""
        if group_id not in self._data_cache["whitelist"]["groups"]:
            self._data_cache["whitelist"]["groups"].append(group_id)
            self._save_json(WHITELIST_FILE, self._data_cache["whitelist"])
            return True
        return False
    
    @_synchronized
    def del_user(self, user_id: int) -> bool:
        """从白名单移除用户~"""
        if user_id in self._data_cache["whitelist"]["users"]:
            self._data_cache["whitelist"]["users"].remove(user_id)
            # 同时移除管理员身份
            self.del_admin(user_id)
            self._save_json(WHITELIST_FILE, self._data_cache["whitelist"])
            return True
        return False
    
    @_synchronized
    def del_group(self, group_id: int) -> bool:
        """从白名单移除群组~"""
        if group_id in self._data_cache["whitelist"]["groups"]:
            self._data_cache["whitelist"]["groups"].remove(group_id)
            self._save_json(WHITELIST_FILE, self._data_cache["whitelist"])
            return True
        return False
    
    def get_whitelist(self) -> dict:
        """获取白名单~"""
        return self._data_cache["whitelist"]
    
    # ===== 管理员管理 =====
    
    def is_admin(self, user_id: int) -> bool:
        """检查是否是管理员~"""
        return user_id in self._data_cache["admins"]["admins"]
    
    def is_owner(self, user_id: int) -> bool:
        """检查是否是主人~"""
        from config import BOT_OWNER_ID
        return BOT_OWNER_ID is not None and user_id == BOT_OWNER_ID
    
    @_synchronized
    def add_admin(self, user_id: int) -> bool:
        """添加管理员~"""
        if user_id not in self._data_cache["admins"]["admins"]:
            self._data_cache["admins"]["admins"].append(user_id)
            self._save_json(ADMIN_FILE, self._data_cache["admins"])
            return True
        return False
    
    @_synchronized
    def del_admin(self, user_id: int) -> bool:
        """删除管理员~"""
        if user_id in self._data_cache["admins"]["admins"]:
            self._data_cache["admins"]["admins"].remove(user_id)
            self._save_json(ADMIN_FILE, self._data_cache["admins"])
            return True
        return False
    
    def get_admins(self) -> list:
        """获取管理员列表~"""
        return self._data_cache["admins"]["admins"]
    
    # ===== 用户数据管理 =====
    
    @_synchronized
    def get_user_data(self, user_id: int) -> dict:
        """获取用户数据~（首次访问会建一条默认记录并加锁）"""
        user_id_str = str(user_id)
        if user_id_str not in self._data_cache["user_data"]:
            self._data_cache["user_data"][user_id_str] = {
                "personality": "default",
                "history": [],
                "created_at": datetime.now().isoformat(),
                "last_active": datetime.now().isoformat()
            }
        return self._data_cache["user_data"][user_id_str]
    
    @_synchronized
    def save_user_data(self, user_id: int, data: dict):
        """保存用户数据~"""
        if not isinstance(data, dict):
            logger.error(f"save_user_data 收到非对象数据（{type(data).__name__}），已忽略~")
            return
        # 每个用户的数据也必须有上限：history 由各模块自己按 MAX_HISTORY_LENGTH 裁，
        # 这里再兜一道，免得哪个模块漏裁就把 user_data.json 越写越大~
        history = data.get("history")
        if isinstance(history, list) and len(history) > MAX_HISTORY_ENTRIES:
            data["history"] = history[-MAX_HISTORY_ENTRIES:]
        self._data_cache["user_data"][str(user_id)] = data
        # 刚写进去的这条必须排除在淘汰之外：超过上限时它可能正好是"最久没活跃"
        # 的那条，一被删，用户正在聊的这份 personality/history 当场回到默认值~
        self._prune_user_data(keep=str(user_id))
        self._save_json(USER_DATA_FILE, self._data_cache["user_data"])
    
    @_synchronized
    def delete_user_data(self, user_id: int) -> bool:
        """删除用户所有数据~"""
        user_id_str = str(user_id)
        if user_id_str in self._data_cache["user_data"]:
            del self._data_cache["user_data"][user_id_str]
            self._save_json(USER_DATA_FILE, self._data_cache["user_data"])
            return True
        return False
    
    @_synchronized
    def delete_user_history(self, user_id: int) -> bool:
        """删除用户对话历史~"""
        user_id_str = str(user_id)
        record = self._data_cache["user_data"].get(user_id_str)
        if isinstance(record, dict):
            record["history"] = []
            self._save_json(USER_DATA_FILE, self._data_cache["user_data"])
            return True
        return False
    
    def get_all_user_data(self) -> dict:
        """获取所有用户数据~"""
        return self._data_cache["user_data"]

    def _prune_user_data(self, keep: Optional[str] = None):
        """user_data 条数超过上限时，淘汰最久没活跃的普通用户记录~

        公开机器人里每个发过消息的人都会留下一条记录（get_user_data 自动创建），
        以前永远不清理：user_data.json 一路变大，而每条消息都要把整份文件重写一遍，
        文件越大保存越慢、写到一半被杀的概率也越高。
        白名单用户 / 管理员 / 主人 的记录一律保留 —— 那才是真正付过钱、不能丢的人~
        keep 是本次正在保存的那条，绝不能淘汰（否则"保存"完的记录当场消失）。
        （调用方已经持锁，这里不再加锁）
        """
        user_data = self._data_cache["user_data"]
        overflow = len(user_data) - MAX_USER_RECORDS
        if overflow <= 0:
            return

        from config import BOT_OWNER_ID
        protected = {str(uid) for uid in self._data_cache["whitelist"]["users"]}
        protected |= {str(uid) for uid in self._data_cache["admins"]["admins"]}
        if BOT_OWNER_ID is not None:
            protected.add(str(BOT_OWNER_ID))

        candidates = [key for key in user_data if key not in protected and key != keep]
        if not candidates:
            return

        def sort_key(key):
            record = user_data.get(key)
            if isinstance(record, dict):
                return str(record.get("last_active") or record.get("created_at") or "")
            return ""

        candidates.sort(key=sort_key)
        removed = 0
        for key in candidates[:overflow]:
            user_data.pop(key, None)
            removed += 1
        if removed:
            logger.warning(
                f"🧹 user_data 超过 {MAX_USER_RECORDS} 条，已淘汰 {removed} 条最久没活跃的普通用户记录"
                f"（白名单/管理员/主人已保留）~"
            )
    
    # ===== 错误日志管理 =====
    
    @_synchronized
    def add_error(self, error_info: dict):
        """添加错误记录~"""
        self._data_cache["errors"]["errors"].append({
            **error_info,
            "timestamp": datetime.now().isoformat()
        })
        # 限制错误日志数量
        if len(self._data_cache["errors"]["errors"]) > 100:
            self._data_cache["errors"]["errors"] = self._data_cache["errors"]["errors"][-100:]
        self._save_json(ERROR_LOG_FILE, self._data_cache["errors"])
    
    def get_errors(self, limit: int = 10) -> list:
        """获取错误日志~"""
        return self._data_cache["errors"]["errors"][-limit:]
    
    @_synchronized
    def clean_errors(self):
        """清除错误日志~"""
        self._data_cache["errors"]["errors"] = []
        self._save_json(ERROR_LOG_FILE, self._data_cache["errors"])
    
    @_synchronized
    def export_errors(self) -> str:
        """导出错误日志~（持锁序列化，避免边序列化边被别的线程写入）"""
        return json.dumps(self._data_cache["errors"], ensure_ascii=False, indent=2)
    
    # ===== 备份管理 =====
    
    @_synchronized
    def backup_data(self) -> Optional[str]:
        """备份所有数据~（原子写 + 自动轮转）"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = os.path.join(BACKUP_DIR, f"backup_{timestamp}.json")

            backup_data = {
                "timestamp": timestamp,
                "data": self._data_cache
            }

            # 改用和正式数据同一套「临时文件 + os.replace」原子写：
            # 以前直接 open("w") 写到一半断电/被杀，备份文件就是半截 JSON，
            # 真出事想拿它恢复时才发现备份本身是坏的~
            if not self._save_json(backup_file, backup_data):
                return None

            self._rotate_backups()
            return backup_file
        except Exception as e:
            logger.error(f"备份失败啦: {e}")
            return None

    def _rotate_backups(self):
        """只保留最近 MAX_BACKUPS 份备份~

        以前只写不删：每天备份一次，一年就是 365 份全量 JSON 躺在 data/backups 里，
        磁盘一路涨。只删 backup_*.json，别把人工放进去的其它 json 一起清掉~
        """
        try:
            names = [
                name for name in os.listdir(BACKUP_DIR)
                if name.startswith("backup_") and name.endswith(".json")
            ]
        except OSError as e:
            logger.warning(f"备份轮转跳过（列目录失败）：{e}")
            return
        if len(names) <= MAX_BACKUPS:
            return
        names.sort()  # 文件名带时间戳，字典序就是时间序
        for name in names[:-MAX_BACKUPS]:
            path = os.path.join(BACKUP_DIR, name)
            try:
                os.remove(path)
                logger.info(f"🧹 备份轮转：已删除最旧的 {name}")
            except OSError as e:
                logger.warning(f"删除旧备份失败 {path}：{e}")

    @_synchronized
    def get_backup_list(self) -> list:
        """获取备份列表~

        listdir 和 getsize 之间有一个窗口：备份刚好被轮转/人工删掉时，
        以前直接抛 FileNotFoundError，连 /stats 的统计都跟着 500。
        现在跳过「已经消失的文件」就好~
        """
        backups = []
        try:
            if not os.path.exists(BACKUP_DIR):
                return backups
            names = sorted(os.listdir(BACKUP_DIR), reverse=True)
        except OSError as e:
            logger.warning(f"读取备份目录失败：{e}")
            return backups
        for f in names:
            if not f.endswith(".json"):
                continue
            filepath = os.path.join(BACKUP_DIR, f)
            try:
                size = os.path.getsize(filepath)
            except OSError:
                # 文件在 listdir 之后被删了，跳过；不能因为一个消失的文件让整张列表挂掉
                continue
            backups.append({"name": f, "size": size, "path": filepath})
        return backups
    
    # ===== 数据统计 =====
    
    def get_stats(self) -> dict:
        """获取数据统计~"""
        return {
            "whitelist_users": len(self._data_cache["whitelist"]["users"]),
            "whitelist_groups": len(self._data_cache["whitelist"]["groups"]),
            "admins": len(self._data_cache["admins"]["admins"]),
            "total_users": len(self._data_cache["user_data"]),
            "total_errors": len(self._data_cache["errors"]["errors"]),
            "backup_count": len(self.get_backup_list())
        }
    
    # ===== 重置功能 =====
    
    @_synchronized
    def reset_logs(self):
        """重置日志~"""
        self._data_cache["errors"]["errors"] = []
        self._save_json(ERROR_LOG_FILE, self._data_cache["errors"])
    
    @_synchronized
    def reset_data(self):
        """重置所有数据~"""
        self._data_cache = {
            "whitelist": {"users": [], "groups": []},
            "admins": {"admins": []},
            "user_data": {},
            "errors": {"errors": []},
        }
        self._save_all()
    
    @_synchronized
    def reset_system(self):
        """完全重置系统~"""
        self.reset_data()
        # 删除备份
        if os.path.exists(BACKUP_DIR):
            shutil.rmtree(BACKUP_DIR)
            os.makedirs(BACKUP_DIR, exist_ok=True)
