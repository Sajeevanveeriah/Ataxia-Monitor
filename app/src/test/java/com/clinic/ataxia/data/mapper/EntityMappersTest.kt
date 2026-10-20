package com.clinic.ataxia.data.mapper

import com.clinic.ataxia.data.local.SensorSampleEntity
import com.clinic.ataxia.data.local.SessionEntity
import com.clinic.ataxia.data.local.SessionWithReadings
import com.clinic.ataxia.data.local.SessionWithSummary
import com.clinic.ataxia.domain.model.SensorSample
import com.clinic.ataxia.domain.model.SensorType
import com.clinic.ataxia.domain.model.TraversalMetrics
import org.junit.Assert.*
import org.junit.Test

class EntityMappersTest {
    private val session = SessionEntity(id = 7, patientId = "fixture", startedAt = 100, notes = "test")

    private fun reading(time: Long, distance: Float, offset: Float = 2f, tremor: Float = 1f) =
        SensorSampleEntity(sessionId = 7, timestamp = time, sensorType = "GYROSCOPE",
            valuesJson = "[1.0,2.0,3.0]", distanceMillimeters = distance,
            offsetMillimeters = offset, angularVelocity = 3f, tremorMagnitude = tremor)

    @Test
    fun cumulativeDistanceIsNotSummedForEverySensorEvent() {
        val samples = listOf(reading(1, 10f), reading(2, 10f), reading(3, 15f))
        assertEquals(15f, SessionWithSummary(session, samples).toDomain().metrics.totalDistanceMillimeters, 0f)
        assertEquals(15f, SessionWithReadings(session, samples).toDomain().metrics.totalDistanceMillimeters, 0f)
    }

    @Test
    fun latestTimestampWinsAfterDistanceResetEvenWhenRoomRowsAreUnsorted() {
        val samples = listOf(reading(3, 3f), reading(1, 10f), reading(2, 15f))
        assertEquals(3f, SessionWithSummary(session, samples).toDomain().metrics.totalDistanceMillimeters, 0f)
        assertEquals(3f, SessionWithReadings(session, samples).toDomain().metrics.totalDistanceMillimeters, 0f)
    }

    @Test
    fun emptySessionHasZeroMetricsAndRetainsMetadata() {
        val mapped = SessionWithReadings(session, emptyList()).toDomain()
        assertEquals(0f, mapped.metrics.totalDistanceMillimeters, 0f)
        assertEquals(0f, mapped.metrics.averageOffsetMillimeters, 0f)
        assertEquals(0f, mapped.metrics.peakTremorMagnitude, 0f)
        assertEquals(7L, mapped.id)
        assertEquals("fixture", mapped.patientId)
        assertEquals("test", mapped.notes)
        assertNull(mapped.endedAt)
    }

    @Test
    fun summaryAndDetailAgreeOnOffsetAndPeakTremor() {
        val samples = listOf(reading(1, 10f, 2f, 4f), reading(2, 15f, 6f, 1f))
        val summary = SessionWithSummary(session, samples).toDomain()
        assertEquals(summary, SessionWithReadings(session, samples).toDomain())
        assertEquals(4f, summary.metrics.averageOffsetMillimeters, 0f)
        assertEquals(4f, summary.metrics.peakTremorMagnitude, 0f)
    }

    @Test
    fun sampleEntityPreservesSessionRawValuesAndMetrics() {
        val sample = SensorSample(123, SensorType.GYROSCOPE, floatArrayOf(1f, -2f, 3f))
        val metrics = TraversalMetrics(123, 10f, 2f, 3f, 4f)
        val entity = sample.toEntity(7, metrics)
        assertEquals(7L, entity.sessionId)
        assertEquals(123L, entity.timestamp)
        assertEquals("GYROSCOPE", entity.sensorType)
        assertEquals("[1.0,-2.0,3.0]", entity.valuesJson)
        assertEquals(metrics, entity.toDomainSample())
    }

    @Test
    fun unknownPersistedSensorTypeFallsBackWithoutThrowing() {
        assertEquals(SensorType.UNKNOWN, "future-sensor".toSensorType())
        assertEquals(SensorType.GYROSCOPE, "GYROSCOPE".toSensorType())
    }
}
