package com.clinic.ataxia.data.local

import androidx.room.Embedded
import androidx.room.Relation

data class SessionWithSummary(
    @Embedded val session: SessionEntity,
    @Relation(
        parentColumn = "id",
        entityColumn = "session_id"
    )
    val samples: List<SensorSampleEntity>
) {
    val totalDistance = samples.sumOf { it.distanceMillimeters.toDouble() }.toFloat()
    val averageOffset = if (samples.isEmpty()) 0f else samples.map { it.offsetMillimeters }.average().toFloat()
    val peakTremor = samples.maxOfOrNull { it.tremorMagnitude } ?: 0f
}

data class SessionWithReadings(
    @Embedded val session: SessionEntity,
    @Relation(
        parentColumn = "id",
        entityColumn = "session_id"
    )
    val samples: List<SensorSampleEntity>
)
