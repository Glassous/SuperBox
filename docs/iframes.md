# Iframe 仓库

Iframe 仓库提供可直接嵌入任意网页的挂件。后端维护条目目录，并渲染可直接作为 `iframe src` 的 HTML 嵌入页；嵌入页为 `text/html`，不是 JSON。目录不属于 `/api/v1/tools` 工具，接口均无需认证。

当前条目：

| slug | 名称 | 分类 | 内容类型 | 推荐尺寸 |
| --- | --- | --- | --- | --- |
| `milk-frog` | 奶蛙 | 图片展示 | `image` | 640 × 640 |
| `taffy` | Taffy探头 | 图片展示 | `image` | 415 × 595 |
| `penguin` | 凑企鹅 | 3D 互动 | `page` | 800 × 800 |

## 目录与搜索

`GET /api/v1/iframes`，可选 `q` 参数在名称、分类、描述和关键词中搜索，最多 100 字符。

```bash
curl http://localhost:8087/api/v1/iframes
curl 'http://localhost:8087/api/v1/iframes?q=奶蛙'
```

```json
{
  "iframes": [
    {
      "slug": "milk-frog",
      "name": "奶蛙",
      "category": "图片展示",
      "description": "奶蛙图片展示，可直接嵌入任意网页。",
      "keywords": ["奶蛙", "图片", "milk frog", "iframe"],
      "content_type": "image",
      "content_url": "https://officialimages.glassous.top/other/%E5%A5%B6%E8%9B%99.png",
      "preview_url": "https://officialimages.glassous.top/other/%E5%A5%B6%E8%9B%99.png",
      "thumbnail_url": "https://officialimages.glassous.top/other/%E5%A5%B6%E8%9B%99.png",
      "embed_path": "/api/v1/iframes/milk-frog/embed",
      "embed_url": "https://superbox.fiacloud.top/api/v1/iframes/milk-frog/embed",
      "width": 640,
      "height": 640,
      "sandbox": "",
      "allow": ""
    },
    {
      "slug": "penguin",
      "name": "凑企鹅",
      "category": "3D 互动",
      "description": "基于 three.js 的凑企鹅 3D 挂件，可切换三段动作并拖拽旋转视角。",
      "keywords": ["凑企鹅", "企鹅", "3d", "three.js", "模型", "penguin", "iframe"],
      "content_type": "page",
      "content_url": "https://superbox.fiacloud.top/widgets/penguin",
      "preview_url": "https://superboxfiles.fiacloud.top/Iframe/%E5%87%91%E4%BC%81%E9%B9%85.png",
      "thumbnail_url": "https://superboxfiles.fiacloud.top/Iframe/%E5%87%91%E4%BC%81%E9%B9%85.png",
      "embed_path": "/api/v1/iframes/penguin/embed",
      "embed_url": "https://superbox.fiacloud.top/api/v1/iframes/penguin/embed",
      "width": 800,
      "height": 800,
      "sandbox": "allow-scripts allow-same-origin",
      "allow": ""
    }
  ]
}
```

`page` 条目的 `content_url` 必须写绝对地址，嵌入页会把它作为嵌套 iframe 的 `src`；`sandbox` 需要允许脚本，否则挂件无法运行。3D 挂件的 `sandbox` 为 `allow-scripts allow-same-origin`：缺少 `allow-same-origin` 时 iframe 变为不透明源，同源加载模型文件会被按跨域请求拒绝。

## 详情

`GET /api/v1/iframes/{slug}`，返回单个条目的元数据，字段与目录项一致。`embed_url` 由 API 基础地址与 `embed_path` 拼接得到；站点经反向代理与 API 同域时，直接使用当前站点地址拼接即可。未知 slug 返回 404，`code` 为 `NOT_FOUND`。

```bash
curl http://localhost:8087/api/v1/iframes/milk-frog
```

## 嵌入页

