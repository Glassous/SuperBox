package com.glassous.superbox.ui

import android.content.Intent
import android.net.Uri
import androidx.activity.compose.BackHandler
import androidx.compose.animation.core.FastOutLinearInEasing
import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.MutableTransitionState
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.rememberTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.awaitEachGesture
import androidx.compose.foundation.gestures.awaitFirstDown
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.asPaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.navigationBars
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LocalRippleConfiguration
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextField
import androidx.compose.material3.TextFieldDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.derivedStateOf
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clipToBounds
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawWithContent
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.geometry.Rect
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.clipRect
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.LayoutCoordinates
import androidx.compose.ui.layout.boundsInWindow
import androidx.compose.ui.layout.onGloballyPositioned
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.IntRect
import androidx.compose.ui.unit.IntSize
import androidx.compose.ui.unit.LayoutDirection
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Popup
import androidx.compose.ui.window.PopupPositionProvider
import androidx.compose.ui.window.PopupProperties
import com.glassous.superbox.BuildConfig
import com.glassous.superbox.R
import com.glassous.superbox.data.CatalogState
import com.glassous.superbox.data.CatalogTool
import com.glassous.superbox.data.ToolAvailability
import com.glassous.superbox.navigation.LocalToolDefinition
import com.glassous.superbox.navigation.LocalToolRegistry
import kotlin.math.roundToInt

/** 悬浮搜索框与顶部栏之间的间距，同时决定滑入/滑出动画的距离。 */
private val SearchBarTopInset = 8.dp

