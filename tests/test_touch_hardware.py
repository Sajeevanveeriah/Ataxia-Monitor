import io
import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from vw_mtc1.touch_hardware import check_touch_hardware

NETLIST = Path(__file__).resolve().parents[1] / (
    "VW-MTC1/Hardware/Reports/20261021-VW-MTC1-Netlist-Rev01.xml")


def test_native_kicad_touch_topology():
    assert check_touch_hardware(NETLIST)["maze_inputs"] == 3


def test_export_corresponds_to_current_schematic_sources():
    root = Path(__file__).resolve().parents[1]
    receipt = json.loads(NETLIST.with_suffix(".json").read_text())
    for relative, digest in receipt["source_sha256"].items():
        assert hashlib.sha256((root / relative).read_bytes()).hexdigest() == digest, relative


def test_esd_or_capacitor_on_exposed_wire_fails():
    root = ET.parse(NETLIST).getroot()
    net = next(n for n in root.find("nets") if n.attrib["name"] == "MAZE_WIRE")
    ET.SubElement(net, "node", ref="C34", pin="1")
    with pytest.raises(ValueError, match="bypasses the limiting resistor"):
        check_touch_hardware(io.BytesIO(ET.tostring(root)))


def test_original_ten_kilohm_resistor_fails_current_boundary():
    root = ET.parse(NETLIST).getroot()
    component = next(c for c in root.find("components") if c.attrib["ref"] == "R51")
    component.find("value").text = "10k"
    with pytest.raises(ValueError, match="limiting resistance changed"):
        check_touch_hardware(io.BytesIO(ET.tostring(root)))
