# 文件转 Markdown/TXT

`POST /api/v1/documents/convert`，使用 `multipart/form-data`，无需认证。

| 字段 | 说明 |
| --- | --- |
| `file` | PDF、DOCX 或 XLSX 上传文件，与 file_url 二选一，最大 5 MiB |
| `file_url` | 公开 HTTP/HTTPS 文件链接，与 file 二选一，最多 2048 字符 |
| `format` | `markdown`（默认）或 `txt` |

```bash
curl -X POST http://localhost:8087/api/v1/documents/convert -F 'file=@report.pdf' -F 'format=markdown'
curl -X POST http://localhost:8087/api/v1/documents/convert -F 'file_url=https://example.com/report.docx' -F 'format=txt'
```

```json
{"result":"## 第 1 页\n\n示例正文","format":"markdown","filename":"report.md","source_type":"pdf","stats":{"pages":1,"worksheets":0,"cells":0,"characters":14},"warnings":[]}
```

结果是 JSON 文本，不是二进制下载。客户端将 `result` 以 UTF-8 保存为 `filename`；服务端处理结束清理临时文件，不提供长期下载链接。`stats` 包含页数、工作表数、遍历单元格数、输出字符数；不适用的统计为 0。

## 提取行为

- PDF 提取已有文本层，Markdown 按页加入标题；纯扫描件报错，混合文件的无文字页通过 warnings 提示。未执行 OCR，不重建复杂表格或多栏排版。
- DOCX 按正文顺序提取标题、段落、表格；不还原图片、页眉页脚和复杂排版。
- XLSX 按工作表输出，Markdown 使用 A/B/C 等列字母作为表头，TXT 使用制表符。只读工作簿，不执行公式或外部链接；公式缺失缓存结果时输出空值并警告。
- 不支持 DOC、XLS、宏、模板或加密文件；验证真实类型，上传文件扩展名须与内容一致。
- 文件链接允许无扩展名的下载路由，类型按内容识别。只允许公开网络的 HTTP/HTTPS、80/443 端口，禁止内网与含凭据地址，最多 3 次重定向，每次重新验证地址。

## 资源限制

请求体最大 6 MiB；单文件最大 5 MiB。读取请求体前限制并发为 1，繁忙请求不排队。转换子进程最多 256 MiB 内存、10 秒 CPU 和 15 秒解析时间；Linux 使用 rlimit，Windows 使用 Job Object，不能建立限制时拒绝转换。公网下载也在子进程中执行，最多 10 秒总下载时间；下载完成后单独计时解析，取消请求会终止下载和解析。

PDF 最多 100 页；XLSX 最多 20 个工作表及累计 50,000 个遍历单元格；输出最多 500,000 字符；Office ZIP 最多 2,000 条目及累计 50 MiB 解压大小。超限明确失败，不返回截断内容。取消或超时终止处理子进程，并清理临时文件。

生产部署使用单个 Uvicorn worker，避免每个 worker 各自接纳一个转换任务。Compose 的容器内存及 swap 总上限均为 512 MiB；部署时需给操作系统和其他服务留出空间。

| HTTP | code | 含义 |
| --- | --- | --- |
| 400 | INVALID_INPUT | 来源冲突、空文件、损坏/不支持文件、无法读取文字或无效链接 |
| 422 | VALIDATION_ERROR | 字段类型、格式或长度无效 |
| 413 | FILE_TOO_LARGE | 文件或请求体超过限制 |
| 413 | DOCUMENT_LIMIT_EXCEEDED | 解压、页数、单元格、输出或内存超过限制 |
| 429 | TOOL_BUSY | 正在转换其他文件；Retry-After 为 2 秒 |
| 503 | DOCUMENT_UNAVAILABLE | 资源限制或处理进程不可用 |
| 504 | DOCUMENT_TIMEOUT | CPU 或解析时间超限 |
