import { onBeforeUnmount, ref } from 'vue'

export function useToolTask() {
  const result = ref(''), error = ref(''), loading = ref(false)
  let controller: AbortController | undefined
  function reset() { controller?.abort(); controller = undefined; result.value = ''; error.value = ''; loading.value = false }
  async function run(action: (signal: AbortSignal) => Promise<string>) {
    reset()
    const current = new AbortController()
    controller = current; loading.value = true
    try { const value = await action(current.signal); if (!current.signal.aborted) result.value = value }
    catch (cause) { if (!current.signal.aborted) error.value = cause instanceof Error ? cause.message : '处理失败。' }
    finally { if (controller === current) loading.value = false }
  }
  onBeforeUnmount(reset)
  return { result, error, loading, run, reset }
}
