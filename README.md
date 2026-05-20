<p align="center">
  <img src="https://img.shields.io/badge/🐱-小南专属TGbot-FF69B4?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/✨-Powered%20by%20ARTI-FFB6C1?style=for-the-badge"/>
  <br>
  <img src="https://img.shields.io/badge/Python-3.8+-FF69B4?style=flat-square&logo=python&logoColor=white"/>
  <img src="https://img.shields.io/badge/Telegram-Bot-26A5E4?style=flat-square&logo=telegram&logoColor=white"/>
  <img src="https://img.shields.io/badge/DeepSeek-AI-4D6BFE?style=flat-square"/>
  <img src="https://img.shields.io/badge/License-MIT-FFB6C1?style=flat-square"/>
</p>

---

<p align="center">
  ✿ <b>一只可可爱爱的 Telegram 机器人 ✨ 全部代码由 AI 编写喵！</b> ✿<br>
  <br>
  🎀 <i>开发者：<b>ARTI</b>（AR•TI）独立开发完成</i> 🎀<br>
  <br>
  🌸 <b>如果有什么 bug... 那一定是 AI 在卖萌！</b> 🌸
</p>

---

> ⚠️ **平台说明：本项目仅适用于 Windows 系统**
>
> 小南的启动器（`start.py`）使用了 Windows 专属命令（`taskkill`、`wmic`、`chcp` 等），
> 暂不支持 Linux / macOS 系统。如果你需要在其他平台部署，请自行修改相关代码~
> 推荐使用 Windows 10/11 系统运行哦！(｡♥‿♥｡)

---

## 🌟 小南——你的专属二次元女友 AI ✨

<p align="center">
  <b>🌸 会聊天 · 会卖萌 · 会撒娇 · 会吃醋 🌸</b><br>
  <b>🌙 会深夜陪聊 · 会记你的喜好 · 会切换 40 种性格 🌙</b><br>
  <br>
  <i>「哥哥~ 人家等你好久了！」</i><br>
  <i>「你来了。我等了你很久呢。」</i>
</p>

**小南**是一只超可可爱爱的 Telegram 机器人~ 她会：

| 技能 | 说明 | 可爱值 |
|:----|:-----|:------:|
| 💬 **AI 聊天** | 接入 DeepSeek AI，超聪明！知道现在几点该说什么话~ | 🌟🌟🌟🌟🌟 |
| 🎭 **40 种性格** | 猫咪、傲娇、病娇、魔法少女、女仆... 每天换一种！ | 🌟🌟🌟🌟🌟 |
| 💭 **记住你** | 你的喜好、名字、讨厌的东西... 越聊越懂你~ | 🌟🌟🌟🌟🌟 |
| 💕 **女友模式** | 🌸完美萝莉女友 + 🌙白月光女友，仅私聊专属甜蜜！ | 🌟🌟🌟🌟🌟 |
| 🎮 **陪你玩** | 掷骰子、猜拳、抽签、今日运势... 玩不停！ | 🌟🌟🌟🌟 |
| 🎉 **欢迎新朋友** | 进群自动欢迎，40+ 条动态欢迎语不重复~ | 🌟🌟🌟🌟 |
| 🎨 **贴纸识别** | 收到贴纸自动识别，200+ 条回复语，动态回复！ | 🌟🌟🌟🌟🌟 |
| ⏰ **时间感知** | 知道现在是清晨/中午/深夜，说话像真人一样自然~ | 🌟🌟🌟🌟🌟 |

---

## 📖 目录