/** 首页是完整独立页面：自带 Scaffold 与顶部栏；搜索框是悬浮在主区域之上的独立组件，不占用布局。 */
@Composable
fun HomeScreen(
    state: CatalogState,
    themeMode: ThemeMode,
    onThemeMode: (ThemeMode) -> Unit,
    onOpen: (LocalToolDefinition) -> Unit,
) {
    var searchExpanded by rememberSaveable { mutableStateOf(false) }
    var query by rememberSaveable { mutableStateOf("") }
    var searchBounds by remember { mutableStateOf(Rect.Zero) }
    var searchButtonBounds by remember { mutableStateOf(Rect.Zero) }
    var rootCoordinates by remember { mutableStateOf<LayoutCoordinates?>(null) }
    val listState = rememberLazyListState()
    val showActionBorder by remember {
        derivedStateOf { listState.firstVisibleItemIndex > 0 || listState.firstVisibleItemScrollOffset > 0 }
    }
    val focusManager = LocalFocusManager.current
    val closeSearch: () -> Unit = {
        searchExpanded = false
        query = ""
        focusManager.clearFocus()
    }

    // 搜索框展开时，返回键先收起搜索框（键盘已隐藏的情况下）
    BackHandler(enabled = searchExpanded) { closeSearch() }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background)
            .onGloballyPositioned { rootCoordinates = it }
            // 搜索框展开后，点击搜索框以外的任何位置（顶部栏、空白、主区域、工具卡片）都会收起它；
            // 搜索按钮自身交给它的 onClick 处理，避免抬起时又被重新展开
            .pointerInput(searchExpanded) {
                if (!searchExpanded) return@pointerInput
                awaitEachGesture {
                    val down = awaitFirstDown(requireUnconsumed = false)
                    val position = rootCoordinates?.localToWindow(down.position) ?: return@awaitEachGesture
                    if (!searchBounds.contains(position) && !searchButtonBounds.contains(position)) closeSearch()
                }
            },
    ) {
        Scaffold(
            // 内容延伸到系统栏之后（小白条沉浸），底部安全距离由列表内容内边距保证
            contentWindowInsets = WindowInsets(0, 0, 0, 0),
            topBar = {
                HomeTopBar(
                    searchExpanded = searchExpanded,
                    onSearchToggle = { if (searchExpanded) closeSearch() else searchExpanded = true },
                    onSearchButtonBounds = { searchButtonBounds = it },
                    showActionBorder = showActionBorder,
                    themeMode = themeMode,
                    onThemeMode = onThemeMode,
                )
            },
        ) { padding ->
            val cards = when (state) {
                is CatalogState.Ready -> state.tools
                is CatalogState.Failed -> state.tools
                CatalogState.Loading -> emptyList()
            }
            val filtered = cards.filter { card ->
                val info = card.info
                query.isBlank() || listOf(info.slug, info.name, info.category, info.description, *info.keywords.toTypedArray())
                    .any { it.contains(query.trim(), ignoreCase = true) }
            }

            Box(Modifier.fillMaxSize()) {
                // 列表可以滚到小白条之后，底部安全距离由内容内边距保证
                val bottomSafePadding = WindowInsets.navigationBars.asPaddingValues().calculateBottomPadding()
                LazyColumn(
                    modifier = Modifier.fillMaxSize(),
                    state = listState,
                    contentPadding = PaddingValues(start = 20.dp, top = 20.dp + padding.calculateTopPadding(), end = 20.dp, bottom = 20.dp + bottomSafePadding),
                    verticalArrangement = Arrangement.spacedBy(14.dp),
                ) {
                    when (state) {
                        CatalogState.Loading -> item {
                            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                                CircularProgressIndicator(modifier = Modifier.size(22.dp), strokeWidth = 2.dp)
                                Text("正在获取工具目录…")
                            }
                        }
                        is CatalogState.Failed -> item {
                            Text(
                                "工具目录加载失败：${state.message}。本次启动不会重复请求，请完全退出后重开应用。",
                                color = MaterialTheme.colorScheme.error,
                            )
                        }
                        is CatalogState.Ready -> Unit
                    }
                    if (state !is CatalogState.Loading) {
                        if (filtered.isEmpty()) item { Text("没有找到匹配的工具，试试其他关键词。") }
                        else items(filtered, key = { it.info.slug }) { card ->
                            val definition = LocalToolRegistry.find(card.info.slug)
                            ToolCard(card) { if (definition != null) onOpen(definition) }
                        }
                    }
                }
                // 悬浮搜索框：位于顶部栏下方，浮在主区域之上，不改变顶部栏与主区域的布局
                Box(Modifier.fillMaxSize().padding(top = padding.calculateTopPadding()).clipToBounds()) {
                    FloatingSearchBar(
                        expanded = searchExpanded,
                        query = query,
                        onQueryChange = { if (it.length <= 100) query = it },
                        onBoundsChange = { searchBounds = it },
                        modifier = Modifier
                            .align(Alignment.TopStart)
                            .padding(start = 20.dp, end = 20.dp, top = SearchBarTopInset),
                    )
                }
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun HomeTopBar(
    searchExpanded: Boolean,
    onSearchToggle: () -> Unit,
    onSearchButtonBounds: (Rect) -> Unit,
    showActionBorder: Boolean,
    themeMode: ThemeMode,
    onThemeMode: (ThemeMode) -> Unit,
) {
    val context = LocalContext.current
    var menuExpanded by remember { mutableStateOf(false) }
    FadingTopAppBar(
        title = { Text("Superbox", fontWeight = FontWeight.Bold) },
        actions = {
            // 搜索框展开时，搜索按钮换成关闭图标
            CompositionLocalProvider(LocalRippleConfiguration provides null) {
                IconButton(
                    onClick = onSearchToggle,
                    modifier = Modifier
                        .onGloballyPositioned { onSearchButtonBounds(it.boundsInWindow()) }
                        .actionCircle(showActionBorder),
                ) {
                    Icon(
                        painterResource(if (searchExpanded) R.drawable.ic_close else R.drawable.ic_search),
                        contentDescription = if (searchExpanded) "关闭搜索" else "搜索",
                        modifier = Modifier.size(24.dp),
                    )
                }
            }
            Spacer(Modifier.width(8.dp))
            // 三点按钮与其呼出的卡片禁用涟漪（波浪纹）
            CompositionLocalProvider(LocalRippleConfiguration provides null) {
                Box {
                    IconButton(
                        onClick = { menuExpanded = !menuExpanded },
                        modifier = Modifier.actionCircle(showActionBorder),
                    ) {
                        Icon(
                            painterResource(R.drawable.ic_more_vert),
                            contentDescription = "更多选项",
                            modifier = Modifier.size(24.dp),
                        )
                    }
                    MoreMenuCard(
                        expanded = menuExpanded,
                        onDismissRequest = { menuExpanded = false },
                        themeMode = themeMode,
                        onThemeMode = onThemeMode,
                        onApiAccess = {
                            menuExpanded = false
                            context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse("${BuildConfig.API_BASE_URL}/docs")))
                        },
                    )
                }
            }
        },
    )
}

