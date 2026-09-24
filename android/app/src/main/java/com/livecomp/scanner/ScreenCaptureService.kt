package com.livecomp.scanner

import android.app.*
import android.content.*
import android.content.pm.ServiceInfo
import android.graphics.Bitmap
import android.graphics.PixelFormat
import android.hardware.display.DisplayManager
import android.hardware.display.VirtualDisplay
import android.media.ImageReader
import android.media.projection.MediaProjection
import android.media.projection.MediaProjectionManager
import android.os.*
import android.util.DisplayMetrics
import android.util.Log
import android.view.WindowManager
import androidx.core.app.NotificationCompat
import kotlinx.coroutines.*

class ScreenCaptureService : Service() {
    companion object {
        const val ACTION_START = "START"
        const val ACTION_STOP = "STOP"
        const val ACTION_RESULT = "com.livecomp.scanner.RESULT"
        const val EXTRA_RESULT_CODE = "result_code"
        const val EXTRA_DATA = "data"
        const val NOTIFICATION_ID = 101
    }

    private var mediaProjection: MediaProjection? = null
    private var virtualDisplay: VirtualDisplay? = null
    private var imageReader: ImageReader? = null
    private var scope: CoroutineScope? = null
    private var isRunning = false

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_START -> {
                val resultCode = intent.getIntExtra(EXTRA_RESULT_CODE, Activity.RESULT_CANCELED)
                val data = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                    intent.getParcelableExtra(EXTRA_DATA, Intent::class.java)
                } else {
                    @Suppress("DEPRECATION")
                    intent.getParcelableExtra(EXTRA_DATA)
                }
                if (resultCode == Activity.RESULT_OK && data != null) {
                    start(resultCode, data)
                } else {
                    stopSelf()
                }
            }
            ACTION_STOP -> stop()
            else -> stop()
        }
        return START_NOT_STICKY
    }

    private fun start(resultCode: Int, data: Intent) {
        if (isRunning) return
        isRunning = true

        val notification = buildNotification("Scanning for cards…")
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.UPSIDE_DOWN_CAKE) {
            startForeground(NOTIFICATION_ID, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PROJECTION)
        } else {
            startForeground(NOTIFICATION_ID, notification)
        }

        val mgr = getSystemService(Context.MEDIA_PROJECTION_SERVICE) as MediaProjectionManager
        mediaProjection = mgr.getMediaProjection(resultCode, data)

        setupCapture()
        startScanLoop()
    }

    private fun setupCapture() {
        val metrics = DisplayMetrics()
        val wm = getSystemService(Context.WINDOW_SERVICE) as WindowManager
        wm.defaultDisplay.getMetrics(metrics)

        val width = (metrics.widthPixels * 0.6).toInt().coerceAtLeast(720)
        val height = (metrics.heightPixels * 0.6).toInt().coerceAtLeast(1280)
        val density = metrics.densityDpi

        imageReader = ImageReader.newInstance(width, height, PixelFormat.RGBA_8888, 2)

        virtualDisplay = mediaProjection?.createVirtualDisplay(
            "LiveCompCapture",
            width, height, density,
            DisplayManager.VIRTUAL_DISPLAY_FLAG_AUTO_MIRROR,
            imageReader?.surface, null, null
        )
    }

    private fun startScanLoop() {
        scope = CoroutineScope(Dispatchers.IO + SupervisorJob())
        scope?.launch {
            var lastHash = 0L
            while (isActive && isRunning) {
                try {
                    val bitmap = acquireFrame() ?: run { delay(500); continue }

                    // Skip nearly identical frames to save backend calls.
                    val hash = bitmap.smallHash()
                    if (hash == lastHash) {
                        bitmap.recycle()
                        delay(300)
                        continue
                    }
                    lastHash = hash

                    try {
                        val response = BackendClient.identify(bitmap)
                        if (response.isSuccessful) {
                            response.body()?.let { result ->
                                broadcastResult(result)
                            }
                        }
                    } catch (e: Exception) {
                        Log.e("ScreenCaptureService", "Identify failed", e)
                    } finally {
                        bitmap.recycle()
                    }

                    delay(1500) // scan every ~1.5s to avoid hammering backend/PC RAM
                } catch (e: Exception) {
                    Log.e("ScreenCaptureService", "Loop error", e)
                    delay(1000)
                }
            }
        }
    }

    private fun acquireFrame(): Bitmap? {
        val reader = imageReader ?: return null
        val image = reader.acquireLatestImage() ?: return null
        try {
            val planes = image.planes
            if (planes.isEmpty()) return null
            val buffer = planes[0].buffer
            val pixelStride = planes[0].pixelStride
            val rowStride = planes[0].rowStride
            val width = image.width
            val height = image.height
            val offset = (rowStride - pixelStride * width) / pixelStride
            val bitmap = Bitmap.createBitmap(width + offset, height, Bitmap.Config.ARGB_8888)
            bitmap.copyPixelsFromBuffer(buffer)
            return Bitmap.createBitmap(bitmap, 0, 0, width, height)
        } catch (e: Exception) {
            Log.e("ScreenCaptureService", "Frame decode error", e)
            return null
        } finally {
            image.close()
        }
    }

    private fun broadcastResult(result: IdentifyResponse) {
        ScanResultBus.emit(result)
        val intent = Intent(ACTION_RESULT).apply {
            setPackage(packageName)
            putExtra("result", result)
        }
        sendBroadcast(intent)
    }

    private fun stop() {
        isRunning = false
        scope?.cancel()
        virtualDisplay?.release()
        imageReader?.close()
        mediaProjection?.stop()
        stopForeground(STOP_FOREGROUND_REMOVE)
        stopSelf()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                "lco_capture",
                "Card Screen Capture",
                NotificationManager.IMPORTANCE_LOW
            )
            val nm = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            nm.createNotificationChannel(channel)
        }
    }

    private fun buildNotification(text: String): Notification {
        val stopIntent = Intent(this, ScreenCaptureService::class.java).apply {
            action = ACTION_STOP
        }
        val stopPending = PendingIntent.getService(
            this, 0, stopIntent, PendingIntent.FLAG_IMMUTABLE
        )
        return NotificationCompat.Builder(this, "lco_capture")
            .setContentTitle("Live Comp Scanner")
            .setContentText(text)
            .setSmallIcon(android.R.drawable.ic_menu_search)
            .addAction(android.R.drawable.ic_menu_close_clear_cancel, "Stop", stopPending)
            .setOngoing(true)
            .build()
    }

    private fun Bitmap.smallHash(): Long {
        val scaled = Bitmap.createScaledBitmap(this, 8, 8, true)
        var hash = 0L
        for (y in 0 until 8) {
            for (x in 0 until 8) {
                hash = hash * 31 + scaled.getPixel(x, y)
            }
        }
        scaled.recycle()
        return hash
    }
}
