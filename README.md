# Superbox

一个由 FastAPI 提供工具能力、Vue 与 Android 负责展示的开发工具箱。提供 JSON、Base64、URL 参数值、时间戳、图片 EXIF、东八区当前时间、每日参考汇率和 PDF/DOCX/XLSX 转 Markdown/TXT 工具。所有搜索、校验与转换均通过后端 API 完成。

新增 API：`GET /api/v1/time/now`、`GET /api/v1/currency/currencies`、`POST /api/v1/currency/convert`、`POST /api/v1/currency/convert-batch`、`POST /api/v1/documents/convert`。官方 Skill 版本为 1.2.0，网页 `/api-access` 提供完整说明、在线测试和调用示例。

网页与 Android 汇率计算器支持搜索货币代码和中文名称、单币种交换、最多 50 种自选目标货币、结果卡片及单项/全部复制。批量转换合并为一次上游查询，逐项显示实际参考日期，部分失败保留成功结果；金额与汇率始终使用十进制字符串。继续使用免费无 Key 的 Frankfurter v2。

文件转换按需启动受限子进程：最大文件 5 MiB、并发 1、256 MiB 内存、10 秒 CPU、15 秒解析时间；支持 Linux 和 Windows，不执行 OCR 或公式。Compose 采用单 API worker，容器内存和 swap 总上限均为 512 MiB。汇率由服务器请求 Frankfurter 最新可用每日参考数据，不需要 API Key。细节见 [文件转换](docs/documents.md) 和 [汇率转换](docs/currency.md)。

## 本地开发

后端（Python 3.12+）：

EXIF 工具还需要 [ExifTool](https://exiftool.org/install.html)。将 `exiftool` 放入 PATH，或设置 `EXIFTOOL_PATH` 为可执行文件路径；容器构建会自动安装。

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8087
```

前端（Node.js 20.19+ 或 22.12+）：

```powershell
cd frontend
Copy-Item .env.example .env.local
npm install
npm run dev
```

浏览器访问 Vite 输出的前端地址。顶栏“API 接入”会在新标签页打开独立的 `/api-access` 页面：页头下方展示 AI 平台 Skill 的两个接口（官方 Markdown 与 JSON 清单，可复制地址或打开查看），工具卡片区按工具提供接口示例、在线测试和可复制的 AI 接入提示词。API 位于 `http://localhost:8087`；`http://localhost:8087/api/v1/skill` 返回一份覆盖全部能力的官方 Skill（纯 Markdown），`http://localhost:8087/api/v1/skill.json` 提供同源的结构化 JSON 清单（功能介绍与接入方式），均可交给其他 AI 平台按 URL 拉取。FastAPI 自动生成的交互式文档仍可在 `http://localhost:8087/docs` 用于内部核对，OpenAPI 定义位于 `http://localhost:8087/api/v1/openapi.json`。

## 仅后端容器化部署

在项目根目录运行：

```powershell
docker compose up --build -d
```

FastAPI 将通过 `http://localhost:8087` 提供服务，健康检查为 `/api/v1/health`。容器的构建上下文只有 `backend/`；前端不被构建、复制或提供。

前端单独部署：在 `frontend/` 中设置 `.env.production` 的 `VITE_API_BASE_URL` 为后端**浏览器可访问**的地址，然后运行 `npm ci` 和 `npm run build`，将 `dist/` 发布到静态网站。该变量在构建时写入前端文件；变更 API 地址后须重新构建。HTTPS 前端应使用 HTTPS API 地址，避免浏览器阻止混合内容。

Vue Router 使用 History 模式。静态网站服务需将不存在的页面路径回退到 `index.html`，例如 Nginx 的 `try_files $uri $uri/ /index.html;`，这样 `/api-access`、`/tools/json` 等直达链接才能正常打开。

部署到 1Panel 站点时有两种方式补齐该回退：

```powershell
# 方式一：服务器上执行（幂等，写入前备份并校验，失败自动回滚）
# 优先写入面板「伪静态」管理的 rewrite 文件，面板重建站点配置后规则依然生效
sudo bash scripts/configure-site-fallback.sh superbox.fiacloud.top /opt/1panel/www/sites/superbox.fiacloud.top/index
```

方式二：在 1Panel「网站 → 站点 → 伪静态」中粘贴以下内容并保存。

```nginx
location / {
    try_files $uri $uri/ /index.html;
}
```

GitHub Actions 部署流程会自动执行 `scripts/configure-site-fallback.sh`（步骤“确保站点支持 History 路由直达”），域名与站点目录取自工作流中的 `SITE_DOMAIN`、`WEB_ROOT`；若该步骤报错，按上面的方式二手动处理即可。

`npm run build` 还会为每个前端路由生成目录索引（`dist/api-access/index.html`、`dist/tools/<slug>/index.html`）：即使站点暂时没有回退规则，这些直达链接也能打开。工具列表变化时构建会自动补齐，无需手工维护。

## 验证

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest
cd ..\frontend
npm run typecheck
npm run build
```

线上发布后可直接核对前端直达链接与接口健康状态：

```powershell
curl.exe -s -o NUL -w "%{http_code}`n" https://superbox.fiacloud.top/api-access
curl.exe -s -o NUL -w "%{http_code}`n" https://superbox.fiacloud.top/tools/json
curl.exe -s -o NUL -w "%{http_code}`n" https://superbox.fiacloud.top/api/v1/health
```

接口契约与扩展说明见 [docs/README.md](docs/README.md)。
