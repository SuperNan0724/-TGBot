# 部署指南 · 小南专属TGbot

四种方式，按场景挑一个。**所有方式共用同一套代码**，配置优先级从低到高：

```
config.example.py 的默认值  →  src/config.py（如果有）  →  同名环境变量
```

也就是说：容器 / systemd / 云平台都可以完全不写 `config.py`，只给环境变量。

### 装完先自检

不联网、不启动机器人，只回答"这套配置能不能跑起来"：

```bash
python src/main.py --check
# 容器里
docker run --rm -e TELEGRAM_BOT_TOKEN=xxx telegram-bot:local python main.py --check
```

它会检查：Token 是否填了、主人 ID、DeepSeek Key、代理、依赖版本、ffmpeg、数据目录可写，
并列出"缺什么 / 什么只影响可选功能"。返回码 0 = 关键项齐全，1 = 启动会失败。
（Token 只显示后 4 位，不会把完整凭据写进日志。）

| 场景 | 用哪种 | 需要什么 |
|:--|:--|:--|
| 自己的 Windows 电脑 | [`start.bat`](../start.bat) | 只有 Python 3.10+ |
| 有 Docker 的机器 / NAS | Docker Compose | Docker + Docker Compose v2 |
| Linux 服务器（长期跑） | systemd 服务 | Linux + sudo |
| 云平台（Railway / Render / Fly.io 等） | 容器 + 环境变量 | 一个平台账号 |

---

## 一、Windows 本机（最简单）

```bat
start.bat
```

首次运行会：建 `.venv` → 装依赖 → 从 `config.example.py` 生成 `config.py` → 让你填 Token。

```bat
start.bat --bg        :: 后台跑
start.bat --status    :: 看状态
start.bat --stop      :: 停止
```

脚本与编码约定：`start.bat` 是 **GBK + CRLF**、`_bothelper.ps1` 是 **UTF-8 BOM + CRLF**，
这是 cmd / Windows PowerShell 5.1 的硬要求，改动时别用编辑器另存成别的编码。

---

## 二、Docker Compose（推荐给"有 Docker 的机器"）

```bash
cp .env.example .env      # 填 TELEGRAM_BOT_TOKEN；国内再填 PROXY_URL
docker compose up -d --build
docker compose logs -f
```

停止 / 更新：

```bash
docker compose down
git pull && docker compose up -d --build
```

要点：

- 构建上下文是**仓库根目录**，`Dockerfile`、`docker-compose.yml`、`.dockerignore` 都在根目录
- 镜像里**没有** `config.py`，配置全部来自 `.env`
- 数据在 `bot-data` 卷（`/app/data`）里：白名单、用户记录、备份都在那，**别删卷**
- 镜像自带 ffmpeg 和非 root 用户，`HEALTHCHECK` 探的是 `data/bot.pid`
- 想用 `config.py` 而不是环境变量：取消 `docker-compose.yml` 里那行注释即可（二选一）

### 容器里的代理

```env
# Docker Desktop（Windows/macOS）
PROXY_URL=http://host.docker.internal:7897
# Linux 宿主机
PROXY_URL=http://172.17.0.1:7897
```

写 `127.0.0.1` 是**容器自己**，连不上宿主机的 Clash/v2ray。

---

## 三、Linux 服务器（systemd，长期运行）

```bash
# 1. 拿到代码
sudo mkdir -p /opt && cd /opt
sudo git clone https://github.com/SuperNan0724/-TGBot.git telegram-bot
sudo chown -R "$USER":"$USER" /opt/telegram-bot
cd /opt/telegram-bot/src/deploy

# 2. 装依赖（国内加 --mirror）
./setup.sh --mirror

# 3. 装成 systemd 服务（会按当前路径改写 unit 文件）
./setup.sh --mirror --service

# 4. 填 Token
sudo nano /etc/telegram-bot.env      # TELEGRAM_BOT_TOKEN=...
sudo systemctl restart telegram-bot

# 5. 看状态与日志
systemctl status telegram-bot
journalctl -u telegram-bot -f
```

不想用 systemd 的话，用管理脚本（等价于 Windows 的 `start.bat --bg/--stop`）：

