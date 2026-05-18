# 🐱 小南专属TGbot

> ✨ **本项目的所有代码均由 AI 编写喵！** ✨
>
> 从第一行代码到最后一行，从功能设计到界面美化，
> 全都是聪明又可爱的 AI 小助手一手包办的哦~
> 所以如果有什么 bug... 那一定是 AI 在卖萌！(｡♥‿♥｡)

一只可可爱爱的 Telegram 机器人，支持 DeepSeek AI 对话~ ✨

## ✨ 功能特色

- 🤖 **AI 对话** - 接入 DeepSeek API，智能聊天，还能切换 40 种性格！
- 🎭 **性格切换** - 可爱猫咪、傲娇、病娇、魔法少女... 总有一款适合你！
- 💭 **记忆功能** - 让小南记住重要信息，越聊越懂你~
- 🎉 **进群欢迎** - 新人加入自动欢迎，40+ 条动态欢迎语不重复，2 分钟自动删除！
- 🎮 **娱乐功能** - 掷骰子、猜拳等小游戏
- 👥 **群聊支持** - @机器人或回复即可触发
- 🎀 **二次元风格** - 粉粉嫩嫩的日志输出，可爱到冒泡~
- 🔄 **自动更新** - 每 12 小时自动检查 GitHub 更新，支持 `/update` 命令手动更新，更新前自动备份，config.py 和 data/ 自动保留~
- 📝 **自定义指令** - 编辑 `src/deploy/commands.txt` 即可添加新指令

## 🚀 快速开始

```bash
# 一行命令启动（自动检测系统）
python start.py
```

启动器会自动：
1. 检测操作系统（Windows/Linux/macOS）
2. 检查项目文件完整性
3. 检测配置是否已填写
4. 提供配置向导（首次使用）
5. 安装依赖并启动机器人

> 💡 **小贴士**：第一次启动时，启动器会贴心地引导你完成配置哦~

## 📝 配置说明

编辑 `src/config.py` 文件，填入以下信息：

| 配置项 | 说明 | 必填 |
|--------|------|------|
| `TELEGRAM_BOT_TOKEN` | 从 @BotFather 获取的 Token | ✅ |
| `DEEPSEEK_API_KEY` | DeepSeek API Key | ❌ |
| `BOT_OWNER_ID` | 你的 Telegram ID | ✅ |
| `BOT_NAME` | 机器人全称 | ❌ |
| `BOT_NAME_SHORT` | 机器人简称（对话中显示的名字） | ❌ |
| `DEFAULT_PERSONALITY` | 默认性格 ID | ❌ |

> ⚠️ **关于网络连接**
>
> 由于 Telegram API 在国内无法直接访问，你需要：
> - **方案一**：使用代理软件（如 Clash、v2ray、SSR 等），开启系统代理或 TUN 模式
> - **方案二**：在服务器上部署（海外服务器无需代理）
> - **方案三**：使用 Docker 部署并配置容器代理
>
> 本项目不内置代理功能，请自行确保网络环境可以访问 Telegram API。

## 🐳 Docker 部署

```bash
# 进入 deploy 目录
cd src/deploy

# 一行命令启动！
docker compose up -d

# 查看日志
docker compose logs -f

# 停止机器人
docker compose down
```

## 📋 指令列表

所有指令在 `src/deploy/commands.txt` 中定义，你可以自由添加/修改：

```
[基础命令]
start - 我是混日子的喵～
help - 查看帮助喵～
chat - 和 AI 聊天喵～
role - 切换小南的性格喵～

[娱乐命令]
dice - 掷骰子喵～
rps - 猜拳喵～
```

## 📁 项目结构

