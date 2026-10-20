"""Export a grouped BOM from KiCad's XML netlist without losing fit status."""
import csv
from pathlib import Path
import re
import xml.etree.ElementTree as ET

COLUMNS = ["Designator", "Value", "Footprint", "MPN", "Manufacturer", "Description", "Qty", "DNP"]


def reference_key(reference):
    return [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", reference)]


def bom_rows(netlist):
    root = ET.parse(netlist).getroot()
    components = root.find("components")
    if root.tag != "export" or components is None:
        raise ValueError("Expected a KiCad XML netlist with components")
    groups, seen = {}, set()
    for component in components.findall("comp"):
        reference = component.attrib["ref"]
        if reference in seen:
            raise ValueError(f"Duplicate component reference: {reference}")
        seen.add(reference)
        properties = {p.attrib["name"]: p.attrib.get("value", "")
                      for p in component.findall("property")}
        if "exclude_from_bom" in properties:
            continue
        fields = {f.attrib["name"]: f.text or "" for f in component.findall("./fields/field")}
        fitted = "dnp" not in properties
        key = (component.findtext("value", ""), component.findtext("footprint", ""),
               fields.get("MPN", ""), fields.get("Manufacturer", ""), fitted)
        group = groups.setdefault(key, {"references": [], "descriptions": set()})
        group["references"].append(reference)
        description = component.findtext("description", "")
        if description:
            group["descriptions"].add(description)
    rows = []
    for (value, footprint, mpn, manufacturer, fitted), group in groups.items():
        references = sorted(group["references"], key=reference_key)
        rows.append(dict(zip(COLUMNS, [",".join(references), value, footprint, mpn, manufacturer,
                    "; ".join(sorted(group["descriptions"])), len(references), "" if fitted else "DNP"])))
    return sorted(rows, key=lambda row: reference_key(row["Designator"].split(",")[0]))


def export_bom(netlist, destination):
    rows = bom_rows(netlist)
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=COLUMNS, quoting=csv.QUOTE_ALL, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return rows
