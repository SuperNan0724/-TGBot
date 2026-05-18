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
| `BOT_NAME` | 机器人名称 | ❌ |

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
