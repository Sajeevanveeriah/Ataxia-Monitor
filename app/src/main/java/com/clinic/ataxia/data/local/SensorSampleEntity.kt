package com.clinic.ataxia.data.local

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.ForeignKey
import androidx.room.Index
import androidx.room.PrimaryKey

@Entity(
    tableName = "sensor_samples",
    indices = [Index(value = ["session_id"]), Index(value = ["timestamp"])],
    foreignKeys = [
        ForeignKey(
            entity = SessionEntity::class,
            parentColumns = ["id"],
            childColumns = ["session_id"],
            onDelete = ForeignKey.CASCADE
        )
    ]
)
data class SensorSampleEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    @ColumnInfo(name = "session_id") val sessionId: Long,
    val timestamp: Long,
    @ColumnInfo(name = "sensor_type") val sensorType: String,
    @ColumnInfo(name = "values_json") val valuesJson: String,
    @ColumnInfo(name = "distance_mm") val distanceMillimeters: Float,
    @ColumnInfo(name = "offset_mm") val offsetMillimeters: Float,
    @ColumnInfo(name = "angular_velocity") val angularVelocity: Float,
    @ColumnInfo(name = "tremor") val tremorMagnitude: Float
)
