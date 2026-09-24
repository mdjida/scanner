package com.livecomp.scanner

import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

object ScanResultBus {
    private val _result = MutableStateFlow<IdentifyResponse?>(null)
    val result: StateFlow<IdentifyResponse?> = _result.asStateFlow()

    fun emit(result: IdentifyResponse) {
        _result.value = result
    }
}