```
小南专属TGbot/
├── README.md               ← 项目说明（从这里开始看！）
├── start.py                ← 跨平台启动器（唯一入口）
├── .gitignore              ← Git 忽略文件（保护隐私~）
├── .dockerignore           ← Docker 忽略文件
├── src/                    ← 调试目录（含配置信息）
│   ├── main.py             ← 主程序入口
│   ├── config.py           ← 配置文件（填入你的 Token/Key/ID）
│   ├── requirements.txt    ← Python 依赖
│   ├── modules/            ← 模块目录
│   │   ├── __init__.py
│   │   ├── base_module.py      # 模块基类
│   │   ├── module_loader.py    # 模块加载器
│   │   ├── data_manager.py     # 数据管理器
│   │   ├── personalities.py    # 40种性格大全！
│   │   ├── deepseek_chat.py    # AI 对话模块
│   │   ├── welcome.py          # 进群欢迎模块
│   │   ├── admin.py            # 管理模块
│   │   ├── help.py             # 帮助模块
│   │   ├── system.py           # 系统状态模块
│   │   ├── fun.py              # 娱乐模块
│   │   ├── auto_updater.py     # 自动更新模块
│   │   └── anime_logger.py     # 二次元日志模块
│   ├── data/              ← 数据文件（自动生成）
│   │   ├── whitelist.json
│   │   ├── admins.json
│   │   ├── user_data.json
│   │   ├── errors.json
│   │   └── backups/
│   └── deploy/            ← 部署文件
│       ├── Dockerfile
│       ├── docker-compose.yml
│       ├── setup.bat
│       ├── setup.sh
│       └── commands.txt
└── source/                ← 源码目录（上传用，不含配置）
    ├── start.py
    ├── README.md
    ├── .gitignore
    ├── .dockerignore
    └── src/
        ├── main.py
        ├── config.py          ← 模板配置（无 Token/Key/ID）
        ├── requirements.txt
        ├── modules/
        └── deploy/
```

## 🧩 模块开发指南 ✨

> 想给小南加新功能？超简单哒！(｡♥‿♥｡)
> 把 `.py` 文件丢进 `src/modules/` 目录就会**自动加载**啦~
> 不需要改任何配置文件，就是这么方便喵！

---

### 📚 基础篇 - 你的第一个模块

#### 第一步：创建文件

在 `src/modules/` 目录下创建一个 `.py` 文件，比如 `my_module.py`~

#### 第二步：写代码

```python
# ✨ src/modules/my_module.py ✨
# 小南的第一个自定义模块~ 喵呜！

from telegram.ext import CommandHandler
from .base_module import BaseModule


class MyModule(BaseModule):
    """我的第一个小模块~ 超可爱！(｡♥‿♥｡)"""
    
    name = "my_module"          # 模块名字（和文件名一样就好~）
    description = "我的自定义模块~"  # 模块描述
    
    def register_handlers(self, application):
        """注册命令处理器~ 告诉小南这个模块能做什么！"""
        # 添加 /hello 命令
        application.add_handler(CommandHandler("hello", self.hello_command))
        
        # 还可以加更多命令哦~
        application.add_handler(CommandHandler("ping", self.ping_command))
    
    async def hello_command(self, update, context):
        """/hello 命令 - 和小南打个招呼~"""
        user_name = update.effective_user.first_name or "小可爱"
        await update.message.reply_text(
            f"你好呀 {user_name}！(｡♥‿♥｡)\n"
            f"我是小南，很高兴认识你~ 喵呜！"
        )
    
    async def ping_command(self, update, context):
        """/ping 命令 - 看看小南在不在~"""
        await update.message.reply_text("🏓 Pong！小南在呢~ 喵！")
    
    def get_help_text(self) -> str:
        """返回帮助文本~ 会在 /help 里显示哦！"""
        return (
            "/hello - 和小南打个招呼喵~\n"
            "/ping - 看看小南在不在~"
        )
```

#### 第三步：重启机器人

```bash
# 重启小南，新模块就自动加载啦！
python start.py
```

#### 第四步：试试看！

在 Telegram 里发送：
- `/hello` → 小南会和你打招呼哦~
- `/ping` → 小南会回复 Pong！
- `/help` → 你的模块也会出现在帮助列表里~

---

### 🎯 进阶篇 - 更多玩法

