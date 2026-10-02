# 汇率转换

使用 [Frankfurter v2](https://frankfurter.dev/) 最新可用每日参考汇率，无需 API Key。银行交易价和手续费可能不同；客户端必须保留返回的汇率日期和来源。供应商请求由服务器发起。

## 货币目录

`GET /api/v1/currency/currencies`，无参数。

```json
{"currencies":[{"code":"CNY","name":"Chinese Renminbi Yuan"},{"code":"USD","name":"United States Dollar"}]}
```

实际支持项由供应商决定，目录缓存 24 小时。

## 金额转换

`POST /api/v1/currency/convert`，JSON 请求：

```json
{"amount":"100","from_currency":"CNY","to_currency":"USD","precision":2}
```

- `amount`：必填字符串，非负普通十进制数，最多 15 位整数、8 位小数，不接受指数、NaN、Infinity、符号或多余前导零。
- `from_currency` / `to_currency`：目录中的三位字母代码，不区分大小写，输出大写。
- `precision`：可选整数，0–8，默认 2，Decimal 四舍五入（ROUND_HALF_UP）。

响应示例（汇率仅为示例）：

```json
{"amount":"100","from_currency":"CNY","to_currency":"USD","precision":2,"result":"14.00","rate":"0.14","rate_date":"2026-10-02","source":"Frankfurter","fetched_at":"2026-10-02T04:00:00+00:00","cached":false,"stale":false}
```

金额、结果和汇率以字符串传输。`rate_date` 是供应商实际报价日期，节假日可能早于今天；`fetched_at` 是服务端获取时间（UTC）。同币种返回汇率 `1`，`source=identity`，`rate_date` 和 `fetched_at` 为 null。

汇率缓存 1 小时，最多 256 个货币对，相同并发请求合并。供应商失败仅可使用获取时间不超过 24 小时的旧缓存，返回 `cached=true, stale=true`；不伪造新日期。缓存为进程内缓存，重启后重新获取。

错误沿用 `{code,message,details?}`：422/VALIDATION_ERROR 表示字段无效，400/INVALID_INPUT 表示不支持的货币，503/EXCHANGE_RATE_UNAVAILABLE 表示供应商不可用且无有效缓存，429/TOOL_BUSY 表示并发上游请求过多。
