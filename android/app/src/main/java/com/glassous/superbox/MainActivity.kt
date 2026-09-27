package com.glassous.superbox

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.SideEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.core.view.WindowCompat
import com.glassous.superbox.navigation.SuperboxNavigation
import com.glassous.superbox.ui.SuperboxColors
import com.glassous.superbox.ui.SuperboxTheme
import com.glassous.superbox.ui.parseThemeMode

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        // 边到边显示：状态栏与底部小白条都沉浸，页面各自保证安全距离
        enableEdgeToEdge()
        val app = application as SuperboxApplication
        val preferences = getSharedPreferences("superbox", MODE_PRIVATE)
        setContent {
            var themeMode by remember {
                mutableStateOf(parseThemeMode(preferences.getString("theme_mode", null)))
            }
            SuperboxTheme(themeMode) {
                val dark = MaterialTheme.colorScheme.background == SuperboxColors.darkBackground
                SideEffect {
                    // 只切换系统栏图标明暗，系统栏本身保持透明（内容沉浸其后）
                    WindowCompat.getInsetsController(window, window.decorView).apply {
                        isAppearanceLightStatusBars = !dark
                        isAppearanceLightNavigationBars = !dark
                    }
                }
                SuperboxNavigation(app.api, app.catalog, themeMode) { next ->
                    themeMode = next
                    preferences.edit().putString("theme_mode", next.name).apply()
                }
            }
        }
    }
}
