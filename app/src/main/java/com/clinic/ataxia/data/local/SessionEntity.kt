package com.clinic.ataxia.data.local

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.PrimaryKey

/**
 * Persisted recording-session header.
 *
 * `endedAt == null` represents a session that has not been closed yet. The numeric
 * primary key is also the parent key used by every [SensorSampleEntity].
 */
@Entity(tableName = "sessions")
data class SessionEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    @ColumnInfo(name = "patient_id") val patientId: String,
    @ColumnInfo(name = "started_at") val startedAt: Long,
    @ColumnInfo(name = "ended_at") val endedAt: Long? = null,
    val notes: String? = null
)
