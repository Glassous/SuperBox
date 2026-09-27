package com.glassous.superbox.data

import com.glassous.superbox.navigation.LocalToolRegistry
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

enum class ToolAvailability { AVAILABLE, SERVER_DISABLED, UPDATE_REQUIRED }

data class CatalogTool(val info: ToolInfo, val availability: ToolAvailability)

sealed interface CatalogState {
    data object Loading : CatalogState
    data class Ready(val tools: List<CatalogTool>) : CatalogState
    data class Failed(val message: String, val tools: List<CatalogTool>) : CatalogState
}

fun reconcileTools(remote: List<ToolInfo>): List<CatalogTool> {
    val seen = mutableSetOf<String>()
    val cloudCards = remote.filter { seen.add(it.slug) }.map { info ->
        CatalogTool(
            info,
            if (LocalToolRegistry.find(info.slug) == null) ToolAvailability.UPDATE_REQUIRED
            else ToolAvailability.AVAILABLE,
        )
    }
    val localOnly = LocalToolRegistry.all.filter { it.slug !in seen }.map { definition ->
        CatalogTool(definition.fallback, ToolAvailability.SERVER_DISABLED)
    }
    return cloudCards + localOnly
}

/** One repository instance belongs to the Application process. Construction triggers exactly one fetch. */
class ToolCatalogRepository(
    fetch: suspend () -> List<ToolInfo>,
    scope: CoroutineScope,
) {
    private val mutableState = MutableStateFlow<CatalogState>(CatalogState.Loading)
    val state: StateFlow<CatalogState> = mutableState.asStateFlow()

    init {
        scope.launch {
            try {
                mutableState.value = CatalogState.Ready(reconcileTools(fetch()))
            } catch (cancel: CancellationException) {
                throw cancel
            } catch (error: Exception) {
                mutableState.value = CatalogState.Failed(
                    error.message ?: "工具目录加载失败",
                    reconcileTools(emptyList()),
                )
            }
        }
    }
}
