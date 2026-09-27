# JSON 工具接口

请求头：`Content-Type: application/json`。三个接口均接收 `{"text":"..."}`，其中 `text` 是 1 至 1,000,000 字符的标准 JSON 文本。顶层对象、数组和标量均可使用；`NaN`、`Infinity` 等非标准常量无效。

## 格式化

`POST /api/v1/json/format` 使用两个空格缩进，保留非 ASCII 字符。

```json
请求：{"text":"{\"name\":\"中文\"}"}
响应：{"result":"{\n  \"name\": \"中文\"\n}"}
```

## 压缩

`POST /api/v1/json/minify` 删除不必要的空白。

```json
请求：{"text":"{ \"a\": 1 }"}
响应：{"result":"{\"a\":1}"}
```

## 校验

`POST /api/v1/json/validate` 对语法无效的 JSON 返回 HTTP 200 与 `valid: false`，以便客户端显示校验结果。格式化或压缩遇到同样输入时返回 HTTP 400、`INVALID_INPUT`。

```json
请求：{"text":"{"}
响应：{"valid":false,"message":"JSON 无效：Expecting property name enclosed in double quotes: line 1 column 2 (char 1)"}
```

空文本、缺少字段、错误字段类型或超长文本返回 HTTP 422、`VALIDATION_ERROR`。错误结构见 [总览](README.md#统一错误格式)。
