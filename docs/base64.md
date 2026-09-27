# Base64 编解码接口

两个接口均接收 JSON 请求体 `{"text":"..."}`，`text` 长度为 1 至 1,000,000 字符，成功时返回 `{"result":"..."}`。操作对象是 UTF-8 文本，不处理任意二进制文件。

## 编码

`POST /api/v1/base64/encode`

```json
请求：{"text":"你好"}
响应：{"result":"5L2g5aW9"}
```

## 解码

`POST /api/v1/base64/decode` 使用严格 Base64 校验；解码得到的字节还必须是有效 UTF-8。不接受多余空白。

```json
请求：{"text":"5L2g5aW9"}
响应：{"result":"你好"}
```

无效 Base64 或非 UTF-8 解码结果返回 HTTP 400、`INVALID_INPUT`。空、缺失或超长输入返回 HTTP 422、`VALIDATION_ERROR`；详见 [总览](README.md#统一错误格式)。
