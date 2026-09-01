package com.clinic.ataxia.data.sensor

import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import android.os.Build
import com.clinic.ataxia.domain.model.SensorSample
import com.clinic.ataxia.domain.model.SensorType
import kotlinx.coroutines.channels.awaitClose
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.callbackFlow

/**
 * Adapts Android's callback-based sensor API into the domain [SensorSample] flow.
 *
 * One listener is registered per available requested sensor. Missing sensors are
 * skipped so a device can still provide partial data. Cancelling collection closes
 * the callbackFlow and unregisters every listener created for that collection.
 */
class SensorCollector(
    private val sensorManager: SensorManager
) {

    /**
     * Emits defensive copies of framework sensor values at `SENSOR_DELAY_GAME`.
     * Android may reuse the event value buffer after the callback returns, so the
     * copy prevents later mutation of a sample that has already entered the flow.
     */
    fun sensorSamples(): Flow<SensorSample> = callbackFlow {
        val listeners = mutableListOf<SensorEventListener>()
        val requestedTypes = mutableListOf(
            Sensor.TYPE_GYROSCOPE,
            Sensor.TYPE_ACCELEROMETER,
            Sensor.TYPE_ROTATION_VECTOR
        )

        // The current domain model expects a two-value distance/offset source.
        // Older devices follow the proximity fallback path. Keep this adapter in
        // sync with the actual physical sensor integration used by the project.
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            requestedTypes += Sensor.TYPE_TIME_OF_FLIGHT
        } else {
            requestedTypes += Sensor.TYPE_PROXIMITY
        }

        requestedTypes.distinct().forEach { type ->
            val sensor = sensorManager.getDefaultSensor(type) ?: return@forEach
            val listener = object : SensorEventListener {
                override fun onSensorChanged(event: SensorEvent) {
                    val values = event.values.copyOf()
                    trySend(
                        SensorSample(
                            timestamp = event.timestamp,
                            sensorType = event.sensor.toDomainType(),
                            values = values
                        )
                    )
                }

                // Accuracy changes are not currently used by the fusion model. If
                // confidence/quality becomes part of the metric, propagate it here.
                override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) = Unit
            }
            listeners += listener
            sensorManager.registerListener(
                listener,
                sensor,
                SensorManager.SENSOR_DELAY_GAME
            )
        }

        // This is the ownership boundary for sensor registrations. Repository job
        // cancellation therefore releases hardware listeners without UI knowledge.
        awaitClose {
            listeners.forEach { sensorManager.unregisterListener(it) }
        }
    }

    /** Maps framework sensor identifiers onto the smaller domain vocabulary. */
    private fun Sensor.toDomainType(): SensorType = when (type) {
        Sensor.TYPE_GYROSCOPE -> SensorType.GYROSCOPE
        Sensor.TYPE_ACCELEROMETER -> SensorType.ACCELEROMETER
        Sensor.TYPE_ROTATION_VECTOR -> SensorType.ROTATION_VECTOR
        // Proximity is deliberately normalised into the distance-domain type so
        // downstream code has one adapter contract rather than Android API branches.
        Sensor.TYPE_TIME_OF_FLIGHT -> SensorType.TIME_OF_FLIGHT
        Sensor.TYPE_PROXIMITY -> SensorType.TIME_OF_FLIGHT
        else -> SensorType.UNKNOWN
    }
}
