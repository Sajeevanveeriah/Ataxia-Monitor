# VW-MTC1 build and regression verification

Scope: integrate the supplied VW-MTC1 package into Ataxia-Monitor, make the Python tools buildable, restore the Android build, and cover previously untested core logic. The baseline remote commit was `c241391`; the remote had four commits, all reviewed. The original VW-MTC1 package was captured in `8b1034d` before software fixes.

## Observed checks

| Check | Observed result | Limit |
| --- | --- | --- |
| Python package, new environment in a clean clone at `343c3d6` | Wheel and source archive built; installed wheel passed 80 tests | Python 3.12.14 on Windows; CI also runs Windows/Linux |
| Python core helpers | 91.5% combined line and branch coverage | `common`, `ltraw`, `lttext`, `runlt`, `waveform`; full package coverage is 45.4% because the full-circuit scripts need regenerated raw waveforms |
| Schematic and summary generation | Passed from the installed wheel in the clean clone | Uses stored evidence, not a fresh simulation; both generated `.asc` files also matched the originals byte-for-byte in the working checkout |
| Firmware header | Host C++ syntax check passed | No executable ESP32 firmware exists in the package |
| Android debug build, clean clone at `343c3d6` | Committed wrapper built the APK; 18 JVM tests passed; lint completed with 0 errors and 24 warnings; all 50 tasks executed | JDK 17 on Windows; dependency downloads cached, build outputs absent initially; sensors and persistence boundaries mocked; no device instrumentation |
| KiCad 10.0.6 DRC with schematic parity, clean clone | 0 errors, 0 unconnected items, 0 parity issues; 219 warnings | No PCB edits or physical measurements |
| LTspice 26.1.1 integration | Fresh operating-point, converter start-up, burst, charger and hot-plug runs completed; fresh start-up raw data parsed successfully | The wider sweep is partial: several long converter/power-path cases exceeded the 180-second per-case limit |
| Preservation | No changes to the supplied hardware, firmware pin map, `Docs/` exports, archived simulation results, plots or netlists relative to `8b1034d` | Python tools and README guidance changed; original delivery ZIP and thesis stay local |

The first Python regression run recorded 22 failures and 29 passes before fixes. Import-safety regressions separately demonstrated both generators writing files on import. After the Android compilation blockers were removed, its regression run recorded 6 failures out of 18 tests before the behavioural fixes. No failing tests were disabled or marked as expected failures.

## Confirmed software bugs and regression checks

Locations below identify the repaired code in this branch. Test names refer to committed, executable tests. Build failures are listed with the actual failing Gradle task because a source/resource compilation failure prevents JVM tests from running.

