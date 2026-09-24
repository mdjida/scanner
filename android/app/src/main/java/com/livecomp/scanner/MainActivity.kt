package com.livecomp.scanner

import android.Manifest
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.os.Bundle
import android.util.Log
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import coil.compose.AsyncImage
import com.google.zxing.integration.android.IntentIntegrator
import com.livecomp.scanner.ui.theme.LiveCompTheme
import kotlinx.coroutines.launch
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.ByteArrayOutputStream

class MainActivity : ComponentActivity() {
    private val tag = "MainActivity"

    private val requestPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { isGranted ->
        if (!isGranted) {
            Toast.makeText(this, "Camera permission is required", Toast.LENGTH_LONG).show()
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA)
            != PackageManager.PERMISSION_GRANTED
        ) {
            requestPermissionLauncher.launch(Manifest.permission.CAMERA)
        }

        val app = application as ScannerApp
        setContent {
            LiveCompTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    ScannerScreen(
                        app = app,
                        onScanQr = { startQrScan() }
                    )
                }
            }
        }
    }

    private fun startQrScan() {
        IntentIntegrator(this)
            .setPrompt("Scan the QR code shown on your PC")
            .setBeepEnabled(false)
            .initiateScan()
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ScannerScreen(app: ScannerApp, onScanQr: () -> Unit) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()

    var backendUrl by remember { mutableStateOf("http://192.168.1.100:8000") }
    var status by remember { mutableStateOf("Checking…") }
    var isScanning by remember { mutableStateOf(false) }
    var result by remember { mutableStateOf<IdentifyResponse?>(null) }
    var showSettings by remember { mutableStateOf(false) }

    val capturedBitmap = remember { mutableStateOf<Bitmap?>(null) }

    LaunchedEffect(Unit) {
        app.backendUrl.collect { saved ->
            saved?.let {
                backendUrl = it
                BackendClient.setBaseUrl(it)
                checkStatus { msg -> status = msg }
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
                .verticalScroll(rememberScrollState())
        ) {
            CameraPreview(
                modifier = Modifier
                    .fillMaxWidth()
                    .aspectRatio(3f / 4f)
                    .padding(12.dp)
                    .clip(RoundedCornerShape(16.dp)),
                onImage = { bitmap ->
                    capturedBitmap.value = bitmap
                }
            )

            Text(
                text = status,
                modifier = Modifier
                    .align(Alignment.CenterHorizontally)
                    .padding(8.dp),
                style = MaterialTheme.typography.bodyMedium
            )

            Button(
                onClick = {
                    val bmp = capturedBitmap.value
                    if (bmp == null) {
                        status = "No camera frame yet"
                        return@Button
                    }
                    isScanning = true
                    scope.launch {
                        status = "Scanning…"
                        try {
                            BackendClient.setBaseUrl(backendUrl)
                            val bytes = bitmapToPng(bmp)
                            val body = bytes.toRequestBody("image/png".toMediaTypeOrNull())
                            val part = MultipartBody.Part.createFormData(
                                "file", "card.png", body
                            )
                            val response = BackendClient.api.identify(part)
                            if (response.isSuccessful) {
                                result = response.body()
                                status = "Resolved: ${result?.best_match?.card?.name ?: "?"}"
                            } else {
                                status = "Backend error: ${response.code()}"
                            }
                        } catch (e: Exception) {
                            Log.e("ScannerScreen", "Scan failed", e)
                            status = "Failed: ${e.message ?: "unknown"}"
                        } finally {
                            isScanning = false
                        }
                    }
                },
                enabled = !isScanning,
                modifier = Modifier
                    .align(Alignment.CenterHorizontally)
                    .padding(8.dp)
            ) {
                Text(if (isScanning) "Scanning…" else "Scan Card")
            }

            result?.let { data ->
                ResultCard(data)
            }
        }
    }

    if (showSettings) {
        SettingsDialog(
            currentUrl = backendUrl,
            onSave = { newUrl ->
                backendUrl = newUrl
                scope.launch {
                    app.setBackendUrl(newUrl)
                    BackendClient.setBaseUrl(newUrl)
                    checkStatus { msg -> status = msg }
                }
            },
            onScanQr = onScanQr,
            onDismiss = { showSettings = false }
        )
    }
}

@Composable
fun ResultCard(data: IdentifyResponse) {
    val card = data.best_match.card
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(12.dp),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row {
                card.image_url?.let { url ->
                    AsyncImage(
                        model = url,
                        contentDescription = card.name,
                        modifier = Modifier
                            .size(100.dp)
                            .clip(RoundedCornerShape(8.dp))
                    )
                }
                Spacer(modifier = Modifier.width(12.dp))
                Column {
                    Text(card.name, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                    Text("${card.set_name ?: ""} ${card.local_id ?: ""}", style = MaterialTheme.typography.bodyMedium)
                    Text("Variant: ${card.variant ?: "Normal"}", style = MaterialTheme.typography.bodySmall)
                    Text("Confidence: ${data.confidence}", style = MaterialTheme.typography.bodySmall)
                    Text("Verified: ${data.verified_by.joinToString()}", style = MaterialTheme.typography.bodySmall)
                }
            }

            Spacer(modifier = Modifier.height(12.dp))

            data.prices_by_condition?.let { prices ->
                val order = listOf("nm", "lp", "mp", "hp", "dmg")
                val labels = mapOf("nm" to "NM", "lp" to "LP", "mp" to "MP", "hp" to "HP", "dmg" to "DMG")
                Column {
                    order.forEach { cond ->
                        val p = prices[cond]
                        if (p?.price != null) {
                            val symbol = if (p.currency == "EUR") "€" else "$"
                            val est = if (p.estimated) " *" else ""
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween
                            ) {
                                Text("${labels[cond]}$est", fontWeight = FontWeight.Bold)
                                Text("$symbol${"%.2f".format(p.price)}")
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun SettingsDialog(
    currentUrl: String,
    onSave: (String) -> Unit,
    onScanQr: () -> Unit,
    onDismiss: () -> Unit,
) {
    var url by remember { mutableStateOf(currentUrl) }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Backend URL") },
        text = {
            Column {
                OutlinedTextField(
                    value = url,
                    onValueChange = { url = it },
                    label = { Text("http://192.168.x.x:8000") },
                    singleLine = true
                )
                Spacer(modifier = Modifier.height(8.dp))
                OutlinedButton(onClick = onScanQr) {
                    Text("Scan QR from PC")
                }
            }
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

fun bitmapToPng(bitmap: Bitmap): ByteArray {
    val stream = ByteArrayOutputStream()
    bitmap.compress(Bitmap.CompressFormat.PNG, 100, stream)
    return stream.toByteArray()
}

suspend fun checkStatus(onStatus: (String) -> Unit) {
    try {
        val res = BackendClient.api.health()
        if (res.isSuccessful) {
            onStatus("Connected")
        } else {
            onStatus("HTTP ${res.code()}")
        }
    } catch (e: Exception) {
        onStatus("Unreachable: ${e.message}")
    }
}
