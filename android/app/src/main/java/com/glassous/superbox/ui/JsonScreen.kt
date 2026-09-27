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
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
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
fun JsonScreen(api: ApiClient, tool: ToolInfo, onBack: () -> Unit) {
    val scope = rememberCoroutineScope()
    val operation = rememberOperationState()
    var input by rememberSaveable { mutableStateOf("") }

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
            Text("输入 JSON")
            CodeInput(input, { input = it }, "JSON 内容", "例如：{\"name\":\"Superbox\",\"ready\":true}")
            HelperText("支持标准 JSON；验证、格式化与压缩均由后端完成。")
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Button(onClick = {
                    val source = input
                    operation.run(scope) { api.textOperation("json/format", source) }
                }, enabled = !operation.loading) { Text("格式化") }
                OutlinedButton(onClick = {
                    val source = input
                    operation.run(scope) { api.textOperation("json/minify", source) }
                }, enabled = !operation.loading) { Text("压缩") }
                OutlinedButton(onClick = {
                    val source = input
                    operation.run(scope) {
                        val (valid, message) = api.validateJson(source)
                        if (!valid) throw IllegalArgumentException(message)
                        message
                    }
                }, enabled = !operation.loading) { Text("校验") }
            }
            TextButton(onClick = { input = ""; operation.reset() }) { Text("清空") }
        }
    }
}
