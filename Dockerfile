# syntax=docker/dockerfile:1
#
# 小南专属TGbot —— 容器镜像
#
# 构建（在仓库根目录执行，构建上下文就是仓库根目录）：
#   docker build -t telegram-bot .
#   docker compose up -d --build          # 推荐，见根目录 docker-compose.yml
#
# 配置方式（二选一，环境变量优先）：
#   1) 环境变量：TELEGRAM_BOT_TOKEN / DEEPSEEK_API_KEY / PROXY_URL ...
#      镜像里**没有** config.py，main.py 会用 config.example.py 的默认值打底，
#      再用同名环境变量覆盖，所以容器部署不需要挂配置文件。
#   2) 挂载配置文件：-v ./src/config.py:/app/config.py:ro
#
# 注意：src/config.py、src/data/、.venv 都被 .dockerignore 排除，
#       自己的 Token 不会被烤进镜像。

FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    TZ=Asia/Shanghai

WORKDIR /app

# ffmpeg 不是可选项：B 站等站点只提供分离的音视频流，必须靠它合并，
# 否则链接解析拿不到视频（requirements.txt 里有同样说明）。
# tzdata 用来让容器里的 datetime.now() 是北京时间。
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg tzdata ca-certificates \
    && ln -snf "/usr/share/zoneinfo/${TZ}" /etc/localtime \
    && echo "${TZ}" > /etc/timezone \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 先装依赖，代码改动时能复用这层缓存
# PIP_INDEX_URL：国内构建慢/失败时传镜像源，例如
#   docker build --build-arg PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple .
ARG PIP_INDEX_URL=
COPY src/requirements.txt /app/requirements.txt
RUN if [ -n "$PIP_INDEX_URL" ]; then \
        python -m pip install -i "$PIP_INDEX_URL" -r /app/requirements.txt; \
    else \
        python -m pip install -r /app/requirements.txt; \
    fi

# 程序本体（config.py / data / .venv 已在 .dockerignore 里排除）
COPY src/ /app/

# 非 root 运行：容器里的进程不该有 root 权限
RUN useradd --create-home --uid 10001 bot \
    && mkdir -p /app/data /app/logs \
    && chown -R bot:bot /app
USER bot

# 数据目录（用户数据、白名单、付费记录都在这里，务必挂出去）
VOLUME ["/app/data"]

# polling 模式没有 HTTP 端口可探伤；main.py 启动成功后会写 data/bot.pid，
# 用这个文件判断进程是否真的活着（容器里 python 一定存在，不需要 curl）
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD python -c "import os,sys; sys.exit(0 if os.path.exists('data/bot.pid') else 1)"

CMD ["python", "-u", "main.py"]
