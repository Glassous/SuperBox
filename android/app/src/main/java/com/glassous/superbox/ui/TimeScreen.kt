package com.glassous.superbox.ui

import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.material3.Button
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.rememberCoroutineScope
import com.glassous.superbox.data.ApiClient
import com.glassous.superbox.data.ToolInfo

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun TimeScreen(api: ApiClient, tool: ToolInfo, onBack: () -> Unit) {
    val scope = rememberCoroutineScope()
    val operation = rememberOperationState()
    LaunchedEffect(api) { operation.run(scope) { api.currentTime() } }
    Scaffold(contentWindowInsets = WindowInsets(0, 0, 0, 0), topBar = { ToolTopBar(tool.name, tool.slug, onBack) }) { padding ->
        ToolScreenFrame(tool, operation, topPadding = padding.calculateTopPadding()) {
            HelperText("显示东八区日期和时间，可手动刷新。")
            Button(onClick = { operation.run(scope) { api.currentTime() } }, enabled = !operation.loading) { Text("刷新时间") }
        }
    }
}