| Bug | Source location | Failing regression before the fix | Fix |
| --- | --- | --- | --- |
| UTF-16 byte-order marks broke waveform/log parsing and lost measurements | `VW-MTC1/Simulation/tools/ltraw.py:19`, `lttext.py:4`, `runlt.py:18` | `test_real_binary_layouts`, `test_measurement_encodings_and_timing`, `test_read_log_encodings` BOM cases | Shared encoding detection, preserving binary payload offsets |
| ASCII negative-time flags created false step boundaries | `VW-MTC1/Simulation/tools/ltraw.py:70` | `test_negative_time_flags_do_not_create_false_steps[False]` | Normalise transient time flags for both input formats |
| Invalid files supplied as Path objects raised TypeError while constructing the intended parser error | `VW-MTC1/Simulation/tools/ltraw.py:35` | `test_missing_marker_accepts_path_objects` | Path-safe error formatting |
| Truncated ASCII data escaped as IndexError instead of a controlled parse failure | `VW-MTC1/Simulation/tools/ltraw.py:107` | `test_truncated_waveforms_are_rejected[real-False]` | Validate declared counts and payload lengths |
| Time averages omitted partial intervals at the requested boundaries and failed when no interior sample existed | `VW-MTC1/Simulation/tools/ltraw.py:163` | `test_time_average_interpolates_window_boundaries`, `test_time_average_window_between_samples`, invalid-window cases | Interpolate both endpoints, integrate over the requested duration and validate the window |
| Serialisation failure truncated the previously saved result set | `VW-MTC1/Simulation/tools/common.py:51` | `test_serialisation_failure_preserves_existing_results` | Serialise before opening a temporary file; atomically replace only after successful writing |
| Plot export failed when the output directory did not exist | `VW-MTC1/Simulation/tools/common.py:27` | `test_savefig_creates_missing_plot_directory` | Create the directory and always close the figure |
| Zero exit codes with missing or stale logs were reported as successful simulations | `VW-MTC1/Simulation/tools/runlt.py:48` | `test_missing_log_is_failure`, `test_stale_log_is_failure` | Require a fresh non-empty log |
| A failed LTspice measurement was reported as success | `VW-MTC1/Simulation/tools/runlt.py:68` | `test_log_failures_are_not_success` failed-measurement case | Detect failed measurements as well as solver failures |
| A circuit name containing `error` caused a false failure | `VW-MTC1/Simulation/tools/runlt.py:68` | `test_error_word_in_circuit_name_is_not_failure` | Recognise error messages rather than arbitrary substrings |
| Timed-out simulator processes were killed without being reaped | `VW-MTC1/Simulation/tools/runlt.py:60` | `test_timeout_kills_and_reaps_its_child` | Wait for the killed child before returning |
| Importing generators overwrote files | `VW-MTC1/Simulation/tools/make_asc.py:67`, `make_summary.py:10` | Both `test_importing_*_writes_nothing` tests | Explicit entry points guarded by `__main__` |
| Android referenced an unavailable XML theme | `app/src/main/res/values/themes.xml:2`, `values-night/themes.xml:2` | `:app:processDebugResources` failed with missing `Theme.Material3.DayNight.NoActionBar` | Use platform host themes; Compose still supplies the UI theme |
| Room tried to populate calculated summary fields as database columns | `app/src/main/java/com/clinic/ataxia/data/local/SessionWithRelations.kt:16` | `:app:kaptDebugKotlin` failed with missing columns/setters | Mark derived fields with `@Ignore` |
| The collector referenced a nonexistent public Android sensor constant | `app/src/main/java/com/clinic/ataxia/data/sensor/SensorCollector.kt:30` | `:app:compileDebugKotlin` failed on `TYPE_TIME_OF_FLIGHT` | Register public Android sensor types |
| History summed cumulative distance once per sensor event and mishandled resets/unordered rows | `app/src/main/java/com/clinic/ataxia/data/local/SessionWithRelations.kt:16`, `data/mapper/EntityMappers.kt:40` | `cumulativeDistanceIsNotSummedForEverySensorEvent`, `latestTimestampWinsAfterDistanceResetEvenWhenRoomRowsAreUnsorted` | Use the latest timestamp's distance and share the summary mapping |
| Concurrent starts inserted multiple sessions | `app/src/main/java/com/clinic/ataxia/data/repository/SensorRepository.kt:66` | `concurrentStartsCreateOnlyOneSession` | Serialise lifecycle transitions with a mutex |
| Stop closed the database session before sensor cleanup completed | `app/src/main/java/com/clinic/ataxia/data/repository/SensorRepository.kt:89` | `stopWaitsForSensorCleanupBeforeClosingTheSession` | Cancel and join collection before closing the record |
| Failed database closes lost the active ID, preventing retry | `app/src/main/java/com/clinic/ataxia/data/repository/SensorRepository.kt:89` | `failedCloseCanBeRetriedWithoutOrphaningTheSession` | Clear the ID only after successful persistence |
| Phone proximity was incorrectly interpreted as along-maze distance in millimetres | `app/src/main/java/com/clinic/ataxia/data/sensor/SensorCollector.kt:78` | `phoneProximityDoesNotBecomeAlongMazeDistance` | Retain proximity as its own sensor type and exclude it from distance fusion |

Android documents phone proximity in centimetres and notes that some sensors only report near/far. It is not a calibrated maze-position measurement: [Android SensorEvent reference](https://developer.android.com/reference/android/hardware/SensorEvent#values).

Additional passing cases cover normal binary/ASCII/complex/FastAccess layouts, case-insensitive traces, NumPy scalar serialisation, preservation on failed replacement, pulse edge cases, smoothing, empty sessions, metadata/JSON mapping, fusion reset, missing sensors, defensive event-buffer copies and listener cancellation.

## Remaining work

- Complete the long analogue sweeps with a larger time budget, then run every full-circuit analysis script on the fresh raw files. Archived results were not relabelled as newly verified.
- Fresh SIM02 post-processing reproduced the existing charger termination check failure: 28.8 mA against the model's 30 to 50 mA target. `an_sim02.py` retains that FAIL. This model/device question was not hidden or "fixed" by changing the acceptance limit.
- Review the 219 KiCad warnings and 24 Android lint warnings. They were not suppressed to obtain a pass.
- Implement and test board firmware, the board-to-app transport and the calibrated sensor contract. The present firmware deliverable is a header only.
- Run physical/device tests and assess the existing design-report open items. Unit tests and DRC cannot establish physical or clinical performance.
- The Python result store supports sequential writers. Atomic replacement protects against interrupted/failed writes, not concurrent updates by multiple processes.

No hardware revision, fabrication export, clinical claim, deployment or merge is part of these changes.
