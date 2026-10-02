# 当前时间

`GET /api/v1/time/now`，无参数，无需认证。服务端从同一个时间点生成所有字段，固定转换为东八区 `UTC+08:00`，与服务器本地时区无关。响应包含 `Cache-Control: no-store`。

```json
{"date":"2026-10-02","time":"12:00:00.000","iso_datetime":"2026-10-02T12:00:00.000+08:00","timezone":"UTC+08:00","weekday":5,"unix_seconds":"1790913600","unix_milliseconds":"1790913600000"}
```

`weekday` 为 ISO 星期（一=1，日=7）；秒和毫秒时间戳为整数字符串。`date`、`time` 和 ISO 字符串均为获取时的时间，客户端刷新时应再次调用。服务器须维护准确的系统时钟。

已有 `/timestamp/to-datetime` 及 `/timestamp/to-unix` 的 UTC 语义保持不变。