`GET /api/v1/iframes/{slug}/embed`，返回可直接作为 `iframe src` 的完整 HTML（`text/html; charset=utf-8`）。

- `image` 类型渲染全屏 `<img>`，使用 `object-fit: contain` 居中显示；嵌入页不绘制任何底色，`html`、`body`、`img` 均为透明，透明 PNG 的留白直接透出宿主页面。
- `page` 类型渲染嵌套 `<iframe>`，按条目的 `sandbox` 与 `allow` 输出，并附加一段脚本把父页面与挂件页之间的 `postMessage` 互相转发；嵌入页的查询串会原样透传给挂件页（如 `?action=2&chrome=0`）。
- 响应头包含 `Cache-Control: public, max-age=300` 与按内容类型生成的 CSP；不设置 `X-Frame-Options`，允许被任意站点嵌入。
- 图片页 CSP 为 `default-src 'none'; img-src https: http: data:; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'`；网页页把 `img-src` 换成 `frame-src https: http:`，并增加 `script-src 'unsafe-inline'` 供消息转发脚本使用。
- 所有条目都不植入底色：网页条目 `body` 透明、内层 iframe 也透明，宿主看到的就是模型本身；图片条目的奶蛙与 Taffy探头都是透明 PNG，嵌入页同样不铺浅色/深色留白，宿主页面是什么底色就透出什么底色。嵌入页也不输出 `color-scheme`，避免浏览器按系统深浅色给画布补一层黑底或白底。
- 未知 slug 返回统一的 JSON 404，而不是 HTML。

```bash
curl -i http://localhost:8087/api/v1/iframes/milk-frog/embed
```

## 嵌入代码

把 `embed_url` 放入 `src`，按推荐尺寸设置宽高。`embed_url` 就是「API 基础地址 + `embed_path`」，反向代理部署下直接拼接站点公网地址：

```html
<iframe src="https://superbox.fiacloud.top/api/v1/iframes/milk-frog/embed" title="奶蛙" width="640" height="640" loading="lazy" sandbox="" style="border:0;max-width:100%"></iframe>
```

`sandbox=""` 表示不允许脚本，适合纯图片条目；网页类型条目按元数据返回的 `sandbox`、`allow` 填写。网页 `/iframes` 列出全部条目，点击卡片会从原位放大成居中对话框，URL 保持不变；弹窗默认只展示预览图，点击播放按钮后才加载实时预览，随后可以复制嵌入代码、打开嵌入页或复制嵌入地址，点击遮罩、关闭按钮或按 `Esc` 收回列表。

凑企鹅 3D 挂件的嵌入代码（脚本与同源资源都需要放行）：

```html
<iframe src="https://superbox.fiacloud.top/api/v1/iframes/penguin/embed" title="凑企鹅" width="800" height="800" loading="lazy" sandbox="allow-scripts allow-same-origin" style="border:0;max-width:100%;background:transparent"></iframe>
```

弹窗的预览区与列表卡片共用同一个 `<img>` 元素：展开时图片容器直接形变到弹窗预览位置，不会发起第二次图片请求。预览框按图片原始比例与可用高度计算尺寸（高度受限、宽度随比例变化），图片完整显示不裁切。点击播放后才挂载实时 iframe：`page` 条目加载 `content_url` 页面本身（本地开发时改取同源路径，避免请求尚未部署的线上地址），`image` 条目加载后端嵌入页；关闭弹窗或点击「返回预览图」会立刻卸载 iframe，避免 3D 挂件在后台继续渲染。前端不提供 `/iframes/{slug}` 页面，条目信息只在弹窗中展示。

## 字段说明

