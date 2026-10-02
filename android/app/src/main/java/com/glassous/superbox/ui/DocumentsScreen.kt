package com.glassous.superbox.ui

import android.content.ContentResolver
import android.net.Uri
import android.provider.OpenableColumns
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.material3.Button
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.platform.LocalContext
import com.glassous.superbox.data.ApiClient
import com.glassous.superbox.data.DocumentConversion
import com.glassous.superbox.data.ToolInfo
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.ByteArrayOutputStream

private data class LocalDocument(val name: String, val bytes: ByteArray)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DocumentsScreen(api: ApiClient, tool: ToolInfo, onBack: () -> Unit) {
    val resolver = LocalContext.current.contentResolver
    val scope = rememberCoroutineScope()
    val operation = rememberOperationState()
    var mode by rememberSaveable { mutableStateOf("upload") }
    var format by rememberSaveable { mutableStateOf("markdown") }
    var link by rememberSaveable { mutableStateOf("") }
    var selected by remember { mutableStateOf<Uri?>(null) }
    var output by remember { mutableStateOf<DocumentConversion?>(null) }
    var message by remember { mutableStateOf<String?>(null) }
    var saving by remember { mutableStateOf(false) }
    fun reset() { operation.reset(); output = null; message = null }
    val picker = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        if (uri != null) { reset(); selected = uri }
    }
    val saver = rememberLauncherForActivityResult(ActivityResultContracts.CreateDocument("text/plain")) { uri ->
        val current = output
        if (uri != null && current != null) scope.launch {
            saving = true; message = null
            try {
                withContext(Dispatchers.IO) {
                    resolver.openOutputStream(uri, "w")?.use { it.write(current.result.toByteArray(Charsets.UTF_8)) }
                        ?: throw IllegalStateException("无法写入选定位置")
                }
                message = "文件已保存"
            } catch (cancel: CancellationException) { throw cancel }
            catch (cause: Exception) { message = "保存失败：${cause.message}" }
            finally { saving = false }
        }
    }
    Scaffold(contentWindowInsets = WindowInsets(0, 0, 0, 0), topBar = { ToolTopBar(tool.name, tool.slug, onBack) }) { padding ->
        ToolScreenFrame(tool, operation, topPadding = padding.calculateTopPadding()) {
            HelperText("支持 PDF、DOCX、XLSX，最大 5 MiB；提取文字和表格，不支持 OCR、旧版 DOC/XLS、宏、加密或复杂排版。")
            ModeChip("上传文件", mode == "upload") { if (mode != "upload") { reset(); mode = "upload" } }
            ModeChip("公开文件链接", mode == "url") { if (mode != "url") { reset(); mode = "url" } }
            if (mode == "upload") {
                Button(onClick = { picker.launch(arrayOf("application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")) }, enabled = !operation.loading) { Text("选择文档") }
                selected?.let { HelperText("已选择：${documentName(resolver, it)}") }
            } else CodeInput(link, { reset(); link = it }, "公开 HTTP/HTTPS 文件链接", "https://…", maxLength = 2048, multiline = false)
            ModeChip("Markdown", format == "markdown") { if (format != "markdown") { reset(); format = "markdown" } }
            ModeChip("TXT", format == "txt") { if (format != "txt") { reset(); format = "txt" } }
            HelperText("最多 100 页 PDF、20 工作表、50,000 单元格、500,000 字符；Office 解压上限 50 MiB。超限报错，不截断；繁忙时请稍后重试。")
            Button(enabled = !operation.loading && !saving, onClick = {
                output = null; message = null
                val sourceMode = mode; val uri = selected; val url = link.trim(); val selectedFormat = format
                operation.run(scope) {
                    val local = if (sourceMode == "upload") readDocument(resolver, uri ?: throw IllegalArgumentException("请选择文件")) else null
                    val converted = api.convertDocument(local?.name, local?.bytes, if (sourceMode == "url") url else "", selectedFormat)
                    output = converted
                    converted.result
                }
            }) { Text("开始转换") }
            output?.let { current ->
                HelperText("${current.characters} 字符 · ${current.filename}")
                current.warnings.forEach { HelperText(it) }
                Button(enabled = !saving, onClick = { saver.launch(current.filename) }) { Text(if (saving) "保存中…" else "保存文件") }
            }
            message?.let { HelperText(it) }
        }
    }
}

private fun documentName(resolver: ContentResolver, uri: Uri): String =
    resolver.query(uri, arrayOf(OpenableColumns.DISPLAY_NAME), null, null, null)?.use {
        if (it.moveToFirst()) it.getString(0) else null
    } ?: "document"

private suspend fun readDocument(resolver: ContentResolver, uri: Uri): LocalDocument = withContext(Dispatchers.IO) {
    val name = documentName(resolver, uri)
    resolver.query(uri, arrayOf(OpenableColumns.SIZE), null, null, null)?.use {
        if (it.moveToFirst() && !it.isNull(0) && it.getLong(0) > 5 * 1024 * 1024) throw IllegalArgumentException("文件不能超过 5 MiB")
    }
    val bytes = ByteArrayOutputStream()
    resolver.openInputStream(uri)?.use { input ->
        val buffer = ByteArray(64 * 1024)
        while (true) {
            val count = input.read(buffer)
            if (count < 0) break
            if (bytes.size() + count > 5 * 1024 * 1024) throw IllegalArgumentException("文件不能超过 5 MiB")
            bytes.write(buffer, 0, count)
        }
    } ?: throw IllegalArgumentException("无法读取文件")
    LocalDocument(name, bytes.toByteArray())
}
