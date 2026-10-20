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
import kotlinx.coroutines.cancelAndJoin
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock

/**
 * Owns the recording-session lifecycle and is the boundary between sensor I/O,
 * fusion, persistence and UI-facing state.
 *
 * Only one session may be active at a time. The repository also owns the sensor
 * collection [Job], so stopping a session cancels hardware collection before the
 * session is closed in Room.
 */
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
    private val lifecycleMutex = Mutex()

    val liveMetrics: StateFlow<TraversalMetrics?> = _liveMetrics.asStateFlow()
    val activeSessionId: StateFlow<Long?> = _activeSessionId.asStateFlow()

    // Eager sharing keeps session history current for the application-scoped UI
    // even when no screen is temporarily collecting this StateFlow.
    val sessionSummaries: StateFlow<List<TraversalSession>> =
        database.sessionDao()
            .observeSessions()
            .map { sessions -> sessions.map { it.toDomain() } }
            .stateIn(scope, SharingStarted.Eagerly, emptyList())

    fun observeSession(sessionId: Long): Flow<TraversalSession?> =
        database.sessionDao()
            .observeSession(sessionId)
            .map { it?.toDomain() }

    /** Starts a recording if another session is not already active. */
    suspend fun startSession(patientId: String, notes: String?) = lifecycleMutex.withLock {
        // Treat repeated start taps as idempotent rather than creating overlapping
        // database sessions that would compete for the same sensor stream.
        if (_activeSessionId.value != null) return@withLock

        // Fusion state is session-scoped even though the engine instance is
        // application-scoped, so reset before accepting new samples.
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

    /** Stops sensor collection and closes the current persisted session. */
    suspend fun stopSession() = lifecycleMutex.withLock {
        val sessionId = _activeSessionId.value ?: return@withLock

        // Wait for in-flight persistence and hardware cleanup. Keep the ID until
        // closing succeeds, so a database failure can be retried.
        collectionJob?.cancelAndJoin()
        collectionJob = null
        withContext(ioDispatcher) {
            database.sessionDao().closeSession(sessionId, System.currentTimeMillis())
        }
        _activeSessionId.value = null
        _liveMetrics.value = null
    }

    private fun startCollecting(sessionId: Long) {
        // Defensive cancellation prevents a stale collection job from surviving a
        // future lifecycle change that calls this method more than once.
        collectionJob?.cancel()
        collectionJob = scope.launch {
            sensorCollector.sensorSamples().collect { sample ->
                val metrics = fusionEngine.process(sample)

                // Persist the raw sample and the metric snapshot together before
                // publishing it live, keeping stored and displayed state ordered.
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
        // Room writes are moved off the collector coroutine's default dispatcher
        // so database I/O does not run on a UI-bound context supplied by a caller.
        withContext(ioDispatcher) {
            database.sensorSampleDao().insert(sample.toEntity(sessionId, metrics))
        }
    }
}
