package com.glassous.superbox.ui

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.material3.Button
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import com.glassous.superbox.data.ApiClient
import com.glassous.superbox.data.CurrencyInfo
import com.glassous.superbox.data.ToolInfo
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CurrencyScreen(api: ApiClient, tool: ToolInfo, onBack: () -> Unit) {
    val scope = rememberCoroutineScope()
    val operation = rememberOperationState()
    var amount by rememberSaveable { mutableStateOf("1") }
    var from by rememberSaveable { mutableStateOf("CNY") }
    var to by rememberSaveable { mutableStateOf("USD") }
    var precision by rememberSaveable { mutableStateOf(2) }
    var currencies by remember { mutableStateOf<List<CurrencyInfo>>(emptyList()) }
    var directoryError by remember { mutableStateOf<String?>(null) }
    var fetching by remember { mutableStateOf(false) }
    fun load() { scope.launch {
        fetching = true; directoryError = null
        try { currencies = api.currencies() }
        catch (cancel: CancellationException) { throw cancel }
        catch (cause: Exception) { directoryError = cause.message }
        finally { fetching = false }
    } }
    LaunchedEffect(api) { load() }
    Scaffold(contentWindowInsets = WindowInsets(0, 0, 0, 0), topBar = { ToolTopBar(tool.name, tool.slug, onBack) }) { padding ->
        ToolScreenFrame(tool, operation, topPadding = padding.calculateTopPadding()) {
            HelperText("每日参考汇率；实际汇率日期以结果为准。")
            if (fetching) HelperText("正在获取货币目录…")
            directoryError?.let { HelperText(it); TextButton(onClick = { load() }) { Text("重新获取货币目录") } }
            CodeInput(amount, { amount = it; operation.reset() }, "金额", "1", maxLength = 24, multiline = false)
            CurrencyPicker("原币种", from, currencies) { from = it; operation.reset() }
            TextButton(onClick = { val old = from; from = to; to = old; operation.reset() }) { Text("交换币种 ⇄") }
            CurrencyPicker("目标币种", to, currencies) { to = it; operation.reset() }
            var showPrecision by remember { mutableStateOf(false) }
            Box {
                TextButton(onClick = { showPrecision = true }) { Text("小数位数：$precision") }
                DropdownMenu(expanded = showPrecision, onDismissRequest = { showPrecision = false }) {
                    (0..8).forEach { n -> DropdownMenuItem(text = { Text(n.toString()) }, onClick = { precision = n; showPrecision = false; operation.reset() }) }
                }
            }
            Button(enabled = !operation.loading && currencies.isNotEmpty(), onClick = {
                val a = amount; val f = from; val t = to; val p = precision
                operation.run(scope) { api.convertCurrency(a, f, t, p).display() }
            }) { Text("转换金额") }
        }
    }
}

@Composable
private fun CurrencyPicker(label: String, value: String, items: List<CurrencyInfo>, onChange: (String) -> Unit) {
    var expanded by remember { mutableStateOf(false) }
    Box {
        TextButton(enabled = items.isNotEmpty(), onClick = { expanded = true }) { Text("$label：$value") }
        DropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
            items.forEach { item -> DropdownMenuItem(text = { Text("${item.code} · ${item.name}") }, onClick = { onChange(item.code); expanded = false }) }
        }
    }
}
