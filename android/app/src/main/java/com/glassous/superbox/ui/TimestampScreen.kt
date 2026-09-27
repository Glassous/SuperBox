package com.glassous.superbox.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
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
fun TimestampScreen(api: ApiClient, tool: ToolInfo, onBack: () -> Unit) {
    val scope = rememberCoroutineScope()
    val operation = rememberOperationState()
    var input by rememberSaveable { mutableStateOf("") }
    var mode by rememberSaveable { mutableStateOf("to-datetime") }
    var unit by rememberSaveable { mutableStateOf("seconds") }

    Scaffold(
        // 内容延伸到系统栏之后（小白条沉浸），底部安全距离由内容自己保证
        contentWindowInsets = WindowInsets(0, 0, 0, 0),
        topBar = { ToolTopBar(tool.name, tool.slug, onBack) },
    ) { padding ->
        ToolScreenFrame(tool, operation, topPadding = padding.calculateTopPadding()) {
            Text("转换方向")
            Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                ModeChip("时间戳 → 日期", mode == "to-datetime") {
                    if (mode != "to-datetime") { mode = "to-datetime"; input = ""; operation.reset() }
                }
                ModeChip("日期 → 时间戳", mode == "to-unix") {
                    if (mode != "to-unix") { mode = "to-unix"; input = ""; operation.reset() }
                }
            }
            CodeInput(
                input, { input = it },
                if (mode == "to-datetime") "Unix 时间戳" else "ISO 8601 日期时间",
                if (mode == "to-datetime") "例如：1758931200" else "例如：2026-09-27T12:30:00+08:00",
                maxLength = if (mode == "to-datetime") 40 else 80,
                multiline = false,
            )
            if (mode == "to-datetime") {
                Text("时间戳单位")
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    ModeChip("秒", unit == "seconds") { unit = "seconds"; operation.reset() }
                    ModeChip("毫秒", unit == "milliseconds") { unit = "milliseconds"; operation.reset() }
                }
            }
            HelperText(
                if (mode == "to-datetime") "请输入整数时间戳，结果以 UTC 显示。"
                else "请输入带 Z 或 ±HH:MM 时区偏移的日期时间。",
            )
            Button(onClick = {
                val source = input
                val direction = mode
                val selectedUnit = unit
                operation.run(scope) {
                    if (direction == "to-datetime") api.timestampToDate(source, selectedUnit)
                    else api.dateToTimestamp(source)
                }
            }, enabled = !operation.loading) { Text("开始转换 →") }
        }
    }
}
