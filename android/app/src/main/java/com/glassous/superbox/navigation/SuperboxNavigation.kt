package com.glassous.superbox.navigation

import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.glassous.superbox.data.ApiClient
import com.glassous.superbox.data.CatalogState
import com.glassous.superbox.data.ToolAvailability
import com.glassous.superbox.data.ToolCatalogRepository
import com.glassous.superbox.ui.HomeScreen
import com.glassous.superbox.ui.ThemeMode
import com.glassous.superbox.ui.ToolUnavailableScreen

/**
 * 导航层只负责路由，不再提供共享 Scaffold 或共享顶部栏。
 * 每个目的地都是完整页面：自带 Scaffold 与顶部栏，切换时整页随 NavHost 默认过渡动画一起进出。
 */
@Composable
fun SuperboxNavigation(
    api: ApiClient,
    catalog: ToolCatalogRepository,
    themeMode: ThemeMode,
    onThemeMode: (ThemeMode) -> Unit,
) {
    val state by catalog.state.collectAsStateWithLifecycle()
    val nav = rememberNavController()

    NavHost(navController = nav, startDestination = "home") {
        composable("home") {
            HomeScreen(
                state = state,
                themeMode = themeMode,
                onThemeMode = onThemeMode,
                onOpen = { definition -> nav.navigate(definition.route) },
            )
        }
        LocalToolRegistry.all.forEach { definition ->
            composable(definition.route) {
                val card = (state as? CatalogState.Ready)?.tools?.firstOrNull { it.info.slug == definition.slug }
                val onBack: () -> Unit = { nav.popBackStack() }
                if (card != null && card.availability == ToolAvailability.AVAILABLE) {
                    definition.screen(api, card.info, onBack)
                } else {
                    ToolUnavailableScreen(
                        title = card?.info?.name ?: definition.fallback.name,
                        loading = state is CatalogState.Loading,
                        onBack = onBack,
                    )
                }
            }
        }
    }
}
