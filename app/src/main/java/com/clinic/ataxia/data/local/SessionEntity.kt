package com.clinic.ataxia.data.local

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "sessions")
data class SessionEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    @ColumnInfo(name = "patient_id") val patientId: String,
    @ColumnInfo(name = "started_at") val startedAt: Long,
    @ColumnInfo(name = "ended_at") val endedAt: Long? = null,
    val notes: String? = null
)
