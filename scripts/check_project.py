"""Build generated text/schematic outputs in build/, preserving source evidence."""
import compileall
import os
from pathlib import Path
import shutil
import subprocess
import sys


def main():
    root = Path(__file__).resolve().parents[1]
    source = root / "VW-MTC1" / "Simulation"
    output = root / "build" / "vw-mtc1"
    if not compileall.compile_dir(source / "tools", quiet=1):
        return 1
    output.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source / "LTspice", output / "LTspice", dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("*.raw"))
    shutil.copy2(source / "results.json", output / "results.json")
    environment = dict(os.environ, VW_MTC1_SIMULATION_DIR=str(output))
    for module in ("make_asc", "make_summary"):
        subprocess.run([sys.executable, "-m", "vw_mtc1." + module], env=environment, check=True)
    print(f"Generated schematics and summary: {output}")
    print("The summary uses stored simulation evidence. No simulator or device was run.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
