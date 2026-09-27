# Superbox

一个由 FastAPI 提供工具能力、Vue 负责展示的开发工具箱。首批提供 JSON、Base64、URL 参数值和时间戳工具。所有搜索、校验与转换均通过后端 API 完成。

## 本地开发

后端（Python 3.12+）：

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

浏览器访问 Vite 输出的前端地址。顶栏“API 接入”会在新标签页打开独立的 `/api-access` 页面，按工具提供接口示例、在线测试和可复制的 AI 接入提示词。API 位于 `http://localhost:8087`；FastAPI 自动生成的交互式文档仍可在 `http://localhost:8087/docs` 用于内部核对，OpenAPI 定义位于 `http://localhost:8087/api/v1/openapi.json`。

## 仅后端容器化部署

在项目根目录运行：

```powershell
docker compose up --build -d
```

FastAPI 将通过 `http://localhost:8087` 提供服务，健康检查为 `/api/v1/health`。容器的构建上下文只有 `backend/`；前端不被构建、复制或提供。

前端单独部署：在 `frontend/` 中设置 `.env.production` 的 `VITE_API_BASE_URL` 为后端**浏览器可访问**的地址，然后运行 `npm ci` 和 `npm run build`，将 `dist/` 发布到静态网站。该变量在构建时写入前端文件；变更 API 地址后须重新构建。HTTPS 前端应使用 HTTPS API 地址，避免浏览器阻止混合内容。

Vue Router 使用 History 模式。静态网站服务需将不存在的页面路径回退到 `index.html`，例如 Nginx 的 `try_files $uri $uri/ /index.html;`，这样 `/tools/json` 等直达链接才能正常打开。

## 验证

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest
cd ..\frontend
npm run typecheck
npm run build
```

接口契约与扩展说明见 [docs/README.md](docs/README.md)。
