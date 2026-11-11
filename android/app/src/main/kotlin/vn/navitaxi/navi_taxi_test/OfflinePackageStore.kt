package vn.navitaxi.navi_taxi_test

import android.app.Activity
import android.content.Intent
import android.net.Uri
import android.os.StatFs
import io.flutter.embedding.android.FlutterActivity
import io.flutter.plugin.common.MethodCall
import io.flutter.plugin.common.MethodChannel
import java.io.File
import java.io.FileInputStream
import java.io.FileOutputStream
import java.security.MessageDigest
import java.util.concurrent.Executors

/**
 * Secure local intake of user-selected PMTiles.
 *
 * All archives remain under app-private /files/offline-quarantine/. This class
 * permits strictly debug-only local review AFTER a complete SHA-256 check.
 * Production P0 map activation remains independently gated and unmodified.
 *
 * SAF is used for the initial user-file import, so broad Android storage
 * permissions are unnecessary. The executor keeps large file I/O off the UI.
 */
class OfflinePackageStore(private val activity: FlutterActivity) {
    private data class Spec(val bytes: Long, val sha256: String)

    private val knownArchives = mapOf(
        "hotosm_vnm_roads_osm.pmtiles" to Spec(
            249894089L,
            "ca575f95bc708ec1fb39e0c3b3f5ee4a3f1596e75e5a0b1f6e50f85e8a28bedd"
        ),
        "hotosm_vnm_buildings_osm.pmtiles" to Spec(
            75340271L,
            "8c6f129a2bf2237215d90be72a52475cb6f0f528ac41dfabc5434d832ca37b6f"
        ),
        "hotosm_vnm_points_of_interest_osm.pmtiles" to Spec(
            15966991L,
            "dda5a9de8412e8d6bdc73ae62d4fa2c3f8ef017bcbc0c833bc2a9e441be87763"
        )
    )

    private val executor = Executors.newSingleThreadExecutor()
    private val quarantineDir: File by lazy {
        File(activity.filesDir, "offline-quarantine").apply {
            check(exists() || mkdirs()) { "Unable to create quarantine storage" }
        }
    }
    private var pendingPicker: MethodChannel.Result? = null
    private var pendingFilename: String? = null

    companion object {
        const val FILE_PICKER_REQUEST = 47072
        private const val COPY_BUFFER = 128 * 1024
        private val MAGIC = "PMTiles".toByteArray(Charsets.US_ASCII) + byteArrayOf(3)
    }

    private fun sendError(result: MethodChannel.Result, cause: Throwable) {
        activity.runOnUiThread {
            result.error(
                "OFFLINE_INTAKE_FAILED",
                cause.message ?: "Unknown archive intake error",
                null
            )
        }
    }

    private fun runIo(
        result: MethodChannel.Result,
        task: () -> Any?
    ) {
        executor.execute {
            try {
                val value = task()
                activity.runOnUiThread { result.success(value) }
            } catch (cause: Exception) {
                sendError(result, cause)
            }
        }
    }

    fun handle(call: MethodCall, result: MethodChannel.Result) {
        when (call.method) {
            "getOfflineDirectory" -> result.success(quarantineDir.absolutePath)
            "getAvailableBytes" -> result.success(StatFs(quarantineDir.path).availableBytes)
            "listImported" -> runIo(result) {
                knownArchives.keys.sorted().mapNotNull { filename ->
                    val file = File(quarantineDir, filename)
                    if (!file.isFile) null else mapOf(
                        "filename" to filename,
                        "bytes" to file.length(),
                        "status" to "quarantined"
                    )
                }
            }
            "getVerifiedArchivePathsDebug" -> {
                // Never grant local tile access to a non-debug APK.
                val debugBuild = activity.applicationInfo.flags and
                    android.content.pm.ApplicationInfo.FLAG_DEBUGGABLE != 0
                if (!debugBuild) {
                    result.error("DEBUG_ONLY", "PMTiles review is not available in release builds", null)
                    return
                }
                runIo(result) {
                    knownArchives.entries.mapNotNull { (filename, spec) ->
                        val file = File(quarantineDir, filename)
                        val valid = file.isFile &&
                            file.length() == spec.bytes &&
                            hasValidHeader(file) &&
                            digest(file) == spec.sha256
                        if (valid) filename to file.canonicalPath else null
                    }.toMap()
                }
            }
            "verifyImported" -> {
                val filename = call.argument<String>("filename")
                if (filename !in knownArchives) {
                    result.error("UNRECOGNIZED_PACKAGE", "Package is not in the intake catalog", null)
                    return
                }
                runIo(result) {
                    val spec = knownArchives.getValue(filename!!)
                    val file = File(quarantineDir, filename)
                    val verified = file.isFile &&
                        file.length() == spec.bytes &&
                        hasValidHeader(file) &&
                        digest(file) == spec.sha256
                    mapOf(
                        "filename" to filename,
                        "sha256Verified" to verified,
                        "status" to "quarantined",
                        "p0Approved" to false
                    )
                }
            }
            "deleteImported" -> {
                val filename = call.argument<String>("filename")
                if (filename !in knownArchives) {
                    result.error("UNRECOGNIZED_PACKAGE", "Invalid quarantine entry", null)
                    return
                }
                runIo(result) {
                    val file = File(quarantineDir, filename!!)
                    !file.exists() || file.delete()
                }
            }
            "importArchive" -> {
                val filename = call.argument<String>("filename")
                if (filename !in knownArchives) {
                    result.error("UNRECOGNIZED_PACKAGE", "Invalid catalog filename", null)
                    return
                }
                if (pendingPicker != null) {
                    result.error("IMPORT_BUSY", "Another file picker is active", null)
                    return
                }
                pendingPicker = result
                pendingFilename = filename
                try {
                    val intent = Intent(Intent.ACTION_OPEN_DOCUMENT).apply {
                        addCategory(Intent.CATEGORY_OPENABLE)
                        type = "*/*"
                    }
                    activity.startActivityForResult(intent, FILE_PICKER_REQUEST)
                } catch (cause: Exception) {
                    pendingPicker = null
                    pendingFilename = null
                    result.error("FILE_PICKER_UNAVAILABLE", cause.message, null)
                }
            }
            else -> result.notImplemented()
        }
    }

