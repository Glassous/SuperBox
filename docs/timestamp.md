# 时间戳转换接口

所有输出日期均为 UTC、以 `Z` 结尾。时间戳值通过字符串传输，避免不同客户端对大整数或小数的精度差异。

## 时间戳转日期

`POST /api/v1/timestamp/to-datetime`

请求体字段：`value` 是最长 40 字符的十进制整数时间戳；`unit` 必须是 `seconds` 或 `milliseconds`。

```json
请求：{"value":"1001","unit":"milliseconds"}
响应：{"iso_utc":"1970-01-01T00:00:01.001000Z"}
```

允许负数。非整数或超出 Python 日期支持范围的值返回 HTTP 400、`INVALID_INPUT`。

## 日期转时间戳

`POST /api/v1/timestamp/to-unix`

请求体 `iso_datetime` 最长 80 字符，必须是带 `Z` 或明确时区偏移的 ISO 8601 日期时间，不接受无时区日期。返回的秒、毫秒值为十进制字符串，可含小数以保留微秒精度。

```json
请求：{"iso_datetime":"1970-01-01T08:00:01.001+08:00"}
响应：{"iso_utc":"1970-01-01T00:00:01.001000Z","seconds":"1.001","milliseconds":"1001"}
```

无效日期或缺少时区返回 HTTP 400、`INVALID_INPUT`；缺少字段、错误单位或字段超长返回 HTTP 422、`VALIDATION_ERROR`。错误结构见 [总览](README.md#统一错误格式)。
