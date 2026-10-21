# ============================================
#   🐱 小南专属TGbot - Docker 部署
#   适用于任何支持 Docker 的系统
# ============================================

# 使用 Python 3.11 作为基础镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Shanghai

# 安装系统依赖
# ffmpeg 是链接解析的硬需求：B站等站点只提供分离的音视频流，
# 必须由 ffmpeg 合并，否则视频下载不下来（见 requirements.txt 的说明）
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    tzdata \
    ffmpeg \
    && ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime \
    && echo "Asia/Shanghai" > /etc/timezone \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
# 注意：**不要** COPY config.py。
# 它被 .gitignore 忽略，全新克隆的仓库里不存在这个文件，
# docker build 会直接死在这一行：COPY failed: file not found in build context。
# 真正的 config.py 由 docker-compose 的 ../config.py 挂载进来（见 docker-compose.yml）。
COPY main.py .
COPY config.example.py .
COPY modules/ modules/
COPY deploy/commands.txt deploy/

# 创建数据目录
RUN mkdir -p data data/backups

# 声明数据卷
VOLUME ["/app/data"]

# 暴露端口（如果需要 Webhook）
EXPOSE 8080

# 启动命令
CMD ["python", "main.py"]
