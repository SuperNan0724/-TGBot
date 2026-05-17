# 🐱 小南专属TGbot

一只可可爱爱的 Telegram 机器人，支持 DeepSeek AI 对话~ ✨

## ✨ 功能特色

- 🤖 **AI 对话** - 接入 DeepSeek API，智能聊天
- 💭 **记忆功能** - 让小南记住重要信息
- 🎮 **娱乐功能** - 掷骰子、猜拳等小游戏
- 👥 **群聊支持** - @机器人或回复即可触发
- 🎀 **二次元风格** - 粉粉嫩嫩的日志输出
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

[娱乐命令]
dice - 掷骰子喵～
rps - 猜拳喵～
```

## 📁 项目结构

```
小南专属TGbot/
├── README.md               ← 项目说明（从这里开始看！）
├── start.py                ← 跨平台启动器（唯一入口）
├── .dockerignore           ← Docker 忽略文件
└── src/                    ← 所有源文件
    ├── main.py             ← 主程序入口
    ├── config.py           ← 配置文件（填入你的 Token/Key/ID）
    ├── requirements.txt    ← Python 依赖
    ├── modules/            ← 模块目录
    │   ├── __init__.py
    │   ├── base_module.py      # 模块基类
    │   ├── module_loader.py    # 模块加载器
    │   ├── data_manager.py     # 数据管理器
    │   ├── deepseek_chat.py    # AI 对话模块
    │   ├── admin.py            # 管理模块
    │   ├── help.py             # 帮助模块
    │   ├── system.py           # 系统状态模块
    │   ├── fun.py              # 娱乐模块
    │   └── anime_logger.py     # 二次元日志模块
    ├── data/              ← 数据文件（自动生成）
    │   ├── whitelist.json
    │   ├── admins.json
    │   ├── user_data.json
    │   ├── errors.json
    │   └── backups/
    └── deploy/            ← 部署文件
        ├── Dockerfile
        ├── docker-compose.yml
        ├── setup.bat
        ├── setup.sh
        └── commands.txt
```

## 💡 小贴士

- 💻 **后台运行**：使用 `nohup python main.py &` 或 screen/tmux
- 🐳 **Docker 更新**：`docker compose pull && docker compose up -d`
- 📊 **查看数据**：数据保存在 `src/data/` 目录
- 🔄 **自动备份**：系统模块会定期备份数据

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
  <em>一只可可爱爱的机器人~ 喵呜！(｡♥‿♥｡)</em>
</p>
