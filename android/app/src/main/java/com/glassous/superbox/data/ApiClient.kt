package com.glassous.superbox.data

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.ensureActive
import kotlinx.coroutines.job
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.nio.charset.StandardCharsets
import java.util.UUID

data class ToolInfo(
    val slug: String,
    val name: String,
    val category: String,
    val description: String,
    val keywords: List<String> = emptyList(),
)

data class ExifTag(
    val key: String,
    val group: String,
    val name: String,
    val value: String,
    val writable: Boolean,
    val reason: String,
)

data class ExifCatalogTag(val key: String, val name: String, val writable: Boolean)
data class ExifInspection(val format: String, val tags: List<ExifTag>)
data class ExifChange(val key: String, val action: String, val value: String = "")

data class CurrencyInfo(val code: String, val name: String)
fun CurrencyInfo.localizedName(): String = runCatching {
    java.util.Currency.getInstance(code).getDisplayName(java.util.Locale.SIMPLIFIED_CHINESE)
}.getOrNull()?.takeIf { it != code } ?: name

sealed interface CurrencyBatchItem {
    val to: String
    fun display(): String
}
data class CurrencySuccess(val conversion: CurrencyConversion) : CurrencyBatchItem {
    override val to: String get() = conversion.to
    override fun display(): String = conversion.display()
}
data class CurrencyFailure(override val to: String, val code: String, val message: String) : CurrencyBatchItem {
    override fun display(): String = "$to：$message"
}
data class CurrencyBatchConversion(val amount: String, val from: String, val precision: Int, val count: Int, val results: List<CurrencyBatchItem>)
data class CurrencyConversion(
    val amount: String, val from: String, val to: String, val result: String,
    val rate: String, val rateDate: String?, val source: String, val fetchedAt: String?,
    val cached: Boolean, val stale: Boolean,
) {
    fun display(): String = "$amount $from = $result $to\n参考汇率：$rate\n参考日期：${rateDate ?: "同币种"}\n来源：${if (source == "identity") "同币种" else source}" +
        (if (stale) "\n暂用上次获取的数据" else "")
}
data class ProcessedFile(val url: String, val filename: String, val contentType: String, val size: Long, val expiresAt: String)
data class DocumentConversion(val result: String, val format: String, val filename: String, val warnings: List<String>, val characters: Int, val file: ProcessedFile)

class ApiException(message: String, val status: Int? = null, val code: String? = null) : Exception(message)

fun apiPath(baseUrl: String, path: String): String =
    "${baseUrl.trimEnd('/')}/api/v1/${path.trimStart('/')}"

fun calculateExifChanges(
    original: List<ExifTag>,
    drafts: Map<String, String>,
    deleted: Set<String>,
): List<ExifChange> {
    val originalByKey = original.associateBy(ExifTag::key)
    val result = deleted.filter(originalByKey::containsKey).map { ExifChange(it, "delete") }.toMutableList()
    for ((key, value) in drafts) {
        if (key !in deleted && value != originalByKey[key]?.value) {
            result += ExifChange(key, "set", value)
        }
    }
    return result
}

class ApiClient(private val baseUrl: String) {
    private suspend fun request(
        path: String,
        method: String = "GET",
        contentType: String? = null,
        body: ByteArray? = null,
    ): ByteArray = withContext(Dispatchers.IO) {
        val connection = (URL(apiPath(baseUrl, path)).openConnection() as HttpURLConnection).apply {
            requestMethod = method
            connectTimeout = 10_000
            readTimeout = 45_000
            setRequestProperty("Accept", "application/json, image/*")
            if (contentType != null) setRequestProperty("Content-Type", contentType)
            if (body != null) doOutput = true
        }
        val completion = currentCoroutineContext().job.invokeOnCompletion { connection.disconnect() }
        try {
            if (body != null) connection.outputStream.use { it.write(body) }
            val status = connection.responseCode
            val response = (if (status in 200..299) connection.inputStream else connection.errorStream)
                ?.use { it.readBytes() } ?: byteArrayOf()
            currentCoroutineContext().ensureActive()
            if (status !in 200..299) {
                val json = runCatching { JSONObject(String(response, StandardCharsets.UTF_8)) }.getOrNull()
                throw ApiException(
                    json?.optString("message")?.takeIf(String::isNotBlank) ?: "请求失败（HTTP $status）",
                    status,
                    json?.optString("code"),
                )
            }
            response
        } catch (error: java.io.IOException) {
            currentCoroutineContext().ensureActive()
            throw ApiException("连接失败，请检查网络后重试")
        } finally {
            completion.dispose()
            connection.disconnect()
        }
    }

    private suspend fun json(path: String, method: String = "GET", body: JSONObject? = null): JSONObject {
        val bytes = request(
            path,
            method,
            if (body == null) null else "application/json; charset=utf-8",
            body?.toString()?.toByteArray(StandardCharsets.UTF_8),
        )
        return try {
            JSONObject(String(bytes, StandardCharsets.UTF_8))
        } catch (_: Exception) {
            throw ApiException("服务返回了无法读取的响应。")
        }
    }