#### 1️⃣ 带参数的命令

```python
async def greet_command(self, update, context):
    """/greet <名字> - 和小南打招呼~"""
    # 获取命令参数
    args = context.args
    if args:
        name = " ".join(args)
        await update.message.reply_text(f"你好呀 {name}！(｡♥‿♥｡)")
    else:
        await update.message.reply_text("叫我干嘛呀~ 喵？")
```

#### 2️⃣ 使用按钮交互

```python
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler

async def menu_command(self, update, context):
    """/menu - 打开功能菜单~"""
    keyboard = [
        [InlineKeyboardButton("🎮 玩游戏", callback_data="game")],
        [InlineKeyboardButton("🎵 听音乐", callback_data="music")],
        [InlineKeyboardButton("❌ 关闭", callback_data="close")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "想要做什么呀~ 选一个吧！(｡♥‿♥｡)",
        reply_markup=reply_markup
    )

# 别忘了在 register_handlers 里注册按钮回调！
def register_handlers(self, application):
    application.add_handler(CommandHandler("menu", self.menu_command))
    application.add_handler(CallbackQueryHandler(self.button_callback, pattern=r"^(game|music|close)$"))

async def button_callback(self, update, context):
    query = update.callback_query
    await query.answer()
    
    if query.data == "game":
        await query.edit_message_text("🎮 来玩游戏吧！")
    elif query.data == "music":
        await query.edit_message_text("🎵 来听音乐吧！")
    elif query.data == "close":
        await query.edit_message_text("好的~ 下次再玩吧！喵~")
```

#### 3️⃣ 读取配置文件

```python
from config import BOT_NAME, BOT_OWNER_ID

async def info_command(self, update, context):
    """/info - 查看机器人信息~"""
    await update.message.reply_text(
        f"🤖 机器人名字：{BOT_NAME}\n"
        f"👑 主人 ID：{BOT_OWNER_ID}\n"
        f"✨ 小南永远爱你们哦~"
    )
```

#### 4️⃣ 使用数据管理器

```python
from .data_manager import DataManager

def __init__(self, bot_app=None):
    super().__init__(bot_app)
    self.dm = DataManager()  # 数据管理器，可以存数据哦~

async def save_command(self, update, context):
    """/save <内容> - 保存小秘密~"""
    user_id = str(update.effective_user.id)
    content = " ".join(context.args) if context.args else "什么都没有~"
    
    # 保存数据
    data = self.dm.load_json("my_data.json")
    if user_id not in data:
        data[user_id] = []
    data[user_id].append(content)
    self.dm.save_json("my_data.json", data)
    
    await update.message.reply_text(f"✅ 已经帮你记住啦~ 喵！")
```

---

### ⚡ 快速模板

想快速开始？复制这个模板就好啦~

```python
"""
✨ [模块名字] - [一句话描述] ✨
"""
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from .base_module import BaseModule


class YourModule(BaseModule):
    """你的模块说明~ (｡♥‿♥｡)"""
    
    name = "your_module"       # ← 改成你的文件名（不含 .py）
    description = "模块描述~"   # ← 改成你的描述
    
    def register_handlers(self, application):
        """在这里注册你的命令~"""
        # application.add_handler(CommandHandler("命令", self.函数))
        pass
    
    async def your_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """你的命令逻辑~"""
        await update.message.reply_text("Hello World！喵~")
    
    def get_help_text(self) -> str:
        """返回帮助文本~"""
        return "/你的命令 - 命令说明喵~"
```

---

### 📖 规则一览

| 项目 | 规则 | 例子 |
|------|------|------|
| 📄 **文件名** | `snake_case`（小写+下划线） | `my_cool_module.py` |
| 🏷️ **类名** | `PascalCase`（首字母大写） | `MyCoolModule` |
| 🧬 **继承** | 必须继承 `BaseModule` | `class MyModule(BaseModule):` |
| 📝 **必写方法** | `register_handlers()` + `get_help_text()` | 告诉小南你的模块能做什么 |
| 🎯 **自动加载** | 丢进 `modules/` 目录就行 | 重启后自动生效~ |

