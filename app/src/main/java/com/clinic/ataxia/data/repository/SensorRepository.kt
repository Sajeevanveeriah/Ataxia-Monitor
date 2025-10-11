package com.clinic.ataxia.data.repository

import com.clinic.ataxia.data.local.AtaxiaDatabase
import com.clinic.ataxia.data.mapper.toDomain
import com.clinic.ataxia.data.mapper.toEntity
import com.clinic.ataxia.data.sensor.SensorCollector
import com.clinic.ataxia.data.sensor.SensorFusionEngine
import com.clinic.ataxia.domain.model.SensorSample
import com.clinic.ataxia.domain.model.TraversalMetrics
import com.clinic.ataxia.domain.model.TraversalSession
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class SensorRepository(
    private val database: AtaxiaDatabase,
    private val sensorCollector: SensorCollector,
    private val fusionEngine: SensorFusionEngine,
    private val scope: CoroutineScope,
    private val ioDispatcher: CoroutineDispatcher = Dispatchers.IO
) {

    private val _activeSessionId = MutableStateFlow<Long?>(null)
    private val _liveMetrics = MutableStateFlow<TraversalMetrics?>(null)
    private var collectionJob: Job? = null

    val liveMetrics: StateFlow<TraversalMetrics?> = _liveMetrics.asStateFlow()
    val activeSessionId: StateFlow<Long?> = _activeSessionId.asStateFlow()

    val sessionSummaries: StateFlow<List<TraversalSession>> =
        database.sessionDao()
            .observeSessions()
            .map { sessions -> sessions.map { it.toDomain() } }
            .stateIn(scope, SharingStarted.Eagerly, emptyList())

    fun observeSession(sessionId: Long): Flow<TraversalSession?> =
        database.sessionDao()
            .observeSession(sessionId)
            .map { it?.toDomain() }

    suspend fun startSession(patientId: String, notes: String?) {
        if (_activeSessionId.value != null) return

        fusionEngine.reset()
        _liveMetrics.value = null
        val sessionId = withContext(ioDispatcher) {
            database.sessionDao().insert(
                com.clinic.ataxia.data.local.SessionEntity(
                    patientId = patientId,
                    startedAt = System.currentTimeMillis(),
                    notes = notes
                )
            )
        }
        _activeSessionId.value = sessionId
        startCollecting(sessionId)
    }

    suspend fun stopSession() {
        val sessionId = _activeSessionId.value ?: return
        _activeSessionId.value = null
        collectionJob?.cancel()
        collectionJob = null
        withContext(ioDispatcher) {
            database.sessionDao().closeSession(sessionId, System.currentTimeMillis())
        }
        _liveMetrics.value = null
    }

    private fun startCollecting(sessionId: Long) {
        collectionJob?.cancel()
        collectionJob = scope.launch {
            sensorCollector.sensorSamples().collect { sample ->
                val metrics = fusionEngine.process(sample)
                persistSample(sample, metrics, sessionId)
                _liveMetrics.value = metrics
            }
        }
    }

    private suspend fun persistSample(
        sample: SensorSample,
        metrics: TraversalMetrics,
        sessionId: Long
    ) {
        withContext(ioDispatcher) {
            database.sensorSampleDao().insert(sample.toEntity(sessionId, metrics))
        }
    }
}