@Composable
private fun Modifier.actionCircle(showBorder: Boolean): Modifier =
    this
        .size(48.dp)
        .clip(CircleShape)
        .background(MaterialTheme.colorScheme.background)
        .border(
            width = 1.dp,
            color = if (showBorder) MaterialTheme.colorScheme.onSurface.copy(alpha = 0.08f) else Color.Transparent,
            shape = CircleShape,
        )

/**
 * 三点按钮呼出的卡片：沿用页面卡片的圆角与配色，右上角与三点按钮重合。
 * 卡片固定在最终位置，可见区域从右上角（按钮处）原地向左下角散开，收起时卷回按钮处。
 */
@Composable
private fun MoreMenuCard(
    expanded: Boolean,
    onDismissRequest: () -> Unit,
    themeMode: ThemeMode,
    onThemeMode: (ThemeMode) -> Unit,
    onApiAccess: () -> Unit,
) {
    val positionProvider = remember {
        object : PopupPositionProvider {
            override fun calculatePosition(
                anchorBounds: IntRect,
                windowSize: IntSize,
                layoutDirection: LayoutDirection,
                popupContentSize: IntSize,
            ): IntOffset {
                val maxX = (windowSize.width - popupContentSize.width).coerceAtLeast(0)
                val maxY = (windowSize.height - popupContentSize.height).coerceAtLeast(0)
                return IntOffset(
                    // 卡片右上角与三点按钮的右上角重合，即从按钮自身位置呼出
                    x = (anchorBounds.right - popupContentSize.width).coerceIn(0, maxX),
                    y = anchorBounds.top.coerceIn(0, maxY),
                )
            }
        }
    }

    SpreadLayer(visible = expanded) { fraction ->
        Popup(
            popupPositionProvider = positionProvider,
            onDismissRequest = onDismissRequest,
            properties = PopupProperties(focusable = true),
        ) {
            Box(modifier = Modifier.spreadFromTopEnd(fraction)) {
                Surface(
                    shape = RoundedCornerShape(18.dp),
                    color = MaterialTheme.colorScheme.surface,
                    shadowElevation = 10.dp,
                    modifier = Modifier.width(304.dp),
                ) {
                    Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .clickable(
                                    interactionSource = remember { MutableInteractionSource() },
                                    indication = null,
                                    onClick = onApiAccess,
                                )
                                .padding(horizontal = 6.dp, vertical = 8.dp),
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            Icon(
                                painterResource(R.drawable.ic_document),
                                contentDescription = null,
                                tint = MaterialTheme.colorScheme.primary,
                                modifier = Modifier.size(20.dp),
                            )
                            Spacer(Modifier.width(10.dp))
                            Text("API 接入", fontWeight = FontWeight.SemiBold)
                        }
                        Text(
                            "主题切换",
                            style = MaterialTheme.typography.labelLarge,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            modifier = Modifier.padding(start = 6.dp),
                        )
                        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                            ThemeMode.entries.forEach { option ->
                                val icon = when (option) {
                                    ThemeMode.SYSTEM -> R.drawable.ic_theme_system
                                    ThemeMode.LIGHT -> R.drawable.ic_theme_light
                                    ThemeMode.DARK -> R.drawable.ic_theme_dark
                                }
                                val label = when (option) {
                                    ThemeMode.SYSTEM -> "系统"
                                    ThemeMode.LIGHT -> "浅色"
                                    ThemeMode.DARK -> "深色"
                                }
                                FilterChip(
                                    selected = themeMode == option,
                                    onClick = { onThemeMode(option) },
                                    label = { Text(label) },
                                    leadingIcon = { Icon(painterResource(icon), contentDescription = null, modifier = Modifier.size(16.dp)) },
                                    modifier = Modifier.weight(1f),
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}

/**
 * 悬浮搜索框：独立于顶部栏、浮在主区域之上，不改变顶部栏与主区域的布局。
 * 圆角放大，输入框自身透明，圆角内部为半透明背景；
 * 整体从顶部栏边缘滑入、滑出，主区域的裁剪让它看上去是从顶部栏后面推出来。
 */
@Composable
private fun FloatingSearchBar(
    expanded: Boolean,
    query: String,
    onQueryChange: (String) -> Unit,
    onBoundsChange: (Rect) -> Unit,
    modifier: Modifier = Modifier,
) {
    DisposableEffect(Unit) { onDispose { onBoundsChange(Rect.Zero) } }
    SpreadLayer(visible = expanded) { fraction ->
        val focusRequester = remember { FocusRequester() }
        var barHeight by remember { mutableFloatStateOf(0f) }
        // 呼出即聚焦：placeholder 只在聚焦时显示，同时符合搜索框的使用预期
        LaunchedEffect(Unit) { focusRequester.requestFocus() }
        Surface(
            shape = RoundedCornerShape(28.dp),
            color = MaterialTheme.colorScheme.surface.copy(alpha = 0.88f),
            shadowElevation = 10.dp,
            modifier = modifier
                .fillMaxWidth()
                .onGloballyPositioned {
                    barHeight = it.size.height.toFloat()
                    onBoundsChange(it.boundsInWindow())
                }
                // 整体上移自身高度 + 顶部间距后正好完全藏进顶部栏；高度测量完成前先整体藏起
                .offset {
                    val distance = if (barHeight > 0f) barHeight + SearchBarTopInset.toPx() else 1_000f
                    IntOffset(0, -(distance * (1f - fraction)).roundToInt())
                },
        ) {
            TextField(
                value = query,
                onValueChange = onQueryChange,
                placeholder = { Text("搜索工具名称或关键词") },
                singleLine = true,
                shape = RoundedCornerShape(28.dp),
                colors = TextFieldDefaults.colors(
                    focusedContainerColor = Color.Transparent,
                    unfocusedContainerColor = Color.Transparent,
                    disabledContainerColor = Color.Transparent,
                    focusedIndicatorColor = Color.Transparent,
                    unfocusedIndicatorColor = Color.Transparent,
                    disabledIndicatorColor = Color.Transparent,
                ),
                modifier = Modifier.fillMaxWidth().focusRequester(focusRequester),
            )
        }
    }
}

/** 展开/收起进度：0 收起、1 完全展开；退场动画播完后自动移出组合，具体动效由调用方使用 fraction 决定。 */
@Composable
private fun SpreadLayer(visible: Boolean, content: @Composable (fraction: Float) -> Unit) {
    val visibleState = remember { MutableTransitionState(false) }
    visibleState.targetState = visible
    if (!visibleState.currentState && !visibleState.targetState) return
    val transition = rememberTransition(visibleState, label = "spreadLayer")
    val fraction by transition.animateFloat(
        transitionSpec = {
            if (targetState) tween(durationMillis = 220, easing = FastOutSlowInEasing)
            else tween(durationMillis = 160, easing = FastOutLinearInEasing)
        },
        label = "spread",
    ) { shown -> if (shown) 1f else 0f }
    content(fraction)
}

/** 以右上角为原点向左下扩散的裁剪显示；外扩的 margin 让阴影同步显现。 */
private fun Modifier.spreadFromTopEnd(fraction: Float): Modifier = drawWithContent {
    if (fraction > 0f) {
        val margin = 12.dp.toPx() * fraction
        clipRect(
            left = size.width * (1f - fraction) - margin,
            top = -margin,
            right = size.width + margin,
            bottom = size.height * fraction + margin,
        ) { this@drawWithContent.drawContent() }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun ToolCard(card: CatalogTool, onClick: () -> Unit) {
    val enabled = card.availability == ToolAvailability.AVAILABLE
    CompositionLocalProvider(LocalRippleConfiguration provides null) {
        Card(
            onClick = onClick,
            enabled = enabled,
            shape = RoundedCornerShape(18.dp),
            colors = CardDefaults.cardColors(
                containerColor = MaterialTheme.colorScheme.surface,
                disabledContainerColor = MaterialTheme.colorScheme.surface,
                disabledContentColor = MaterialTheme.colorScheme.onSurface,
            ),
            modifier = Modifier
                .fillMaxWidth()
                .sharedToolContainer(card.info.slug),
        ) {
            Column(Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    ToolMark(
                        card.info.slug,
                        modifier = Modifier.sharedToolMark(card.info.slug),
                    )
                    Column(
                        modifier = Modifier.weight(1f),
                        verticalArrangement = Arrangement.spacedBy(2.dp),
                    ) {
                        Text(
                            card.info.name,
                            style = MaterialTheme.typography.titleLarge,
                            fontWeight = FontWeight.Bold,
                            modifier = Modifier.sharedToolText(toolTitleKey(card.info.slug)),
                        )
                        Text(card.info.category, color = MaterialTheme.colorScheme.primary, style = MaterialTheme.typography.labelMedium)
                    }
                }
                Text(
                    card.info.description,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.sharedToolText(toolDescriptionKey(card.info.slug)),
                )
                val status = when (card.availability) {
                    ToolAvailability.AVAILABLE -> null
                    ToolAvailability.SERVER_DISABLED -> "云端暂未提供，当前不可使用"
                    ToolAvailability.UPDATE_REQUIRED -> "请更新应用后使用此功能"
                }
                status?.let {
                    Text(
                        it,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        fontWeight = FontWeight.SemiBold,
                    )
                }
            }
        }
    }
}

@Composable
private fun ToolMark(slug: String, modifier: Modifier = Modifier) {
    val dark = MaterialTheme.colorScheme.background == SuperboxColors.darkBackground
    val (mark, tint, lightBackground) = when (slug) {
        "json" -> Triple("{ }", Color(0xFF4F46E5), Color(0xFFE0E7FF))
        "base64" -> Triple("64", Color(0xFF7C3AED), Color(0xFFEDE9FE))
        "url" -> Triple("↗", Color(0xFF0284C7), Color(0xFFE0F2FE))
        "timestamp" -> Triple("◷", Color(0xFFD97706), Color(0xFFFEF3C7))
        "exif" -> Triple("◎", Color(0xFF047857), Color(0xFFD1FAE5))
        else -> Triple("✦", Color(0xFF4F46E5), Color(0xFFE0E7FF))
    }
    Surface(
        color = if (dark) tint.copy(alpha = 0.16f) else lightBackground,
        shape = RoundedCornerShape(16.dp),
        modifier = modifier,
    ) {
        Text(
            mark,
            color = if (dark) tint.copy(alpha = 0.85f) else tint,
            fontWeight = FontWeight.Bold,
            modifier = Modifier.padding(horizontal = 15.dp, vertical = 12.dp),
        )
    }
}
