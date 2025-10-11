package com.clinic.ataxia

import android.app.Application
import android.hardware.SensorManager
import androidx.core.content.getSystemService
import com.clinic.ataxia.data.local.AtaxiaDatabase
import com.clinic.ataxia.data.repository.SensorRepository
import com.clinic.ataxia.data.sensor.SensorCollector
import com.clinic.ataxia.data.sensor.SensorFusionEngine
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob

class AtaxiaMonitorApp : Application() {

    lateinit var sensorRepository: SensorRepository
        private set

    private val applicationScope by lazy { CoroutineScope(SupervisorJob() + Dispatchers.Default) }

    override fun onCreate() {
        super.onCreate()
        val database = AtaxiaDatabase.getInstance(this)
        val sensorManager: SensorManager = getSystemService() ?: throw IllegalStateException("SensorManager not available")
        val sensorCollector = SensorCollector(sensorManager)
        val fusionEngine = SensorFusionEngine()
        sensorRepository = SensorRepository(
            database = database,
            sensorCollector = sensorCollector,
            fusionEngine = fusionEngine,
            scope = applicationScope
        )
    }
}
