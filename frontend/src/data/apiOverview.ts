import { apiDocs } from './apiDocs'

export interface ApiOverviewItem {
  category: string
  method: 'GET' | 'POST'
  path: string
  name: string
  summary: string
  toolSlug?: string
  operationId?: string
}

export interface ApiOverviewGroup {
  category: string
  items: ApiOverviewItem[]
}

const CATEGORY_ORDER = ['公共接口', '数据处理', '编码转换', '时间日期', '图片处理']

const publicEndpoints: ApiOverviewItem[] = [
  {
    category: '公共接口',
    method: 'GET',
    path: '/health',
    name: '健康检查',
    summary: '返回服务状态，用于探活与连通性检查。',
  },
  {
    category: '公共接口',
    method: 'GET',
    path: '/tools',
    name: '工具目录',
    summary: '返回全部工具元数据，支持在名称、分类、描述与关键词中搜索。',
  },
  {
    category: '公共接口',
    method: 'GET',
    path: '/tools/{slug}',
    name: '工具详情',
    summary: '按 slug 返回单个工具元数据，未知 slug 返回 404。',
  },
  {
    category: '公共接口',
    method: 'GET',
    path: '/openapi.json',
    name: 'OpenAPI 定义',
    summary: '机器可读的 OpenAPI 3 定义，供客户端生成器与 AI 工具读取。',
  },
]

function categoryRank(category: string): number {
  const index = CATEGORY_ORDER.indexOf(category)
  return index === -1 ? CATEGORY_ORDER.length : index
}

export const apiOverview: ApiOverviewItem[] = [
  ...publicEndpoints,
  ...apiDocs.flatMap(doc =>
    doc.operations.map(operation => ({
      category: doc.category,
      method: operation.method ?? 'POST',
      path: operation.path,
      name: `${doc.name} · ${operation.name}`,
      summary: operation.summary,
      toolSlug: doc.slug,
      operationId: operation.id,
    })),
  ),
].sort((a, b) => categoryRank(a.category) - categoryRank(b.category))

export function groupApiOverview(items: ApiOverviewItem[] = apiOverview): ApiOverviewGroup[] {
  return items.reduce<ApiOverviewGroup[]>((groups, item) => {
    const group = groups.find(candidate => candidate.category === item.category)
    if (group) group.items.push(item)
    else groups.push({ category: item.category, items: [item] })
    return groups
  }, [])
}

export function isTestableItem(item: ApiOverviewItem): boolean {
  return Boolean(item.toolSlug && item.operationId)
}
