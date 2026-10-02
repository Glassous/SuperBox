# 汇率转换

使用 [Frankfurter v2](https://frankfurter.dev/) 最新可用每日参考汇率，无需 API Key。银行交易价和手续费可能不同；客户端必须保留返回的汇率日期和来源。供应商请求由服务器发起。

## 货币目录

`GET /api/v1/currency/currencies`，无参数。

```json
{"currencies":[{"code":"CNY","name":"Chinese Renminbi Yuan"},{"code":"USD","name":"United States Dollar"}]}
```

实际支持项由供应商决定，目录缓存 24 小时。客户端展示时将名称本地化为中文，无法本地化时保留供应商名称；货币代码是 API 的唯一标识。

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

## 多币种金额转换

`POST /api/v1/currency/convert-batch`，JSON 请求：

```json
{"amount":"100","from_currency":"CNY","to_currencies":["USD","EUR","JPY"],"precision":2}
```

`amount`、`from_currency` 和 `precision` 与单币种接口相同。`to_currencies` 为 1–50 项三位货币代码的 JSON 数组，输出统一大写；大小写归一化后不能重复。空数组、超过 50 项、重复或字段格式无效返回 `422 / VALIDATION_ERROR`；不支持的原币种或任一目标币种返回 `400 / INVALID_INPUT`。

响应示例（示意部分失败，汇率为示例）：

```json
{
  "amount": "100", "from_currency": "CNY", "precision": 2, "count": 3,
  "results": [
    {"status":"success","amount":"100","from_currency":"CNY","to_currency":"USD","precision":2,"result":"14.00","rate":"0.14","rate_date":"2026-10-02","source":"Frankfurter","fetched_at":"2026-10-02T04:00:00+00:00","cached":false,"stale":false},
    {"status":"error","to_currency":"EUR","code":"EXCHANGE_RATE_UNAVAILABLE","message":"暂时无法获取该币种的汇率，请稍后重试"},
    {"status":"error","to_currency":"JPY","code":"EXCHANGE_RATE_UNAVAILABLE","message":"暂时无法获取该币种的汇率，请稍后重试"}
  ]
}
```

- `count` 为请求目标数量，包含成功与失败项；`results` 始终按请求顺序排列。
- 成功项在单币种响应字段基础上增加 `status=success`；失败项为 `status=error`，带目标币种、错误代码与提示，不伪造金额或日期。
- 部分成功返回 HTTP 200；全部不可用且没有有效缓存返回 `503 / EXCHANGE_RATE_UNAVAILABLE`。同币种不访问汇率接口，返回汇率 1。
- 先读取单币种和批量接口共用的缓存，仅将待更新目标合并成一次 Frankfurter 查询。同一基币、相同待更新目标集合的请求合并；最多 32 个待处理上游请求，超限返回 `429 / TOOL_BUSY`。
- 缓存保持 1 小时 TTL、最多 256 个货币对。上游失败、遗漏或返回无效行时，逐项使用获取时间不超过 24 小时的旧缓存，标记 `cached=true, stale=true`，否则返回该项错误。

网页和 Android 默认单币种人民币兑美元，金额 1、精度 2。多币种初始选择目录支持的美元、欧元、日元，可搜索并自由选择最多 50 种。货币列表和计算结果均来自 API；继续使用免费无 Key 的 Frankfurter，不配置密钥。
