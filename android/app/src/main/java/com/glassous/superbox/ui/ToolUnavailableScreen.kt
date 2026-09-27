package com.glassous.superbox.ui

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.navigationBars
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

/** 工具暂不可用时同样是完整独立页面，自带顶部栏与返回按钮。 */
@Composable
fun ToolUnavailableScreen(slug: String, title: String, loading: Boolean, onBack: () -> Unit) {
    Scaffold(
        // 内容延伸到系统栏之后（小白条沉浸），底部安全距离由内容自己保证
        contentWindowInsets = WindowInsets(0, 0, 0, 0),
        topBar = { ToolTopBar(title, slug, onBack) },
    ) { _ ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .windowInsetsPadding(WindowInsets.navigationBars)
                .padding(24.dp),
            contentAlignment = Alignment.Center,
        ) {
            if (loading) CircularProgressIndicator()
            else Text("该功能目前不可用。", color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}
