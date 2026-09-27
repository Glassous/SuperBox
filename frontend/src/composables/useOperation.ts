import { ref } from 'vue'
import { postTool } from '../api/client'

export function useOperation() {
  const result = ref('')
  const error = ref('')
  const loading = ref(false)
  let requestId = 0

  async function run<T>(path: string, body: object, display: (data: T) => string) {
    const current = ++requestId
    result.value = ''
    error.value = ''
    loading.value = true
    try {
      const data = await postTool<T>(path, body)
      if (current === requestId) result.value = display(data)
    } catch (cause) {
      if (current === requestId) {
        error.value = cause instanceof Error ? cause.message : '处理失败，请稍后重试。'
      }
    } finally {
      if (current === requestId) loading.value = false
    }
  }

  function reset() {
    requestId++
    result.value = ''
    error.value = ''
    loading.value = false
  }

  return { result, error, loading, run, reset }
}
