package com.clinic.ataxia.data.sensor

import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import com.clinic.ataxia.domain.model.SensorSample
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.collect
import kotlinx.coroutines.test.*
import org.junit.Assert.*
import org.junit.Test
import org.mockito.ArgumentCaptor
import org.mockito.ArgumentMatchers.*
import org.mockito.Mockito.*

@OptIn(ExperimentalCoroutinesApi::class)
class SensorCollectorTest {
    @Test
    fun missingSensorsDoNotPreventOtherEventsAndCancellationUnregistersListeners() = runTest {
        val manager = mock(SensorManager::class.java)
        val sensor = mock(Sensor::class.java)
        `when`(sensor.type).thenReturn(Sensor.TYPE_GYROSCOPE)
        `when`(manager.getDefaultSensor(Sensor.TYPE_GYROSCOPE)).thenReturn(sensor)
        val received = mutableListOf<SensorSample>()
        val job = launch { SensorCollector(manager).sensorSamples().collect { received += it } }
        runCurrent()
        val captor = ArgumentCaptor.forClass(SensorEventListener::class.java)
        verify(manager).registerListener(captor.capture(), eq(sensor), eq(SensorManager.SENSOR_DELAY_GAME))
        val event = mock(SensorEvent::class.java)
        val values = floatArrayOf(1f, 2f, 3f)
        SensorEvent::class.java.getField("values").set(event, values)
        event.sensor = sensor
        event.timestamp = 123
        captor.value.onSensorChanged(event)
        values[0] = 99f
        runCurrent()
        assertEquals(1f, received.single().values[0], 0f)
        assertEquals(123L, received.single().timestamp)
        job.cancelAndJoin()
        verify(manager).unregisterListener(captor.value)
    }

    @Test
    fun phoneProximityDoesNotBecomeAlongMazeDistance() = runTest {
        val manager = mock(SensorManager::class.java)
        val sensor = mock(Sensor::class.java)
        `when`(sensor.type).thenReturn(Sensor.TYPE_PROXIMITY)
        `when`(manager.getDefaultSensor(Sensor.TYPE_PROXIMITY)).thenReturn(sensor)
        val received = mutableListOf<SensorSample>()
        val job = launch { SensorCollector(manager).sensorSamples().collect { received += it } }
        runCurrent()
        val captor = ArgumentCaptor.forClass(SensorEventListener::class.java)
        verify(manager).registerListener(captor.capture(), eq(sensor), eq(SensorManager.SENSOR_DELAY_GAME))
        val event = mock(SensorEvent::class.java)
        SensorEvent::class.java.getField("values").set(event, floatArrayOf(5f))
        event.sensor = sensor
        captor.value.onSensorChanged(event)
        runCurrent()
        assertEquals(0f, SensorFusionEngine().process(received.single()).distanceMillimeters, 0f)
        job.cancelAndJoin()
    }
}