- [🌟 小南——你的专属二次元女友 AI](#-小南——你的专属二次元女友-ai)
- [🤔 萌新必看 - 什么是 Telegram Bot？](#-萌新必看---什么是-telegram-bot)
- [🚀 5 分钟拥有小南！](#-5-分钟拥有小南)
- [✨ 功能特色](#-功能特色)
- [📝 配置说明](#-配置说明)
- [🐳 Docker 部署](#-docker-部署)
- [📋 指令列表](#-指令列表)
- [📁 项目结构](#-项目结构)
- [🧩 模块开发指南](#-模块开发指南)
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

**第 1 步：找到 BotFather**
1. 打开 Telegram
2. 在搜索框输入 **@BotFather**（这是 Telegram 官方的 Bot 工厂~）
3. 点进去，点击 **START**（开始）

**第 2 步：创建你的 Bot**
1. 输入 `/newbot` 并发送
2. BotFather 会问你想给 Bot 取什么名字~
   - 比如输入：`小南专属TGbot`（这是显示的名字）
3. 然后问你想给 Bot 什么用户名~
   - 比如输入：`MyNanBot_bot`（这是唯一的 ID，**必须以 _bot 结尾**）
   - 如果被占用了就换一个试试~

**第 3 步：拿到你的 Token（小钥匙🔑）**

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

> 🎉 **恭喜你！你的 Bot 已经出生啦！**
> 现在去搜索你的 Bot 用户名（比如 @MyNanBot_bot），点 START 就能和它聊天啦~
> 不过现在它什么都不会... 别急！接下来我们就教它变成小南！(｡♥‿♥｡)

---

## 🚀 5 分钟拥有小南！

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

**第一步：下载项目 📥**

**方式一：直接下载 ZIP（推荐萌新~）**
1. 打开项目页面：https://github.com/SuperNan0724/-TGBot
2. 点击绿色的 **「Code」** 按钮
3. 选择 **「Download ZIP」**
4. 解压到你想放的地方，比如 `D:\小南专属TGbot\`

**方式二：使用 Git（进阶~）**
```bash
git clone https://github.com/SuperNan0724/-TGBot.git
cd -TGBot
```

**第二步：安装 Python 🐍**

1. 打开 https://www.python.org/downloads/
2. 点击黄色的 **Download Python 3.x.x** 按钮
3. 运行下载的安装包
4. **⚠️ 重要！** 安装时一定要勾选 **「Add Python to PATH」**
5. 点击 Install Now，等它装完~

**第三步：一行命令启动！🎉**

```cmd
cd D:\小南专属TGbot
python start.py
```

启动器会自动帮你：
1. ✅ 检测系统环境
2. ✅ 引导你填写 Token 和 Key（**第一次启动时**）
3. ✅ 自动安装依赖
4. ✅ 启动小南！

> 💖 **下载 → 解压 → 双击运行，搞定！**

**第四步：和小南玩耍！**

```
╭─ 🕐 23:25:04 ✦ ⏱ 0s
├─ ✨ INFO ✨ ✦ @小南
╰─ 🚀 小南专属TGbot 正在启动...
╭─ 🕐 23:25:05 ✦ ⏱ 1s
├─ ✨ INFO ✨ ✦ @小南
╰─ ✅ 小南已经准备好啦~ 喵呜！(｡♥‿♥｡)
```

快去 Telegram 里找你的 Bot 聊天吧！发送 `/start` 试试~ 🎀

---

## ✨ 功能特色

<p align="center">
  <b>🌸 小南的功能超丰富！总有一款让你心动~ 🌸</b>
</p>

| 功能 | 说明 | 可爱程度 |
|:----|:-----|:--------:|
| 🤖 **AI 对话** | 接入 DeepSeek API，智能聊天，还能切换 40 种性格！ | 🌟🌟🌟🌟🌟 |
| 🎭 **性格切换** | 可爱猫咪、傲娇、病娇、魔法少女... 每页 9 种，翻着选！ | 🌟🌟🌟🌟🌟 |
| 💭 **记忆功能** | 让小南记住重要信息，越聊越懂你~ | 🌟🌟🌟🌟 |
| 🎉 **进群欢迎** | 新人加入自动欢迎，40+ 条动态欢迎语不重复，2 分钟自动删除！ | 🌟🌟🌟🌟 |
| 🎮 **娱乐功能** | 掷骰子、猜拳、抽签、今日运势... 玩不停！ | 🌟🌟🌟🌟 |
| 👥 **群聊支持** | @机器人或回复即可触发，群聊也能玩~ | 🌟🌟🌟🌟 |
| 🎨 **贴纸识别** | 收到贴纸自动识别，根据 emoji 动态回复，200+ 条回复语！ | 🌟🌟🌟🌟🌟 |
| 💕 **女友模式** | 两种女友性格：🌸完美萝莉女友 + 🌙白月光女友，仅私聊可用~ 拥有独立记忆系统，牢牢记住你们的每一句对话！ | 🌟🌟🌟🌟🌟 |
| 🎀 **二次元风格** | 粉粉嫩嫩的日志输出，可爱到冒泡~ | 🌟🌟🌟🌟🌟 |
| ⏰ **时间感知** | AI 知道现在是清晨还是深夜，说话像真人一样自然~ | 🌟🌟🌟🌟🌟 |
| 📝 **自定义指令** | 编辑 `指令集.txt` 就能添加新指令~ | 🌟🌟🌟 |

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

所有指令在 `src/deploy/指令集.txt` 中定义，你可以自由添加/修改哦~

```
🌸 [基础命令] 🌸
start       - 我是混日子的喵～
role        - 切换性格喵～（专属于你的性格喵～）
status      - 查看状态喵
clear       - 清空我对你的印象喵～
reset       - 完全重置喵～
help        - 查看帮助喵～
chat        - 和 AI 聊天喵～
think       - 让小南帮你思考问题喵～
remember    - 让小南记住一件事喵～
memories    - 查看小南记得的事情喵～
forget      - 让小南忘记一件事喵～
clear_memories - 清除所有记忆喵～
girlfriend  - 开启女友模式喵～（仅私聊可用，两种性格可选！）
gf          - 女友模式快捷命令喵～

🎮 [娱乐命令] 🎮
dice        - 掷骰子喵～
rps         - 猜拳喵～
fortune     - 今日运势喵～
lottery     - 抽签喵～
choose      - 选择困难症救星喵～

🎨 [贴纸命令] 🎨
add_sticker - 收藏贴纸喵～（主人专属喵）
sticker_list - 查看收藏的贴纸喵～（主人专属喵）
del_sticker - 删除收藏的贴纸喵～（主人专属喵）

👑 [管理命令] 👑
add_user    - 添加白名单小鱼干喵～
del_user    - 移除小鱼干喵～
error_detail - 错误详细报告喵～
error_clean - 清除错误报告喵～
system_status - 当前小南身体状态喵～
```

### 📝 如何添加新指令？

> 想给小南加新指令？超简单！只需要两步~ (｡♥‿♥｡)

**第一步：编辑指令集**

打开 `src/deploy/指令集.txt`，按照格式添加你的指令：

```txt
[你的分类名]
你的指令名 - 指令说明喵～
```

**第二步：重启小南**

```bash
python start.py
```

> 🎉 **搞定！** 指令会自动出现在 `/help` 帮助列表中哦！

---

## 📁 项目结构

```
🌸 小南专属TGbot/ 🌸
├── README.md               ← 📖 就是你现在看的这个！
├── start.py                🚀 Windows 启动器
├── sync.py                 🔄 一键同步工具
├── .gitignore              🙈 Git 忽略文件
├── .dockerignore           🐳 Docker 忽略文件
│
├── src/                    💻 你的调试目录（含配置信息）
│   ├── main.py             🎯 主程序入口
│   ├── config.py           🔑 你的配置（Token/Key/ID）
│   ├── requirements.txt    📦 Python 依赖
│   │
│   ├── modules/            🧩 所有功能都在这里！
│   │   ├── __init__.py
│   │   ├── base_module.py      # 🧬 模块基类
│   │   ├── module_loader.py    # 📥 自动加载器
│   │   ├── data_manager.py     # 💾 数据管理器
│   │   ├── helpers.py          # 🔧 辅助函数
│   │   ├── personalities.py    # 🎭 40种性格！
│   │   ├── deepseek_chat.py    # 🤖 AI 对话
│   │   ├── girlfriend.py       # 💕 女友模式
│   │   ├── welcome.py          # 🎉 进群欢迎
│   │   ├── admin.py            # 👑 管理模块
│   │   ├── help.py             # 📚 帮助模块
│   │   ├── system.py           # 📊 系统状态
│   │   ├── fun.py              # 🎮 娱乐模块
│   │   ├── sticker.py          # 🎨 贴纸模块
│   │   ├── think.py            # 💭 思考模块
│   │   └── anime_logger.py     # 🌸 二次元日志
│   │
│   ├── data/              📂 数据文件（自动生成）
│   │   ├── whitelist.json       # 白名单
│   │   ├── admins.json          # 管理员
│   │   ├── user_data.json       # 用户数据
│   │   ├── errors.json          # 错误日志
│   │   └── backups/             # 备份
│   │
│   └── deploy/            🚢 部署文件
│       ├── Dockerfile
│       ├── docker-compose.yml
│       ├── setup.bat
│       ├── setup.sh
│       └── 指令集.txt
│
└── source/                📦 源码目录（上传 GitHub 用的）
    ├── start.py
    ├── README.md
    └── src/（不含你的配置信息）
```

---

## 🧩 模块开发指南 ✨

> 想给小南加新功能？超简单哒！(｡♥‿♥｡)
> 把 `.py` 文件丢进 `src/modules/` 目录就会**自动加载**啦~

### ⚡ 快速模板

```python
"""
✨ [模块名字] ✨
"""
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from .base_module import BaseModule

class YourModule(BaseModule):
    """你的模块说明~ (｡♥‿♥｡)"""
    name = "your_module"
    description = "模块描述~"
    
    def register_handlers(self, application):
        application.add_handler(CommandHandler("命令", self.your_command))
    
    async def your_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Hello World！喵~")
    
    def get_help_text(self) -> str:
        return "/你的命令 - 命令说明喵~"
```

### 📖 规则一览

| 项目 | 规则 | 例子 |
|:----|:-----|:-----|
| 📄 **文件名** | `snake_case`（小写+下划线） | `my_cool_module.py` |
| 🏷️ **类名** | `PascalCase`（首字母大写） | `MyCoolModule` |
| 🧬 **继承** | 必须继承 `BaseModule` | `class MyModule(BaseModule):` |
| 🎯 **自动加载** | 丢进 `modules/` 目录就行 | 重启后自动生效~ |

> 🎀 **快来写你的第一个模块吧！小南等着你给她加新功能呢~**

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
| 🎭 **切换性格** | 发送 `/role` 翻页选择 |
| 💭 **让小南记住** | 发送 `/remember 我喜欢吃草莓` |
| 💕 **开启女友模式** | 发送 `/girlfriend` 或 `/gf` |
| 🔧 **加新功能** | 在 `modules/` 下创建 `.py` 文件即可 |
| 📊 **查看数据** | 数据保存在 `src/data/` 目录 |

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

> 💖 **开发者：ARTI（AR•TI）**
> 💖 **欢迎来和小南聊天、提建议、或者一起让机器人变得更可爱！**

---

<p align="center">
  <br>
  🐱 <b>小南专属TGbot</b> ✨<br>
  <br>
  <i>🌸 一只可可爱爱的机器人 ~ 全部代码由 AI 编写喵！</i><br>
  <i>🌸 开发者：<b>ARTI</b>（AR•TI）独立开发完成</i><br>
  <br>
  <b>给小南一个 ⭐ Star，让她更有动力卖萌吧！</b><br>
  <br>
  <img src="https://img.shields.io/badge/🌸-Thanks%20for%20visiting-FFB6C1?style=for-the-badge"/>
  <br><br>
</p>
