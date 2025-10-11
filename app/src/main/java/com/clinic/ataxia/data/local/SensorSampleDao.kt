package com.clinic.ataxia.data.local

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.Query

@Dao
interface SensorSampleDao {
    @Insert
    suspend fun insert(sample: SensorSampleEntity)

    @Query("DELETE FROM sensor_samples WHERE session_id = :sessionId")
    suspend fun deleteBySession(sessionId: Long)
}
