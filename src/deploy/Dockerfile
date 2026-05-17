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
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    tzdata \
    && ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime \
    && echo "Asia/Shanghai" > /etc/timezone \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY main.py .
COPY config.py .
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
