package com.clinic.ataxia.data.sensor

import com.clinic.ataxia.domain.model.SensorSample
import com.clinic.ataxia.domain.model.SensorType
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class SensorFusionEngineTest {

    @Test
    fun resetClearsEveryAccumulator() {
        val engine = SensorFusionEngine()
        engine.process(SensorSample(1, SensorType.TIME_OF_FLIGHT, floatArrayOf(20f, 5f)))
        engine.process(SensorSample(2, SensorType.GYROSCOPE, floatArrayOf(3f, 4f, 0f)))
        engine.process(SensorSample(3, SensorType.ACCELEROMETER, floatArrayOf(0f, 0f, 12f)))
        engine.reset()
        val metrics = engine.process(SensorSample(4, SensorType.UNKNOWN, floatArrayOf()))
        assertEquals(4L, metrics.timestamp)
        assertEquals(0f, metrics.distanceMillimeters, 0f)
        assertEquals(0f, metrics.radialOffsetMillimeters, 0f)
        assertEquals(0f, metrics.angularVelocity, 0f)
        assertEquals(0f, metrics.tremorMagnitude, 0f)
    }

    @Test
    fun distanceResetAndMissingOffsetFollowTheDocumentedContract() {
        val engine = SensorFusionEngine()
        engine.process(SensorSample(1, SensorType.TIME_OF_FLIGHT, floatArrayOf(20f, 5f)))
        val metrics = engine.process(SensorSample(2, SensorType.TIME_OF_FLIGHT, floatArrayOf(3f)))
        assertEquals(3f, metrics.distanceMillimeters, 0f)
        assertEquals(5f, metrics.radialOffsetMillimeters, 0f)
    }

    @Test
    fun shortAndUnusedSamplesPreserveExistingMetrics() {
        val engine = SensorFusionEngine()
        engine.process(SensorSample(1, SensorType.GYROSCOPE, floatArrayOf(3f, 4f, 0f)))
        for (type in SensorType.values()) {
            val metrics = engine.process(SensorSample(2, type, floatArrayOf()))
            assertEquals(5f, metrics.angularVelocity, 0f)
            assertEquals(0f, metrics.tremorMagnitude, 0f)
        }
    }

    @Test
    fun accelerationUsesTheSpecifiedExponentialWeighting() {
        val engine = SensorFusionEngine()
        val gravity = 9.80665f
        val first = engine.process(SensorSample(1, SensorType.ACCELEROMETER, floatArrayOf(0f, 0f, gravity + 1f)))
        val second = engine.process(SensorSample(2, SensorType.ACCELEROMETER, floatArrayOf(0f, 0f, gravity)))
        assertEquals(.2f, first.tremorMagnitude, .00001f)
        assertEquals(.16f, second.tremorMagnitude, .00001f)
    }

    @Test
    fun accumulatesDistanceAndOffset() {
        val engine = SensorFusionEngine()

        val first = engine.process(
            SensorSample(
                timestamp = 0L,
                sensorType = SensorType.TIME_OF_FLIGHT,
                values = floatArrayOf(10f, 2f)
            )
        )
        assertEquals(10f, first.distanceMillimeters, 0.001f)
        assertEquals(2f, first.radialOffsetMillimeters, 0.001f)

        val second = engine.process(
            SensorSample(
                timestamp = 1L,
                sensorType = SensorType.TIME_OF_FLIGHT,
                values = floatArrayOf(15f, 1f)
            )
        )
        assertEquals(15f, second.distanceMillimeters, 0.001f)
        assertEquals(1f, second.radialOffsetMillimeters, 0.001f)
    }

    @Test
    fun computesAngularVelocityAndTremor() {
        val engine = SensorFusionEngine()

        val gyroMetrics = engine.process(
            SensorSample(
                timestamp = 10L,
                sensorType = SensorType.GYROSCOPE,
                values = floatArrayOf(1f, 2f, 2f)
            )
        )
        assertEquals(3f, gyroMetrics.angularVelocity, 0.001f)

        val accelMetrics = engine.process(
            SensorSample(
                timestamp = 11L,
                sensorType = SensorType.ACCELEROMETER,
                values = floatArrayOf(0f, 0f, 9.81f)
            )
        )
        assertEquals(0f, accelMetrics.tremorMagnitude, 0.05f)

        val tremorMetrics = engine.process(
            SensorSample(
                timestamp = 12L,
                sensorType = SensorType.ACCELEROMETER,
                values = floatArrayOf(2f, 2f, 9.81f)
            )
        )
        assertTrue(tremorMetrics.tremorMagnitude > 0f)
    }
}
