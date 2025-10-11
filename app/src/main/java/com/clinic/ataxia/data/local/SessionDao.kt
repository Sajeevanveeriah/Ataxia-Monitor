package com.clinic.ataxia.data.local

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.Query
import androidx.room.Transaction
import kotlinx.coroutines.flow.Flow

@Dao
interface SessionDao {
    @Insert
    suspend fun insert(session: SessionEntity): Long

    @Query("UPDATE sessions SET ended_at = :endedAt WHERE id = :sessionId")
    suspend fun closeSession(sessionId: Long, endedAt: Long)

    @Transaction
    @Query("SELECT * FROM sessions ORDER BY started_at DESC")
    fun observeSessions(): Flow<List<SessionWithSummary>>

    @Transaction
    @Query("SELECT * FROM sessions WHERE id = :sessionId")
    fun observeSession(sessionId: Long): Flow<SessionWithReadings?>
}
