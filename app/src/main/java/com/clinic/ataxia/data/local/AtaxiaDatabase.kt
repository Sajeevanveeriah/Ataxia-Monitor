package com.clinic.ataxia.data.local

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase

/**
 * Process-wide Room database for sessions and their sensor samples.
 *
 * Schema version 1 has no migration path yet and schema export is disabled. Before
 * changing entities in a way that increments the version, add explicit migration
 * coverage rather than relying on destructive recreation for recorded sessions.
 */
@Database(
    entities = [SessionEntity::class, SensorSampleEntity::class],
    version = 1,
    exportSchema = false
)
abstract class AtaxiaDatabase : RoomDatabase() {
    abstract fun sessionDao(): SessionDao
    abstract fun sensorSampleDao(): SensorSampleDao

    companion object {
        @Volatile
        private var INSTANCE: AtaxiaDatabase? = null

        /**
         * Returns one database instance for the process. The volatile reference and
         * synchronised initialisation prevent duplicate Room instances during races.
         */
        fun getInstance(context: Context): AtaxiaDatabase {
            return INSTANCE ?: synchronized(this) {
                INSTANCE ?: Room.databaseBuilder(
                    context.applicationContext,
                    AtaxiaDatabase::class.java,
                    "ataxia-monitor.db"
                ).build().also { INSTANCE = it }
            }
        }
    }
}
