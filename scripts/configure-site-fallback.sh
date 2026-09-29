#!/usr/bin/env bash
# 为静态托管的 SPA 站点补齐 History 回退规则。
#
# 背景：前端使用 Vue Router 的 History 模式，/api-access、/tools/<slug> 等路径在
# 静态服务器上没有对应文件，若站点未配置回退就会直接返回 404。本脚本会在
# 1Panel（OpenResty/Nginx）站点配置里写入 try_files 回退，并在写入前校验语法、
# 失败时回滚，重复执行不会产生重复规则。
#
# 用法（服务器上以 root 运行）：
#   sudo bash configure-site-fallback.sh <站点域名> [站点根目录] [--dry-run]
#
# 退出码：0 已存在或写入成功；1 无法安全修改（会打印手动处理方式）；2 参数/权限错误。
set -euo pipefail

fallback_directive='try_files $uri $uri/ /index.html;'
comment_line='# Superbox SPA 回退：History 路由直达时回退到 index.html（由部署流程维护）'

dry_run=0
positional=()
for arg in "$@"; do
  case "$arg" in
    --dry-run) dry_run=1 ;;
    -h|--help) sed -n '2,12p' "$0"; exit 0 ;;
    *) positional+=("$arg") ;;
  esac
done

domain="${positional[0]:-}"
site_root="${positional[1]:-}"

log() { printf '[spa-fallback] %s\n' "$*"; }
fail() { printf '::error::[spa-fallback] %s\n' "$*" >&2; exit 1; }

manual_hint() {
  printf '::error::[spa-fallback] 未能自动配置站点 %s，请在 1Panel「网站 → %s → 伪静态」中粘贴以下内容并保存：\n    location / {\n        %s\n    }\n' \
    "$domain" "$domain" "$fallback_directive" >&2
}

if [ -z "$domain" ]; then
  printf '::error::用法：%s <站点域名> [站点根目录] [--dry-run]\n' "$0" >&2
  exit 2
fi

if [ "$(id -u)" -ne 0 ]; then
  printf '::error::请以 root 运行：sudo bash %s %s\n' "$0" "$domain" >&2
  exit 2
fi

conf_roots=(
  /opt/1panel/apps/openresty/openresty/conf
  /opt/1panel/apps/nginx/nginx/conf
  /usr/local/openresty/nginx/conf
  /etc/nginx
)

grep_args=(-rl -F -e "$domain")
if [ -n "$site_root" ]; then
  grep_args+=(-e "$site_root")
fi

declare -a candidates=()
matched_root=''
for root in "${conf_roots[@]}"; do
  [ -d "$root" ] || continue
  found_root=0
  while IFS= read -r file; do
    if [ -n "$file" ]; then
      candidates+=("$file")
      found_root=1
    fi
  done < <(grep "${grep_args[@]}" --include='*.conf' "$root" 2>/dev/null || true)
  if [ "$found_root" -eq 1 ]; then
    matched_root="$root"
  fi
done

if [ "${#candidates[@]}" -gt 0 ]; then
  mapfile -t candidates < <(printf '%s\n' "${candidates[@]}" | sort -u)
fi

if [ "${#candidates[@]}" -eq 0 ]; then
  manual_hint
  exit 1
fi

log "命中站点配置：${candidates[*]}"

# 优先写入 1Panel「伪静态」管理的 rewrite 文件：面板重建站点配置时该文件仍会被 include。
rewrite_file=''
for file in "${candidates[@]}"; do
  while IFS= read -r include_path; do
    include_path="${include_path//\"/}"
    include_path="${include_path//\'/}"
    include_path="${include_path%\*}"
    case "$include_path" in
      *rewrite*)
        rewrite_file="$include_path"
        break
        ;;
    esac
  done < <(grep -oE 'include[[:space:]]+[^;]*rewrite[^;]*;' "$file" 2>/dev/null |
    sed -E 's/^include[[:space:]]+//; s/;[[:space:]]*$//' || true)
  [ -n "$rewrite_file" ] && break
done

target=''
mode=''
if [ -n "$rewrite_file" ]; then
  target="$rewrite_file"
  mode='rewrite'
else
  # 没有伪静态 include 时直接改站点配置：文件里只要存在 server 块或 location / 即可安全注入。
  for file in "${candidates[@]}"; do
    if grep -qE '^[[:space:]]*server[[:space:]]*\{' "$file" ||
      grep -qE '^[[:space:]]*location[[:space:]]+/[[:space:]]*\{' "$file"; then
      target="$file"
      mode='server-block'
      break
    fi
  done
fi

if [ -z "$target" ]; then
  manual_hint
  exit 1
fi

log "写入目标：$target（模式：$mode）"

if [ -f "$target" ] && grep -qF "$fallback_directive" "$target"; then
  log "已存在 SPA 回退规则，无需修改"
  exit 0
fi

