# 图片 EXIF 编辑 API

支持 JPEG、PNG、WebP，单张图片最大 20 MiB。图片来源有两种：`multipart/form-data` 上传的 `image` 文件，或由服务端下载的 `image_url` 图片链接，两者只能提供其中一个。图片仅在单次请求期间保存在临时目录，请求结束后清理。服务端需安装 ExifTool；容器镜像已包含，其他部署可用 `EXIFTOOL_PATH` 指向可执行文件。

## `POST /api/v1/exif/inspect`

`multipart/form-data`，字段 `image` 为图片文件或 `image_url` 为图片链接。返回 JSON：

```json
{"format":"JPEG","tags":[{"key":"IFD0:Make","group":"IFD0","name":"Make","value":"Canon","writable":true,"reason":""}]}
```

`key` 是组名与标签名的组合，可直接用于编辑。只读标签的 `writable` 为 `false`，`reason` 说明原因。无 EXIF 时 `tags` 为空数组。

```bash
curl -X POST "http://localhost:8087/api/v1/exif/inspect" \
  -F "image_url=https://example.com/photo.jpg"
```

`image_url` 必须是以 `http://` 或 `https://` 开头的公开链接，仅支持 80 与 443 端口、最多 2048 字符、最多跟随 3 次重定向，且不能指向本机、内网或其他保留地址；链接超过 20 MiB 返回 413。服务端按图片内容识别格式，不信任链接的扩展名与 `Content-Type`。

## `GET /api/v1/exif/tags?q=DateTime`

搜索当前 ExifTool 版本支持的安全可写 EXIF 标签，`q` 可选，最多 100 字符；最多返回 100 项。响应示例：

```json
{"tags":[{"key":"ExifIFD:DateTimeOriginal","group":"ExifIFD","name":"DateTimeOriginal","type":"string","writable":true}]}
```

## `POST /api/v1/exif/edit`

`multipart/form-data`：原图为 `image` 文件或 `image_url` 图片链接（二选一），`changes` 为 JSON 字符串，包含 1 至 100 项操作。`key` 必须来自可写标签目录；`action` 为 `set` 或 `delete`。`set` 必须提供非空 `value`，最多 4096 字符；`delete` 不需要 `value`。

```bash
curl -X POST "http://localhost:8087/api/v1/exif/edit" \
  -F "image_url=https://example.com/photo.jpg" \
  -F 'changes=[{"key":"IFD0:Make","action":"set","value":"Superbox"}]' \
  -o edited-exif.jpg
```

```json
[
  {"key":"IFD0:Make","action":"set","value":"Superbox"},
  {"key":"ExifIFD:DateTimeOriginal","action":"delete"}
]
```

成功时返回原格式图片，`Content-Type` 为 `image/jpeg`、`image/png` 或 `image/webp`，`Content-Disposition` 带有下载文件名。失败时返回统一 JSON 错误：文件无效、标签只读、格式不支持写入、图片链接无效或无法下载为 400 `INVALID_INPUT`；请求字段无效为 422 `VALIDATION_ERROR`；图片超出 20 MiB 为 413 `FILE_TOO_LARGE`；ExifTool 不可用为 503 `EXIF_UNAVAILABLE`。

仅写 EXIF，不主动同步 XMP、IPTC。危险、二进制、厂商私有和结构性标签只读。写入在临时副本上进行，原始文件不会被修改；若目标格式不能写入指定标签，请求报错，不静默改写到其他元数据类型。
