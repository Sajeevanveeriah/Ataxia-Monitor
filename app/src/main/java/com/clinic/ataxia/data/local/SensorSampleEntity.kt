package com.clinic.ataxia.data.local

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.ForeignKey
import androidx.room.Index
import androidx.room.PrimaryKey

/**
 * One persisted sensor event plus the fused metric snapshot produced from it.
 *
 * Raw values are retained in `valuesJson` so later analysis is not limited to the
 * metric implementation that existed when the sample was recorded. The session
 * foreign key cascades deletion to prevent orphaned high-frequency samples.
 */
@Entity(
    tableName = "sensor_samples",
    // Session and timestamp are the two expected access paths for review/export.
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
