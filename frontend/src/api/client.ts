import type { ToolInfo } from '../types'

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
  } catch {
    throw new ApiError('无法连接后端服务，请确认 API 已在 8087 端口启动。')
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

export function postTool<T>(path: string, body: object): Promise<T> {
  return request<T>(path, { method: 'POST', body: JSON.stringify(body) })
}
