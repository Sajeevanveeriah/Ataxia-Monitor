package com.clinic.ataxia.data.repository

import com.clinic.ataxia.data.local.*
import com.clinic.ataxia.data.sensor.SensorCollector
import com.clinic.ataxia.data.sensor.SensorFusionEngine
import com.clinic.ataxia.domain.model.SensorSample
import com.clinic.ataxia.domain.model.SensorType
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.test.*
import org.junit.Assert.*
import org.junit.Test
import org.mockito.Mockito.*

@OptIn(ExperimentalCoroutinesApi::class)
class SensorRepositoryTest {
    private class Sessions(private val events: MutableList<String>) : SessionDao {
        val inserted = mutableListOf<SessionEntity>()
        val closed = mutableListOf<Long>()
        var failClose = false
        override suspend fun insert(session: SessionEntity): Long {
            yield() // Real database I/O suspends; keep the race reproducible.
            inserted += session
            return inserted.size.toLong()
        }
        override suspend fun closeSession(sessionId: Long, endedAt: Long) {
            if (failClose) error("fixture database failure")
            events += "closed"
            closed += sessionId
        }
        override fun observeSessions(): Flow<List<SessionWithSummary>> = flowOf(emptyList())
        override fun observeSession(sessionId: Long): Flow<SessionWithReadings?> = flowOf(null)
    }

    private fun TestScope.repository(sessions: Sessions, samples: Flow<SensorSample> = emptyFlow()): SensorRepository {
        val database = mock(AtaxiaDatabase::class.java)
        val collector = mock(SensorCollector::class.java)
        `when`(database.sessionDao()).thenReturn(sessions)
        `when`(database.sensorSampleDao()).thenReturn(mock(SensorSampleDao::class.java))
        `when`(collector.sensorSamples()).thenReturn(samples)
        return SensorRepository(database, collector, SensorFusionEngine(), backgroundScope,
            StandardTestDispatcher(testScheduler))
    }

    @Test
    fun concurrentStartsCreateOnlyOneSession() = runTest {
        val sessions = Sessions(mutableListOf())
        val repository = repository(sessions)
        launch { repository.startSession("first", null) }
        launch { repository.startSession("second", null) }
        advanceUntilIdle()
        assertEquals(1, sessions.inserted.size)
        assertEquals(1L, repository.activeSessionId.value)
    }

    @Test
    fun stopWaitsForSensorCleanupBeforeClosingTheSession() = runTest {
        val events = mutableListOf<String>()
        val sessions = Sessions(events)
        val stream = flow<SensorSample> {
            events += "collecting"
            try { awaitCancellation() }
            finally {
                withContext(NonCancellable) { delay(10); events += "released" }
            }
        }
        val repository = repository(sessions, stream)
        repository.startSession("fixture", null)
        runCurrent()
        launch { repository.stopSession() }
        advanceTimeBy(20)
        runCurrent()
        assertEquals(listOf("collecting", "released", "closed"), events)
        assertNull(repository.activeSessionId.value)
    }

    @Test
    fun failedCloseCanBeRetriedWithoutOrphaningTheSession() = runTest {
        val sessions = Sessions(mutableListOf())
        val repository = repository(sessions)
        repository.startSession("fixture", null)
        sessions.failClose = true
        try { repository.stopSession(); fail("Expected database failure") }
        catch (_: IllegalStateException) { }
        assertEquals(1L, repository.activeSessionId.value)
        sessions.failClose = false
        repository.stopSession()
        assertEquals(listOf(1L), sessions.closed)
        assertNull(repository.activeSessionId.value)
    }

    @Test
    fun repeatedStopsAreIdempotentAndClearLiveMetrics() = runTest {
        val sessions = Sessions(mutableListOf())
        val stream = flowOf(SensorSample(1, SensorType.TIME_OF_FLIGHT, floatArrayOf(12f, 2f)))
        val repository = repository(sessions, stream)
        repository.stopSession()
        repository.startSession("fixture", null)
        runCurrent()
        assertEquals(12f, repository.liveMetrics.value!!.distanceMillimeters, 0f)
        repository.stopSession()
        repository.stopSession()
        assertEquals(listOf(1L), sessions.closed)
        assertNull(repository.liveMetrics.value)
    }
}
