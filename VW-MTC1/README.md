# Voltwyn VW-MTC1 MazeTrack Controller - Rev B prototype

Replacement controller board for the SEJ446 wire-maze ataxia assessment rig.

| Folder | Contents |
|---|---|
| `Docs/` | Datasheet PDF, design report PDF, schematic PDF, `Images/` (3D renders, layer plots, schematic PNGs) |
| `Hardware/KiCad/` | KiCad 10 project (open `VW-MTC1.kicad_pro`); custom symbol `Voltwyn.kicad_sym`, custom rules `VW-MTC1.kicad_dru` |
| `Hardware/Fabrication/` | Rev02 BOM for Rev B; older Rev A fabrication exports retained and identified in the folder README |
| `Hardware/Reports/` | KiCad ERC and DRC reports |
| `Simulation/` | LTspice netlists and `.asc` schematics, plots, `results.json`, `Simulation_Summary.md` (raw waveform files not included: re-run the `.cir` files in LTspice to regenerate) |
| `Firmware/` | Rev B ESP32-S3 pin map, portable decoder, acquisition application and pinned PlatformIO build |

Status: Rev B model and CAD checks are recorded in the
[Rev01 touch design note](../docs/20261021-Touch-Redesign-Rev01.md).
Native ERC has 0 errors and 1 warning. DRC has 0 errors, 0 unconnected items,
0 schematic mismatches and 206 warnings. The warnings remain for fabrication review.
The board has not been built or measured.
Research and education use only; not a registered medical device.

The original Rev00 PDFs and fabrication exports describe Rev A. The maintained
Python tools have a package build and hardware-free regression suite. See the
[repository build instructions](../README.md) and
[latest verification record](../docs/20261020-VW-MTC1-Verification-Rev01.md).
The Rev B touch design has passed 103,680 channel replays, including 5 ms gaps.
Its 10 µA contact criterion uses an explicit measurement network; raw contact
pulses exceed that value. Read the current definition and model limits in the
Rev01 note before using the results.

The Rev02 BOM is generated from the current schematic. Do not combine it with
the Rev A Gerbers or placement file. The standalone firmware produces an ESP32-S3
image but has not been run on hardware or integrated with the Android app.
