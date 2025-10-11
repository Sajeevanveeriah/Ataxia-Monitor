package com.clinic.ataxia.domain.model

data class TraversalMetrics(
    val timestamp: Long,
    val distanceMillimeters: Float,
    val radialOffsetMillimeters: Float,
    val angularVelocity: Float,
    val tremorMagnitude: Float
)
