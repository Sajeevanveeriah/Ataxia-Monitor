# Ataxia Monitor

Ataxia Monitor is an Android prototype for recording motion and distance signals from a wire-maze style measurement setup. It collects Android sensor events, converts them into a small domain model, derives live traversal metrics and persists both the session record and each sensor sample in Room.

The repository demonstrates the software pipeline around data capture and review. The current fusion logic is deliberately simple and should be treated as an engineering prototype, not as evidence that the resulting metrics are clinically validated measurements.

## System flow

```text
Android sensors
    |
    v
SensorCollector
    |
    v
SensorSample
    |
    +--------------------+
    |                    |
    v                    v
SensorFusionEngine   raw sample values
    |                    |
    v                    |
TraversalMetrics         |
    |                    |
    +----------+---------+
               |
               v
        SensorRepository
               |
        +------+------+
        |             |
        v             v
   Room database   live StateFlow
        |             |
        v             v
 session history   Compose UI
```

`SensorRepository` is the orchestration boundary. It starts and stops collection, resets the fusion state between sessions, persists readings on the IO dispatcher and exposes live/session state to the ViewModel.

## Source map

| Area | Responsibility |
| --- | --- |
| `AtaxiaMonitorApp.kt` | Creates the application-scoped dependency graph: Room database, `SensorManager`, collector, fusion engine and repository. |
| `MainActivity.kt` | Compose presentation and interaction layer. It binds the UI to `MainViewModel` state and actions. |
| `data/sensor/SensorCollector.kt` | Registers available Android sensors and converts callback events into a `Flow<SensorSample>`. |
| `data/sensor/SensorFusionEngine.kt` | Stateful metric derivation for distance, offset, angular velocity and a smoothed acceleration-derived tremor proxy. |
| `data/repository/SensorRepository.kt` | Session lifecycle, collection job ownership, persistence and live-state publication. |
| `data/local/` | Room schema, DAOs and session/sample relationships. |
| `data/mapper/` | Conversion between persisted Room objects and domain models. |
| `domain/model/` | Sensor, metric and session types used outside persistence. |
| `ui/MainViewModel.kt` | Combines repository streams with participant input into a single `MainUiState`. |

## Sensor handling

The collector requests:

- gyroscope
- accelerometer
- rotation vector
- time-of-flight on supported Android versions in the current implementation
- proximity as the fallback path used by the current implementation when the time-of-flight branch is not selected

Sensors that are unavailable are skipped rather than failing the complete stream.

Each Android callback copies the sensor value array before emitting it. That is important because Android may reuse the framework-provided event buffer after the callback returns.

`callbackFlow` owns the listener lifecycle. Every listener registered by a collection is unregistered in `awaitClose`, so cancelling the repository's collection job also releases the sensor subscriptions.

## Fusion behaviour

`SensorFusionEngine` is stateful. It must be reset at the beginning of each recording session.

### Distance and radial offset

The current implementation expects the first two values of a time-of-flight-domain sample to represent:

1. along-path distance in millimetres
2. radial offset in millimetres

The first distance reading seeds the running total. Positive deltas are accumulated. A negative delta is treated as a sensor reset or new-lap condition and replaces the running total with the new reading.

That behaviour is an explicit modelling assumption. If the physical sensor reports signed motion, wrap-around or calibrated absolute position differently, update the algorithm and its tests rather than changing the data interpretation silently.

### Angular velocity

The gyroscope metric is the Euclidean magnitude of the three angular-rate components:

```text
omega = sqrt(x^2 + y^2 + z^2)
```

The result therefore represents rotational-rate magnitude rather than orientation about a specific maze axis.

### Acceleration-derived tremor proxy

The accelerometer path computes vector magnitude, subtracts standard Earth gravity and exponentially smooths the absolute residual:

```text
linear = abs(|a| - g)
smoothed = 0.8 * previous + 0.2 * linear
```

The 0.8/0.2 weighting is a fixed smoothing choice in the prototype. It is not currently loaded from calibration data and should not be changed without updating the interpretation, verification data and tests.

## Session lifecycle

`SensorRepository.startSession` intentionally ignores a second start request while a session is already active.

Starting a session:

1. resets fusion state
2. clears the live metric
3. inserts a new Room session
4. publishes the generated session ID
5. starts sensor collection

Stopping a session:

1. clears the active session ID
2. cancels the sensor collection job
3. records the session end time
4. clears the live metric

Samples are persisted with both their raw value payload and the metrics produced at that point in the stream. This makes later analysis possible without needing to reconstruct the exact live fusion state from UI state.

## Persistence

The Room database is `ataxia-monitor.db` and currently uses schema version 1.

`SensorSampleEntity` references `SessionEntity` through `session_id` with `ON DELETE CASCADE`. Deleting a session at the database level therefore removes its associated samples as part of the same relationship contract.

Indexes on `session_id` and `timestamp` support the two principal lookup dimensions: readings belonging to one session and chronological sample access.

The current database configuration has `exportSchema = false`. If migration history becomes important, enable schema export and add explicit migrations before incrementing the database version.

## UI state

`MainViewModel` combines five sources into `MainUiState`:

- participant identifier input
- notes input
- live traversal metrics
- stored session summaries
- active session ID

The active session ID is converted into the UI-facing `isSessionActive` flag. This keeps the Compose layer dependent on presentation state rather than repository implementation details.

If the operator leaves the patient identifier blank, the ViewModel generates a timestamp-based placeholder. Treat that as a convenience for prototype use, not as a durable participant identity strategy.

## Build and run

Open the project in Android Studio with JDK 17. The repository targets Android devices and should be exercised on physical hardware when validating sensor behaviour.

When a Gradle wrapper is present:

```bash
./gradlew assembleDebug
./gradlew test
```

The JVM tests should remain focused on deterministic fusion and mapping behaviour. Hardware availability, sensor timing and end-to-end collection require device or instrumentation validation.

## Verification priorities

When changing the sensor pipeline, verify at least:

- a session reset removes state from the previous session
- missing sensors do not prevent other sensors from streaming
- collector cancellation unregisters listeners
- distance accumulation handles the documented reset rule
- gyroscope magnitude remains dimensionally consistent with the input angular-rate units
- the acceleration filter uses the intended weighting and gravity reference
- persistence links each sample to the correct session
- stopping a session prevents further samples from being associated with it
- UI active/inactive state follows repository session state

## Maintenance notes

- Do not interpret `SensorType.TIME_OF_FLIGHT` as proof of a particular physical sensor interface. The collector-to-domain mapping is an adapter and should match the actual hardware path used by the project.
- Rotation-vector events are collected but are not currently consumed by the fusion engine.
- The repository writes every collected sample to Room. Higher sensor rates may require batching or another persistence strategy if profiling shows write pressure.
- `applicationScope` intentionally outlives activities and ViewModels. Any work launched there must have an explicit lifecycle or cancellation owner.
- Metric names shown in the UI should stay aligned with the algorithms that produce them. If an algorithm changes meaning, update the domain name and documentation rather than only changing its implementation.
- Patient identifiers and notes are stored locally as plain Room fields in the current prototype. Any real deployment involving regulated or sensitive study data requires a separate security, consent, retention and access-control design.
