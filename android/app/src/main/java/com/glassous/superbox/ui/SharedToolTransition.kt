package com.glassous.superbox.ui

import androidx.compose.animation.AnimatedVisibilityScope
import androidx.compose.animation.BoundsTransform
import androidx.compose.animation.EnterTransition
import androidx.compose.animation.ExitTransition
import androidx.compose.animation.ExperimentalSharedTransitionApi
import androidx.compose.animation.SharedTransitionScope
import androidx.compose.animation.core.Easing
import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.compositionLocalOf
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.RectangleShape
import androidx.compose.ui.unit.dp

/**
 * 首页卡片与功能页之间的共享元素转场。
 *
 * 页面本身不做位移：首页在转场期间原地保持，功能页整体并入共享元素，
 * 整段切换看上去是一个连续的动作——卡片容器扩展成整页（主体内容随之展开），
 * 卡片图标滑到顶部栏返回按钮，卡片标题与介绍分别滑到顶部栏标题与介绍文本的位置。
 */

/** 页面转场与共享滑动共用同一条时间线，避免共享元素动画被页面切换提前打断。 */
internal const val ToolTransitionMillis = 320

/** 首页卡片与功能页共享的圆角。 */
private val ToolCardShape = RoundedCornerShape(18.dp)

/** 首页卡片图标与顶部栏返回按钮共享的圆角。 */
private val ToolMarkShape = RoundedCornerShape(16.dp)

/** 共享元素在两端之间的位移与尺寸动画。 */
private val ToolBoundsTransform: BoundsTransform = { _, _ ->
    tween(durationMillis = ToolTransitionMillis, easing = FastOutSlowInEasing)
}

/** 首页退出：转场绝大部分时间里原地完全可见，最后随功能页铺满而消失。 */
private val LateFadeEasing = Easing { fraction -> ((fraction - 0.9f) / 0.1f).coerceIn(0f, 1f) }

/** 首页返回：先快速出现再保持不动，避免首页出现明显的整体淡入。 */
private val EarlyAppearEasing = Easing { fraction -> (fraction / 0.12f).coerceIn(0f, 1f) }

/**
 * 页面级转场只负责占用与共享滑动相同的时长，几乎不产生可见的淡入淡出：
 * 首页原地保持，功能页（自身已是共享元素）先快速就位，视觉变化全部由共享元素承担。
 */
internal val HomeEnter: EnterTransition =
    fadeIn(tween(durationMillis = ToolTransitionMillis, easing = EarlyAppearEasing))

internal val HomeExit: ExitTransition =
    fadeOut(tween(durationMillis = ToolTransitionMillis, easing = LateFadeEasing))

internal val ToolScreenEnter: EnterTransition =
    fadeIn(tween(durationMillis = ToolTransitionMillis, easing = EarlyAppearEasing))

internal val ToolScreenExit: ExitTransition =
    fadeOut(tween(durationMillis = ToolTransitionMillis, easing = LateFadeEasing))

/** 共享内容自身的交接：卡片内容与页面内容在容器展开的同时快速互换。 */
private val ToolContentEnter: EnterTransition =
    fadeIn(tween(durationMillis = 160, easing = FastOutSlowInEasing))

private val ToolContentExit: ExitTransition =
    fadeOut(tween(durationMillis = 160, easing = FastOutSlowInEasing))

/** 共享元素 key：首页卡片与对应功能页成对使用。 */
internal fun toolCardKey(slug: String) = "tool-card-$slug"

internal fun toolMarkKey(slug: String) = "tool-mark-$slug"

internal fun toolTitleKey(slug: String) = "tool-title-$slug"

internal fun toolDescriptionKey(slug: String) = "tool-description-$slug"

@OptIn(ExperimentalSharedTransitionApi::class)
private val LocalSharedTransitionScope = compositionLocalOf<SharedTransitionScope?> { null }

private val LocalSharedElementVisibility = compositionLocalOf<AnimatedVisibilityScope?> { null }

/** 在目的地内容中提供共享元素作用域；缺失时共享修饰符自动退化为普通布局。 */
@OptIn(ExperimentalSharedTransitionApi::class)
@Composable
internal fun ProvideToolSharedTransition(
    sharedTransitionScope: SharedTransitionScope,
    animatedVisibilityScope: AnimatedVisibilityScope,
    content: @Composable () -> Unit,
) {
    CompositionLocalProvider(
        LocalSharedTransitionScope provides sharedTransitionScope,
        LocalSharedElementVisibility provides animatedVisibilityScope,
        content = content,
    )
}

/** 首页卡片容器 ↔ 功能页整页：卡片从列表里的位置展开为完整页面，页内主体随之展开。 */
@OptIn(ExperimentalSharedTransitionApi::class)
@Composable
internal fun Modifier.sharedToolContainer(slug: String): Modifier {
    val shared = LocalSharedTransitionScope.current ?: return this
    val visibility = LocalSharedElementVisibility.current ?: return this
    return with(shared) {
        sharedBounds(
            rememberSharedContentState(toolCardKey(slug)),
            animatedVisibilityScope = visibility,
            enter = ToolContentEnter,
            exit = ToolContentExit,
            boundsTransform = ToolBoundsTransform,
            // 内容随容器尺寸重新布局，展开过程不缩放、不变形
            resizeMode = SharedTransitionScope.ResizeMode.RemeasureToBounds,
            clipInOverlayDuringTransition = OverlayClip(ToolCardShape),
        )
    }
}

/** 首页卡片图标 ↔ 功能页顶部栏返回按钮：图标滑到顶部栏左侧。 */
@OptIn(ExperimentalSharedTransitionApi::class)
@Composable
internal fun Modifier.sharedToolMark(slug: String): Modifier {
    val shared = LocalSharedTransitionScope.current ?: return this
    val visibility = LocalSharedElementVisibility.current ?: return this
    return with(shared) {
        sharedBounds(
            rememberSharedContentState(toolMarkKey(slug)),
            animatedVisibilityScope = visibility,
            enter = ToolContentEnter,
            exit = ToolContentExit,
            boundsTransform = ToolBoundsTransform,
            clipInOverlayDuringTransition = OverlayClip(ToolMarkShape),
        )
    }
}

/** 首页卡片文字 ↔ 功能页文字：两端重测量后平滑滑到对方位置。 */
@OptIn(ExperimentalSharedTransitionApi::class)
@Composable
internal fun Modifier.sharedToolText(key: String): Modifier {
    val shared = LocalSharedTransitionScope.current ?: return this
    val visibility = LocalSharedElementVisibility.current ?: return this
    return with(shared) {
        sharedElement(
            rememberSharedContentState(key),
            animatedVisibilityScope = visibility,
            boundsTransform = ToolBoundsTransform,
            // 文字在卡片与顶部栏之间滑动时会跨出两端容器，转场期间不做裁剪
            clipInOverlayDuringTransition = OverlayClip(RectangleShape),
        )
    }
}
