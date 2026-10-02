package com.glassous.superbox.ui

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.asPaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.navigationBars
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import com.glassous.superbox.data.ToolInfo
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Job
import kotlinx.coroutines.launch

class OperationState {
    var result by mutableStateOf("")
        private set
    var error by mutableStateOf<String?>(null)
        private set
    var loading by mutableStateOf(false)
        private set
    private var job: Job? = null
    private var requestId = 0

    fun reset() {
        requestId++
        job?.cancel()
        result = ""
        error = null
        loading = false
    }

    fun run(scope: CoroutineScope, action: suspend () -> String) {
        reset()
        val current = ++requestId
        loading = true
        job = scope.launch {
            try {
                val output = action()
                if (current == requestId) result = output
            } catch (cancel: CancellationException) {
                throw cancel
            } catch (cause: Exception) {
                if (current == requestId) error = cause.message ?: "处理失败，请稍后重试。"
            } finally {
                if (current == requestId) loading = false
            }
        }
    }
}

@Composable
fun rememberOperationState(): OperationState {
    val state = remember { OperationState() }
    DisposableEffect(state) { onDispose { state.reset() } }
    return state
}

/** 只提供工具页的内容区；Scaffold 与顶部栏由每个页面自己提供。 */
@Composable
fun ToolScreenFrame(
    tool: ToolInfo,
    state: OperationState,
    modifier: Modifier = Modifier,
    topPadding: Dp = 0.dp,
    resultContent: (@Composable () -> Unit)? = null,
    form: @Composable ColumnScope.() -> Unit,
) {
    // 列表可以滚到小白条之后，底部安全距离由内容内边距保证
    val bottomSafePadding = WindowInsets.navigationBars.asPaddingValues().calculateBottomPadding()
    LazyColumn(
        modifier = modifier.fillMaxSize(),
        contentPadding = PaddingValues(start = 20.dp, top = 20.dp + topPadding, end = 20.dp, bottom = 20.dp + bottomSafePadding),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        item {
            Text(
                tool.description,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.sharedToolText(toolDescriptionKey(tool.slug)),
            )
        }
        item {
            Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface), shape = RoundedCornerShape(18.dp)) {
                Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(14.dp), content = form)
            }
        }
        item { if (resultContent != null) resultContent() else OperationResultCard(state) }
    }
}

@Composable
fun CodeInput(
    value: String,
    onValueChange: (String) -> Unit,
    label: String,
    placeholder: String,
    maxLength: Int = 1_000_000,
    multiline: Boolean = true,
) {
    OutlinedTextField(
        value = value,
        onValueChange = { if (it.length <= maxLength) onValueChange(it) },
        label = { Text(label) },
        placeholder = { Text(placeholder) },
        minLines = if (multiline) 7 else 1,
        maxLines = if (multiline) 18 else 1,
        modifier = Modifier.fillMaxWidth(),
        textStyle = MaterialTheme.typography.bodyMedium.copy(fontFamily = FontFamily.Monospace),
    )
}

@Composable
fun ModeChip(label: String, selected: Boolean, onClick: () -> Unit) {
    FilterChip(selected = selected, onClick = onClick, label = { Text(label) })
}

@Composable
fun HelperText(text: String) {
    Text(text, color = MaterialTheme.colorScheme.onSurfaceVariant, style = MaterialTheme.typography.bodySmall)
}

@Composable
private fun OperationResultCard(state: OperationState) {
    val context = LocalContext.current
    var copied by remember(state.result) { mutableStateOf(false) }
    Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface), shape = RoundedCornerShape(18.dp)) {
        Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text("输出结果", fontWeight = FontWeight.Bold)
                if (state.result.isNotEmpty() && state.error == null) TextButton(onClick = {
                    (context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager)
                        .setPrimaryClip(ClipData.newPlainText("Superbox 结果", state.result))
                    copied = true
                }) { Text(if (copied) "已复制" else "复制结果") }
            }
            when {
                state.loading -> Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    CircularProgressIndicator(modifier = Modifier.padding(2.dp), strokeWidth = 2.dp)
                    Text("正在处理…")
                }
                state.error != null -> Text(state.error.orEmpty(), color = MaterialTheme.colorScheme.error)
                state.result.isNotEmpty() -> Text(
                    state.result,
                    style = MaterialTheme.typography.bodyMedium.copy(fontFamily = FontFamily.Monospace),
                )
                else -> Text("选择一个操作后，结果将显示在这里", color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
    }
}
