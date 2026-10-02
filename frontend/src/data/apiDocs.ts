export interface ApiField {
  name: string
  label: string
  type: string
  description: string
  options?: { value: string; label: string }[]
  multiline?: boolean
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
  binaryResponse?: boolean
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
    slug: 'exif',
    name: 'EXIF 编辑',
    category: '图片处理',
    description: '读取、编辑图片 EXIF 并下载原格式文件。',
    operations: [
      {
        id: 'inspect', name: '读取 EXIF', summary: '上传图片或提供图片链接，获取现有标签及可编辑状态。',
        path: '/exif/inspect', multipart: true,
        fields: [
          { name: 'image', label: '图片文件', type: 'file', description: '与 image_url 二选一，JPEG、PNG 或 WebP，最大 20 MB。' },
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
        id: 'edit', name: '编辑并下载', summary: '上传原图或提供图片链接和标签操作，返回修改后的原格式图片。',
        path: '/exif/edit', multipart: true, binaryResponse: true,
        fields: [
          { name: 'image', label: '图片文件', type: 'file', description: '与 image_url 二选一，JPEG、PNG 或 WebP，最大 20 MB。' },
          { name: 'image_url', label: '图片链接', type: 'url', description: '与 image 二选一，http/https 公开链接，最大 20 MB。' },
          { name: 'changes', label: '标签操作', type: 'JSON string', description: '必填，1 至 100 项；每项包含 key、action（set/delete），set 时包含 value。', multiline: true },
        ],
        exampleBody: { image: '<选择图片文件>', image_url: 'https://example.com/photo.jpg', changes: JSON.stringify([{ key: 'IFD0:Make', action: 'set', value: 'Superbox' }]) },
        exampleResponse: { type: 'image/jpeg | image/png | image/webp', download: 'edited-exif.<原格式扩展名>' },
        note: '仅修改安全可写的 EXIF 标签；图片像素不重新编码。图片链接由服务端下载，仅支持公开可访问的 http/https 地址，不指向内网。响应为二进制图片，请作为文件保存。',
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

export function makeAiPrompt(doc: ApiToolDoc, baseUrl: string): string {
  const endpoints = doc.operations.map(operation => `- ${operation.method ?? 'POST'} ${baseUrl}/api/v1${operation.path}（${operation.name}）：${operation.multipart ? 'multipart/form-data' : 'JSON／查询参数'}，请求 ${JSON.stringify(operation.exampleBody)}；成功响应示例 ${JSON.stringify(operation.exampleResponse)}`).join('\n')
  return `请帮我在现有项目中接入 Superbox 的「${doc.name}」API。先阅读项目现有的请求封装和代码风格，再根据我的技术栈实现调用，不要在客户端重写工具计算。\n\nAPI 基础地址：${baseUrl}/api/v1\n${doc.slug === 'exif' ? '图片接口使用 multipart/form-data：图片通过 image 文件或 image_url 图片链接二选一提供；编辑接口返回二进制图片，须保存为文件。' : '请求和响应均为 JSON；请求头使用 Content-Type: application/json。'}当前接口不需要认证。\n${endpoints}\n\n请为每个接口补齐请求与响应类型、调用函数、加载与错误状态，并给出一个最小使用示例和必要的测试。HTTP 400 表示 INVALID_INPUT，HTTP 422 表示 VALIDATION_ERROR；API 地址请放在环境配置中，不要写死在业务组件里。如果我还没有提供项目技术栈或目标页面，先向我确认。`
}
