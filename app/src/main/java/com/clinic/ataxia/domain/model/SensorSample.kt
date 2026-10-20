package com.clinic.ataxia.domain.model

data class SensorSample(
    val timestamp: Long,
    val sensorType: SensorType,
    val values: FloatArray
)

enum class SensorType {
    TIME_OF_FLIGHT,
    GYROSCOPE,
    ACCELEROMETER,
    ROTATION_VECTOR,
    PROXIMITY,
    UNKNOWN
}