| 字段 | 说明 |
| --- | --- |
| `slug` | 条目标识，用于 API 详情、嵌入页路径与弹窗内标识 |
| `name` | 展示名称，同时作为嵌入页标题 |
| `category` | 分类文案 |
| `description` | 简介 |
| `keywords` | 搜索关键词 |
| `content_type` | `image` 或 `page` |
| `content_url` | 原始图片或网页地址 |
| `preview_url` | 预览图地址，供列表卡片与弹窗预览使用；图片条目默认复用 `content_url`，网页条目取条目声明的预览截图，未声明时为空字符串 |
| `thumbnail_url` | 列表缩略图地址，当前与 `preview_url` 同源；无预览图的条目为空字符串 |
| `embed_path` | 嵌入页的站内路径 |
| `embed_url` | 嵌入页绝对地址，由 API 基础地址与 `embed_path` 拼接 |
| `width`、`height` | 推荐嵌入尺寸，不是原始像素尺寸 |
| `sandbox` | 建议写入 `iframe` 的 `sandbox` 值，空字符串表示禁止脚本 |
| `allow` | 建议写入 `iframe` 的 `allow` 值，可为空 |

## 错误行为

| HTTP | code | 含义 |
| --- | --- | --- |
| 404 | NOT_FOUND | 未知 slug，详情与嵌入页一致 |
| 422 | VALIDATION_ERROR | `q` 超过 100 字符 |

## 新增 Iframe 条目

1. 在 `backend/app/iframes.py` 的 `IFRAMES` 列表加入条目：`slug`、`name`、`category`、`description`、`keywords`、`content_type`、`content_url`、`preview_url`、`width`、`height`、`sandbox`、`allow`。`preview_url` 可留空：`image` 条目自动复用 `content_url`，`page` 条目留空则列表显示占位图。`page` 条目的 `content_url` 必须是绝对地址，并先完成前端页面部署。素材建议使用透明底 PNG 或透明背景页面，嵌入页不会给条目补底色。
2. 在 `backend/tests/test_iframes.py` 补充目录、搜索、详情与嵌入页断言；如条目数变化，同步 `backend/tests/test_api.py` 中的 Skill 接口总数。
3. 需要条目级文档时在本目录新增说明；网页 `/iframes` 会自动展示目录与弹窗预览，无需为单个条目改动前端代码，构建脚本也不再生成条目级静态路由。
4. 图片地址直接引用外部图床；若图床限制防盗链，需要改为服务端代理或转存 COS。
5. 挂件页面本身是前端路由。新增挂件时在 `frontend/src/views` 创建页面、在 `frontend/src/router/index.ts` 注册路由，并把路由目录加入 `frontend/scripts/generate-spa-fallbacks.mjs` 的兜底列表，否则静态托管会 404。

## 凑企鹅 3D 挂件

挂件页面为前端路由 `/widgets/penguin`（`meta.bare`，不渲染站点头部），three.js 随站点构建，模型文件从 COS 加载：`https://superboxfiles.fiacloud.top/Iframe/%E5%87%91%E4%BC%81%E9%B9%85.glb`。该地址需要桶开启 CORS 并放行站点来源与本地开发来源（`http://localhost:5173`），否则 `GLTFLoader` 的跨域读取会失败。Iframe 仓库的弹窗在点击播放后以 iframe 形式加载该页面，关闭弹窗即卸载。

