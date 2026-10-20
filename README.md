# Ataxia Device and Monitor

This repository contains the VW-MTC1 MazeTrack controller design, its LTspice analysis tools, and the Android monitoring prototype. The controller package is the current hardware setup. The Android app still reads phone sensors; a board-to-app transport and executable board firmware have not been implemented.

## Project map

| Path | Contents |
| --- | --- |
| `VW-MTC1/Hardware/` | KiCad 10 sources, fabrication exports and archived ERC/DRC reports |
| `VW-MTC1/Firmware/` | ESP32-S3 pin-map header; no flashable firmware application yet |
| `VW-MTC1/Simulation/` | LTspice circuits, archived results/plots and Python analysis tools |
| `VW-MTC1/Docs/` | Original Rev00 design report, datasheet and images |
| `app/` | Android app, local JVM tests and [app documentation](app/README.md) |
| `tests/` | Python unit tests using synthetic waveforms and mocked simulator processes |
| `scripts/check_project.py` | Rebuild generated schematics and summary in `build/` |

The board has not been physically built or measured. Saved simulation and CAD reports are historical evidence, not a fresh hardware acceptance result. See [VW-MTC1/README.md](VW-MTC1/README.md) and the design report for outstanding engineering checks.

## Python build and tests from a clean checkout

Use Python 3.12 or newer. The development dependency set is pinned in `requirements-dev.txt`. NumPy 2 or newer is required because the analysis uses `numpy.trapezoid`.

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pip install --no-build-isolation -e .
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m build --no-isolation
.\.venv\Scripts\python.exe scripts/check_project.py
```

Linux/macOS:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pip install --no-build-isolation -e .
.venv/bin/python -m pytest -q
.venv/bin/python -m build --no-isolation
.venv/bin/python scripts/check_project.py
```

The build produces a Python wheel and source archive in `dist/`. It packages the tools, not the large hardware exports. The generation check writes to `build/vw-mtc1/` and preserves the supplied simulation evidence. Its summary is rebuilt from stored results; it does not claim a fresh simulation.

For line and branch coverage:

```sh
python -m pytest --cov=vw_mtc1 --cov-report=term-missing
```

Coverage reports include the full analysis scripts as well as the reusable helpers. Hardware-free unit tests do not execute every full-circuit analysis path.

A host C++ syntax check for the pin-map header is also available:

```sh
g++ -std=c++17 -Wall -Wextra -Werror -fsyntax-only tests/pinmap_compile.cpp
```

This checks header compilation only. It does not produce ESP32 firmware.

## Running LTspice

LTspice 26.1.1 was used for the supplied Rev00 evidence. Install LTspice separately, with its standard model library. No simulator is needed for the unit tests or Python package build.

The runner accepts `--executable`, then checks `LTSPICE_EXE`, `PATH` and standard Windows installation locations. It returns a failure for a timeout, a non-zero simulator exit, missing/unchanged/empty logs, simulator errors or failed measurements.

Run against a scratch copy when retaining the original logs:

```powershell
Copy-Item -Recurse VW-MTC1\Simulation\LTspice build\ltspice-run
.\.venv\Scripts\python.exe -m vw_mtc1.runlt build\ltspice-run\sim00_mosfet_model_check.cir 300
```

The source package omits raw waveform files. Regenerate the required `.cir` files before running `an_sim01` through `an_sim06_07`. Set `VW_MTC1_SIMULATION_DIR` to the scratch simulation directory containing `LTspice/`, `results.json` and, when generated, `Plots/`:

```powershell
$env:VW_MTC1_SIMULATION_DIR = (Resolve-Path build\vw-mtc1).Path
.\.venv\Scripts\python.exe -m vw_mtc1.an_sim01
```

The scripts execute sequentially when updating the same `results.json`; concurrent writers are not supported. Analysis modules should be run with `python -m vw_mtc1.<module>` after installation. A wheel installed outside this checkout also needs `VW_MTC1_SIMULATION_DIR` for data-dependent commands.

## Android build and tests

Use JDK 17, Android SDK platform 34 and build-tools 34.0.0. Set `JAVA_HOME` and `ANDROID_HOME` to those installations, or configure the SDK in Android Studio. The committed Gradle 8.2.1 wrapper verifies its distribution checksum.

```powershell
.\gradlew.bat assembleDebug testDebugUnitTest lintDebug
```

On Linux/macOS, use `./gradlew` with the same tasks. The debug APK is written to `app/build/outputs/apk/debug/`. JVM tests mock Android sensors and Room boundaries; they do not require a phone or emulator. Device instrumentation and physical sensor validation remain separate checks.

The app preserves raw phone proximity readings in their own sensor type. They are not calibrated along-maze distance. External board samples need an explicit transport and calibration contract before they can drive distance/offset fusion.

## Automated verification

The PR workflow builds and tests the Python tools on Windows and Linux, checks the pin-map header on Linux, and builds/tests/lints Android on Linux. It does not flash hardware, run physical measurements or regenerate fabrication exports.

The original thesis and previously delivered package ZIP remain local and are excluded from Git. The original Rev00 package files under `VW-MTC1/` remain available alongside the maintained source tools.
