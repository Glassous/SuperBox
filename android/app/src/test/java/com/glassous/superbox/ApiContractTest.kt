package com.glassous.superbox

import com.glassous.superbox.data.ApiClient
import com.glassous.superbox.data.ApiException
import com.glassous.superbox.data.ExifTag
import com.glassous.superbox.data.CatalogState
import com.glassous.superbox.data.ToolAvailability
import com.glassous.superbox.data.ToolCatalogRepository
import com.glassous.superbox.data.ToolInfo
import com.glassous.superbox.data.apiPath
import com.glassous.superbox.data.calculateExifChanges
import com.glassous.superbox.data.reconcileTools
import com.glassous.superbox.ui.ThemeMode
import com.glassous.superbox.ui.parseThemeMode
import com.sun.net.httpserver.HttpServer
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test
import java.net.InetSocketAddress

class ApiContractTest {
    @Test fun newToolsUseExpectedGetJsonAndMultipartContracts() = runBlocking {
        val requests = mutableListOf<Pair<String, String>>()
        val server = HttpServer.create(InetSocketAddress("127.0.0.1", 0), 0)
        server.createContext("/") { exchange ->
            val path = exchange.requestURI.path
            val requestBody = exchange.requestBody.bufferedReader().readText()
            requests += path to requestBody
            val reply = when (path) {
                "/api/v1/time/now" -> """{"iso_datetime":"2026-10-02T12:00:00.000+08:00","timezone":"UTC+08:00","weekday":5,"unix_seconds":"1790913600","unix_milliseconds":"1790913600000"}"""
                "/api/v1/currency/currencies" -> """{"currencies":[{"code":"CNY","name":"Yuan"},{"code":"USD","name":"Dollar"}]}"""
                "/api/v1/currency/convert" -> """{"amount":"1","from_currency":"CNY","to_currency":"USD","result":"0.14","rate":"0.14","rate_date":"2026-10-01","source":"Frankfurter","fetched_at":"2026-10-02T04:00:00Z","cached":true,"stale":true}"""
                else -> """{"result":"中文正文","format":"markdown","filename":"报告.md","warnings":["部分页面无文字"],"stats":{"characters":4}}"""
            }.toByteArray()
            exchange.responseHeaders.add("Content-Type", "application/json")
            exchange.sendResponseHeaders(200, reply.size.toLong())
            exchange.responseBody.use { it.write(reply) }
        }
        server.start()
        try {
            val api = ApiClient("http://127.0.0.1:${server.address.port}")
            assertEquals(true, api.currentTime().contains("+08:00"))
            assertEquals(listOf("CNY", "USD"), api.currencies().map { it.code })
            val converted = api.convertCurrency("1", "CNY", "USD", 2)
            assertEquals("0.14", converted.result)
            assertEquals(true, converted.stale)
            val json = org.json.JSONObject(requests.last().second)
            assertEquals("1", json.getString("amount")); assertEquals(2, json.getInt("precision"))
            val uploaded = api.convertDocument("报告.docx", "test".toByteArray(), "", "markdown")
            assertEquals("报告.md", uploaded.filename); assertEquals("中文正文", uploaded.result)
            assertEquals(true, requests.last().second.contains("name=\"file\"; filename=\"报告.docx\""))
            assertEquals(true, requests.last().second.contains("name=\"format\""))
            api.convertDocument(null, null, "https://example.com/report.pdf", "txt")
            assertEquals(true, requests.last().second.contains("name=\"file_url\""))
            assertEquals(false, requests.last().second.contains("filename="))
        } finally { server.stop(0) }
    }

    @Test fun documentUploadRejectsOversizeBeforeNetwork() {
        assertThrows(IllegalArgumentException::class.java) {
            runBlocking { ApiClient("http://127.0.0.1:1").convertDocument("a.pdf", ByteArray(5 * 1024 * 1024 + 1), "", "txt") }
        }
    }

    @Test fun baseUrlAddsApiPrefixExactlyOnce() {
        assertEquals(
            "https://superbox.example/api/v1/json/format",
            apiPath("https://superbox.example/", "/json/format"),
        )
    }

