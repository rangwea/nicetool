# NiceTool 应用镜像
# 构建: docker build --platform linux/amd64 -t nicetool .
# 运行: docker run -d --env-file .env -p 8000:8000 --name nicetool nicetool
FROM python:3.13-alpine

COPY --from=ghcr.io/astral-sh/uv:0.12.12 /uv /uvx /usr/local/bin/

WORKDIR /app

# 将虚拟环境放在源码目录之外，支持挂载源码到 /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_PYTHON_DOWNLOADS=never \
    PATH="/opt/venv/bin:$PATH"

RUN apk add --no-cache curl

# 先安装锁定依赖，源码变更可复用依赖层
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project --no-cache

COPY . ./

# 健康检查随 PROJECT_PATH 和 PORT 配置变化；这里只检测 HTTP 服务存活。
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl --fail --silent "http://127.0.0.1:${PORT:-8000}${PROJECT_PATH:-}/health" || exit 1

CMD ["python", "main.py"]
