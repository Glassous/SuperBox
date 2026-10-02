package com.glassous.superbox.ui

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import com.glassous.superbox.data.*
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.launch
import java.time.OffsetDateTime
import java.time.ZoneOffset
import java.time.format.DateTimeFormatter

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CurrencyScreen(api: ApiClient, tool: ToolInfo, onBack: () -> Unit) {
    val scope = rememberCoroutineScope()
    val operation = rememberOperationState()
    var amount by rememberSaveable { mutableStateOf("1") }
    var from by rememberSaveable { mutableStateOf("CNY") }
    var to by rememberSaveable { mutableStateOf("USD") }
    var multiple by rememberSaveable { mutableStateOf(false) }
    var targets by rememberSaveable { mutableStateOf(listOf("USD", "EUR", "JPY")) }
    var precision by rememberSaveable { mutableStateOf(2) }
    var currencies by remember { mutableStateOf<List<CurrencyInfo>>(emptyList()) }
    var directoryError by remember { mutableStateOf<String?>(null) }
    var fetching by remember { mutableStateOf(false) }
    var results by remember { mutableStateOf<List<CurrencyBatchItem>>(emptyList()) }
    var picker by remember { mutableStateOf<String?>(null) }
    var precisionMenu by remember { mutableStateOf(false) }
    fun reset() { operation.reset(); results = emptyList() }
    suspend fun load() {
        if (fetching) return
        fetching = true; directoryError = null
        try {
            val common = listOf("CNY", "USD", "EUR", "JPY", "GBP", "HKD", "SGD", "AUD", "CAD", "CHF")
            currencies = api.currencies().sortedWith(compareBy<CurrencyInfo> {
                common.indexOf(it.code).takeIf { index -> index >= 0 } ?: 100
            }.thenBy { it.code })
            val supported = currencies.map { it.code }.toSet()
            if (from !in supported) from = currencies.firstOrNull()?.code.orEmpty()
            if (to !in supported) to = currencies.firstOrNull()?.code.orEmpty()
            targets = targets.filter { it in supported }
        } catch (cancel: CancellationException) { throw cancel }
        catch (cause: Exception) { directoryError = cause.message ?: "货币列表加载失败" }
        finally { fetching = false }
    }
    fun name(code: String) = currencies.find { it.code == code }?.localizedName() ?: code
    LaunchedEffect(api) { load() }
    Scaffold(contentWindowInsets = WindowInsets(0, 0, 0, 0), topBar = { ToolTopBar(tool.name, tool.slug, onBack) }) { padding ->
        ToolScreenFrame(tool, operation, topPadding = padding.calculateTopPadding(), resultContent = {
            CurrencyResults(operation, results, ::name)
        }) {
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                ModeChip("单币种", !multiple) { multiple = false; reset() }
                ModeChip("多币种", multiple) { multiple = true; reset() }
            }
            OutlinedTextField(
                value = amount, onValueChange = { if (it.length <= 24) { amount = it; reset() } },
                label = { Text("金额") }, singleLine = true, modifier = Modifier.fillMaxWidth(),
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                textStyle = MaterialTheme.typography.headlineLarge,
            )
            if (fetching) HelperText("正在处理…")
            directoryError?.let { HelperText(it); TextButton(onClick = { scope.launch { load() } }) { Text("重试") } }
            OutlinedButton(enabled = currencies.isNotEmpty(), modifier = Modifier.fillMaxWidth(), onClick = { picker = "from" }) {
                Text("原币种：$from · ${name(from)}")
            }
            if (!multiple) {
                TextButton(enabled = currencies.isNotEmpty(), onClick = { val old = from; from = to; to = old; reset() }) { Text("交换币种 ⇄") }
                OutlinedButton(enabled = currencies.isNotEmpty(), modifier = Modifier.fillMaxWidth(), onClick = { picker = "to" }) {
                    Text("目标币种：$to · ${name(to)}")
                }
            } else {
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    Text("已选 ${targets.size} / 50", fontWeight = FontWeight.Bold)
                    TextButton(enabled = targets.isNotEmpty(), onClick = { targets = emptyList(); reset() }) { Text("清空") }
                }
                targets.chunked(4).forEach { row ->
                    Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                        row.forEach { code -> InputChip(selected = true, onClick = {
                            targets = targets.filter { it != code }; reset()
                        }, label = { Text("$code ×") }) }
                    }
                }
                OutlinedButton(enabled = currencies.isNotEmpty(), modifier = Modifier.fillMaxWidth(), onClick = { picker = "multiple" }) { Text("选择目标币种") }
                if (targets.size == 50) HelperText("最多选择 50 种货币，可移除后重新选择。")
            }
            Box {
                TextButton(onClick = { precisionMenu = true }) { Text("小数位数：$precision ▾") }
                DropdownMenu(expanded = precisionMenu, onDismissRequest = { precisionMenu = false }) {
                    (0..8).forEach { n ->
                        DropdownMenuItem(text = { Text(n.toString()) }, onClick = { precision = n; precisionMenu = false; reset() })
                    }
                }
            }
            Button(enabled = !operation.loading && currencies.isNotEmpty() && (!multiple || targets.isNotEmpty()),
                modifier = Modifier.fillMaxWidth(), onClick = {
                    val a = amount; val f = from; val t = to; val p = precision; val selected = targets.toList(); val multi = multiple
                    results = emptyList()
                    operation.run(scope) {
                        val response = if (multi) api.convertCurrencies(a, f, selected, p).results
                            else listOf(CurrencySuccess(api.convertCurrency(a, f, t, p)))
                        results = response
                        response.joinToString("\n\n") { it.display() }
                    }
                }) { Text(if (operation.loading) "正在处理…" else "计算") }
            HelperText("每日参考汇率，实际兑换金额可能因手续费等因素有所不同。")
        }
    }
    picker?.let { which ->
        CurrencySelectionDialog(
            title = if (which == "from") "原币种" else "目标币种",
            currencies = currencies, selected = if (which == "multiple") targets.toSet() else setOf(if (which == "from") from else to),
            multiple = which == "multiple", onDismiss = { picker = null },
            onSelect = { code ->
                if (which == "multiple") {
                    targets = if (code in targets) targets.filter { it != code } else if (targets.size < 50) targets + code else targets
                } else {
                    if (which == "from") from = code else to = code
                    picker = null
                }
                reset()
            },
        )
    }
}

