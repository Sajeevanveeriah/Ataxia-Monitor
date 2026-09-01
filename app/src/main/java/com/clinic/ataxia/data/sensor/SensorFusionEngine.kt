package com.clinic.ataxia.data.sensor

import android.hardware.SensorManager
import com.clinic.ataxia.domain.model.SensorSample
import com.clinic.ataxia.domain.model.SensorType
import com.clinic.ataxia.domain.model.TraversalMetrics
import kotlin.math.abs
import kotlin.math.pow
import kotlin.math.sqrt

/**
 * Stateful prototype fusion layer for the live traversal metrics shown by the app.
 *
 * The engine intentionally keeps only the latest cross-sensor state. Call [reset]
 * before every new recording session so distance accumulation and smoothing do not
 * leak between participants or runs.
 *
 * The calculations here are engineering approximations, not clinical validation:
 * - time-of-flight-domain value 0 is treated as along-path distance in millimetres;
 * - value 1 is treated as radial offset in millimetres;
 * - gyroscope output is vector magnitude, not rotation about one maze axis;
 * - tremor is a smoothed acceleration residual after subtracting standard gravity.
 */
class SensorFusionEngine {

    private var lastDistanceMm: Float? = null
    private var totalDistanceMm: Float = 0f
    private var currentOffsetMm: Float = 0f
    private var currentAngularVelocity: Float = 0f
    private var tremorMagnitude: Float = 0f

    /** Clears all history-dependent state at the boundary between sessions. */
    fun reset() {
        lastDistanceMm = null
        totalDistanceMm = 0f
        currentOffsetMm = 0f
        currentAngularVelocity = 0f
        tremorMagnitude = 0f
    }

    /**
     * Applies one sensor sample to the appropriate metric accumulator and returns
     * a complete snapshot using the most recent value known for every metric.
     */
    fun process(sample: SensorSample): TraversalMetrics {
        when (sample.sensorType) {
            SensorType.TIME_OF_FLIGHT -> handleTimeOfFlight(sample)
            SensorType.GYROSCOPE -> handleGyroscope(sample)
            SensorType.ACCELEROMETER -> handleAccelerometer(sample)
            // Rotation-vector and unknown samples are retained by persistence but
            // do not currently alter the live fusion state.
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
                // The first absolute reading seeds the accumulated distance rather
                // than adding a delta from an undefined previous position.
                totalDistanceMm = distanceMeasurement
            } else {
                val delta = distanceMeasurement - last
                if (delta >= 0f) {
                    totalDistanceMm += delta
                } else {
                    // A negative jump is interpreted as sensor reset/wrap/new-lap
                    // behaviour. Change this rule only with matching hardware data.
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
            // Preserve the input unit while collapsing x/y/z into rotational-rate
            // magnitude. Axis-specific interpretation belongs in a calibrated model.
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

            // Fixed exponential smoothing prevents the UI from following every
            // high-frequency acceleration spike. The 0.8/0.2 split is part of the
            // current metric definition and should be validated if recalibrated.
            tremorMagnitude = (tremorMagnitude * 0.8f) + (linearComponent * 0.2f)
        }
    }
}