```bash
cd /opt/telegram-bot
src/deploy/manage.sh start     # 后台启动，日志写 logs/
src/deploy/manage.sh status
src/deploy/manage.sh logs
src/deploy/manage.sh stop
```

要点：

- `setup.sh` 会建仓库根目录的 `.venv`，`manage.sh` 用的也是它
- systemd unit 里的路径按 `/opt/telegram-bot` 写的，`setup.sh --service` 会自动替换成你的真实路径
- 用专用账号跑更安全：`useradd -r -s /sbin/nologin telegram-bot`，然后取消 unit 里 `User=` 注释并 `chown` 数据目录
- 日志轮转：systemd 走 journald（`journalctl` 自带轮转）；`manage.sh` 的 `logs/` 会自动删 7 天前的文件
- macOS 没有 systemd，直接 `manage.sh` 或自己写 launchd plist

---

## 四、云平台（Railway / Render / Fly.io 等）

只要能跑 Docker 的平台都行，**不需要改代码**：

1. 把仓库连到平台
2. 平台若问 Dockerfile 路径，填 `Dockerfile`；构建上下文填**仓库根目录**
3. 环境变量里加 `TELEGRAM_BOT_TOKEN`（必填）、`BOT_OWNER_ID`、`DEEPSEEK_API_KEY`、`PROXY_URL`（按平台网络情况，一般不需要）
4. 数据卷：把 `/app/data` 挂成持久卷，否则每次部署都会丢白名单和历史

注意事项：

- 机器人用 **long polling**，不需要公网入口，也不用暴露端口；平台要你选"Web Service / 端口"时，只要进程能常驻即可（具体字段名以各平台当前文档为准）
- **同一个 Token 只能跑一个实例**，否则 Telegram 返回 `409 Conflict`：本地和云上别同时开
- 平台时区默认 UTC，`TZ=Asia/Shanghai` 已经在镜像里设好；想改就改这个环境变量
- 装完先跑一次自检：`python src/main.py --check`（容器里 `docker run --rm -e TELEGRAM_BOT_TOKEN=xxx <镜像> python main.py --check`）

---

## 五、配置项速查

变量名与 `src/config.example.py` 里的配置项**完全同名**，留空 = 不覆盖。
完整清单见 [.env.example](../.env.example) 和 [config.example.py](../src/config.example.py)。

| 变量 | 必填 | 说明 |
|:--|:--:|:--|
| `TELEGRAM_BOT_TOKEN` | ✅ | @BotFather 的 `/newbot` 给的 Token |
| `BOT_OWNER_ID` | ⬜ | 你的数字 ID（@userinfobot 查），不填主人命令不可用 |
| `DEEPSEEK_API_KEY` | ⬜ | 不填则 AI 聊天 / 性格 / 思考 / 女友模式不可用 |
| `PROXY_URL` | ⬜ | 国内访问 Telegram 必填 |
| `VISION_MODEL` | ⬜ | 看图用的视觉模型，默认 `deepseek-flash` |
| `DISABLE_THINKING` | ⬜ | `true` = 关思考（默认，省 token） |

类型规则：bool 写 `true/false/1/0/yes/no`；整数直接写数字；元组用逗号分隔（`LINK_UNSUPPORTED_PLATFORMS=抖音,快手`）。

---

## 六、排障

| 现象 | 原因 / 处理 |
|:--|:--|
| 启动就报 `Unauthorized` | Token 不对或已被 `/revoke` |
| `409 Conflict` | 同一个 Token 有另一个实例在跑：`start.bat --stop` / `docker compose down` / `systemctl stop telegram-bot` |
| 启动卡住然后 `TimedOut` | 网络到不了 `api.telegram.org`，填 `PROXY_URL` |
| 日志里 `⚠️ config.py 缺少 N 个配置项` | 正常：老配置缺新键，已用模板默认值补齐，想自定义就复制进 `config.py` |
| 容器里看不了视频 | 镜像自带 ffmpeg；自己装的镜像记得装 `ffmpeg` |
| 数据"全丢了" | 直接 `python src/main.py` 时工作目录不同会写到另一个 `data/`；现在 main.py 会自己 `chdir` 到 `src/`，但历史遗留的 `./data` 需要手动搬 |
