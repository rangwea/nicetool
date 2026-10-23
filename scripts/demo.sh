#!/bin/sh
# 从 .env 读取界面语言；数据库和认证仍使用 Compose 固定的演示配置。
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
if ! command -v docker >/dev/null 2>&1; then
    echo '未找到 Docker。请安装并启动支持 Compose v2 的 Docker，再运行此脚本。' >&2
    exit 1
fi
COMPOSE_ENV="$ROOT/.env"
if [ ! -f "$COMPOSE_ENV" ]; then
    COMPOSE_ENV="$ROOT/.env.example"
fi
# 界面语言以配置文件为准，不使用终端里残留的同名变量。
unset LANGUAGE
if docker compose version >/dev/null 2>&1; then
    compose() { docker compose "$@"; }
elif command -v docker-compose >/dev/null 2>&1; then
    compose() { docker-compose "$@"; }
else
    echo '需要 Docker Compose v2 或更新版本。' >&2
    exit 1
fi
if ! docker info >/dev/null 2>&1; then
    echo 'Docker 服务未启动或当前用户无法访问。' >&2
    exit 1
fi
if ! compose --env-file "$COMPOSE_ENV" -f "$ROOT/compose.demo.yaml" up --build -d --wait --wait-timeout 240; then
    echo '演示启动失败。请运行以下命令检查状态：' >&2
    echo "docker compose --env-file /dev/null -f \"$ROOT/compose.demo.yaml\" ps" >&2
    echo "docker compose --env-file /dev/null -f \"$ROOT/compose.demo.yaml\" logs --tail 80 app db" >&2
    exit 1
fi
printf '\n演示已启动：http://localhost:%s/user\n' "${DEMO_PORT:-8000}"
printf '全部数据均为合成数据，演示仅供本机使用。\n'
