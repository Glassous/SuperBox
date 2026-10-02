export interface ApiField {
  name: string
  label: string
  type: string
  description: string
  options?: { value: string; label: string }[]
  multiline?: boolean
  accept?: string
}

export interface ApiOperation {
  id: string
  name: string
  summary: string
  path: string
  fields: ApiField[]
  exampleBody: Record<string, string>
  exampleResponse: Record<string, unknown>
  note?: string
  method?: 'GET' | 'POST'
  multipart?: boolean
}

export interface ApiToolDoc {
  slug: string
  name: string
  category: string
  description: string
  operations: ApiOperation[]
}

const textField: ApiField = {
  name: 'text',
  label: '文本内容',
  type: 'string',
  description: '必填，1 至 1,000,000 个字符。',
  multiline: true,
}

export const apiDocs: ApiToolDoc[] = [
  {
    slug: 'time', name: '当前时间', category: '时间日期', description: '获取服务器当前日期和时间，固定显示东八区。',
    operations: [{ id: 'now', name: '获取当前时间', summary: '返回同一时间点的日期、时间、星期和时间戳，禁止缓存。', path: '/time/now', method: 'GET', fields: [], exampleBody: {},
      exampleResponse: { date: '2026-10-02', time: '12:00:00.000', iso_datetime: '2026-10-02T12:00:00.000+08:00', timezone: 'UTC+08:00', weekday: 5, unix_seconds: '1790913600', unix_milliseconds: '1790913600000' } }],
  },
  {
    slug: 'currency', name: '汇率转换', category: '数据处理', description: '使用每日参考汇率，将金额兑换为一种或最多 50 种自选货币，并保留日期和来源。',
    operations: [
      { id: 'currencies', name: '货币目录', summary: '获取支持的货币代码和名称。', path: '/currency/currencies', method: 'GET', fields: [], exampleBody: {}, exampleResponse: { currencies: [{ code: 'CNY', name: 'Chinese Renminbi Yuan' }, { code: 'USD', name: 'United States Dollar' }] } },
      { id: 'convert', name: '兑换金额', summary: '使用 Frankfurter 最新可用每日参考汇率进行兑换。', path: '/currency/convert', fields: [
        { name: 'amount', label: '金额', type: 'string', description: '非负十进制字符串，最多 15 位整数、8 位小数。' },
        { name: 'from_currency', label: '原币种', type: 'string', description: '货币目录中的三位货币代码。' },
        { name: 'to_currency', label: '目标币种', type: 'string', description: '货币目录中的三位货币代码。' },
        { name: 'precision', label: '小数位数', type: 'integer', description: '0–8，默认 2。', options: Array.from({ length: 9 }, (_, n) => ({ value: String(n), label: String(n) })) },
      ], exampleBody: { amount: '100', from_currency: 'CNY', to_currency: 'USD', precision: '2' },
      exampleResponse: { amount: '100', from_currency: 'CNY', to_currency: 'USD', precision: 2, result: '14.00', rate: '0.14', rate_date: '2026-10-02', source: 'Frankfurter', fetched_at: '2026-10-02T04:00:00+00:00', cached: false, stale: false },
      note: '参考汇率每日更新；必须保留汇率日期。缓存 1 小时，上游失败仅使用获取时间不超过 24 小时的缓存（stale=true）。无有效缓存返回 503 / EXCHANGE_RATE_UNAVAILABLE。同币种汇率 1，日期为 null。' },
      { id: 'convert-batch', name: '多币种兑换', summary: '将一个金额兑换为最多 50 种自选货币，结果按目标顺序返回。', path: '/currency/convert-batch', fields: [
        { name: 'amount', label: '金额', type: 'string', description: '非负十进制字符串，最多 15 位整数、8 位小数。' },
        { name: 'from_currency', label: '原币种', type: 'string', description: '货币目录中的三位货币代码。' },
        { name: 'to_currencies', label: '目标币种数组', type: 'string[]', multiline: true, description: 'JSON 字符串数组，1–50 个不重复的货币代码，例如 ["USD","EUR","JPY"]。' },
        { name: 'precision', label: '小数位数', type: 'integer', description: '0–8，默认 2。', options: Array.from({ length: 9 }, (_, n) => ({ value: String(n), label: String(n) })) },
      ], exampleBody: { amount: '100', from_currency: 'CNY', to_currencies: '["USD","EUR","JPY"]', precision: '2' },
      exampleResponse: { amount: '100', from_currency: 'CNY', precision: 2, count: 3, results: [{ status: 'success', amount: '100', from_currency: 'CNY', to_currency: 'USD', precision: 2, result: '14.00', rate: '0.14', rate_date: '2026-10-02', source: 'Frankfurter', fetched_at: '2026-10-02T04:00:00+00:00', cached: false, stale: false }, { status: 'error', to_currency: 'EUR', code: 'EXCHANGE_RATE_UNAVAILABLE', message: '暂时无法获取该币种的汇率，请稍后重试' }, { status: 'error', to_currency: 'JPY', code: 'EXCHANGE_RATE_UNAVAILABLE', message: '暂时无法获取该币种的汇率，请稍后重试' }] },
      note: '一次查询所有需要更新的目标汇率；结果按请求顺序返回。成功项 status=success；失败项 status=error，带 to_currency/code/message。部分成功返回 200，全部不可用返回 503 / EXCHANGE_RATE_UNAVAILABLE。重复或超过 50 项返回 422，不支持的货币返回 400。金额和汇率是字符串；逐项保留日期、来源及缓存标记。' },
    ],
  },
  {
    slug: 'documents', name: '文件转换', category: '文件处理', description: 'PDF、DOCX、XLSX 的文字和表格转 Markdown/TXT。',
    operations: [{ id: 'convert', name: '转换文件', summary: '上传文档或提供公开链接，返回转换后的文本与警告。', path: '/documents/convert', multipart: true,
      fields: [
        { name: 'file', label: '文件', type: 'file', accept: '.pdf,.docx,.xlsx', description: '与 file_url 二选一，最大 5 MiB。' },
        { name: 'file_url', label: '公开文件链接', type: 'url', description: '与 file 二选一，最多 2048 字符，仅公开 HTTP/HTTPS 地址。' },
        { name: 'format', label: '输出格式', type: 'string', description: 'markdown（默认）或 txt。', options: [{ value: 'markdown', label: 'Markdown' }, { value: 'txt', label: 'TXT' }] },
      ], exampleBody: { file_url: '', format: 'markdown' },
      exampleResponse: { result: '## 第 1 页\n\n示例正文', format: 'markdown', filename: 'document.md', source_type: 'pdf', stats: { pages: 1, worksheets: 0, cells: 0, characters: 14 }, warnings: [], url: 'https://superboxfiles.fiacloud.top/superbox-temp/1791007200/0123456789abcdef0123456789abcdef/document.md', content_type: 'text/markdown; charset=utf-8', size: 30, expires_at: '2026-10-03T06:00:00Z' },
      note: '返回 JSON，包含正文和 COS 下载地址 url、content_type、size（字节）、expires_at（UTC）；文件保留 2 小时。最多 100 页 PDF、20 工作表、累计 50,000 单元格、500,000 字符；Office ZIP 最多 2,000 条目和 50 MiB 解压大小。并发 1，内存 256 MiB、CPU 10 秒、解析 15 秒。不支持 OCR、DOC/XLS、宏、加密或复杂排版；不执行公式。超限报错，不截断。' }],
  },
  {
    slug: 'exif',
    name: 'EXIF 编辑',
    category: '图片处理',
    description: '读取、编辑图片 EXIF 并下载原格式文件。',
    operations: [
      {
        id: 'inspect', name: '读取 EXIF', summary: '上传图片或提供图片链接，获取现有标签及可编辑状态。',
        path: '/exif/inspect', multipart: true,
        fields: [
          { name: 'image', label: '图片文件', type: 'file', accept: '.jpg,.jpeg,.png,.webp', description: '与 image_url 二选一，JPEG、PNG 或 WebP，最大 20 MB。' },
          { name: 'image_url', label: '图片链接', type: 'url', description: '与 image 二选一，http/https 公开链接，最大 20 MB。' },
        ],
        exampleBody: { image: '<选择图片文件>', image_url: 'https://example.com/photo.jpg' },
        exampleResponse: { format: 'JPEG', tags: [{ key: 'IFD0:Make', group: 'IFD0', name: 'Make', value: 'Canon', writable: true, reason: '' }] },
      },
      {
        id: 'tags', name: '搜索可写标签', summary: '搜索当前 ExifTool 版本支持的安全可写 EXIF 标签。',
        path: '/exif/tags', method: 'GET',
        fields: [{ name: 'q', label: '关键词', type: 'string', description: '可选，最多 100 字符。' }],
        exampleBody: { q: 'DateTimeOriginal' },
        exampleResponse: { tags: [{ key: 'ExifIFD:DateTimeOriginal', group: 'ExifIFD', name: 'DateTimeOriginal', type: 'string', writable: true }] },
      },
      {
        id: 'edit', name: '编辑并下载', summary: '上传原图或提供图片链接和标签操作，返回修改后的原格式图片下载地址。',
        path: '/exif/edit', multipart: true,
        fields: [
          { name: 'image', label: '图片文件', type: 'file', accept: '.jpg,.jpeg,.png,.webp', description: '与 image_url 二选一，JPEG、PNG 或 WebP，最大 20 MB。' },
          { name: 'image_url', label: '图片链接', type: 'url', description: '与 image 二选一，http/https 公开链接，最大 20 MB。' },
          { name: 'changes', label: '标签操作', type: 'JSON string', description: '必填，1 至 100 项；每项包含 key、action（set/delete），set 时包含 value。', multiline: true },
        ],
        exampleBody: { image: '<选择图片文件>', image_url: 'https://example.com/photo.jpg', changes: JSON.stringify([{ key: 'IFD0:Make', action: 'set', value: 'Superbox' }]) },
        exampleResponse: { url: 'https://superboxfiles.fiacloud.top/superbox-temp/1791007200/0123456789abcdef0123456789abcdef/edited-exif.jpg', filename: 'edited-exif.jpg', content_type: 'image/jpeg', size: 12345, expires_at: '2026-10-03T06:00:00Z' },
        note: '仅修改安全可写的 EXIF 标签；图片像素不重新编码。图片链接由服务端下载，仅支持公开可访问的 http/https 地址，不指向内网。成功返回 JSON，请通过 url 下载；size 单位为字节，expires_at 为 UTC。文件保留 2 小时，COS 不可用或上传失败返回 503。',
      },
    ],
  },
  {
    slug: 'json',
    name: 'JSON 工具',
    category: '数据处理',
    description: '格式化、压缩和校验 JSON 内容。',
    operations: [
      {
        id: 'format',
        name: '格式化',
        summary: '使用两个空格缩进，并保留非 ASCII 字符。',
        path: '/json/format',
        fields: [textField],
        exampleBody: { text: '{"name":"Superbox","ready":true}' },
        exampleResponse: { result: '{\n  "name": "Superbox",\n  "ready": true\n}' },
        note: '接受标准 JSON 的对象、数组及顶层标量；NaN 和 Infinity 无效。',
      },
      {
        id: 'minify',
        name: '压缩',
        summary: '移除 JSON 中不必要的空白。',
        path: '/json/minify',
        fields: [textField],
        exampleBody: { text: '{ "name": "Superbox" }' },
        exampleResponse: { result: '{"name":"Superbox"}' },
      },
      {
        id: 'validate',
        name: '校验',
        summary: '检查 JSON 语法并返回校验结果。',
        path: '/json/validate',
        fields: [textField],
        exampleBody: { text: '{"name":"Superbox"}' },
        exampleResponse: { valid: true, message: 'JSON 格式有效' },
        note: '语法无效时仍返回 HTTP 200，响应中 valid 为 false；空输入等请求参数错误返回 422。',
      },
    ],
  },
  {
    slug: 'base64',
    name: 'Base64 编解码',
    category: '编码转换',
    description: '在 UTF-8 文本与 Base64 之间转换。',
    operations: [
      {
        id: 'encode',
        name: '编码',
        summary: '将 UTF-8 文本转换为标准 Base64。',
        path: '/base64/encode',
        fields: [textField],
        exampleBody: { text: '你好' },
        exampleResponse: { result: '5L2g5aW9' },
      },
      {
        id: 'decode',
        name: '解码',
        summary: '将标准 Base64 解码为 UTF-8 文本。',
        path: '/base64/decode',
        fields: [textField],
        exampleBody: { text: '5L2g5aW9' },
        exampleResponse: { result: '你好' },
        note: '无效 Base64、额外空白或解码后不是 UTF-8 文本时返回 400。',
      },
    ],
  },
  {
    slug: 'url',
    name: 'URL 编解码',
    category: '编码转换',
    description: '对单个 URL 参数值进行编码或解码。',
    operations: [
      {
        id: 'encode',
        name: '编码',
        summary: '将参数值按 UTF-8 百分号编码。',
        path: '/url/encode',
        fields: [textField],
        exampleBody: { text: '你好 & a+b' },
        exampleResponse: { result: '%E4%BD%A0%E5%A5%BD%20%26%20a%2Bb' },
        note: '用于 URL 参数值，不会把输入解析为完整网址。',
      },
      {
        id: 'decode',
        name: '解码',
        summary: '将百分号编码还原为 UTF-8 文本。',
        path: '/url/decode',
        fields: [textField],
        exampleBody: { text: '%E4%BD%A0%E5%A5%BD' },
        exampleResponse: { result: '你好' },
        note: '加号保持为“+”，不会转换为空格；无效转义或 UTF-8 返回 400。',
      },
    ],
  },
  {
    slug: 'timestamp',
    name: '时间戳转换',
    category: '时间日期',
    description: '在 Unix 时间戳与带时区的日期时间之间转换。',
    operations: [
      {
        id: 'to-datetime',
        name: '时间戳转日期',
        summary: '把整数 Unix 时间戳转换为 UTC 日期时间。',
        path: '/timestamp/to-datetime',
        fields: [
          { name: 'value', label: '时间戳', type: 'string', description: '必填，最多 40 字符的十进制整数。' },
          { name: 'unit', label: '单位', type: '"seconds" | "milliseconds"', description: '必填，明确指定秒或毫秒。', options: [{ value: 'seconds', label: '秒' }, { value: 'milliseconds', label: '毫秒' }] },
        ],
        exampleBody: { value: '1001', unit: 'milliseconds' },
        exampleResponse: { iso_utc: '1970-01-01T00:00:01.001000Z' },
        note: '允许负时间戳；超出支持日期范围时返回 400。',
      },
      {
        id: 'to-unix',
        name: '日期转时间戳',
        summary: '把带时区的 ISO 8601 日期时间转换为 Unix 时间戳。',
        path: '/timestamp/to-unix',
        fields: [{ name: 'iso_datetime', label: '日期时间', type: 'string', description: '必填，最多 80 字符；必须包含 Z 或时区偏移。' }],
        exampleBody: { iso_datetime: '1970-01-01T08:00:01.001+08:00' },
        exampleResponse: { iso_utc: '1970-01-01T00:00:01.001000Z', seconds: '1.001', milliseconds: '1001' },
        note: '秒和毫秒以字符串返回，可能包含小数，用于保留微秒精度。',
      },
    ],
  },
]

