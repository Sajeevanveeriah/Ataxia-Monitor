package com.clinic.ataxia.data.mapper

import com.clinic.ataxia.data.local.SensorSampleEntity
import com.clinic.ataxia.data.local.SessionEntity
import com.clinic.ataxia.data.local.SessionWithReadings
import com.clinic.ataxia.data.local.SessionWithSummary
import com.clinic.ataxia.domain.model.SensorSample
import com.clinic.ataxia.domain.model.SensorType
import com.clinic.ataxia.domain.model.SessionMetricsSummary
import com.clinic.ataxia.domain.model.TraversalMetrics
import com.clinic.ataxia.domain.model.TraversalSession
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json

private val json = Json { encodeDefaults = true }

fun SensorSampleEntity.toDomainSample(): TraversalMetrics =
    TraversalMetrics(
        timestamp = timestamp,
        distanceMillimeters = distanceMillimeters,
        radialOffsetMillimeters = offsetMillimeters,
        angularVelocity = angularVelocity,
        tremorMagnitude = tremorMagnitude
    )

fun SessionWithSummary.toDomain(): TraversalSession =
    TraversalSession(
        id = session.id,
        patientId = session.patientId,
        startedAt = session.startedAt,
        endedAt = session.endedAt,
        notes = session.notes,
        metrics = SessionMetricsSummary(
            totalDistanceMillimeters = totalDistance,
            averageOffsetMillimeters = averageOffset,
            peakTremorMagnitude = peakTremor
        )
    )

fun SessionWithReadings.toDomain(): TraversalSession =
    TraversalSession(
        id = session.id,
        patientId = session.patientId,
        startedAt = session.startedAt,
        endedAt = session.endedAt,
        notes = session.notes,
        metrics = SessionMetricsSummary(
            totalDistanceMillimeters = samples.sumOf { it.distanceMillimeters.toDouble() }.toFloat(),
            averageOffsetMillimeters = if (samples.isEmpty()) 0f else samples.map { it.offsetMillimeters }.average().toFloat(),
            peakTremorMagnitude = samples.maxOfOrNull { it.tremorMagnitude } ?: 0f
        )
    )

fun SensorSample.toEntity(
    sessionId: Long,
    metrics: TraversalMetrics
): SensorSampleEntity = SensorSampleEntity(
    sessionId = sessionId,
    timestamp = timestamp,
    sensorType = sensorType.name,
    valuesJson = json.encodeToString(values.toList()),
    distanceMillimeters = metrics.distanceMillimeters,
    offsetMillimeters = metrics.radialOffsetMillimeters,
    angularVelocity = metrics.angularVelocity,
    tremorMagnitude = metrics.tremorMagnitude
)

fun String.toSensorType(): SensorType =
    runCatching { SensorType.valueOf(this) }.getOrElse { SensorType.UNKNOWN }