    @Suppress("DEPRECATION")
    fun onFilePickerResult(
        requestCode: Int,
        resultCode: Int,
        data: Intent?
    ): Boolean {
        if (requestCode != FILE_PICKER_REQUEST) return false
        val reply = pendingPicker ?: return true
        val filename = pendingFilename
        pendingPicker = null
        pendingFilename = null

        val uri = data?.data
        if (resultCode != Activity.RESULT_OK || uri == null || filename == null) {
            reply.success(null)
            return true
        }

        runIo(reply) { copyToQuarantine(uri, filename) }
        return true
    }

    private fun hasValidHeader(file: File): Boolean {
        FileInputStream(file).use { stream ->
            val header = ByteArray(MAGIC.size)
            return stream.read(header) == MAGIC.size && header.contentEquals(MAGIC)
        }
    }

    private fun digest(file: File): String {
        val sha = MessageDigest.getInstance("SHA-256")
        FileInputStream(file).use { input ->
            val chunk = ByteArray(COPY_BUFFER)
            while (true) {
                val read = input.read(chunk)
                if (read < 0) break
                if (read > 0) sha.update(chunk, 0, read)
            }
        }
        return sha.digest().joinToString("") { "%02x".format(it.toInt() and 0xff) }
    }

    private fun copyToQuarantine(uri: Uri, filename: String): Map<String, Any> {
        val spec = knownArchives.getValue(filename)
        val destination = File(quarantineDir, filename)
        if (destination.exists()) {
            check(
                destination.isFile &&
                    destination.length() == spec.bytes &&
                    hasValidHeader(destination) &&
                    digest(destination) == spec.sha256
            ) { "Existing package is damaged. Delete it before reimporting." }
            return mapOf(
                "filename" to filename,
                "bytes" to spec.bytes,
                "sha256Verified" to true,
                "status" to "quarantined",
                "p0Approved" to false
            )
        }

        val temporary = File.createTempFile("incoming-", ".partial", quarantineDir)
        try {
            val hash = MessageDigest.getInstance("SHA-256")
            var total = 0L
            val source = activity.contentResolver.openInputStream(uri)
                ?: error("Cannot read selected file")
            source.use { input ->
                FileOutputStream(temporary).use { output ->
                    val buffer = ByteArray(COPY_BUFFER)
                    while (true) {
                        val count = input.read(buffer)
                        if (count < 0) break
                        if (count == 0) continue
                        total += count
                        check(total <= spec.bytes) { "Selected archive exceeds expected byte length" }
                        hash.update(buffer, 0, count)
                        output.write(buffer, 0, count)
                    }
                    output.fd.sync()
                }
            }
            check(total == spec.bytes) { "Selected archive is incomplete" }
            check(hasValidHeader(temporary)) { "PMTiles v3 header is invalid" }
            val calculatedHash = hash.digest().joinToString("") {
                "%02x".format(it.toInt() and 0xff)
            }
            check(calculatedHash == spec.sha256) { "Archive SHA-256 is not in catalog" }
            check(temporary.renameTo(destination)) { "Atomic package rename failed" }
            return mapOf(
                "filename" to filename,
                "bytes" to spec.bytes,
                "sha256Verified" to true,
                "status" to "quarantined",
                "p0Approved" to false
            )
        } finally {
            temporary.delete()
        }
    }

    fun dispose() {
        pendingPicker?.error("ACTIVITY_CLOSED", "Import interrupted", null)
        pendingPicker = null
        pendingFilename = null
        executor.shutdown()
    }
}
