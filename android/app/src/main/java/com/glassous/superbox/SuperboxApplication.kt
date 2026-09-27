package com.glassous.superbox

import android.app.Application
import com.glassous.superbox.data.ApiClient
import com.glassous.superbox.data.ToolCatalogRepository
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob

class SuperboxApplication : Application() {
    val api by lazy { ApiClient(BuildConfig.API_BASE_URL) }
    private val processScope = CoroutineScope(SupervisorJob() + Dispatchers.Main.immediate)
    val catalog by lazy { ToolCatalogRepository(api::tools, processScope) }

    override fun onCreate() {
        super.onCreate()
        catalog.state // Fetch once at process start, before the first screen is shown.
    }
}
