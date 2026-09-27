#!/usr/bin/env bash
# 服务器端发布脚本：拉取 GHCR 镜像、重建容器并校验健康状态。
# 由 GitHub Actions 通过 SSH 调用，工作目录为部署目录（含 compose.yaml 与 .env）。
set -euo pipefail

cd "$(dirname "$0")"

env_file=".env"
if [ ! -f "$env_file" ]; then
  echo "::error::$env_file 不存在，请先创建生产配置（可参考 .env.example）" >&2
  exit 1
fi

value_of() {
  sed -n "s/^[[:space:]]*$1[[:space:]]*=[[:space:]]*//p" "$env_file" | tail -n 1 | sed -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//" -e 's/[[:space:]]*$//'
}

image="$(value_of SUPERBOX_IMAGE)"
if [ -z "$image" ]; then
  echo "::error::$env_file 中缺少 SUPERBOX_IMAGE" >&2
  exit 1
fi

# 去掉 tag 得到仓库名（ghcr.io 不带端口，可直接按最后一个冒号切分）
repo="${image%:*}"
if [ "$repo" = "$image" ]; then
  repo="$image"
fi

echo "拉取镜像：$image"
docker compose pull

echo "重建容器"
docker compose up -d --remove-orphans

echo "等待健康检查通过"
container_id="$(docker compose ps -q api)"
if [ -z "$container_id" ]; then
  echo "::error::未找到 api 容器" >&2
  docker compose logs --tail 50 api || true
  exit 1
fi

healthy=0
for _ in $(seq 1 40); do
  status="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$container_id" 2>/dev/null || echo unknown)"
  case "$status" in
    healthy|running)
      echo "服务状态：$status"
      healthy=1
      break
      ;;
    unhealthy|exited|dead)
      echo "::error::服务状态异常：$status" >&2
      docker compose logs --tail 80 api || true
      exit 1
      ;;
    *)
      sleep 3
      ;;
  esac
done

if [ "$healthy" -ne 1 ]; then
  echo "::error::等待健康检查超时" >&2
  docker compose logs --tail 80 api || true
  exit 1
fi

# 清理旧版本镜像（保留当前容器正在使用的那个）
current_image_id="$(docker inspect --format '{{.Image}}' "$container_id" 2>/dev/null || true)"
if [ -n "$current_image_id" ]; then
  docker images --filter "reference=${repo}" --format '{{.ID}}' | sort -u | while read -r id; do
    if [ "$id" != "$current_image_id" ]; then
      docker rmi "$id" >/dev/null 2>&1 || true
    fi
  done
fi

echo "发布完成：$image"
