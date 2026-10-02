import type { ExifCatalogTag, ExifChange, ExifInspectResult, ToolInfo } from '../types'
import type { ApiOperation } from '../data/apiDocs'
import { apiFieldValue } from '../data/apiDocs'

export const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8087').replace(/\/$/, '')

interface ApiErrorBody {
  code?: string
  message?: string
}

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status?: number,
    public readonly code?: string,
  ) {
    super(message)
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${apiBaseUrl}/api/v1${path}`, {
      credentials: 'omit',
      ...init,
      headers: {
        'Content-Type': 'application/json',
        ...init?.headers,
      },
    })
  } catch (cause) {
    if (cause instanceof DOMException && cause.name === 'AbortError') throw cause
    throw new ApiError('连接失败，请检查网络后重试')
  }

  let data: unknown
  try {
    data = await response.json()
  } catch {
    throw new ApiError('服务返回了无法读取的响应。', response.status)
  }

  if (!response.ok) {
    const error = data as ApiErrorBody
    throw new ApiError(error.message || '请求失败，请稍后重试。', response.status, error.code)
  }
  return data as T
}

export function getTools(q = '', signal?: AbortSignal): Promise<{ tools: ToolInfo[] }> {
  const query = q ? `?q=${encodeURIComponent(q)}` : ''
  return request(`/tools${query}`, { signal })
}

export function getTool(slug: string, signal?: AbortSignal): Promise<ToolInfo> {
  return request(`/tools/${encodeURIComponent(slug)}`, { signal })
}

export function postTool<T>(path: string, body: object, signal?: AbortSignal): Promise<T> {
  return request<T>(path, { method: 'POST', body: JSON.stringify(body), signal })
}

export function getToolResult<T>(path: string, signal?: AbortSignal): Promise<T> {
  return request<T>(path, { signal, cache: 'no-store' })
}

export interface DocumentResult {
  result: string; format: 'markdown' | 'txt'; filename: string; source_type: string
  stats: Record<string, number>; warnings: string[]
}

export interface CurrencyResult {
  result: string; amount: string; from_currency: string; to_currency: string; rate: string
  rate_date: string | null; source: string; fetched_at: string | null; cached: boolean; stale: boolean
}

export type CurrencyBatchItem = (CurrencyResult & { status: 'success' }) | {
  status: 'error'; to_currency: string; code: string; message: string
}
export interface CurrencyBatchResult {
  amount: string; from_currency: string; precision: number; count: number; results: CurrencyBatchItem[]
}

export function convertCurrencies(amount: string, from: string, targets: string[], precision: number, signal?: AbortSignal) {
  return postTool<CurrencyBatchResult>('/currency/convert-batch', {
    amount, from_currency: from, to_currencies: targets, precision,
  }, signal)
}

export function saveBlob(blob: Blob, name: string) {
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url; anchor.download = name; anchor.click()
  setTimeout(() => URL.revokeObjectURL(url), 60_000)
}

export async function executeOperation(operation: ApiOperation, values: Record<string, string>, file?: File | null, signal?: AbortSignal): Promise<unknown | Blob> {
  let path = operation.path
  const method = operation.method ?? 'POST'
  let body: BodyInit | undefined
  let headers: Record<string, string> = {}
  if (method === 'GET') {
    const params = new URLSearchParams(Object.entries(values).filter(([, value]) => value !== ''))
    if (params.size) path += `?${params}`
  } else if (operation.multipart) {
    const form = new FormData()
    for (const field of operation.fields) {
      if (field.type === 'file') { if (file) form.append(field.name, file) }
      else if (values[field.name]) form.append(field.name, values[field.name]!)
    }
    body = form
  } else {
    body = JSON.stringify(Object.fromEntries(operation.fields.map(field => [field.name,
      apiFieldValue(field.type, values[field.name] ?? '')])))
    headers = { 'Content-Type': 'application/json' }
  }
  let response: Response
  try { response = await fetch(`${apiBaseUrl}/api/v1${path}`, { method, body, headers, signal, credentials: 'omit', cache: 'no-store' }) }
  catch (cause) {
    if (cause instanceof DOMException && cause.name === 'AbortError') throw cause
    throw new ApiError('连接失败，请检查网络后重试')
  }
  if (!response.ok) {
    const error = await response.json().catch(() => ({})) as ApiErrorBody
    throw new ApiError(error.message || '请求失败。', response.status, error.code)
  }
  return operation.binaryResponse ? response.blob() : response.json()
}

export async function convertDocument(source: File | string, format: string, signal?: AbortSignal): Promise<DocumentResult> {
  const form = new FormData()
  form.append(typeof source === 'string' ? 'file_url' : 'file', source)
  form.append('format', format)
  return (await multipartRequest('/documents/convert', form, signal)).json() as Promise<DocumentResult>
}

async function multipartRequest(path: string, form: FormData, signal?: AbortSignal): Promise<Response> {
  let response: Response
  try {
    response = await fetch(`${apiBaseUrl}/api/v1${path}`, {
      method: 'POST', body: form, credentials: 'omit', signal,
    })
  } catch (cause) {
    if (cause instanceof DOMException && cause.name === 'AbortError') throw cause
    throw new ApiError('连接失败，请检查网络后重试')
  }
  if (!response.ok) {
    let body: ApiErrorBody = {}
    try { body = await response.json() as ApiErrorBody } catch { /* Keep the HTTP status. */ }
    throw new ApiError(body.message || '文件处理失败。', response.status, body.code)
  }
  return response
}

export async function inspectExif(source: File | string, signal?: AbortSignal): Promise<ExifInspectResult> {
  const form = new FormData()
  form.append(typeof source === 'string' ? 'image_url' : 'image', source)
  return (await multipartRequest('/exif/inspect', form, signal)).json() as Promise<ExifInspectResult>
}

export function searchExifTags(q = '', signal?: AbortSignal): Promise<{ tags: ExifCatalogTag[] }> {
  return request(`/exif/tags?q=${encodeURIComponent(q)}`, { signal })
}

export async function editExif(source: File | string, changes: ExifChange[]): Promise<Blob> {
  const form = new FormData()
  form.append(typeof source === 'string' ? 'image_url' : 'image', source)
  form.append('changes', JSON.stringify(changes))
  return (await multipartRequest('/exif/edit', form)).blob()
}