    suspend fun tools(): List<ToolInfo> {
        return json("tools").getJSONArray("tools").mapObjects { item ->
            ToolInfo(
                item.getString("slug"), item.getString("name"), item.getString("category"),
                item.getString("description"), item.optJSONArray("keywords")?.mapStrings().orEmpty(),
            )
        }
    }

    suspend fun textOperation(path: String, text: String): String =
        json(path, "POST", JSONObject().put("text", text)).getString("result")

    suspend fun currentTime(): String = json("time/now").let {
        listOf("获取时间：${it.getString("iso_datetime")}", "时区：东八区（${it.getString("timezone")}）",
            "星期：${it.getInt("weekday")}", "Unix 秒：${it.getString("unix_seconds")}",
            "Unix 毫秒：${it.getString("unix_milliseconds")}").joinToString("\n")
    }

    suspend fun currencies(): List<CurrencyInfo> = json("currency/currencies").getJSONArray("currencies").mapObjects {
        CurrencyInfo(it.getString("code"), it.getString("name"))
    }

    suspend fun convertCurrency(amount: String, from: String, to: String, precision: Int): CurrencyConversion =
        json("currency/convert", "POST", JSONObject().put("amount", amount).put("from_currency", from)
            .put("to_currency", to).put("precision", precision)).let {
            parseCurrency(it)
        }

    private fun parseCurrency(item: JSONObject) = CurrencyConversion(
        item.getString("amount"), item.getString("from_currency"), item.getString("to_currency"),
        item.getString("result"), item.getString("rate"), if (item.isNull("rate_date")) null else item.getString("rate_date"),
        item.getString("source"), if (item.isNull("fetched_at")) null else item.getString("fetched_at"), item.getBoolean("cached"), item.getBoolean("stale"),
    )

    suspend fun convertCurrencies(amount: String, from: String, targets: List<String>, precision: Int): CurrencyBatchConversion {
        require(targets.size in 1..50) { "请选择 1–50 种目标货币" }
        require(targets.map { it.uppercase(java.util.Locale.ROOT) }.distinct().size == targets.size) { "目标币种不能重复" }
        val response = json("currency/convert-batch", "POST", JSONObject().put("amount", amount)
            .put("from_currency", from).put("to_currencies", JSONArray(targets)).put("precision", precision))
        val results = response.getJSONArray("results").mapObjects<CurrencyBatchItem> { item ->
            when (item.getString("status")) {
                "success" -> CurrencySuccess(parseCurrency(item))
                "error" -> CurrencyFailure(item.getString("to_currency"), item.getString("code"), item.getString("message"))
                else -> throw ApiException("服务返回了无法读取的响应。")
            }
        }
        return CurrencyBatchConversion(response.getString("amount"), response.getString("from_currency"),
            response.getInt("precision"), response.getInt("count"), results)
    }

    suspend fun convertDocument(filename: String?, file: ByteArray?, fileUrl: String, format: String): DocumentConversion {
        require((file != null) != fileUrl.isNotBlank()) { "请只提供文件或公开文件链接中的一种" }
        require(file == null || file.size <= 5 * 1024 * 1024) { "文件不能超过 5 MiB" }
        val boundary = "superbox-${UUID.randomUUID()}"
        val body = java.io.ByteArrayOutputStream()
        fun write(value: String) = body.write(value.toByteArray(StandardCharsets.UTF_8))
        if (file != null) {
            val safeName = (filename ?: "document").replace(Regex("[\\r\\n\"]"), "_")
            write("--$boundary\r\nContent-Disposition: form-data; name=\"file\"; filename=\"$safeName\"\r\nContent-Type: application/octet-stream\r\n\r\n")
            body.write(file); write("\r\n")
        } else {
            write("--$boundary\r\nContent-Disposition: form-data; name=\"file_url\"\r\n\r\n$fileUrl\r\n")
        }
        write("--$boundary\r\nContent-Disposition: form-data; name=\"format\"\r\n\r\n$format\r\n--$boundary--\r\n")
        val response = JSONObject(String(request("documents/convert", "POST", "multipart/form-data; boundary=$boundary", body.toByteArray()), StandardCharsets.UTF_8))
        return DocumentConversion(response.getString("result"), response.getString("format"), response.getString("filename"),
            response.getJSONArray("warnings").mapStrings(), response.getJSONObject("stats").getInt("characters"), parseFile(response))
    }

    suspend fun validateJson(text: String): Pair<Boolean, String> =
        json("json/validate", "POST", JSONObject().put("text", text)).let {
            it.getBoolean("valid") to it.getString("message")
        }

    suspend fun timestampToDate(value: String, unit: String): String =
        json("timestamp/to-datetime", "POST", JSONObject().put("value", value).put("unit", unit))
            .getString("iso_utc")

