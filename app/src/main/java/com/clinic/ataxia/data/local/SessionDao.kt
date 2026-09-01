package com.clinic.ataxia.data.local

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.Query
import androidx.room.Transaction
import kotlinx.coroutines.flow.Flow

/**
 * Session persistence boundary.
 *
 * The observation queries are transactions because their projection types include
 * related sample data/aggregates. Keeping the relation read consistent matters more
 * than exposing the underlying table operations to higher layers.
 */
@Dao
interface SessionDao {
    /** Inserts a session header and returns the generated parent key for samples. */
    @Insert
    suspend fun insert(session: SessionEntity): Long

    /** Marks an open session as complete without rewriting participant metadata. */
    @Query("UPDATE sessions SET ended_at = :endedAt WHERE id = :sessionId")
    suspend fun closeSession(sessionId: Long, endedAt: Long)

    /** Emits newest-first summaries used by the history screen. */
    @Transaction
    @Query("SELECT * FROM sessions ORDER BY started_at DESC")
    fun observeSessions(): Flow<List<SessionWithSummary>>

    /** Emits one session together with its related readings for detailed review. */
    @Transaction
    @Query("SELECT * FROM sessions WHERE id = :sessionId")
    fun observeSession(sessionId: Long): Flow<SessionWithReadings?>
}
