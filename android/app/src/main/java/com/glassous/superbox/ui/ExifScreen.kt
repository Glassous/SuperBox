package com.glassous.superbox.ui

import android.content.ContentResolver
import android.content.Intent
import android.graphics.BitmapFactory
import android.net.Uri
import android.provider.OpenableColumns
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.asPaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.navigationBars
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.LocalRippleConfiguration
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.glassous.superbox.data.ApiClient
import com.glassous.superbox.data.ExifCatalogTag
import com.glassous.superbox.data.ExifInspection
import com.glassous.superbox.data.ExifTag
import com.glassous.superbox.data.ToolInfo
import com.glassous.superbox.data.calculateExifChanges
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.ByteArrayOutputStream

private const val MAX_IMAGE_BYTES = 20 * 1024 * 1024
private data class LocalImage(val name: String, val bytes: ByteArray)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ExifScreen(api: ApiClient, tool: ToolInfo, onBack: () -> Unit) {
    val context = LocalContext.current
    val resolver = context.contentResolver
    val scope = rememberCoroutineScope()
    var image by remember { mutableStateOf<LocalImage?>(null) }
    var inspection by remember { mutableStateOf<ExifInspection?>(null) }
    var drafts by remember { mutableStateOf<Map<String, String>>(emptyMap()) }
    var deleted by remember { mutableStateOf<Set<String>>(emptySet()) }
    var filter by remember { mutableStateOf("") }
    var tagQuery by remember { mutableStateOf("") }
    var catalog by remember { mutableStateOf<List<ExifCatalogTag>>(emptyList()) }
    var loading by remember { mutableStateOf(false) }
    var searching by remember { mutableStateOf(false) }
    var saving by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }
    var message by remember { mutableStateOf<String?>(null) }
    var pendingOutput by remember { mutableStateOf<LocalImage?>(null) }
    var inspectJob by remember { mutableStateOf<Job?>(null) }

    val changes = calculateExifChanges(inspection?.tags.orEmpty(), drafts, deleted)
    val original = inspection?.tags.orEmpty()
    val visibleTags = original.filter { "${it.group} ${it.name} ${it.key}".contains(filter, ignoreCase = true) } +
        drafts.keys.filter { key -> original.none { it.key == key } && key.contains(filter, ignoreCase = true) }
            .map { key -> ExifTag(key, key.substringBefore(':'), key.substringAfter(':'), "", true, "") }

    val picker = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        if (uri != null) {
            inspectJob?.cancel()
            inspectJob = scope.launch {
                loading = true
                error = null
                message = null
                image = null
                inspection = null
                drafts = emptyMap()
                deleted = emptySet()
                catalog = emptyList()
                filter = ""
                tagQuery = ""
                try {
                    val loaded = readImage(resolver, uri)
                    image = loaded
                    inspection = api.inspectExif(loaded.name, loaded.bytes)
                } catch (cancel: CancellationException) {
                    throw cancel
                } catch (cause: Exception) {
                    error = cause.message ?: "读取图片失败。"
                } finally {
                    loading = false
                }
            }
        }
    }

    val saver = rememberLauncherForActivityResult(ActivityResultContracts.StartActivityForResult()) { activityResult ->
        val uri = activityResult.data?.data
        val output = pendingOutput
        if (activityResult.resultCode != android.app.Activity.RESULT_OK || uri == null || output == null) {
            pendingOutput = null
            saving = false
        } else {
            scope.launch {
                try {
                    withContext(Dispatchers.IO) {
                        resolver.openOutputStream(uri, "w")?.use { it.write(output.bytes) }
                            ?: throw IllegalStateException("无法写入选定的位置。")
                    }
                    image = output
                    drafts = emptyMap()
                    deleted = emptySet()
                    message = "已保存编辑后的图片，当前内容已更新。"
                    try {
                        inspection = api.inspectExif(output.name, output.bytes)
                    } catch (refreshError: Exception) {
                        inspection = null
                        message = "图片已保存，但重新读取 EXIF 失败：${refreshError.message}"
                    }
                } catch (cancel: CancellationException) {
                    throw cancel
                } catch (cause: Exception) {
                    error = cause.message ?: "保存图片失败。"
                } finally {
                    pendingOutput = null
                    saving = false
                }
            }
        }
    }

    LaunchedEffect(tagQuery, inspection) {
        if (inspection == null) return@LaunchedEffect
        delay(if (tagQuery.isEmpty()) 0 else 250)
        searching = true
        try {
            catalog = api.searchExifTags(tagQuery)
        } catch (cancel: CancellationException) {
            throw cancel
        } catch (cause: Exception) {
            error = cause.message ?: "搜索标签失败。"
        } finally {
            searching = false
        }
    }

    Scaffold(
        // 内容延伸到系统栏之后（小白条沉浸），底部安全距离由内容自己保证
        contentWindowInsets = WindowInsets(0, 0, 0, 0),
        topBar = { ToolTopBar(tool.name, tool.slug, onBack) },
    ) { padding ->
        // 列表可以滚到小白条之后，底部安全距离由内容内边距保证
        val bottomSafePadding = WindowInsets.navigationBars.asPaddingValues().calculateBottomPadding()
        LazyColumn(
            modifier = Modifier.fillMaxSize(),
            contentPadding = PaddingValues(start = 20.dp, top = 20.dp + padding.calculateTopPadding(), end = 20.dp, bottom = 20.dp + bottomSafePadding),
            verticalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            item {
                Text(tool.description, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            item {
                Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface), shape = RoundedCornerShape(18.dp)) {
                    Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                        Text("图片", fontWeight = FontWeight.Bold)
                        OutlinedButton(
                            onClick = { picker.launch(arrayOf("image/jpeg", "image/png", "image/webp")) },
                            enabled = !saving,
                            modifier = Modifier.fillMaxWidth(),
                        ) { Text("选择 JPEG、PNG 或 WebP 图片") }
                        Text("单张图片，最大 20 MB。", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        image?.let { selected ->
                            val bitmap = remember(selected) { previewBitmap(selected.bytes) }
                            if (bitmap != null) Image(
                                bitmap = bitmap.asImageBitmap(),
                                contentDescription = "图片预览：${selected.name}",
                                modifier = Modifier.fillMaxWidth().heightIn(max = 260.dp),
                                contentScale = ContentScale.Fit,
                            )
                            Text("${selected.name}${inspection?.let { " · ${it.format} · ${it.tags.size} 个 EXIF 标签" }.orEmpty()}", style = MaterialTheme.typography.bodySmall)
                        }
                        if (loading || saving) Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                            CircularProgressIndicator(modifier = Modifier.padding(2.dp), strokeWidth = 2.dp)
                            Text(if (saving) "正在编辑或保存…" else "正在读取 EXIF…")
                        }
                        error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
                        message?.let { Text(it, color = ColorSuccess) }
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            Button(onClick = {
                                val selected = image ?: return@Button
                                if (changes.any { it.action == "set" && it.value.isBlank() }) {
                                    error = "新增或修改的标签值不能为空；如需移除，请使用“删除”。"
                                    return@Button
                                }
                                scope.launch {
                                    saving = true
                                    error = null
                                    message = null
                                    try {
                                        val result = api.editExif(selected.name, selected.bytes, changes)
                                        val extension = when (inspection?.format) { "JPEG" -> "jpg"; "PNG" -> "png"; else -> "webp" }
                                        val name = "${selected.name.substringBeforeLast('.', selected.name)}-exif.$extension"
                                        pendingOutput = LocalImage(name, result)
                                        val mime = when (extension) { "jpg" -> "image/jpeg"; "png" -> "image/png"; else -> "image/webp" }
                                        saver.launch(Intent(Intent.ACTION_CREATE_DOCUMENT).apply {
                                            addCategory(Intent.CATEGORY_OPENABLE)
                                            type = mime
                                            putExtra(Intent.EXTRA_TITLE, name)
                                        })
                                    } catch (cancel: CancellationException) {
                                        throw cancel
                                    } catch (cause: Exception) {
                                        error = cause.message ?: "编辑图片失败。"
                                        saving = false
                                    }
                                }
                            }, enabled = inspection != null && changes.isNotEmpty() && !loading && !saving) {
                                Text("编辑并保存${if (changes.isEmpty()) "" else "（${changes.size} 项）"}")
                            }
                            if (changes.isNotEmpty()) OutlinedButton(onClick = {
                                drafts = emptyMap(); deleted = emptySet(); message = null
                            }, enabled = !saving) { Text("撤销修改") }
                        }
                        if (changes.isNotEmpty()) Text("${changes.size} 项修改尚未保存。", color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }
            }
            item {
                Text("EXIF 标签", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                if (inspection != null) OutlinedTextField(
                    value = filter,
                    onValueChange = { if (it.length <= 100) filter = it },
                    label = { Text("筛选现有标签") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                )
            }
            if (image == null) item { Text("选择图片后可查看和编辑 EXIF 标签。") }
            else if (inspection != null) {
                if (visibleTags.isEmpty()) item { Text(if (filter.isNotEmpty()) "没有匹配的标签。" else "这张图片没有 EXIF 标签。可在下方添加。") }
                items(visibleTags, key = ExifTag::key) { tag ->
                    Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)) {
                        Column(Modifier.padding(15.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                                Text(tag.key, color = MaterialTheme.colorScheme.primary, fontWeight = FontWeight.SemiBold,
                                    style = MaterialTheme.typography.bodySmall.copy(fontFamily = FontFamily.Monospace), modifier = Modifier.weight(1f))
                                if (tag.writable) CompositionLocalProvider(LocalRippleConfiguration provides null) {
                                    TextButton(onClick = {
                                        if (original.none { it.key == tag.key }) drafts = drafts - tag.key
                                        else deleted = if (tag.key in deleted) deleted - tag.key else deleted + tag.key
                                        message = null
                                    }) { Text(if (tag.key in deleted) "撤销删除" else "删除") }
                                }
                                else Text("只读", color = MaterialTheme.colorScheme.onSurfaceVariant)
                            }
                            if (!tag.writable) {
                                if (tag.reason.isNotBlank()) Text(tag.reason, style = MaterialTheme.typography.bodySmall)
                                Text(tag.value, style = MaterialTheme.typography.bodySmall.copy(fontFamily = FontFamily.Monospace))
                            } else OutlinedTextField(
                                value = drafts[tag.key] ?: tag.value,
                                onValueChange = { if (it.length <= 4096) { drafts = drafts + (tag.key to it); deleted = deleted - tag.key; message = null } },
                                label = { Text("编辑 ${tag.key}") },
                                enabled = tag.key !in deleted && !saving,
                                minLines = 2,
                                maxLines = 6,
                                modifier = Modifier.fillMaxWidth(),
                            )
                        }
                    }
                }
                item {
                    Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)) {
                        Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                            Text("添加标签", fontWeight = FontWeight.Bold)
                            Text("搜索安全可写的 EXIF 标签；只读字段仅供查看。", style = MaterialTheme.typography.bodySmall)
                            OutlinedTextField(
                                value = tagQuery,
                                onValueChange = { if (it.length <= 100) tagQuery = it },
                                label = { Text("例如 DateTimeOriginal 或 GPS") },
                                singleLine = true,
                                modifier = Modifier.fillMaxWidth(),
                            )
                            if (searching) Text("正在搜索…")
                            catalog.filter { candidate -> candidate.writable && original.none { it.key == candidate.key } && candidate.key !in drafts }
                                .take(30).forEach { candidate ->
                                    CompositionLocalProvider(LocalRippleConfiguration provides null) {
                                        TextButton(onClick = { drafts = drafts + (candidate.key to ""); filter = ""; message = null }) {
                                            Text("＋ ${candidate.key}", modifier = Modifier.fillMaxWidth())
                                        }
                                    }
                                }
                            if (!searching && tagQuery.isNotBlank() && catalog.none { it.writable && original.none { tag -> tag.key == it.key } && it.key !in drafts }) {
                                Text("没有找到可添加的标签。", style = MaterialTheme.typography.bodySmall)
                            }
                        }
                    }
                }
            }
        }
    }
}

