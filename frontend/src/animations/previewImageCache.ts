/**
 * 预览图内存缓存。
 *
 * 列表卡片与详情大卡片共用同一个 preview_url；这里保留已加载的 Image 对象，
 * 让 SPA 往返时的翻转过渡直接复用内存中的位图，而不是重新发起图片请求。
 */
const cached = new Map<string, HTMLImageElement>()

export function warmPreviewImage(url: string) {
  if (!url || cached.has(url)) return
  const image = new Image()
  image.decoding = 'async'
  image.src = url
  cached.set(url, image)
}
