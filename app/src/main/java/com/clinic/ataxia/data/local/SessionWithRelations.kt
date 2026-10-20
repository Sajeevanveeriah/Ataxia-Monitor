package com.clinic.ataxia.data.local

import androidx.room.Embedded
import androidx.room.Ignore
import androidx.room.Relation

data class SessionWithSummary(
    @Embedded val session: SessionEntity,
    @Relation(
        parentColumn = "id",
        entityColumn = "session_id"
    )
    val samples: List<SensorSampleEntity>
) {
    // Each row stores a cumulative snapshot. Room does not order relation rows.
    @Ignore val totalDistance = samples.maxByOrNull { it.timestamp }?.distanceMillimeters ?: 0f
    @Ignore val averageOffset = if (samples.isEmpty()) 0f else samples.map { it.offsetMillimeters }.average().toFloat()
    @Ignore val peakTremor = samples.maxOfOrNull { it.tremorMagnitude } ?: 0f
}

data class SessionWithReadings(
    @Embedded val session: SessionEntity,
    @Relation(
        parentColumn = "id",
        entityColumn = "session_id"
    )
    val samples: List<SensorSampleEntity>
)
