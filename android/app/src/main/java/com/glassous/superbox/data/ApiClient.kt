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
            throw ApiException("无法连接后端服务，请检查网络和 API 地址。")
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

    suspend fun editExif(filename: String, image: ByteArray, changes: List<ExifChange>): ByteArray {
        val (type, body) = multipart(filename, image, changes)
        return request("exif/edit", "POST", type, body)
    }
}

private inline fun <T> JSONArray.mapObjects(transform: (JSONObject) -> T): List<T> =
    (0 until length()).map { transform(getJSONObject(it)) }

private fun JSONArray.mapStrings(): List<String> = (0 until length()).map { getString(it) }
