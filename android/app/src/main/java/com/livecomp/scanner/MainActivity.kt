package com.livecomp.scanner

import android.annotation.SuppressLint
import android.app.Activity
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.graphics.PixelFormat
import android.media.projection.MediaProjectionManager
import android.os.Build
import android.os.Bundle
import android.net.Uri
import android.provider.Settings
import android.view.Gravity
import android.view.MotionEvent
import android.view.WindowManager
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.ComposeView
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.lifecycleScope
import com.livecomp.scanner.ui.theme.LiveCompTheme
import kotlinx.coroutines.launch

class MainActivity : ComponentActivity() {
    private val overlayPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) { _ ->
        // Result doesn't matter; user either granted or denied in settings.
    }

    private val projectionLauncher = registerForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) { result ->
        if (result.resultCode == Activity.RESULT_OK && result.data != null) {
            val intent = Intent(this, ScreenCaptureService::class.java).apply {
                action = ScreenCaptureService.ACTION_START
                putExtra(ScreenCaptureService.EXTRA_RESULT_CODE, result.resultCode)
                putExtra(ScreenCaptureService.EXTRA_DATA, result.data)
            }
            startForegroundService(intent)
            Toast.makeText(this, "Capture started", Toast.LENGTH_SHORT).show()
        } else {
            Toast.makeText(this, "Screen capture permission denied", Toast.LENGTH_LONG).show()
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val app = application as ScannerApp
        setContent {
            LiveCompTheme {
                Surface(modifier = Modifier.fillMaxSize()) {
                    ControlScreen(
                        app = app,
                        onStartCapture = { startCapture() },
                        onStopCapture = { stopService(Intent(this, ScreenCaptureService::class.java)) }
                    )
                }
            }
        }

        registerResultReceiver()
    }

    private fun startCapture() {
        if (!Settings.canDrawOverlays(this)) {
            val intent = Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION, Uri.parse("package:$packageName"))
            overlayPermissionLauncher.launch(intent)
            return
        }
        val mgr = getSystemService(Context.MEDIA_PROJECTION_SERVICE) as MediaProjectionManager
        projectionLauncher.launch(mgr.createScreenCaptureIntent())
    }

    private fun registerResultReceiver() {
        val receiver = object : BroadcastReceiver() {
            override fun onReceive(context: Context?, intent: Intent?) {
                val result = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                    intent?.getParcelableExtra("result", IdentifyResponse::class.java)
                } else {
                    @Suppress("DEPRECATION")
                    intent?.getParcelableExtra("result")
                }
                result?.let { showOverlay(it) }
            }
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            registerReceiver(receiver, IntentFilter(ScreenCaptureService.ACTION_RESULT), Context.RECEIVER_NOT_EXPORTED)
        } else {
            @Suppress("UnspecifiedRegisterReceiverFlag")
            registerReceiver(receiver, IntentFilter(ScreenCaptureService.ACTION_RESULT))
        }
    }

    @SuppressLint("ClickableViewAccessibility")
    private fun showOverlay(result: IdentifyResponse) {
        val wm = getSystemService(Context.WINDOW_SERVICE) as WindowManager
        val card = result.best_match.card
        val prices = result.prices_by_condition ?: emptyMap()

        val view = ComposeView(this).apply {
            setContent {
                LiveCompTheme {
                    Surface(
                        color = MaterialTheme.colorScheme.surfaceVariant,
                        tonalElevation = 6.dp,
                        shape = MaterialTheme.shapes.large,
                        modifier = Modifier.padding(8.dp)
                    ) {
                        Column(modifier = Modifier.padding(16.dp)) {
                            Text(card.name, fontWeight = FontWeight.Bold, style = MaterialTheme.typography.titleMedium)
                            Text("${card.set_name ?: ""} ${card.local_id ?: ""}", style = MaterialTheme.typography.bodySmall)
                            Text("Confidence: ${result.confidence}", style = MaterialTheme.typography.bodySmall)
                            Spacer(modifier = Modifier.height(8.dp))
                            listOf("nm" to "NM", "lp" to "LP", "mp" to "MP", "hp" to "HP", "dmg" to "DMG")
                                .forEach { (key, label) ->
                                    val p = prices[key]
                                    if (p?.price != null) {
                                        val sym = if (p.currency == "EUR") "€" else "$"
                                        val est = if (p.estimated) " *" else ""
                                        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                                            Text("$label$est")
                                            Text("$sym${"%.2f".format(p.price)}", fontWeight = FontWeight.Bold)
                                        }
                                    }
                                }
                        }
                    }
                }
            }
        }

        val params = WindowManager.LayoutParams(
            WindowManager.LayoutParams.WRAP_CONTENT,
            WindowManager.LayoutParams.WRAP_CONTENT,
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY else WindowManager.LayoutParams.TYPE_PHONE,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL,
            PixelFormat.TRANSLUCENT
        ).apply {
            gravity = Gravity.TOP or Gravity.CENTER_HORIZONTAL
            y = 80
        }

        var startX = 0f
        var startY = 0f
        var initialX = 0
        var initialY = 0
        view.setOnTouchListener { _, event ->
            when (event.actionMasked) {
                MotionEvent.ACTION_DOWN -> {
                    startX = event.rawX
                    startY = event.rawY
                    initialX = params.x
                    initialY = params.y
                }
                MotionEvent.ACTION_MOVE -> {
                    params.x = initialX + (event.rawX - startX).toInt()
                    params.y = initialY + (event.rawY - startY).toInt()
                    wm.updateViewLayout(view, params)
                }
            }
            true
        }

        try {
            wm.addView(view, params)
        } catch (e: Exception) {
            // Already showing; ignore.
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ControlScreen(
    app: ScannerApp,
    onStartCapture: () -> Unit,
    onStopCapture: () -> Unit,
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var backendUrl by remember { mutableStateOf("http://localhost:8000") }
    var status by remember { mutableStateOf("Idle") }
    var showSettings by remember { mutableStateOf(false) }

    LaunchedEffect(Unit) {
        app.backendUrl.collect { saved ->
            saved?.let {
                backendUrl = it
                try {
                    BackendClient.setBaseUrl(it)
                } catch (_: Exception) {}
            }
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Live Comp Scanner") },
                actions = {
                    IconButton(onClick = { showSettings = true }) {
                        Icon(Icons.Default.Settings, contentDescription = "Settings")
                    }
                }
            )
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .padding(padding)
                .fillMaxSize()
                .padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            Text(
                text = "Detect Pokémon cards while watching Whatnot, Twitch, or YouTube on your phone.",
                style = MaterialTheme.typography.bodyLarge
            )

            Text(text = status, color = MaterialTheme.colorScheme.primary)

            Button(
                onClick = {
                    scope.launch {
                        try {
                            BackendClient.setBaseUrl(backendUrl)
                            val res = BackendClient.api.health()
                            status = if (res.isSuccessful) "Connected" else "HTTP ${res.code()}"
                        } catch (e: Exception) {
                            status = "Unreachable: ${e.message}"
                        }
                    }
                },
                modifier = Modifier.fillMaxWidth()
            ) {
                Text("Test Backend")
            }

            Button(
                onClick = onStartCapture,
                modifier = Modifier.fillMaxWidth()
            ) {
                Text("Start Screen Capture")
            }

            OutlinedButton(
                onClick = onStopCapture,
                modifier = Modifier.fillMaxWidth()
            ) {
                Text("Stop Capture")
            }
        }
    }

    if (showSettings) {
        SettingsDialog(
            currentUrl = backendUrl,
            onSave = { newUrl ->
                backendUrl = newUrl
                scope.launch { app.setBackendUrl(newUrl) }
            },
            onDismiss = { showSettings = false }
        )
    }
}

@Composable
fun SettingsDialog(
    currentUrl: String,
    onSave: (String) -> Unit,
    onDismiss: () -> Unit,
) {
    var url by remember { mutableStateOf(currentUrl) }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Backend URL") },
        text = {
                OutlinedTextField(
                    value = url,
                    onValueChange = { url = it },
                    label = { Text("http://localhost:8000  (USB) or http://192.168.x.x:8000 (Wi-Fi)") },
                    singleLine = true
                )
        },
        confirmButton = {
            TextButton(onClick = { onSave(url); onDismiss() }) {
                Text("Save")
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text("Cancel")
            }
        }
    )
}
