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
