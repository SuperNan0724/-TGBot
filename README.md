# 🐱 小南专属TGbot ✨

> 🌸 **本项目的所有代码均由 AI 编写喵！** 🌸
>
> 从第一行代码到最后一行，从功能设计到界面美化，
> 全都是聪明又可爱的 AI 小助手一手包办的哦~
> 所以如果有什么 bug... 那一定是 AI 在卖萌！(｡♥‿♥｡)

---

> ⚠️ **平台说明：本项目仅适用于 Windows 系统**
>
> 小南的启动器（`start.py`）使用了 Windows 专属命令（`taskkill`、`wmic`、`chcp` 等），
> 暂不支持 Linux / macOS 系统。如果你需要在其他平台部署，请自行修改相关代码~
> 推荐使用 Windows 10/11 系统运行哦！(｡♥‿♥｡)

---

## 🌟 小南是谁呀？

**小南**是一只可可爱爱的 Telegram 机器人~ 她会：
- 💬 **和你聊天** - 接入 DeepSeek AI，超聪明！
- 🎭 **切换 40 种性格** - 猫咪、傲娇、魔法少女... 每天换一种！
- 💭 **记住你说的话** - 越聊越懂你~
- 🎮 **陪你玩游戏** - 掷骰子、猜拳、抽签...
- 🎉 **欢迎新朋友** - 进群自动欢迎，超热情！
- 🎨 **贴纸识别** - 收到贴纸自动识别，根据 emoji 动态回复！
- 📥 **贴纸收藏** - 主人可以收藏喜欢的贴纸，随时查看管理~

而且最重要的是——**小南是开源的！** 你可以自己搭建一只属于你的小南哦~ (｡♥‿♥｡)

---

## 📖 目录

