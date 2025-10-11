package com.clinic.ataxia.domain.model

data class TraversalSession(
    val id: Long,
    val patientId: String,
    val startedAt: Long,
    val endedAt: Long?,
    val notes: String?,
    val metrics: SessionMetricsSummary = SessionMetricsSummary()
)

data class SessionMetricsSummary(
    val totalDistanceMillimeters: Float = 0f,
    val averageOffsetMillimeters: Float = 0f,
    val peakTremorMagnitude: Float = 0f
)
