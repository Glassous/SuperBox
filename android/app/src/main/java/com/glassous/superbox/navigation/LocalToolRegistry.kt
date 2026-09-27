package com.glassous.superbox.navigation

import androidx.compose.runtime.Composable
import com.glassous.superbox.data.ApiClient
import com.glassous.superbox.data.ToolInfo
import com.glassous.superbox.ui.Base64Screen
import com.glassous.superbox.ui.ExifScreen
import com.glassous.superbox.ui.JsonScreen
import com.glassous.superbox.ui.TimestampScreen
import com.glassous.superbox.ui.UrlScreen

data class LocalToolDefinition(
    val slug: String,
    val route: String,
    val fallback: ToolInfo,
    /** 每个工具页是完整独立页面，自行处理顶部栏与返回行为。 */
    val screen: @Composable (api: ApiClient, tool: ToolInfo, onBack: () -> Unit) -> Unit,
)

/** Add one definition and its Screen to support a new locally implemented tool. */
object LocalToolRegistry {
    val all = listOf(
        LocalToolDefinition(
            "json", "tool/json",
            ToolInfo("json", "JSON 工具", "数据处理", "格式化、压缩和校验 JSON 内容。", listOf("格式化", "压缩", "校验")),
        ) { api, tool, onBack -> JsonScreen(api, tool, onBack) },
        LocalToolDefinition(
            "base64", "tool/base64",
            ToolInfo("base64", "Base64 编解码", "编码转换", "在 UTF-8 文本与 Base64 之间转换。", listOf("编码", "解码")),
        ) { api, tool, onBack -> Base64Screen(api, tool, onBack) },
        LocalToolDefinition(
            "url", "tool/url",
            ToolInfo("url", "URL 编解码", "编码转换", "对 URL 参数值进行编码或解码。", listOf("URI", "参数", "百分号")),
        ) { api, tool, onBack -> UrlScreen(api, tool, onBack) },
        LocalToolDefinition(
            "timestamp", "tool/timestamp",
            ToolInfo("timestamp", "时间戳转换", "时间日期", "在 Unix 时间戳与带时区的日期时间之间转换。", listOf("Unix", "秒", "毫秒", "日期")),
        ) { api, tool, onBack -> TimestampScreen(api, tool, onBack) },
        LocalToolDefinition(
            "exif", "tool/exif",
            ToolInfo("exif", "EXIF 编辑", "图片处理", "查看、编辑图片 EXIF 标签并下载原格式图片。", listOf("图片", "照片", "GPS")),
        ) { api, tool, onBack -> ExifScreen(api, tool, onBack) },
    )

    private val bySlug = all.associateBy(LocalToolDefinition::slug)
    fun find(slug: String): LocalToolDefinition? = bySlug[slug]
}
