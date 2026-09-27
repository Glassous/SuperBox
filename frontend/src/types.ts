export interface ToolInfo {
  slug: string
  name: string
  category: string
  description: string
  keywords: string[]
}

export interface TextResult {
  result: string
}

export interface JsonValidationResult {
  valid: boolean
  message: string
}

export interface DateTimeResult {
  iso_utc: string
}

export interface UnixTimestampResult {
  iso_utc: string
  seconds: string
  milliseconds: string
}

export interface ExifTag {
  key: string
  group: string
  name: string
  value: string
  writable: boolean
  reason: string
}

export interface ExifCatalogTag {
  key: string
  group: string
  name: string
  type: string
  writable: boolean
}

export interface ExifInspectResult {
  format: 'JPEG' | 'PNG' | 'WEBP'
  tags: ExifTag[]
}

export interface ExifChange {
  key: string
  action: 'set' | 'delete'
  value?: string
}
