# Voltwyn VW-MTC1 MazeTrack Controller - Rev A (Rev00 package, 19 October 2026)

Replacement controller board for the SEJ446 wire-maze ataxia assessment rig.

| Folder | Contents |
|---|---|
| `Docs/` | Datasheet PDF, design report PDF, schematic PDF, `Images/` (3D renders, layer plots, schematic PNGs) |
| `Hardware/KiCad/` | KiCad 10 project (open `VW-MTC1.kicad_pro`); custom symbol `Voltwyn.kicad_sym`, custom rules `VW-MTC1.kicad_dru` |
| `Hardware/Fabrication/` | Gerbers + drill (ZIP), BOM (CSV), pick-and-place (CSV), STEP 3D model |
| `Hardware/Reports/` | KiCad ERC and DRC reports |
| `Simulation/` | LTspice netlists and `.asc` schematics, plots, `results.json`, `Simulation_Summary.md` (raw waveform files not included: re-run the `.cir` files in LTspice to regenerate) |
| `Firmware/` | `vw_mtc1_pins.h` ESP32-S3 pin map |

Status: design complete, ERC 0 errors, DRC 0 errors / 0 unconnected / 0 schematic-parity issues.
Not yet built or measured. See the open items in section 10 of the design report before ordering.
Research and education use only; not a registered medical device.
