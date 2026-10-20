"""Safety-relevant Rev B topology checks against a native KiCad XML export."""
import xml.etree.ElementTree as ET


def check_touch_hardware(netlist):
    root = ET.parse(netlist).getroot()
    components = {c.attrib["ref"]: c for c in root.findall("./components/comp")}
    nets = {n.attrib["name"]: {(p.attrib["ref"], p.attrib["pin"]) for p in n.findall("node")}
            for n in root.findall("./nets/net")}

    def require(condition, message):
        if not condition:
            raise ValueError(message)

    for raw, sense, resistor, capacitor, pin, esd in (
        ("MAZE_WIRE", "TCH_WIRE", "R51", "C34", "1", "1"),
        ("MAZE_START", "TCH_START", "R53", "C35", "2", "2"),
        ("MAZE_FINISH", "TCH_FIN", "R55", "C36", "3", "4"),
    ):
        require(nets[raw] == {("J4", pin), (resistor, "1")},
                f"{raw}: capacitor, protection or alternate path bypasses the limiting resistor")
        require((resistor, "2") in nets[sense] and (capacitor, "1") in nets[sense]
                and ("U10", esd) in nets[sense], f"{sense}: protection/filter is on the wrong side")
        require(components[resistor].findtext("value") == "1.15M",
                f"{resistor}: limiting resistance changed")
        require(components[capacitor].findtext("value") == "270pF C0G",
                f"{capacitor}: node capacitance changed")

    for net, output, feedback, adc_pin in (
        ("TCH_ADC0", "1", "2", "1"), ("TCH_ADC1", "7", "6", "2"),
        ("TCH_ADC2", "8", "9", "3"), ("TCH_ADC_REF", "14", "13", "4"),
    ):
        require(nets[net] == {("U11", output), ("U11", feedback), ("U13", adc_pin)},
                f"{net}: quad buffer feedback or ADC channel map changed")
    require(all(("U13", str(p)) in nets["GND"] for p in (5, 6, 7, 8, 9, 13, 14)),
            "Unused ADC inputs, COM and grounds must be tied to GND")
    require(all(("U13", str(p)) in nets["+3V3_TOUCH"] for p in (10, 12, 20)),
            "ADC supply filter bypassed")
    require(nets["+2V5_TOUCH"] == {("U13", "11"), ("U14", "2"), ("C44", "1")},
            "ADC reference or reference reservoir bypassed")
    require(("U14", "1") in nets["+3V3_TOUCH"] and ("U14", "3") in nets["GND"],
            "REF3325 SOT-23 pin map mismatch")
    for net, pin in (("ADC_SCK", "19"), ("ADC_MOSI", "17"), ("ADC_MISO", "15"),
                     ("TOUCH_CS", "18"), ("TOUCH_BUSY", "16")):
        require(("U13", pin) in nets[net], f"{net}: ADC digital pin mismatch")
    for ref, value in (("R70", "220R 0.05%"), ("R71", "100R 0.05%"), ("R74", "10R")):
        require(components[ref].findtext("value") == value, f"{ref}: drive/filter value changed")
    return {"maze_inputs": 3, "buffer_channels": 4, "adc_bits": 16}
