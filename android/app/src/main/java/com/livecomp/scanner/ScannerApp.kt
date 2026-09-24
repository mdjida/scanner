package com.livecomp.scanner

import android.app.Application
import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

private val Context.dataStore: DataStore<Preferences> by preferencesDataStore(name = "settings")

class ScannerApp : Application() {

    companion object {
        val BACKEND_URL = stringPreferencesKey("backend_url")
    }

    val backendUrl: Flow<String?>
        get() = dataStore.data.map { prefs -> prefs[BACKEND_URL] }

    suspend fun setBackendUrl(url: String) {
        dataStore.edit { prefs ->
            prefs[BACKEND_URL] = url
        }
    }
}
