// 为静态托管的 SPA 生成路由级入口文件。
//
// 静态服务器（例如刚创建、还没配置 try_files 回退的 1Panel 站点）对
// /api-access、/tools/<slug> 这类没有实体文件的路径会直接返回 404。
// 这里把构建出的 index.html 复制到对应路由目录，请求会命中目录索引正常渲染。
// 部署流程同时会尝试写入 Nginx 回退规则；两者兼容，且本兜底在无服务器配置时也有效。
import { access, copyFile, mkdir, readdir, readFile } from 'node:fs/promises'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const dist = join(root, 'dist')
const indexPath = join(dist, 'index.html')

async function slugsFromToolFiles() {
  const entries = await readdir(join(root, 'src', 'tools'))
  return entries
    .filter(name => name.endsWith('Tool.vue'))
    .map(name => name.slice(0, -'Tool.vue'.length).toLowerCase())
    .sort()
}

async function slugsFromToolView() {
  const source = await readFile(join(root, 'src', 'views', 'ToolView.vue'), 'utf8')
  const start = source.indexOf('const forms = {')
  if (start === -1) throw new Error('未在 src/views/ToolView.vue 中找到 forms 映射，无法核对工具路由')

  const slugs = []
  const lines = source.slice(start).split('\n')
  for (const line of lines.slice(1)) {
    if (/^\}/.test(line)) break
    const matched = /^\s*([A-Za-z0-9_-]+)\s*:/.exec(line)
    if (matched) slugs.push(matched[1].toLowerCase())
  }
  return slugs.sort()
}

const [fromFiles, fromView] = await Promise.all([slugsFromToolFiles(), slugsFromToolView()])
if (fromFiles.join(',') !== fromView.join(',')) {
  throw new Error(
    `工具路由不一致：src/tools 目录为 [${fromFiles.join(', ')}]，ToolView.vue 的 forms 为 [${fromView.join(', ')}]，请先对齐再构建`,
  )
}

await access(indexPath).catch(() => {
  throw new Error('未找到 dist/index.html，请先执行 vite build')
})

const routes = ['api-access', ...fromFiles.map(slug => `tools/${slug}`)]
for (const route of routes) {
  const target = join(dist, route, 'index.html')
  await mkdir(dirname(target), { recursive: true })
  await copyFile(indexPath, target)
}

console.log(`已生成 SPA 路由入口：${routes.map(route => `/${route}`).join('、')}`)
