# URL 参数值编解码接口

接口处理单个 URL 参数值，语义与 `encodeURIComponent`／`decodeURIComponent` 相近，**不处理完整网址**。两个接口均接收 `{"text":"..."}`，长度为 1 至 1,000,000 字符，成功时返回 `{"result":"..."}`。

## 编码

`POST /api/v1/url/encode`

```json
请求：{"text":"你好 & a+b"}
响应：{"result":"%E4%BD%A0%E5%A5%BD%20%26%20a%2Bb"}
```

## 解码

`POST /api/v1/url/decode`

```json
请求：{"text":"%E4%BD%A0%E5%A5%BD%20%26%20a%2Bb"}
响应：{"result":"你好 & a+b"}
```

解码时 `+` 保持为加号，不转换为空格。无效百分号转义或无效 UTF-8 返回 HTTP 400、`INVALID_INPUT`；空、缺失或超长输入返回 HTTP 422、`VALIDATION_ERROR`。错误结构见 [总览](README.md#统一错误格式)。
