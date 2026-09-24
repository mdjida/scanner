package com.livecomp.scanner

import android.util.Log
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
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
}
