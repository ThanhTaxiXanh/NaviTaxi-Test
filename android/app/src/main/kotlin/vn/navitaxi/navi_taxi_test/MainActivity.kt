package vn.navitaxi.navi_taxi_test

import android.os.StatFs
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterActivity() {
    private val channelName = "vn.navitaxi/map_storage"

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        MethodChannel(
            flutterEngine.dartExecutor.binaryMessenger,
            channelName
        ).setMethodCallHandler { call, result ->
            val dir = getExternalFilesDir(null) ?: filesDir
            when (call.method) {
                "getOfflineDirectory" -> result.success(dir.absolutePath)
                "getAvailableBytes" -> result.success(
                    StatFs(dir.absolutePath).availableBytes
                )
                else -> result.notImplemented()
            }
        }
    }
}
