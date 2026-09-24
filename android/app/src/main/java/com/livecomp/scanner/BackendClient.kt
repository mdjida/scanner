package com.livecomp.scanner

import android.graphics.Bitmap
import android.util.Log
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.OkHttpClient
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Response
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.io.ByteArrayOutputStream
import java.util.concurrent.TimeUnit

object BackendClient {
    private const val TAG = "BackendClient"
    private var retrofit: Retrofit? = null

    fun setBaseUrl(url: String) {
        Log.d(TAG, "Setting backend URL: $url")
        val cleanUrl = url.trim().removeSuffix("/") + "/"
        val logging = HttpLoggingInterceptor().apply {
            level = HttpLoggingInterceptor.Level.BASIC
        }
        val client = OkHttpClient.Builder()
            .addInterceptor(logging)
            .connectTimeout(30, TimeUnit.SECONDS)
            .readTimeout(120, TimeUnit.SECONDS)
            .writeTimeout(30, TimeUnit.SECONDS)
            .build()

        retrofit = Retrofit.Builder()
            .baseUrl(cleanUrl)
            .client(client)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
    }

    val api: BackendApi
        get() = retrofit?.create(BackendApi::class.java)
            ?: throw IllegalStateException("Backend URL not set. Call setBaseUrl first.")

    fun bitmapToPng(bitmap: Bitmap): ByteArray {
        val stream = ByteArrayOutputStream()
        bitmap.compress(Bitmap.CompressFormat.PNG, 100, stream)
        return stream.toByteArray()
    }

    suspend fun identify(bitmap: Bitmap): Response<IdentifyResponse> {
        val bytes = bitmapToPng(bitmap)
        val body = bytes.toRequestBody("image/png".toMediaTypeOrNull())
        val part = MultipartBody.Part.createFormData("file", "card.png", body)
        return api.identify(part)
    }
}
