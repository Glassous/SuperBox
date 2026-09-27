package com.glassous.superbox.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.material3.Button
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.glassous.superbox.R
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
        topBar = {
            TopAppBar(
                title = { Text(tool.name, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold) },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(
                            painterResource(R.drawable.ic_arrow_back),
                            contentDescription = "返回",
                            modifier = Modifier.size(24.dp),
                            tint = MaterialTheme.colorScheme.onSurface,
                        )
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = MaterialTheme.colorScheme.background),
            )
        },
    ) { padding ->
        ToolScreenFrame(tool, operation, Modifier.padding(padding)) {
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