    suspend fun dateToTimestamp(value: String): String =
        json("timestamp/to-unix", "POST", JSONObject().put("iso_datetime", value)).let {
            "UTC 时间：${it.getString("iso_utc")}\n秒：${it.getString("seconds")}\n毫秒：${it.getString("milliseconds")}" 
        }

    private fun multipart(filename: String, image: ByteArray, changes: List<ExifChange>?): Pair<String, ByteArray> {
        val boundary = "superbox-${UUID.randomUUID()}"
        val bytes = java.io.ByteArrayOutputStream()
        fun write(value: String) = bytes.write(value.toByteArray(StandardCharsets.UTF_8))
        val safeFilename = filename.replace(Regex("[\\r\\n\"]"), "_")
        write("--$boundary\r\nContent-Disposition: form-data; name=\"image\"; filename=\"$safeFilename\"\r\n")
        val mime = when (filename.substringAfterLast('.', "").lowercase()) {
            "jpg", "jpeg" -> "image/jpeg"
            "png" -> "image/png"
            else -> "image/webp"
        }
        write("Content-Type: $mime\r\n\r\n")
        bytes.write(image)
        write("\r\n")
        if (changes != null) {
            val array = JSONArray()
            changes.forEach { change ->
                val item = JSONObject().put("key", change.key).put("action", change.action)
                if (change.action == "set") item.put("value", change.value)
                array.put(item)
            }
            write("--$boundary\r\nContent-Disposition: form-data; name=\"changes\"\r\n\r\n${array}\r\n")
        }
        write("--$boundary--\r\n")
        return "multipart/form-data; boundary=$boundary" to bytes.toByteArray()
    }

    suspend fun inspectExif(filename: String, image: ByteArray): ExifInspection {
        val (type, body) = multipart(filename, image, null)
        val result = JSONObject(String(request("exif/inspect", "POST", type, body), StandardCharsets.UTF_8))
        return ExifInspection(result.getString("format"), result.getJSONArray("tags").mapObjects { tag ->
            ExifTag(
                tag.getString("key"), tag.getString("group"), tag.getString("name"),
                tag.getString("value"), tag.getBoolean("writable"), tag.optString("reason"),
            )
        })
    }

    suspend fun searchExifTags(query: String): List<ExifCatalogTag> =
        json("exif/tags?q=${java.net.URLEncoder.encode(query, "UTF-8")}").getJSONArray("tags")
            .mapObjects { ExifCatalogTag(it.getString("key"), it.getString("name"), it.getBoolean("writable")) }

    private fun parseFile(response: JSONObject) = ProcessedFile(
        response.getString("url"), response.getString("filename"), response.getString("content_type"),
        response.getLong("size"), response.getString("expires_at"),
    )

    suspend fun editExif(filename: String, image: ByteArray, changes: List<ExifChange>): ProcessedFile {
        val (type, body) = multipart(filename, image, changes)
        return parseFile(JSONObject(String(request("exif/edit", "POST", type, body), StandardCharsets.UTF_8)))
    }

    suspend fun downloadFile(file: ProcessedFile): ByteArray = withContext(Dispatchers.IO) {
        val url = URL(file.url)
        require(url.protocol == "https") { "文件下载地址必须使用 HTTPS" }
        require(file.size in 0..(20L * 1024 * 1024)) { "下载文件超过大小限制" }
        if (!java.time.Instant.now().isBefore(java.time.Instant.parse(file.expiresAt))) {
            throw ApiException("文件下载地址已过期，请重新处理文件")
        }
        val connection = (url.openConnection() as HttpURLConnection).apply {
            connectTimeout = 10_000
            readTimeout = 45_000
            useCaches = false
        }
        val completion = currentCoroutineContext().job.invokeOnCompletion { connection.disconnect() }
        try {
            val status = connection.responseCode
            if (status !in 200..299) throw ApiException(
                if (status == 404) "文件已过期或不存在，请重新处理文件" else "文件下载失败（HTTP $status）", status,
            )
            val bytes = java.io.ByteArrayOutputStream()
            connection.inputStream.use { input ->
                val buffer = ByteArray(64 * 1024)
                while (true) {
                    currentCoroutineContext().ensureActive()
                    val count = input.read(buffer)
                    if (count < 0) break
                    if (bytes.size().toLong() + count > file.size) throw ApiException("下载文件大小与返回信息不一致")
                    bytes.write(buffer, 0, count)
                }
            }
            currentCoroutineContext().ensureActive()
            if (bytes.size().toLong() != file.size) throw ApiException("文件下载不完整，请重试")
            bytes.toByteArray()
        } catch (error: java.io.IOException) {
            currentCoroutineContext().ensureActive()
            throw ApiException("文件下载失败，请检查网络后重试")
        } finally {
            completion.dispose()
            connection.disconnect()
        }
    }
}

private inline fun <T> JSONArray.mapObjects(transform: (JSONObject) -> T): List<T> =
    (0 until length()).map { transform(getJSONObject(it)) }

private fun JSONArray.mapStrings(): List<String> = (0 until length()).map { getString(it) }
