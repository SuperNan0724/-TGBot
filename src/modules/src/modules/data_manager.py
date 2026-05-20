"""
数据管理模块~ 负责管理所有小数据！(｡･ω･｡)ﾉ♡
"""
import json
import os
import shutil
import logging
from datetime import datetime
from typing import Optional, Any

from config import (
    WHITELIST_FILE, ADMIN_FILE, USER_DATA_FILE, 
    ERROR_LOG_FILE, BACKUP_DIR, DATA_DIR
)

logger = logging.getLogger(__name__)


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
        try:
            if os.path.exists(filepath):
                with open(filepath, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"加载 {filepath} 失败啦: {e}")
        return default
    
    def _save_json(self, filepath: str, data: Any):
        """保存 JSON 文件~"""
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
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
    
    def add_user(self, user_id: int) -> bool:
        """添加用户到白名单~"""
        if user_id not in self._data_cache["whitelist"]["users"]:
            self._data_cache["whitelist"]["users"].append(user_id)
            self._save_json(WHITELIST_FILE, self._data_cache["whitelist"])
            return True
        return False
    
    def add_group(self, group_id: int) -> bool:
        """添加群组到白名单~"""
        if group_id not in self._data_cache["whitelist"]["groups"]:
            self._data_cache["whitelist"]["groups"].append(group_id)
            self._save_json(WHITELIST_FILE, self._data_cache["whitelist"])
            return True
        return False
    
    def del_user(self, user_id: int) -> bool:
        """从白名单移除用户~"""
        if user_id in self._data_cache["whitelist"]["users"]:
            self._data_cache["whitelist"]["users"].remove(user_id)
            # 同时移除管理员身份
            self.del_admin(user_id)
            self._save_json(WHITELIST_FILE, self._data_cache["whitelist"])
            return True
        return False
    
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
    
    def add_admin(self, user_id: int) -> bool:
        """添加管理员~"""
        if user_id not in self._data_cache["admins"]["admins"]:
            self._data_cache["admins"]["admins"].append(user_id)
            self._save_json(ADMIN_FILE, self._data_cache["admins"])
            return True
        return False
    
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
    
    def get_user_data(self, user_id: int) -> dict:
        """获取用户数据~"""
        user_id_str = str(user_id)
        if user_id_str not in self._data_cache["user_data"]:
            self._data_cache["user_data"][user_id_str] = {
                "personality": "default",
                "history": [],
                "created_at": datetime.now().isoformat(),
                "last_active": datetime.now().isoformat()
            }
        return self._data_cache["user_data"][user_id_str]
    
    def save_user_data(self, user_id: int, data: dict):
        """保存用户数据~"""
        self._data_cache["user_data"][str(user_id)] = data
        self._save_json(USER_DATA_FILE, self._data_cache["user_data"])
    
    def delete_user_data(self, user_id: int) -> bool:
        """删除用户所有数据~"""
        user_id_str = str(user_id)
        if user_id_str in self._data_cache["user_data"]:
            del self._data_cache["user_data"][user_id_str]
            self._save_json(USER_DATA_FILE, self._data_cache["user_data"])
            return True
        return False
    
    def delete_user_history(self, user_id: int) -> bool:
        """删除用户对话历史~"""
        user_id_str = str(user_id)
        if user_id_str in self._data_cache["user_data"]:
            self._data_cache["user_data"][user_id_str]["history"] = []
            self._save_json(USER_DATA_FILE, self._data_cache["user_data"])
            return True
        return False
    
    def get_all_user_data(self) -> dict:
        """获取所有用户数据~"""
        return self._data_cache["user_data"]
    
    # ===== 错误日志管理 =====
    
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
    
    def clean_errors(self):
        """清除错误日志~"""
        self._data_cache["errors"]["errors"] = []
        self._save_json(ERROR_LOG_FILE, self._data_cache["errors"])
    
    def export_errors(self) -> str:
        """导出错误日志~"""
        return json.dumps(self._data_cache["errors"], ensure_ascii=False, indent=2)
    
    # ===== 备份管理 =====
    
    def backup_data(self) -> Optional[str]:
        """备份所有数据~"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = os.path.join(BACKUP_DIR, f"backup_{timestamp}.json")
            
            backup_data = {
                "timestamp": timestamp,
                "data": self._data_cache
            }
            
            with open(backup_file, "w", encoding="utf-8") as f:
                json.dump(backup_data, f, ensure_ascii=False, indent=2)
            
            return backup_file
        except Exception as e:
            logger.error(f"备份失败啦: {e}")
            return None
    
    def get_backup_list(self) -> list:
        """获取备份列表~"""
        backups = []
        if os.path.exists(BACKUP_DIR):
            for f in sorted(os.listdir(BACKUP_DIR), reverse=True):
                if f.endswith(".json"):
                    filepath = os.path.join(BACKUP_DIR, f)
                    size = os.path.getsize(filepath)
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
    
    def reset_logs(self):
        """重置日志~"""
        self._data_cache["errors"]["errors"] = []
        self._save_json(ERROR_LOG_FILE, self._data_cache["errors"])
    
    def reset_data(self):
        """重置所有数据~"""
        self._data_cache = {
            "whitelist": {"users": [], "groups": []},
            "admins": {"admins": []},
            "user_data": {},
            "errors": {"errors": []},
        }
        self._save_all()
    
    def reset_system(self):
        """完全重置系统~"""
        self.reset_data()
        # 删除备份
        if os.path.exists(BACKUP_DIR):
            shutil.rmtree(BACKUP_DIR)
            os.makedirs(BACKUP_DIR, exist_ok=True)
