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

/**
 * Presentation-state adapter between [SensorRepository] and the Compose screen.
 *
 * Repository implementation details stay out of the UI: an active session ID is
 * reduced to a Boolean, live metrics remain nullable until data arrives and the two
 * editable participant fields are combined with repository streams into one state.
 */
class MainViewModel(
    private val repository: SensorRepository
) : ViewModel() {

    private val patientId = MutableStateFlow("")
    private val notes = MutableStateFlow("")

    /** Single observable state consumed by the screen. */
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
        // Eager collection keeps repository state reflected immediately when the
        // ViewModel is alive, avoiding a second screen-specific lifecycle contract.
        started = SharingStarted.Eagerly,
        initialValue = MainUiState()
    )

    fun updatePatientId(value: String) {
        patientId.value = value
    }

    fun updateNotes(value: String) {
        notes.value = value
    }

    /** Starts a repository session from the current form state. */
    fun startSession() {
        viewModelScope.launch {
            // The generated identifier is only a prototype fallback. It prevents an
            // empty database key but is not a substitute for a real participant-ID policy.
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

/** Immutable screen model derived from form input and repository state. */
data class MainUiState(
    val patientId: String = "",
    val notes: String = "",
    val isSessionActive: Boolean = false,
    val liveMetrics: TraversalMetrics? = null,
    val sessions: List<TraversalSession> = emptyList()
)