### 💖 小贴士

- ✨ **不需要改任何配置文件**，丢进去就能用！
- 🗑️ **删除文件 = 卸载模块**，不会影响其他功能~
- 🔄 **更新时选「仅核心文件」**，你的自定义模块安全无忧~
- 📚 **多看其他模块的代码**，比如 `fun.py`、`help.py`，学习写法~
- 🐛 **出错了别怕**，小南会记录错误日志，看看 `data/errors.json`~
- 💬 **有问题可以提 Issue**，大家一起让机器人更可爱！

---

> 🎀 **快来写你的第一个模块吧！**
> 小南等着你给她加新功能呢~ (｡♥‿♥｡)

## 🔄 自动更新说明

自动更新模块会每 12 小时检查 GitHub 仓库更新：

- **核心文件**（必须更新）：`main.py`、`module_loader.py`、`base_module.py` 等关键文件
- **模块文件**（可选更新）：官方提供的模块文件，更新时可选
- **自定义模块**：永远不会被覆盖，放心写自己的模块~
- **受保护文件**：`config.py` 和 `data/` 目录自动保留

更新方式：
- `/update` 命令手动检查
- 选择「全部更新」或「仅核心文件」
- 更新前自动备份旧文件到 `data/backups/`

## 🎭 性格系统

小南拥有 **40 种性格**，每种都有独特的 emoji、描述和 AI 提示词！

| 分类 | 性格数量 | 举例 |
|------|---------|------|
| 🐱 经典系列 | 7 种 | 可爱猫咪、傲娇、萝莉、病娇... |
| 💕 恋爱系列 | 6 种 | 甜心、醋坛子、小妖精、害羞... |
| 😂 搞笑系列 | 5 种 | 搞笑艺人、捣蛋鬼、毒舌、中二病... |
| 🧠 知性系列 | 5 种 | 哲学家、学霸、艺术家、科学家... |
| 🌟 奇幻系列 | 6 种 | 魔法少女、吸血鬼、精灵、天使... |
| 🎭 角色扮演 | 7 种 | 女仆、执事、忍者、侦探、老师... |
| 🌈 性格特质 | 4 种 | 小太阳、高冷、温柔、吃货... |

> 发送 `/role` 命令，通过翻页菜单选择喜欢的性格~
> 每页 9 个，共 5 页，翻着选超方便！(｡♥‿♥｡)

## 💡 小贴士

- 💻 **后台运行**：使用 `nohup python main.py &` 或 screen/tmux
- 🐳 **Docker 更新**：`docker compose pull && docker compose up -d`
- 📊 **查看数据**：数据保存在 `src/data/` 目录
- 🔄 **自动备份**：系统模块会定期备份数据
- 🎭 **切换性格**：发送 `/role` 试试看！
- 💭 **记忆功能**：发送 `/remember 我喜欢吃草莓` 让小南记住~

## 🎀 二次元日志

启动后你会看到这样的日志：

```
╭─ 🕐 23:25:04 ✦ ⏱ 0s
├─ ✨ INFO ✨ ✦ @小南
╰─ 🚀 小南专属TGbot 正在启动...
```

## 📜 许可证

MIT License

---

<p align="center">
  🐱 <strong>小南专属TGbot</strong> ✨<br>
  <em>一只可可爱爱的机器人~ 全部代码由 AI 编写喵！(｡♥‿♥｡)</em>
</p>

---

## 📞 联系我们

有任何问题、建议或者只是想来找小南玩，都可以通过以下方式联系哦~

| 平台 | 账号 |
|------|------|
| 💬 **Telegram** | [@xiaonan0_0](https://t.me/xiaonan0_0) |
| 🐧 **QQ** | 1404383787 |

> 💖 欢迎来和小南聊天、提建议、或者一起让机器人变得更可爱！(｡♥‿♥｡)
