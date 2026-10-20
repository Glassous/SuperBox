# Iframe 仓库

Iframe 仓库提供可直接嵌入任意网页的挂件。后端维护条目目录，并渲染可直接作为 `iframe src` 的 HTML 嵌入页；嵌入页为 `text/html`，不是 JSON。目录不属于 `/api/v1/tools` 工具，接口均无需认证。

当前条目：

| slug | 名称 | 分类 | 内容类型 | 推荐尺寸 |
| --- | --- | --- | --- | --- |
| `milk-frog` | 奶蛙 | 图片展示 | `image` | 640 × 640 |

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
      "thumbnail_url": "https://officialimages.glassous.top/other/%E5%A5%B6%E8%9B%99.png",
      "embed_path": "/api/v1/iframes/milk-frog/embed",
      "embed_url": "https://superbox.fiacloud.top/api/v1/iframes/milk-frog/embed",
      "width": 640,
      "height": 640,
      "sandbox": "",
      "allow": ""
    }
  ]
}
```

## 详情

`GET /api/v1/iframes/{slug}`，返回单个条目的元数据，字段与目录项一致。`embed_url` 由 API 基础地址与 `embed_path` 拼接得到；站点经反向代理与 API 同域时，直接使用当前站点地址拼接即可。未知 slug 返回 404，`code` 为 `NOT_FOUND`。

```bash
curl http://localhost:8087/api/v1/iframes/milk-frog
```

## 嵌入页

`GET /api/v1/iframes/{slug}/embed`，返回可直接作为 `iframe src` 的完整 HTML（`text/html; charset=utf-8`）。

- `image` 类型渲染全屏 `<img>`，使用 `object-fit: contain` 居中显示；浅色背景为 `#f6f8fc`，`prefers-color-scheme: dark` 时为 `#0c1020`。
- `page` 类型渲染嵌套 `<iframe>`，按条目的 `sandbox` 与 `allow` 输出。
- 响应头包含 `Cache-Control: public, max-age=300` 与按内容类型生成的 CSP；不设置 `X-Frame-Options`，允许被任意站点嵌入。
- 图片页 CSP 为 `default-src 'none'; img-src https: http: data:; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'`；网页页把 `img-src` 换成 `frame-src https: http:`。
- 未知 slug 返回统一的 JSON 404，而不是 HTML。

```bash
curl -i http://localhost:8087/api/v1/iframes/milk-frog/embed
```

## 嵌入代码

把 `embed_url` 放入 `src`，按推荐尺寸设置宽高。`embed_url` 就是「API 基础地址 + `embed_path`」，反向代理部署下直接拼接站点公网地址：

```html
<iframe src="https://superbox.fiacloud.top/api/v1/iframes/milk-frog/embed" title="奶蛙" width="640" height="640" loading="lazy" sandbox="" style="border:0;max-width:100%"></iframe>
```

`sandbox=""` 表示不允许脚本，适合纯图片条目；网页类型条目按元数据返回的 `sandbox`、`allow` 填写。网页 `/iframes` 的预览面板可以复制以上代码、打开嵌入页或复制嵌入地址。

## 字段说明

| 字段 | 说明 |
| --- | --- |
| `slug` | 条目标识，用于详情与嵌入页路径 |
| `name` | 展示名称，同时作为嵌入页标题 |
| `category` | 分类文案 |
| `description` | 简介 |
| `keywords` | 搜索关键词 |
| `content_type` | `image` 或 `page` |
| `content_url` | 原始图片或网页地址 |
| `thumbnail_url` | 缩略图地址；无 `poster` 的图片条目复用 `content_url`，网页条目为空字符串 |
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

1. 在 `backend/app/iframes.py` 的 `IFRAMES` 列表加入条目：`slug`、`name`、`category`、`description`、`keywords`、`content_type`、`content_url`、`poster`、`width`、`height`、`sandbox`、`allow`。
2. 在 `backend/tests/test_iframes.py` 补充目录、搜索、详情与嵌入页断言；如条目数变化，同步 `backend/tests/test_api.py` 中的 Skill 接口总数。
3. 需要条目级文档时在本目录新增说明；网页 `/iframes` 会自动展示目录，无需改动前端代码。
4. 图片地址直接引用外部图床；若图床限制防盗链，需要改为服务端代理或转存 COS。
