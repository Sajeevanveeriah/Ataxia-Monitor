package com.clinic.ataxia.data.local

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase

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
