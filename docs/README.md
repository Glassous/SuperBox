# Superbox API 文档

基础地址：`http://localhost:8087/api/v1`。所有工具操作使用 JSON 请求与响应，字符串输入长度为 1 至 1,000,000 个字符。时间戳与日期字段有各自的更短限制。所有工具运算和搜索均由后端执行。

面向接入方的页面位于前端路由 `/api-access`，提供分工具说明、在线测试与 AI 接入提示词。本目录中的 Markdown 文档保留接口契约，FastAPI 的 `/docs` 仅作为自动生成的技术参考。

| 功能 | 文档 |
| --- | --- |
| JSON 格式化、压缩、校验 | [json.md](json.md) |
| Base64 编解码 | [base64.md](base64.md) |
| URL 参数值编解码 | [url.md](url.md) |
| 时间戳转换 | [timestamp.md](timestamp.md) |

## 公共接口

- `GET /api/v1/health`：返回 `{"status":"ok"}`。
- `GET /api/v1/tools`：返回 `{"tools":[{"slug","name","category","description","keywords"}, ...]}`；可选 `q` 参数在名称、分类、描述和关键词中搜索，最多 100 字符。
- `GET /api/v1/tools/{slug}`：返回单个工具的元数据；未知 slug 返回 404。
- `GET /api/v1/openapi.json`：可供客户端生成器读取的 OpenAPI 定义。
- `GET /docs`：交互式接口文档。

## 统一错误格式

参数结构或长度无效时返回 HTTP 422，例如：

```json
{"code":"VALIDATION_ERROR","message":"请求参数无效","details":[{"field":"body.text","message":"String should have at least 1 character"}]}
```

内容无法进行对应操作时返回 HTTP 400，例如：

```json
{"code":"INVALID_INPUT","message":"时间戳必须是整数"}
```

未知接口或工具返回 HTTP 404，`code` 为 `NOT_FOUND`。客户端应依据 HTTP 状态及 `code` 处理错误，不解析中文提示文本。当前接口无需认证，CORS 允许所有来源，但不支持携带浏览器凭据的跨域请求。

## 新增工具

1. 在后端工具目录加入元数据，并为每个操作定义独立的版本化路由、请求／响应模型及服务函数。
2. 在前端加入对应表单组件，并将 slug 映射到组件；表单只发起请求与展示响应，不复制后端工具逻辑。
3. 在 `docs/` 新增功能文档，记录所有接口、字段、示例和错误；补充后端测试。
4. 若新操作需要对外部应用开放，优先沿用 `/api/v1` 的稳定契约；不兼容的变更使用新 API 版本。