export function apiFieldValue(type: string, value: string): unknown {
  if (type === 'integer') return Number(value)
  if (type === 'string[]') {
    let parsed: unknown
    try { parsed = JSON.parse(value) } catch { throw new Error('目标币种请输入 JSON 数组，例如 ["USD","EUR"]') }
    if (!Array.isArray(parsed) || parsed.length < 1 || parsed.length > 50 ||
        parsed.some(item => typeof item !== 'string' || !/^[A-Za-z]{3}$/.test(item))) {
      throw new Error('目标币种须为包含 1–50 个三位货币代码的 JSON 数组')
    }
    if (new Set(parsed.map(item => item.toUpperCase())).size !== parsed.length) throw new Error('目标币种不能重复')
    return parsed
  }
  return value
}

export function apiExampleBody(operation: ApiOperation): Record<string, unknown> {
  return Object.fromEntries(Object.entries(operation.exampleBody).map(([key, value]) => [key,
    apiFieldValue(operation.fields.find(field => field.name === key)?.type ?? 'string', value)]))
}

export function makeAiPrompt(doc: ApiToolDoc, baseUrl: string): string {
  const endpoints = doc.operations.map(operation => `- ${operation.method ?? 'POST'} ${baseUrl}/api/v1${operation.path}（${operation.name}）：${operation.multipart ? 'multipart/form-data' : 'JSON／查询参数'}，请求 ${JSON.stringify(apiExampleBody(operation))}；成功响应示例 ${JSON.stringify(operation.exampleResponse)}`).join('\n')
  const transport = doc.operations.some(operation => operation.multipart)
    ? '文件接口使用 multipart/form-data，文件与公开链接二选一；不要手工设置 multipart 的 Content-Type，让客户端生成 boundary。所有工具接口返回 JSON。文件输出包含 COS 下载地址 url、filename、content_type、size 和 expires_at，文件保留 2 小时。'
    : 'GET 无请求体；POST 使用 JSON，Content-Type: application/json。各字段类型以接口文档为准。'
  const notes = doc.operations.map(operation => operation.note).filter(Boolean).join('\n')
  return `请帮我在现有项目中接入 Superbox 的「${doc.name}」API。先阅读项目现有的请求封装和代码风格，再根据我的技术栈实现调用，不要在客户端重写工具计算。\n\nAPI 基础地址：${baseUrl}/api/v1\n${transport} 当前接口不需要认证。\n${endpoints}\n${notes}\n\n请补齐请求与响应类型、调用函数、加载与错误状态。HTTP 400 / INVALID_INPUT，422 / VALIDATION_ERROR，413 表示容量超限，429 / TOOL_BUSY，503 表示服务不可用，504 / DOCUMENT_TIMEOUT；依据 HTTP 状态和 code 处理，不解析中文提示。API 地址放在环境配置中。文件转换结果的 result 用于预览和复制；保存文件时通过 url 下载，expires_at 为 UTC 到期时间。金额精度运算全部交给服务器。如果我还没有提供项目技术栈或目标页面，先向我确认。`
}
