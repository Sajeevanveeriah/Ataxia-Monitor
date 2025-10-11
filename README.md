# Ataxia Monitor

An Android application for capturing high-frequency sensor data from a wire-maze device used in ataxia clinical trials. The app records readings from time-of-flight (ToF), gyroscope, accelerometer, and rotation vector sensors, fuses them into clinically relevant metrics, and stores the results for session review and export.

## Features

- **Live monitoring dashboard**: View distance travelled along the wire, radial offset from the ring centre, angular velocity, and tremor magnitude in real time.
- **Session management**: Start/stop recording runs with patient identifiers and clinician notes.
- **Persistent storage**: Raw sensor readings and fused metrics are stored locally via Room for later analysis.
- **Historical review**: Inspect previous sessions with automatically calculated summaries (total distance, average offset, peak tremor).
- **Extensible architecture**: Modular repository, sensor collector, and fusion layers to support additional sensors or export formats.

## Project structure

```
app/
├── src/main/java/com/clinic/ataxia/
│   ├── AtaxiaMonitorApp.kt            # Application class and dependency container
│   ├── MainActivity.kt                # Compose UI and interaction layer
│   ├── data/
│   │   ├── local/                     # Room database, entities, DAO relations
│   │   ├── mapper/                    # Database ↔ domain converters
│   │   ├── repository/                # SensorRepository orchestrating collection
│   │   └── sensor/                    # SensorCollector + SensorFusionEngine
│   ├── domain/model/                  # Core domain data classes
│   └── ui/                            # ViewModel and UI state definitions
└── src/test/java/...                  # Unit tests for fusion logic
```

## Getting started

1. **Android Studio**: Open the project folder (`Ataxia-Monitor`) in Android Studio Giraffe or newer with JDK 17.
2. **Gradle wrapper**: If the Gradle wrapper is not yet generated, run `gradle wrapper` from within Android Studio or the terminal. Once created, you can build with `./gradlew assembleDebug`.
3. **Run the app**: Deploy to a device running Android 8.0 (API 26) or later. Physical hardware is recommended to access motion sensors.

## Sensor assumptions

- **Time-of-flight**: A ToF sensor channel provides the along-wire distance (values[0]) and radial offset from the ring centre (values[1]) in millimetres. When the ToF sensor is unavailable, the app falls back to proximity readings.
- **Gyroscope**: Angular velocity vector (rad/s) used to monitor ring rotation and tremor.
- **Accelerometer**: Used to estimate tremor magnitude via a high-pass filter over gravity.
- **Rotation vector**: Registered for potential orientation tracking and future fusion improvements.

The `SensorFusionEngine` consolidates readings into session metrics, applying simple filters and drift handling. Update this class if calibration constants change or more precise models are needed.

## Data export

Session summaries and detailed readings reside in a Room database (`ataxia-monitor.db`). They can be exported by querying `sensor_samples` and `sessions` tables, or by adding an export workflow that consumes the repository API.

## Testing

Run JVM unit tests with:

```bash
./gradlew test
```

The included tests cover the sensor fusion accumulator behaviour. Add instrumentation tests for end-to-end validation when hardware is available.

## Next steps

- Integrate Bluetooth/USB ingestion if the maze sensors stream data externally.
- Add CSV/JSON export and secure data upload to the clinical data platform.
- Harden calibration logic with configurable offsets and drift compensation.
- Implement authentication and patient consent workflows if required by the study protocol.
