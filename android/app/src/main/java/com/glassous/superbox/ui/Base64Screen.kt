package com.glassous.superbox.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.material3.Button
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.unit.dp
import com.glassous.superbox.data.ApiClient
import com.glassous.superbox.data.ToolInfo

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun Base64Screen(api: ApiClient, tool: ToolInfo, onBack: () -> Unit) {
    val scope = rememberCoroutineScope()
    val operation = rememberOperationState()
    var input by rememberSaveable { mutableStateOf("") }
    var mode by rememberSaveable { mutableStateOf("encode") }

    Scaffold(
        // 内容延伸到系统栏之后（小白条沉浸），底部安全距离由内容自己保证
        contentWindowInsets = WindowInsets(0, 0, 0, 0),
        topBar = { ToolTopBar(tool.name, tool.slug, onBack) },
    ) { padding ->
        ToolScreenFrame(tool, operation, topPadding = padding.calculateTopPadding()) {
            Text("操作设置")
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                ModeChip("编码", mode == "encode") { mode = "encode"; operation.reset() }
                ModeChip("解码", mode == "decode") { mode = "decode"; operation.reset() }
            }
            CodeInput(
                input, { input = it },
                if (mode == "encode") "输入原始文本" else "输入 Base64 内容",
                if (mode == "encode") "在这里输入需要编码的文本…" else "在这里输入 Base64…",
            )
            HelperText("以 UTF-8 文本为基础；解码结果必须是有效 UTF-8。")
            Button(onClick = {
                val source = input
                val action = mode
                operation.run(scope) { api.textOperation("base64/$action", source) }
            }, enabled = !operation.loading) {
                Text(if (mode == "encode") "开始编码 →" else "开始解码 →")
            }
        }
    }
}
