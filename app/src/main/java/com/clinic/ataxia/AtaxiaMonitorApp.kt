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

/**
 * Application-scoped composition root for the prototype.
 *
 * Dependencies are intentionally constructed here rather than inside activities so
 * the database, fusion state and repository survive configuration changes. The
 * application scope is long-lived; work launched into it therefore needs an
 * explicit cancellation owner inside the repository or collector.
 */
class AtaxiaMonitorApp : Application() {

    /** Shared repository consumed by screen ViewModels. */
    lateinit var sensorRepository: SensorRepository
        private set

    // SupervisorJob prevents one child coroutine failure from automatically
    // cancelling unrelated application-scoped streams such as session history.
    private val applicationScope by lazy { CoroutineScope(SupervisorJob() + Dispatchers.Default) }

    override fun onCreate() {
        super.onCreate()

        val database = AtaxiaDatabase.getInstance(this)

        // Sensor capture is fundamental to this application; fail early if the
        // Android service is absent rather than constructing a partially valid graph.
        val sensorManager: SensorManager = getSystemService()
            ?: throw IllegalStateException("SensorManager not available")

        val sensorCollector = SensorCollector(sensorManager)
        val fusionEngine = SensorFusionEngine()

        // The repository is the single owner that coordinates these lower-level
        // components for session lifecycle, persistence and UI-facing state.
        sensorRepository = SensorRepository(
            database = database,
            sensorCollector = sensorCollector,
            fusionEngine = fusionEngine,
            scope = applicationScope
        )
    }
}
