package com.livecomp.scanner

import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Multipart
import retrofit2.http.POST
import retrofit2.http.Part
import retrofit2.http.Query
import okhttp3.MultipartBody
import com.google.gson.annotations.SerializedName

import android.os.Parcelable
import kotlinx.parcelize.Parcelize

interface BackendApi {
    @GET("/health")
    suspend fun health(): Response<Map<String, String>>

    @GET("/admin/info")
    suspend fun info(): Response<BackendInfo>

    @Multipart
    @POST("/identify")
    suspend fun identify(
        @Part file: MultipartBody.Part,
        @Query("use_ocr") useOcr: Int = 1,
        @Query("k") k: Int = 8,
    ): Response<IdentifyResponse>
}

data class BackendInfo(
    val version: String,
    val lan_ip: String,
    val backend_url: String,
    val cards_in_db: Int,
    val faiss_index_ready: Boolean,
)

@Parcelize
data class IdentifyResponse(
    val best_match: Candidate,
    val candidates: List<Candidate>,
    val confidence: String,
    val verified_by: List<String>,
    val collector: String?,
    val ocr_name: String?,
    val prices_by_condition: Map<String, PriceByCondition>?,
) : Parcelable

@Parcelize
data class Candidate(
    val score: Double,
    val card: Card,
) : Parcelable

@Parcelize
data class Card(
    val id: String,
    val external_id: String,
    val name: String,
    val local_id: String?,
    val set_code: String?,
    val set_name: String?,
    val rarity: String?,
    val image_url: String?,
    val variant: String?,
) : Parcelable

@Parcelize
data class PriceByCondition(
    val price: Double?,
    val currency: String?,
    val estimated: Boolean,
) : Parcelable
