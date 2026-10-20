"""Convert a fresh KiCad XML netlist to an assembly BOM, preserving DNP flags."""
import argparse
from pathlib import Path

from vw_mtc1.bom import export_bom

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("netlist", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    rows = export_bom(args.netlist, args.output)
    print(f"Exported {len(rows)} BOM groups, {sum(row['Qty'] for row in rows)} components: {args.output}")
