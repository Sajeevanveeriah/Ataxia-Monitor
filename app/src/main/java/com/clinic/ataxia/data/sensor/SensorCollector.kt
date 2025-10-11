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

class SensorCollector(
    private val sensorManager: SensorManager
) {

    fun sensorSamples(): Flow<SensorSample> = callbackFlow {
        val listeners = mutableListOf<SensorEventListener>()
        val requestedTypes = mutableListOf(
            Sensor.TYPE_GYROSCOPE,
            Sensor.TYPE_ACCELEROMETER,
            Sensor.TYPE_ROTATION_VECTOR
        )

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

                override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) = Unit
            }
            listeners += listener
            sensorManager.registerListener(
                listener,
                sensor,
                SensorManager.SENSOR_DELAY_GAME
            )
        }

        awaitClose {
            listeners.forEach { sensorManager.unregisterListener(it) }
        }
    }

    private fun Sensor.toDomainType(): SensorType = when (type) {
        Sensor.TYPE_GYROSCOPE -> SensorType.GYROSCOPE
        Sensor.TYPE_ACCELEROMETER -> SensorType.ACCELEROMETER
        Sensor.TYPE_ROTATION_VECTOR -> SensorType.ROTATION_VECTOR
        Sensor.TYPE_TIME_OF_FLIGHT -> SensorType.TIME_OF_FLIGHT
        Sensor.TYPE_PROXIMITY -> SensorType.TIME_OF_FLIGHT
        else -> SensorType.UNKNOWN
    }
}
