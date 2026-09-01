package com.clinic.ataxia.data.local

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.Query

/** High-frequency sample write/delete boundary used by [com.clinic.ataxia.data.repository.SensorRepository]. */
@Dao
interface SensorSampleDao {
    /** Persists one raw sensor event and its same-instant fused metric snapshot. */
    @Insert
    suspend fun insert(sample: SensorSampleEntity)

    /**
     * Explicit per-session cleanup hook. The schema also declares cascade deletion
     * from `sessions`, so callers should prefer one ownership path and avoid doing both.
     */
    @Query("DELETE FROM sensor_samples WHERE session_id = :sessionId")
    suspend fun deleteBySession(sessionId: Long)
}