@Composable
private fun CurrencySelectionDialog(
    title: String, currencies: List<CurrencyInfo>, selected: Set<String>, multiple: Boolean,
    onDismiss: () -> Unit, onSelect: (String) -> Unit,
) {
    var query by remember { mutableStateOf("") }
    val filtered = currencies.filter { item ->
        "${item.code} ${item.name} ${item.localizedName()}".contains(query.trim(), ignoreCase = true)
    }
    Dialog(onDismissRequest = onDismiss) {
        Surface(shape = RoundedCornerShape(20.dp)) {
            Column(Modifier.fillMaxWidth().padding(20.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                Text(title, style = MaterialTheme.typography.titleLarge)
                if (multiple) Text("已选 ${selected.size} / 50")
                OutlinedTextField(query, { query = it }, label = { Text("搜索代码或名称") }, singleLine = true, modifier = Modifier.fillMaxWidth())
                LazyColumn(Modifier.heightIn(max = 320.dp)) {
                    items(filtered, key = { it.code }) { item ->
                        val checked = item.code in selected
                        val enabled = !multiple || checked || selected.size < 50
                        Row(Modifier.fillMaxWidth().clickable(enabled = enabled) { onSelect(item.code) }.padding(vertical = 6.dp)) {
                            if (multiple) Checkbox(checked = checked, enabled = enabled, onCheckedChange = { onSelect(item.code) })
                            Text("${item.code} · ${item.localizedName()}", modifier = Modifier.padding(12.dp),
                                color = if (enabled) MaterialTheme.colorScheme.onSurface else MaterialTheme.colorScheme.onSurfaceVariant)
                        }
                    }
                    if (filtered.isEmpty()) item { Text("没有匹配的货币") }
                }
                TextButton(onClick = onDismiss, modifier = Modifier.fillMaxWidth()) { Text("完成") }
            }
        }
    }
}

@Composable
private fun CurrencyResults(state: OperationState, results: List<CurrencyBatchItem>, name: (String) -> String) {
    val context = LocalContext.current
    var copied by remember(results) { mutableStateOf("") }
    fun copy(items: List<CurrencyBatchItem>, key: String) {
        (context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager)
            .setPrimaryClip(ClipData.newPlainText("Superbox 汇率", items.joinToString("\n\n") { it.display() }))
        copied = key
    }
    Card(shape = RoundedCornerShape(18.dp), colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)) {
        Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text("兑换结果", fontWeight = FontWeight.Bold)
                if (results.isNotEmpty()) TextButton(onClick = { copy(results, "all") }) { Text(if (copied == "all") "已复制" else "复制全部") }
            }
            when {
                state.loading -> Text("正在处理…")
                state.error != null -> Text(state.error.orEmpty(), color = MaterialTheme.colorScheme.error)
                results.isEmpty() -> HelperText("输入金额，选择货币后点击计算")
                else -> results.forEach { item ->
                    OutlinedCard(Modifier.fillMaxWidth()) {
                        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                                Text("${item.to} · ${name(item.to)}", modifier = Modifier.weight(1f), fontWeight = FontWeight.Bold)
                                TextButton(onClick = { copy(listOf(item), item.to) }) { Text(if (copied == item.to) "已复制" else "复制") }
                            }
                            when (item) {
                                is CurrencySuccess -> {
                                    val value = item.conversion
                                    Text(value.result, style = MaterialTheme.typography.headlineLarge)
                                    HelperText("${value.amount} ${value.from} · 参考汇率 ${value.rate}")
                                    HelperText("参考日期：${value.rateDate ?: "同币种"} · 来源：${if (value.source == "identity") "同币种" else value.source}")
                                    value.fetchedAt?.let {
                                        val formatted = runCatching { OffsetDateTime.parse(it).withOffsetSameInstant(ZoneOffset.ofHours(8))
                                            .format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss")) }.getOrDefault(it)
                                        HelperText("更新时间：$formatted")
                                    }
                                    if (value.stale) HelperText("暂用上次获取的数据")
                                }
                                is CurrencyFailure -> Text(item.message, color = MaterialTheme.colorScheme.error)
                            }
                        }
                    }
                }
            }
        }
    }
}
