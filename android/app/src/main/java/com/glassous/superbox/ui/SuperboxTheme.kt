package com.glassous.superbox.ui

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

enum class ThemeMode(val label: String) {
    SYSTEM("跟随系统"), LIGHT("浅色模式"), DARK("深色模式")
}

fun parseThemeMode(value: String?): ThemeMode =
    ThemeMode.entries.firstOrNull { it.name == value } ?: ThemeMode.SYSTEM

object SuperboxColors {
    val brandAction = Color(0xFF4F46E5)
    val lightBackground = Color(0xFFF6F8FC)
    val darkBackground = Color(0xFF0C1020)
    val darkCard = Color(0xFF141A2C)
    val lightField = Color(0xFFF8FAFC)
    val lightOutline = Color(0xFFE2E8F0)
    val darkOutline = Color(0xFF30374D)
    val mutedLight = Color(0xFF64748B)
    val mutedDark = Color(0xFF94A3B8)
}

private val lightColors = lightColorScheme(
    primary = SuperboxColors.brandAction,
    onPrimary = Color.White,
    primaryContainer = Color(0xFFE0E7FF),
    onPrimaryContainer = Color(0xFF312E81),
    secondary = Color(0xFF6D28D9),
    background = SuperboxColors.lightBackground,
    onBackground = Color(0xFF0F172A),
    surface = Color.White,
    onSurface = Color(0xFF0F172A),
    surfaceVariant = SuperboxColors.lightField,
    onSurfaceVariant = Color(0xFF475569),
    outline = SuperboxColors.lightOutline,
    error = Color(0xFFBE123C),
    errorContainer = Color(0xFFFFF1F2),
    onErrorContainer = Color(0xFF9F1239),
)

private val darkColors = darkColorScheme(
    primary = Color(0xFFA5B4FC),
    onPrimary = Color(0xFF1E1B4B),
    primaryContainer = Color(0xFF252D47),
    onPrimaryContainer = Color(0xFFC7D2FE),
    secondary = Color(0xFFC4B5FD),
    background = SuperboxColors.darkBackground,
    onBackground = Color(0xFFF1F5F9),
    surface = SuperboxColors.darkCard,
    onSurface = Color(0xFFF1F5F9),
    surfaceVariant = SuperboxColors.darkBackground,
    onSurfaceVariant = Color(0xFFCBD5E1),
    outline = SuperboxColors.darkOutline,
    error = Color(0xFFFDA4AF),
    errorContainer = Color(0xFF4C1D2B),
    onErrorContainer = Color(0xFFFDA4AF),
)

@Composable
fun SuperboxTheme(mode: ThemeMode, content: @Composable () -> Unit) {
    val dark = when (mode) {
        ThemeMode.SYSTEM -> isSystemInDarkTheme()
        ThemeMode.DARK -> true
        ThemeMode.LIGHT -> false
    }
    MaterialTheme(colorScheme = if (dark) darkColors else lightColors, content = content)
}