if [ -f "$target" ] && grep -qE '^[[:space:]]*try_files' "$target"; then
  fail "配置 $target 中已存在其它 try_files 规则，为避免破坏现有行为未自动修改；请手动把 location / 的 try_files 调整为：$fallback_directive"
fi

tmp_file="$(mktemp)"
if [ -f "$target" ]; then
  # server 块感知的注入：块内已有 location / 时补一条 try_files，
  # 否则在该 server 块闭合前补一个完整 location / 块；
  # 目标文件不含 server 块（伪静态片段）时留空，交由后面的追加逻辑处理。
  awk -v comment="$comment_line" -v directive="$fallback_directive" '
    function braces(text, char,   i, total) {
      total = 0
      for (i = 1; i <= length(text); i++) {
        if (substr(text, i, 1) == char) total++
      }
      return total
    }
    {
      line[NR] = $0
      opens = braces($0, "{")
      closes = braces($0, "}")
      if (!in_server && $0 ~ /^[[:space:]]*server[[:space:]]*\{/) {
        in_server = 1
        depth = opens - closes
        total++
        server_start[total] = NR
        has_root[total] = 0
      } else if (in_server) {
        depth += opens - closes
        if ($0 ~ /^[[:space:]]*location[[:space:]]+\/[[:space:]]*\{/) has_root[total] = 1
        if (depth <= 0) {
          server_end[total] = NR
          in_server = 0
        }
      }
    }
    END {
      for (i = 1; i <= NR; i++) {
        for (s = 1; s <= total; s++) {
          if (!has_root[s] && i == server_end[s]) {
            print "    " comment
            print "    location / {"
            print "        " directive
            print "    }"
          }
        }
        print line[i]
        for (s = 1; s <= total; s++) {
          if (i < server_start[s] || i > server_end[s]) continue
          if (has_root[s] && line[i] ~ /^[[:space:]]*location[[:space:]]+\/[[:space:]]*\{/) {
            print "        " comment
            print "        " directive
          }
        }
      }
    }
  ' "$target" > "$tmp_file"
fi

if ! grep -qF "$fallback_directive" "$tmp_file"; then
  {
    printf '\n%s\n' "$comment_line"
    printf 'location / {\n    %s\n}\n' "$fallback_directive"
  } >> "$tmp_file"
fi

if [ "$dry_run" -eq 1 ]; then
  log "--dry-run：以下内容将写入 $target"
  cat "$tmp_file"
  rm -f "$tmp_file"
  exit 0
fi

had_target=0
backup_file=''
if [ -f "$target" ]; then
  had_target=1
  backup_file="$(mktemp)"
  cp -p "$target" "$backup_file"
fi

mkdir -p "$(dirname "$target")"
install -m 0644 "$tmp_file" "$target"
rm -f "$tmp_file"

# 载体探测：优先选择挂载了本次命中配置目录的容器，避免误用其它应用的 Nginx 实例。
find_web_container() {
  command -v docker >/dev/null 2>&1 || return 0
  local names name fallback=''
  names="$(docker ps --format '{{.Names}}' 2>/dev/null | grep -iE 'openresty|nginx' || true)"
  [ -n "$names" ] || return 0
  while IFS= read -r name; do
    [ -n "$name" ] || continue
    if [ -n "$matched_root" ] &&
      docker inspect "$name" --format '{{range .Mounts}}{{.Source}}{{"\n"}}{{end}}' 2>/dev/null | grep -qF "$matched_root"; then
      printf '%s' "$name"
      return 0
    fi
    if [ -z "$fallback" ]; then
      fallback="$name"
    fi
  done <<< "$names"
  printf '%s' "$fallback"
}

reload_web() {
  local container
  container="$(find_web_container)"
  if [ -n "$container" ]; then
    # 已定位到实际承载站点配置的容器：校验或重载失败即视为失败，不用宿主命令掩盖。
    if docker exec "$container" sh -c '
      if command -v nginx >/dev/null 2>&1; then nginx -t && nginx -s reload
      elif command -v openresty >/dev/null 2>&1; then openresty -t && openresty -s reload
      else echo "容器内未找到 nginx/openresty 命令" >&2; exit 1
      fi'; then
      return 0
    fi
    printf '::error::[spa-fallback] 容器 %s 校验或重载失败\n' "$container" >&2
    return 1
  fi
  if command -v openresty >/dev/null 2>&1; then
    openresty -t && openresty -s reload && return 0
  fi
  if command -v nginx >/dev/null 2>&1; then
    nginx -t && nginx -s reload && return 0
  fi
  printf '::error::[spa-fallback] 未找到可校验/重载的 OpenResty 或 Nginx（宿主与容器均未命中）\n' >&2
  return 1
}

if ! reload_web; then
  if [ "$had_target" -eq 1 ]; then
    cp -p "$backup_file" "$target"
  else
    rm -f "$target"
  fi
  reload_web >/dev/null 2>&1 || true
  fail "Nginx 配置校验失败，已回滚 $target"
fi

[ -n "$backup_file" ] && rm -f "$backup_file"
log "SPA 回退规则已生效：$target"