private val ColorSuccess = androidx.compose.ui.graphics.Color(0xFF047857)

private suspend fun readImage(resolver: ContentResolver, uri: Uri): LocalImage = withContext(Dispatchers.IO) {
    val name = resolver.query(uri, arrayOf(OpenableColumns.DISPLAY_NAME), null, null, null)?.use { cursor ->
        if (cursor.moveToFirst()) cursor.getString(0) else null
    } ?: throw IllegalArgumentException("无法读取图片文件名。")
    if (!name.matches(Regex("(?i).+\\.(jpg|jpeg|png|webp)"))) {
        throw IllegalArgumentException("请选择 JPEG、PNG 或 WebP 图片。")
    }
    val bytes = ByteArrayOutputStream()
    resolver.openInputStream(uri)?.use { input ->
        val buffer = ByteArray(8192)
        while (true) {
            val count = input.read(buffer)
            if (count < 0) break
            if (bytes.size() + count > MAX_IMAGE_BYTES) throw IllegalArgumentException("图片不能超过 20 MB。")
            bytes.write(buffer, 0, count)
        }
    } ?: throw IllegalArgumentException("无法打开图片。")
    if (bytes.size() == 0) throw IllegalArgumentException("请选择图片文件。")
    LocalImage(name, bytes.toByteArray())
}

private fun previewBitmap(bytes: ByteArray): android.graphics.Bitmap? = runCatching {
    val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
    BitmapFactory.decodeByteArray(bytes, 0, bytes.size, bounds)
    var sample = 1
    while (bounds.outWidth / sample > 1200 || bounds.outHeight / sample > 1200) sample *= 2
    BitmapFactory.decodeByteArray(bytes, 0, bytes.size, BitmapFactory.Options().apply { inSampleSize = sample })
}.getOrNull()