- [🌟 小南是谁呀？](#-小南是谁呀)
- [🤔 萌新必看 - 什么是 Telegram Bot？](#-萌新必看---什么是-telegram-bot)
- [🚀 快速开始 - 5 分钟拥有小南！](#-快速开始---5-分钟拥有小南)
- [✨ 功能特色](#-功能特色)
- [📝 配置说明](#-配置说明)
- [🐳 Docker 部署](#-docker-部署)
- [📋 指令列表](#-指令列表)
- [📁 项目结构](#-项目结构)
- [🧩 模块开发指南](#-模块开发指南)
- [🔄 自动更新说明](#-自动更新说明)
- [🎭 性格系统](#-性格系统)
- [💡 小贴士](#-小贴士)
- [📞 联系我们](#-联系我们)

---

## 🤔 萌新必看 - 什么是 Telegram Bot？

> 第一次接触 Telegram Bot？别怕！跟着小南一步一步来~ (｡•̀ᴗ-)✧

### 📱 什么是 Telegram？

Telegram 是一款超好用的聊天软件~ 就像微信/QQ 一样，但是更自由、更安全！

### 🤖 什么是 Bot（机器人）？

Bot 就是 Telegram 里的**自动小助手**~ 你可以：
- 和它聊天（就像和小南聊天一样！）
- 让它帮你做事（查天气、玩游戏、记笔记...）
- 把它拉进群聊，让它和大家一起玩~

### 🎯 如何创建自己的 Bot？

> 超简单！只需要 2 分钟~ 跟着做就行啦！(｡♥‿♥｡)

#### 第 1 步：找到 BotFather

1. 打开 Telegram
2. 在搜索框输入 **@BotFather**（这是 Telegram 官方的 Bot 工厂~）
3. 点进去，点击 **START**（开始）

#### 第 2 步：创建你的 Bot

1. 输入 `/newbot` 并发送
2. BotFather 会问你想给 Bot 取什么名字~
   - 比如输入：`小南专属TGbot`（这是显示的名字）
3. 然后问你想给 Bot 什么用户名~
   - 比如输入：`MyNanBot_bot`（这是唯一的 ID，**必须以 _bot 结尾**）
   - 如果被占用了就换一个试试~

#### 第 3 步：拿到你的 Token（小钥匙🔑）

```
Done! Congratulations on your new bot.
You will find it at t.me/MyNanBot_bot.
You can now add a description, about section and profile picture for your bot.

Use this token to access the HTTP API:
1234567890:ABCdefGHIjklMNOpqrsTUVwxyz-ABCDEFG

Keep your token secure and store it safely.
```

看到这串 **`1234567890:ABCdef...`** 了吗？这就是你的 **Token（小钥匙）**！
- 🔑 **一定要复制保存好！** 这是你的 Bot 的身份证~
- 🤫 **不要告诉别人！** 谁拿到这个 Token 谁就能控制你的 Bot~

#### 第 4 步：设置 Bot 头像和介绍（可选）

```
/setuserpic - 设置头像（给小南换张可爱的照片~）
/setdescription - 设置介绍（写一句欢迎语~）
/setabouttext - 设置关于信息
```

> 🎉 **恭喜你！你的 Bot 已经出生啦！**
> 现在去搜索你的 Bot 用户名（比如 @MyNanBot_bot），点 START 就能和它聊天啦~
> 不过现在它什么都不会... 别急！接下来我们就教它变成小南！(｡♥‿♥｡)

---

## 🚀 快速开始 - 5 分钟拥有小南！

### 📋 你需要准备

| 需要的东西 | 从哪里拿 | 难度 |
|-----------|---------|:----:|
| 💻 一台 Windows 电脑 | 你面前这个~ | ⭐ |
| 🌐 能访问 Telegram 的网络 | 代理软件 or 海外服务器 | ⭐⭐ |
| 🔑 Telegram Bot Token | 上面教过啦！@BotFather | ⭐ |
| 🔑 DeepSeek API Key（可选） | [platform.deepseek.com](https://platform.deepseek.com) | ⭐⭐ |

---

### 🪟 Windows 部署（最简单！）

> Windows 用户看这里~ 跟着做就行啦！(｡♥‿♥｡)

#### 第一步：下载项目 📥

**方式一：直接下载 ZIP（推荐萌新~）**
1. 打开项目页面：https://github.com/SuperNan0724/-TGBot
2. 点击绿色的 **「Code」** 按钮
3. 选择 **「Download ZIP」**
4. 解压到你想放的地方，比如 `D:\小南专属TGbot\`

**方式二：使用 Git（进阶~）**
```bash
# 先安装 Git：https://git-scm.com/download/win
# 然后打开 cmd 或 PowerShell，输入：
git clone https://github.com/SuperNan0724/-TGBot.git
cd -TGBot
```

#### 第二步：安装 Python 🐍

1. 打开 https://www.python.org/downloads/
2. 点击黄色的 **Download Python 3.x.x** 按钮
3. 运行下载的安装包
4. **⚠️ 重要！** 安装时一定要勾选 **「Add Python to PATH」**（把 Python 添加到系统路径）
5. 点击 Install Now，等它装完~

验证安装成功：
```cmd
# 打开 cmd 或 PowerShell，输入：
python --version
# 如果显示 Python 3.8+ 就说明成功啦！
```

#### 第三步：启动小南！🎉

```cmd
# 1️⃣ 进入项目目录（换成你的实际路径~）
cd D:\小南专属TGbot

# 2️⃣ 一行命令启动！（启动器会自动帮你搞定一切~）
python start.py
```

启动器会自动帮你：
1. ✅ 检测你的系统
2. ✅ 检查文件有没有缺失
3. ✅ 检测你有没有填好配置
4. ✅ **引导你填写 Token 和 Key**（第一次启动时）
5. ✅ 自动安装需要的依赖
6. ✅ 启动小南！

> 💖 **Windows 就是这么简单！** 下载 → 解压 → 双击运行，搞定！

#### 第四步：后台运行（可选~）

想让小南在后台一直运行，关掉窗口也不停？
- 使用 `start.py` 启动后，它会自动在后台运行~
- 或者直接运行 `python src\main.py`

---

### 🎉 小南活过来啦！

启动成功后都会看到这样的日志~

```
╭─ 🕐 23:25:04 ✦ ⏱ 0s
├─ ✨ INFO ✨ ✦ @小南
╰─ 🚀 小南专属TGbot 正在启动...
╭─ 🕐 23:25:05 ✦ ⏱ 1s
├─ ✨ INFO ✨ ✦ @小南
╰─ ✅ 小南已经准备好啦~ 喵呜！(｡♥‿♥｡)
```

快去 Telegram 里找你的 Bot 聊天吧！发送 `/start` 试试~ 🎀

> 💖 **恭喜你！你已经成功拥有了一只属于自己的小南！**
> 接下来去看看功能特色，和小南一起玩吧~ (｡♥‿♥｡)

---

## ✨ 功能特色

| 功能 | 说明 | 可爱程度 |
|:----|:-----|:--------:|
| 🤖 **AI 对话** | 接入 DeepSeek API，智能聊天，还能切换 40 种性格！ | 🌟🌟🌟🌟🌟 |
| 🎭 **性格切换** | 可爱猫咪、傲娇、病娇、魔法少女... 总有一款适合你！ | 🌟🌟🌟🌟🌟 |
| 💭 **记忆功能** | 让小南记住重要信息，越聊越懂你~ | 🌟🌟🌟🌟 |
| 🎉 **进群欢迎** | 新人加入自动欢迎，40+ 条动态欢迎语不重复，2 分钟自动删除！ | 🌟🌟🌟🌟 |
| 🎮 **娱乐功能** | 掷骰子、猜拳、抽签、今日运势... 玩不停！ | 🌟🌟🌟🌟 |
| 👥 **群聊支持** | @机器人或回复即可触发，群聊也能玩~ | 🌟🌟🌟🌟 |
| 🎨 **贴纸识别** | 收到贴纸自动识别，根据 emoji 动态回复，200+ 条回复语！ | 🌟🌟🌟🌟🌟 |
| 🎀 **二次元风格** | 粉粉嫩嫩的日志输出，可爱到冒泡~ | 🌟🌟🌟🌟🌟 |
| 🔄 **自动更新** | 每 12 小时自动检查 GitHub 更新，更新前自动备份~ | 🌟🌟🌟🌟🌟 |
| 📝 **自定义指令** | 编辑 `commands.txt` 就能添加新指令~ | 🌟🌟🌟 |

---

## 📝 配置说明

### 📄 配置文件位置

所有配置都在 **`src/config.py`** 文件中，用记事本或任意代码编辑器打开就能修改啦~

> ⚠️ **注意：** 项目中有两个 `config.py` 文件：
> - **`src/config.py`** ← 你实际要修改的配置文件（含你的敏感信息）
> - `source/src/config.py` ← 上传 GitHub 用的模板（不含敏感信息，不要改这个！）
>
> 使用 `sync.py` 同步时，`source/src/config.py` 会自动保留你的敏感字段，不会丢失哦~

---

### 🔑 需要修改的配置项

打开 `src/config.py`，你会看到这样的内容：

```python
# ===== 🔑 必填项（不填小南不会理你哦~）=====

# 1️⃣ Telegram Bot Token（从 @BotFather 获取）
TELEGRAM_BOT_TOKEN = "这里填你的Token"  # ← 把引号里的内容换成你的 Token！

# 2️⃣ DeepSeek API Key（让 AI 更聪明~）
DEEPSEEK_API_KEY = "这里填你的Key"      # ← 把引号里的内容换成你的 Key！

# 3️⃣ 你的 Telegram ID（主人专属命令用~）
BOT_OWNER_ID = 123456789                # ← 把数字换成你的 ID！
```

| 配置项 | 在哪里获取 | 怎么填 | 必填 |
|--------|-----------|:------|:----:|
| 🔑 `TELEGRAM_BOT_TOKEN` | [@BotFather](https://t.me/BotFather) → `/newbot` → 复制 Token | 填在引号里：`"123456:ABCdef..."` | ✅ **必填！** |
| 🔑 `DEEPSEEK_API_KEY` | [platform.deepseek.com](https://platform.deepseek.com) → API Keys → 创建 | 填在引号里：`"sk-xxxx..."` | ❌ 可选 |
| 👑 `BOT_OWNER_ID` | [@userinfobot](https://t.me/userinfobot) → START → 复制 ID | 直接填数字：`7609256840` | ✅ **推荐填！** |

> 💡 **怎么获取我的 Telegram ID？**
> 1. 打开 Telegram，搜索 **@userinfobot**
> 2. 点击 **START**（开始）
> 3. 它会直接回复你一串数字，比如：`Your ID: 7609256840`
> 4. 把这串数字填到 `BOT_OWNER_ID = ` 后面就行啦~

---

### ✨ 可选配置项

除了上面的必填项，你还可以自定义这些：

| 配置项 | 默认值 | 说明 |
|--------|:------:|:-----|
| `BOT_NAME` | `"小南专属TGbot"` | 机器人的全称（显示在日志里~） |
| `BOT_NAME_SHORT` | `"小南"` | 机器人的简称（对话中显示的名字~） |
| `BOT_OWNER_NAME` | `"主人"` | 主人的名字（会显示在欢迎消息等地方~） |
| `DEFAULT_PERSONALITY` | `"default"` | 默认性格 ID（对应 personalities.py 中的 id） |
| `MAX_HISTORY_LENGTH` | `10` | 每个小可爱最多保留的对话历史条数~ |

---

### ⚠️ 关于网络连接

由于 Telegram API 在国内无法直接访问，你需要：
- **方案一**：使用代理软件（如 Clash、v2ray、SSR 等），开启系统代理或 TUN 模式
- **方案二**：在海外服务器上部署（比如阿里云国际版、AWS、Vultr 等）
- **方案三**：使用 Docker 部署并配置容器代理

本项目不内置代理功能，请自行确保网络环境可以访问 Telegram API 哦~

---

## 🐳 Docker 部署

> 适合有 Docker 基础的小伙伴~ 更稳定、更方便！

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

---

## 📋 指令列表

所有指令在 `src/deploy/commands.txt` 中定义，你可以自由添加/修改哦~

```
[基础命令]
start - 我是混日子的喵～
role - 切换性格喵～（专属于你的性格喵～）
status - 查看状态喵
clear - 清空我对你的印象喵～
reset - 完全重置喵～
help - 查看帮助喵～
chat - 和 AI 聊天喵～
think - 让小南帮你思考问题喵～
remember - 让小南记住一件事喵～
memories - 查看小南记得的事情喵～
forget - 让小南忘记一件事喵～
clear_memories - 清除所有记忆喵～

[娱乐命令]
dice - 掷骰子喵～
rps - 猜拳喵～
fortune - 今日运势喵～
lottery - 抽签喵～
choose - 选择困难症救星喵～

[更新命令]
update - 检查并更新小南到最新版本喵～
check_update - 手动检查更新，不自动下载喵～

[管理命令]
add_user - 添加白名单小鱼干喵～（主人专属喵）
del_user - 移除小鱼干喵～（主人专属喵）
...
```

---

## 📁 项目结构

```
小南专属TGbot/
├── README.md               ← 📖 项目说明（就是你现在看的这个！）
├── start.py                🚀 Windows 启动器（唯一入口！）
├── .gitignore              🙈 Git 忽略文件
├── .dockerignore           🐳 Docker 忽略文件
├── src/                    💻 调试目录（含你的配置信息）
│   ├── main.py             🎯 主程序入口
│   ├── config.py           🔑 配置文件（填你的 Token/Key/ID）
│   ├── requirements.txt    📦 Python 依赖
│   ├── modules/            🧩 模块目录（所有功能都在这里！）
│   │   ├── __init__.py
│   │   ├── base_module.py      # 🧬 模块基类
│   │   ├── module_loader.py    # 📥 模块加载器
│   │   ├── data_manager.py     # 💾 数据管理器
│   │   ├── personalities.py    # 🎭 40种性格大全！
│   │   ├── deepseek_chat.py    # 🤖 AI 对话模块
│   │   ├── welcome.py          # 🎉 进群欢迎模块
│   │   ├── admin.py            # 👑 管理模块
│   │   ├── help.py             # 📚 帮助模块
│   │   ├── system.py           # 📊 系统状态模块
│   │   ├── fun.py              # 🎮 娱乐模块
│   │   ├── sticker.py          # 🎨 贴纸模块
│   │   ├── auto_updater.py     # 🔄 自动更新模块
│   │   └── anime_logger.py     # 🌸 二次元日志模块
│   ├── data/              📂 数据文件（自动生成~）
│   │   ├── whitelist.json
│   │   ├── admins.json
│   │   ├── user_data.json
│   │   ├── errors.json
│   │   └── backups/
│   └── deploy/            🚢 部署文件
│       ├── Dockerfile
│       ├── docker-compose.yml
│       ├── setup.bat
│       ├── setup.sh
│       └── commands.txt
└── source/                📦 源码目录（上传 GitHub 用的，不含配置）
    ├── start.py
    ├── README.md
    ├── .gitignore
    ├── .dockerignore
    └── src/
        ├── main.py
        ├── config.py          ← 📋 模板配置（没有 Token/Key/ID）
        ├── requirements.txt
        ├── modules/
        └── deploy/
```

---

## 🧩 模块开发指南 ✨

> 想给小南加新功能？超简单哒！(｡♥‿♥｡)
> 把 `.py` 文件丢进 `src/modules/` 目录就会**自动加载**啦~
> 不需要改任何配置文件，就是这么方便喵！

---

### 📚 基础篇 - 你的第一个模块

#### 第一步：创建文件 📄

在 `src/modules/` 目录下创建一个 `.py` 文件，比如 `my_module.py`~

#### 第二步：写代码 💻

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

#### 第三步：重启机器人 🔄

```bash
# 重启小南，新模块就自动加载啦！
python start.py
```

#### 第四步：试试看！🎉

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
|:----|:-----|:-----|
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
- 💬 **有问题可以联系我们**，大家一起让机器人更可爱！

---

> 🎀 **快来写你的第一个模块吧！**
> 小南等着你给她加新功能呢~ (｡♥‿♥｡)

---

## 🔄 自动更新说明

小南会自动检查更新，保持最新版本哦~

| 文件类型 | 说明 | 更新方式 |
|:---------|:-----|:---------|
| ⚡ **核心文件** | `main.py`、`module_loader.py`、`base_module.py` 等关键文件 | **必须更新** |
| 🧩 **模块文件** | 官方提供的模块（`deepseek_chat.py`、`personalities.py` 等） | **可选更新** |
| 💖 **自定义模块** | 你自己写的模块 | **永远不会被覆盖！** |
| 🔒 **受保护文件** | `config.py` 和 `data/` 目录 | **自动保留** |

**更新方式：**
- `/update` - 检查更新，可选择「全部更新」或「仅核心文件」
- `/check_update` - 仅检查，不下载
- 更新前自动备份旧文件到 `data/backups/`~

---

## 🎭 性格系统

小南拥有 **40 种性格**，每种都有独特的 emoji、描述和 AI 提示词！

| 分类 | 数量 | 举例 |
|:----|:----|:-----|
| 🐱 **经典系列** | 7 种 | 可爱猫咪、傲娇、萝莉、病娇... |
| 💕 **恋爱系列** | 6 种 | 甜心、醋坛子、小妖精、害羞... |
| 😂 **搞笑系列** | 5 种 | 搞笑艺人、捣蛋鬼、毒舌、中二病... |
| 🧠 **知性系列** | 5 种 | 哲学家、学霸、艺术家、科学家... |
| 🌟 **奇幻系列** | 6 种 | 魔法少女、吸血鬼、精灵、天使... |
| 🎭 **角色扮演** | 7 种 | 女仆、执事、忍者、侦探、老师... |
| 🌈 **性格特质** | 4 种 | 小太阳、高冷、温柔、吃货... |

> 发送 `/role` 命令，通过翻页菜单选择喜欢的性格~
> 每页 9 个，共 5 页，翻着选超方便！(｡♥‿♥｡)

---

## 💡 小贴士

| 想做什么？ | 怎么做？ |
|:----------|:---------|
| 💻 **后台运行** | 使用 `python start.py` 启动后保持窗口打开即可 |
| 🐳 **Docker 更新** | `docker compose pull && docker compose up -d` |
| 📊 **查看数据** | 数据保存在 `src/data/` 目录 |
| 🔄 **自动备份** | 系统模块会定期备份数据 |
| 🎭 **切换性格** | 发送 `/role` 试试看！ |
| 💭 **记忆功能** | 发送 `/remember 我喜欢吃草莓` 让小南记住~ |

---

## 🎀 二次元日志

启动后你会看到这样的日志，粉粉嫩嫩的超可爱~

```
╭─ 🕐 23:25:04 ✦ ⏱ 0s
├─ ✨ INFO ✨ ✦ @小南
╰─ 🚀 小南专属TGbot 正在启动...
╭─ 🕐 23:25:05 ✦ ⏱ 1s
├─ ✨ INFO ✨ ✦ @小南
╰─ ✅ 小南已经准备好啦~ 喵呜！(｡♥‿♥｡)
```

---

## 📜 许可证

MIT License ~ 随便玩，随便改，记得注明出处就好啦~ (｡♥‿♥｡)

---

## 📞 联系我们

有任何问题、建议或者只是想来找小南玩，都可以通过以下方式联系哦~

| 平台 | 账号 |
|:----|:-----|
| 💬 **Telegram** | [@xiaonan0_0](https://t.me/xiaonan0_0) |
| 🐧 **QQ** | 1404383787 |

> 💖 **欢迎来和小南聊天、提建议、或者一起让机器人变得更可爱！** (｡♥‿♥｡)

---

<p align="center">
  🐱 <strong>小南专属TGbot</strong> ✨<br>
  <em>一只可可爱爱的机器人~ 全部代码由 AI 编写喵！(｡♥‿♥｡)</em>
  <br><br>
  🌸 <strong>给小南一个 ⭐ Star，让她更有动力卖萌吧！</strong> 🌸
</p>
