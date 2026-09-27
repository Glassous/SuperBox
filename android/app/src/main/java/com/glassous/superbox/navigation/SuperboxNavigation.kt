package com.glassous.superbox.navigation

import androidx.compose.animation.AnimatedVisibilityScope
import androidx.compose.animation.ExperimentalSharedTransitionApi
import androidx.compose.animation.SharedTransitionLayout
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.glassous.superbox.data.ApiClient
import com.glassous.superbox.data.CatalogState
import com.glassous.superbox.data.ToolAvailability
import com.glassous.superbox.data.ToolCatalogRepository
import com.glassous.superbox.ui.HomeEnter
import com.glassous.superbox.ui.HomeExit
import com.glassous.superbox.ui.HomeScreen
import com.glassous.superbox.ui.ProvideToolSharedTransition
import com.glassous.superbox.ui.ThemeMode
import com.glassous.superbox.ui.ToolScreenEnter
import com.glassous.superbox.ui.ToolScreenExit
import com.glassous.superbox.ui.ToolUnavailableScreen
import com.glassous.superbox.ui.sharedToolContainer

/**
 * 导航层只负责路由，不再提供共享 Scaffold 或共享顶部栏。
 * 每个目的地都是完整页面：自带 Scaffold 与顶部栏；页面之间不位移，
 * 切换观感由首页卡片与功能页之间的共享元素承担（见 ui/SharedToolTransition.kt）。
 */
@OptIn(ExperimentalSharedTransitionApi::class)
@Composable
fun SuperboxNavigation(
    api: ApiClient,
    catalog: ToolCatalogRepository,
    themeMode: ThemeMode,
    onThemeMode: (ThemeMode) -> Unit,
) {
    val state by catalog.state.collectAsStateWithLifecycle()
    val nav = rememberNavController()

    SharedTransitionLayout(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background),
    ) {
        NavHost(
            navController = nav,
            startDestination = "home",
            // 首页在转场期间原地保持，功能页只做整体淡入淡出；滑动交给共享元素
            enterTransition = { ToolScreenEnter },
            exitTransition = { HomeExit },
            popEnterTransition = { HomeEnter },
            popExitTransition = { ToolScreenExit },
        ) {
            composable("home") {
                val animatedVisibilityScope: AnimatedVisibilityScope = this
                ProvideToolSharedTransition(this@SharedTransitionLayout, animatedVisibilityScope) {
                    HomeScreen(
                        state = state,
                        themeMode = themeMode,
                        onThemeMode = onThemeMode,
                        onOpen = { definition -> nav.navigate(definition.route) },
                    )
                }
            }
            LocalToolRegistry.all.forEach { definition ->
                composable(definition.route) {
                    val animatedVisibilityScope: AnimatedVisibilityScope = this
                    ProvideToolSharedTransition(this@SharedTransitionLayout, animatedVisibilityScope) {
                        // 整页与首页卡片共享同一个 key：卡片从列表位置展开成这一页
                        Box(
                            Modifier
                                .fillMaxSize()
                                .sharedToolContainer(definition.slug),
                        ) {
                            val card = (state as? CatalogState.Ready)?.tools?.firstOrNull { it.info.slug == definition.slug }
                            val onBack: () -> Unit = { nav.popBackStack() }
                            if (card != null && card.availability == ToolAvailability.AVAILABLE) {
                                definition.screen(api, card.info, onBack)
                            } else {
                                ToolUnavailableScreen(
                                    slug = definition.slug,
                                    title = card?.info?.name ?: definition.fallback.name,
                                    loading = state is CatalogState.Loading,
                                    onBack = onBack,
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}