- 页面初始静态，点击「动作一 / 动作二 / 动作三」只播放对应片段：播到区间末尾后停止并回到绑定姿态；播放中再次点击当前动作可提前中断。
- 三段动作共用模型里 `Action` 这一条时间轴（总长 55.67s / 1671 帧 / 30fps），按帧区间定位播放：动作一第 1–63 帧、动作二第 70–149 帧、动作三第 150–1670 帧。实现方式与 `GlLab/web` 的 `loadGlbModel` 一致：`action.time = (起始帧 - 1) / 30`，`LoopOnce` + `clampWhenFinished`，`action.time` 到达 `(结束帧 - 1) / 30` 时停止并恢复骨骼绑定姿态，代码在 `frontend/src/three/penguinClips.ts` 与 `penguinScene.ts`。
- 舞台、轨道控件、按需渲染与资源释放实现在 `frontend/src/three/penguinScene.ts`；页面不可见或离开容器视口时暂停动画帧。
- 页面背景透明、无舞台底色与边框；相机按模型包围盒取景并在四周留出约 1/8 的边距，企鹅占据画面主体但不贴边。直接访问或站内弹窗预览时保留三段动作的小胶囊按钮；通过嵌入页对外提供时默认追加 `chrome=0`，宿主只会看到模型本身，底色完全透出宿主页面。
- `html`、`body`、挂件根节点与 WebGL 画布都不设置背景色，宿主页面是什么底色就显示什么底色；嵌入代码里的 `style` 也带了 `background:transparent`，避免宿主自身的 iframe 背景规则叠加出白底。
- Iframe 仓库弹窗在实时预览加载完成后会隐藏底层的预览截图，避免透明挂件后面透出截图背景；点击「返回预览图」后恢复。
- 5.2MB 模型在 800 × 800 的嵌入尺寸下首次加载较慢，页面提供进度与失败重试；建议对该 COS 对象开启浏览器长缓存（`Cache-Control`），避免每次打开重复下载。
- 图片预览框按图片原始比例计算：高度取可用高度，宽度随比例变化；图片使用 `object-contain` 完整显示，不做裁切。

## 控制三段动作（接入方）

挂件支持两种控制方式，可组合使用：URL 参数决定“进来时播什么”，`postMessage` 用于宿主页面在运行时切换。

### URL 参数

`/widgets/penguin` 与 `/api/v1/iframes/penguin/embed` 都支持以下参数，嵌入页会把查询串原样透传给挂件页：

| 参数 | 取值 | 说明 |
| --- | --- | --- |
| `action` | `1` / `2` / `3` | 模型加载完成后播放对应片段（只播一次，结束回到静态），不传则保持静态 |
| `autoplay` | `0` | 配合 `action` 使用：设为 `0` 时只记录初始动作，等宿主发指令再播放 |
| `chrome` | `0` / `1` | `0` 隐藏挂件自带的动作按钮，只留模型；`1` 强制显示。嵌入页默认按 `0` 处理，需要自带按钮时在嵌入地址显式加 `chrome=1` |

```html
<iframe src="https://superbox.fiacloud.top/api/v1/iframes/penguin/embed?action=2&chrome=0"
  title="凑企鹅" width="800" height="800" loading="lazy"
  sandbox="allow-scripts allow-same-origin" style="border:0;max-width:100%;background:transparent"></iframe>
```

也可以直接使用挂件页：`https://superbox.fiacloud.top/widgets/penguin?action=3`。

### postMessage

宿主向 iframe 发送指令：

```js
const frame = document.querySelector('iframe')
frame.contentWindow.postMessage(
  { type: 'superbox:penguin', action: 2 },
  'https://superbox.fiacloud.top',
)
// action：1 | 2 | 3 播放对应片段（播完自动回到静态），0 或 'stop' 立即中断
```

挂件回传加载完成与状态变化：

```js
window.addEventListener('message', event => {
  if (event.data?.type === 'superbox:penguin:ready') {
    // 模型已就绪，可以下发第一条指令
  }
  if (event.data?.type === 'superbox:penguin:state') {
    console.log(event.data.action) // 0 表示静态，1/2/3 对应动作
  }
})
```

- 使用 `embed_url` 接入时，嵌入页负责在父页面与挂件页之间转发消息，宿主不需要拿到内层 iframe 的 `contentWindow`。
- 挂件只处理来自父窗口的消息；嵌入页只转发来自父页面或内层挂件页的消息。
- 宿主 iframe 的 `sandbox` 必须包含 `allow-scripts`（消息转发与 three.js 都依赖脚本）；`allow-same-origin` 仍是加载模型所必需。
- 目标来源建议写成站点域名而非 `'*'`；`chrome=0` 时请确保宿主自己提供动作切换入口。