    @Test fun textOperationSendsExpectedJsonAndPath() = runBlocking {
        var path = ""
        var body = ""
        val server = HttpServer.create(InetSocketAddress("127.0.0.1", 0), 0)
        server.createContext("/") { exchange ->
            path = exchange.requestURI.path
            body = exchange.requestBody.bufferedReader().readText()
            val reply = "{\"result\":\"ok\"}".toByteArray()
            exchange.responseHeaders.add("Content-Type", "application/json")
            exchange.sendResponseHeaders(200, reply.size.toLong())
            exchange.responseBody.use { it.write(reply) }
        }
        server.start()
        try {
            assertEquals("ok", ApiClient("http://127.0.0.1:${server.address.port}/").textOperation("json/format", "中文"))
            assertEquals("/api/v1/json/format", path)
            assertEquals("中文", org.json.JSONObject(body).getString("text"))
        } finally {
            server.stop(0)
        }
    }

    @Test fun apiErrorsKeepStatusAndCode() = runBlocking {
        val server = HttpServer.create(InetSocketAddress("127.0.0.1", 0), 0)
        server.createContext("/") { exchange ->
            val reply = "{\"code\":\"INVALID_INPUT\",\"message\":\"输入无效\"}".toByteArray()
            exchange.sendResponseHeaders(400, reply.size.toLong())
            exchange.responseBody.use { it.write(reply) }
        }
        server.start()
        try {
            val cause = assertThrows(ApiException::class.java) {
                runBlocking { ApiClient("http://127.0.0.1:${server.address.port}").validateJson("bad") }
            }
            assertEquals(400, cause.status)
            assertEquals("INVALID_INPUT", cause.code)
            assertEquals("输入无效", cause.message)
        } finally {
            server.stop(0)
        }
    }

    @Test fun exifDiffIgnoresUnchangedAndNeverDeletesNewDrafts() {
        val original = listOf(ExifTag("EXIF:Artist", "EXIF", "Artist", "Before", true, ""))
        val changes = calculateExifChanges(original, mapOf("EXIF:Artist" to "Before", "EXIF:Copyright" to "New"), setOf("EXIF:Artist"))
        assertEquals(listOf("delete:EXIF:Artist", "set:EXIF:Copyright"), changes.map { "${it.action}:${it.key}" })
    }

    @Test fun themeFallsBackToSystem() {
        assertEquals(ThemeMode.DARK, parseThemeMode("DARK"))
        assertEquals(ThemeMode.SYSTEM, parseThemeMode("unexpected"))
        assertEquals(ThemeMode.SYSTEM, parseThemeMode(null))
    }

    @Test fun cloudAndLocalCatalogAreReconciledInCloudOrder() {
        val result = reconcileTools(listOf(
            ToolInfo("json", "服务器 JSON", "数据", "在线"),
            ToolInfo("future", "新功能", "其他", "需要新版本"),
        ))
        assertEquals(listOf("json", "future", "base64", "url", "timestamp", "exif", "time", "currency", "documents"), result.map { it.info.slug })
        assertEquals(ToolAvailability.AVAILABLE, result[0].availability)
        assertEquals("服务器 JSON", result[0].info.name)
        assertEquals(ToolAvailability.UPDATE_REQUIRED, result[1].availability)
        assertEquals(ToolAvailability.SERVER_DISABLED, result[2].availability)
    }

    @Test fun catalogIsFetchedOnlyOnceForRepositoryLifetime() {
        var calls = 0
        val catalog = ToolCatalogRepository(
            fetch = { calls++; listOf(ToolInfo("json", "JSON", "数据", "在线")) },
            scope = CoroutineScope(Dispatchers.Unconfined),
        )
        assertEquals(1, calls)
        assertEquals(ToolAvailability.AVAILABLE, (catalog.state.value as CatalogState.Ready).tools.first().availability)
        // Reading the catalog repeatedly, like navigating away and back, cannot invoke the API.
        repeat(3) { catalog.state.value }
        assertEquals(1, calls)
    }
}
