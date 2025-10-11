package com.clinic.ataxia.data.sensor

import android.hardware.SensorManager
import com.clinic.ataxia.domain.model.SensorSample
import com.clinic.ataxia.domain.model.SensorType
import com.clinic.ataxia.domain.model.TraversalMetrics
import kotlin.math.abs
import kotlin.math.pow
import kotlin.math.sqrt

class SensorFusionEngine {

    private var lastDistanceMm: Float? = null
    private var totalDistanceMm: Float = 0f
    private var currentOffsetMm: Float = 0f
    private var currentAngularVelocity: Float = 0f
    private var tremorMagnitude: Float = 0f

    fun reset() {
        lastDistanceMm = null
        totalDistanceMm = 0f
        currentOffsetMm = 0f
        currentAngularVelocity = 0f
        tremorMagnitude = 0f
    }

    fun process(sample: SensorSample): TraversalMetrics {
        when (sample.sensorType) {
            SensorType.TIME_OF_FLIGHT -> handleTimeOfFlight(sample)
            SensorType.GYROSCOPE -> handleGyroscope(sample)
            SensorType.ACCELEROMETER -> handleAccelerometer(sample)
            else -> Unit
        }

        return TraversalMetrics(
            timestamp = sample.timestamp,
            distanceMillimeters = totalDistanceMm,
            radialOffsetMillimeters = currentOffsetMm,
            angularVelocity = currentAngularVelocity,
            tremorMagnitude = tremorMagnitude
        )
    }

    private fun handleTimeOfFlight(sample: SensorSample) {
        val distanceMeasurement = sample.values.getOrNull(0)
        val offsetMeasurement = sample.values.getOrNull(1)

        if (distanceMeasurement != null) {
            val last = lastDistanceMm
            if (last == null) {
                totalDistanceMm = distanceMeasurement
            } else {
                val delta = distanceMeasurement - last
                if (delta >= 0f) {
                    totalDistanceMm += delta
                } else {
                    // Sensor drift or reset. Treat as new lap.
                    totalDistanceMm = distanceMeasurement
                }
            }
            lastDistanceMm = distanceMeasurement
        }

        if (offsetMeasurement != null) {
            currentOffsetMm = offsetMeasurement
        }
    }

    private fun handleGyroscope(sample: SensorSample) {
        val values = sample.values
        if (values.size >= 3) {
            currentAngularVelocity = sqrt(
                values[0].pow(2) + values[1].pow(2) + values[2].pow(2)
            )
        }
    }

    private fun handleAccelerometer(sample: SensorSample) {
        val values = sample.values
        if (values.size >= 3) {
            val magnitude = sqrt(
                values[0].pow(2) + values[1].pow(2) + values[2].pow(2)
            )
            val linearComponent = abs(magnitude - SensorManager.GRAVITY_EARTH)
            tremorMagnitude = (tremorMagnitude * 0.8f) + (linearComponent * 0.2f)
        }
    }
}
