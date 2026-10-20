import csv
import io

import pytest

from vw_mtc1.bom import bom_rows, export_bom


def netlist(refs):
    components = []
    for reference, properties in refs:
        components.append(f"""<comp ref="{reference}">
          <value>100k</value><footprint>Resistor_SMD:R_0603_1608Metric</footprint>
          <description>Resistor</description>
          <fields><field name="MPN">RC0603FR-07100kL</field><field name="Manufacturer">Yageo</field></fields>
          {properties}</comp>""")
    return io.StringIO("<export><components>" + "".join(components) + "</components></export>")


def test_same_part_dnp_and_fitted_must_be_separate_groups():
    # The delivered Rev00 CSV incorrectly marked this entire six-part group DNP.
    rows = bom_rows(netlist([(r, '<property name="dnp"/>' if r == "R16" else "")
                            for r in ["R8", "R9", "R16", "R33", "R50", "R59"]]))
    assert len(rows) == 2
    fitted = next(row for row in rows if not row["DNP"])
    dnp = next(row for row in rows if row["DNP"])
    assert fitted["Designator"] == "R8,R9,R33,R50,R59"
    assert fitted["Qty"] == 5
    assert dnp["Designator"] == "R16" and dnp["Qty"] == 1


def test_kicad_exclude_from_bom_is_respected():
    rows = bom_rows(netlist([("R8", ""), ("TP1", '<property name="exclude_from_bom"/>')]))
    assert len(rows) == 1 and rows[0]["Designator"] == "R8"


def test_duplicate_references_fail_instead_of_double_counting():
    with pytest.raises(ValueError, match="Duplicate"):
        bom_rows(netlist([("R8", ""), ("R8", "")]))


def test_wrong_xml_document_is_rejected():
    with pytest.raises(ValueError, match="KiCad"):
        bom_rows(io.StringIO("<unrelated/>"))


def test_csv_round_trip_keeps_quantity_and_fit_status(tmp_path):
    target = tmp_path / "bom.csv"
    export_bom(netlist([("R8", ""), ("R16", '<property name="dnp"/>')]), target)
    with target.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert [(row["Designator"], row["Qty"], row["DNP"]) for row in rows] == [
        ("R8", "1", ""), ("R16", "1", "DNP")]
