package com.clinic.ataxia.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.clinic.ataxia.data.repository.SensorRepository
import com.clinic.ataxia.domain.model.TraversalMetrics
import com.clinic.ataxia.domain.model.TraversalSession
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

class MainViewModel(
    private val repository: SensorRepository
) : ViewModel() {

    private val patientId = MutableStateFlow("")
    private val notes = MutableStateFlow("")

    val uiState: StateFlow<MainUiState> = combine(
        patientId,
        notes,
        repository.liveMetrics,
        repository.sessionSummaries,
        repository.activeSessionId
    ) { patient, note, metrics, sessions, activeId ->
        MainUiState(
            patientId = patient,
            notes = note,
            isSessionActive = activeId != null,
            liveMetrics = metrics,
            sessions = sessions
        )
    }.stateIn(
        scope = viewModelScope,
        started = SharingStarted.Eagerly,
        initialValue = MainUiState()
    )

    fun updatePatientId(value: String) {
        patientId.value = value
    }

    fun updateNotes(value: String) {
        notes.value = value
    }

    fun startSession() {
        viewModelScope.launch {
            val id = patientId.value.ifBlank { defaultPatientId() }
            repository.startSession(id, notes.value.ifBlank { null })
        }
    }

    fun stopSession() {
        viewModelScope.launch {
            repository.stopSession()
        }
    }

    private fun defaultPatientId(): String =
        "patient-${System.currentTimeMillis()}"
}

data class MainUiState(
    val patientId: String = "",
    val notes: String = "",
    val isSessionActive: Boolean = false,
    val liveMetrics: TraversalMetrics? = null,
    val sessions: List<TraversalSession> = emptyList()
)
