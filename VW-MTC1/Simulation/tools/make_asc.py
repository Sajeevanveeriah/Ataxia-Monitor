"""make_asc.py - generate LTspice .asc schematics for SIM01a and SIM04a.

Parts are placed on a grid; every pin gets a net-label FLAG at its exact
coordinates (LTspice joins a flag to a pin at the same point), plus a short
wire stub so the labels sit clear of the bodies. The schematics are checked
by running them in LTspice batch mode and comparing .meas results with the
.cir versions.
"""
from common import LT
import os

# pin offsets for R0 orientation (from the LTspice .asy files)
PINS = {
    'res': [(16, 16), (16, 96)],
    'cap': [(16, 0), (16, 64)],
    'ind': [(16, 16), (16, 96)],
    'voltage': [(0, 16), (0, 96)],
    'current': [(0, 0), (0, 80)],
    'PowerProducts\\LTC3536': {'Rt': (-128, 48), 'SGND': (-64, 208), 'Mode': (-128, 144), 'SW1': (-64, -208),
                               'SW2': (48, -208), 'Vout': (112, -144), 'Vin': (-128, -144), 'SHDN': (-128, -48),
                               'FB': (112, 48), 'Vc': (112, 144), 'PGND': (48, 208)},
    'OpAmps\\UniversalOpAmp2': {'In+': (-32, 16), 'In-': (-32, -16), 'V+': (0, -32), 'V-': (0, 32), 'OUT': (32, 0)},
}


class Asc:
    def __init__(self, w=2400, h=1400):
        self.lines = ['Version 4', 'SHEET 1 %d %d' % (w, h)]

    def flag(self, x, y, net):
        self.lines.append('FLAG %d %d %s' % (x, y, net))

    def wire(self, x1, y1, x2, y2):
        self.lines.append('WIRE %d %d %d %d' % (x1, y1, x2, y2))

    def two(self, sym, name, x, y, value, nets, spiceline=None):
        self.lines.append('SYMBOL %s %d %d R0' % (sym, x, y))
        self.lines.append('SYMATTR InstName %s' % name)
        self.lines.append('SYMATTR Value %s' % value)
        if spiceline:
            self.lines.append('SYMATTR SpiceLine %s' % spiceline)
        (ax, ay), (bx, by) = PINS[sym]
        # stubs: up from pin A, down from pin B
        self.wire(x + ax, y + ay, x + ax, y + ay - 16)
        self.flag(x + ax, y + ay - 16, nets[0])
        self.wire(x + bx, y + by, x + bx, y + by + 16)
        self.flag(x + bx, y + by + 16, nets[1])

    def multi(self, sym, name, x, y, pinnets, attrs):
        self.lines.append('SYMBOL %s %d %d R0' % (sym, x, y))
        self.lines.append('SYMATTR InstName %s' % name)
        for a in attrs:
            self.lines.append('SYMATTR %s' % a)
        for pin, net in pinnets.items():
            px, py = PINS[sym][pin]
            self.flag(x + px, y + py, net)

    def text(self, x, y, s, directive=False, size=2):
        self.lines.append('TEXT %d %d Left %d %s%s' % (x, y, size, '!' if directive else ';', s))

    def save(self, path):
        with open(path, 'w', newline='\r\n') as f:
            f.write('\n'.join(self.lines) + '\n')
        print('wrote', path)


# ---------------- SIM01a ----------------
a = Asc()
a.text(-600, -560, 'SIM01a VW-MTC1 +3V3 buck-boost start-up (schematic version of sim01a_buckboost_startup.cir)', size=3)
a.text(-600, -520, 'U4 LTC3536EMSE, L1 4.7 uH XFL4020-472 (24 mohm), COUT C30/C31 2 x 22 uF modelled 10 uF effective each (DC bias)')
a.text(-600, -490, 'RT and SHDN tied to VIN (1.2 MHz), MODE = GND (PWM). VIN 3.7 V via 50 mohm, load 11 ohm (300 mA)')
a.two('voltage', 'Vbat', -560, -100, '3.7', ['vsrc', '0'])
a.two('res', 'Rsrc', -440, -100, '50m', ['vsrc', 'vin'])
a.two('cap', 'C28', -320, -100, '10u', ['vin', '0'], 'Rser=3m Lser=0.5n')
a.two('cap', 'C29', -220, -100, '100n', ['vin', '0'], 'Rser=10m')
a.multi('PowerProducts\\LTC3536', 'U4', 160, 100,
        {'Rt': 'vin', 'SGND': '0', 'Mode': '0', 'SW1': 'sw1', 'SW2': 'sw2', 'Vout': 'out', 'Vin': 'vin',
         'SHDN': 'vin', 'FB': 'fb', 'Vc': 'vc', 'PGND': '0'}, ['Value LTC3536'])
a.two('ind', 'L1', 120, -260, '4.7u', ['sw1', 'sw2'], 'Rser=24m')
a.two('cap', 'C30', 480, -100, '10u', ['out', '0'], 'Rser=3m Lser=0.5n')
a.two('cap', 'C31', 580, -100, '10u', ['out', '0'], 'Rser=3m Lser=0.5n')
a.two('res', 'R30', 700, -100, '1Meg', ['out', 'fb'])
a.two('cap', 'C32', 800, -84, '47p', ['out', 'fb'], 'Rser=6.49k')
a.two('res', 'R31', 700, 100, '221k', ['fb', '0'])
a.two('cap', 'C33', 800, 116, '220p', ['fb', 'vc'], 'Rser=49.9k')
a.two('res', 'Rload', 920, -100, '11', ['out', '0'])
a.text(-600, 420, '.tran 0 3m 0 startup', directive=True)
a.text(-600, 450, '.meas TRAN vfinal AVG V(out) FROM 2.5m TO 3m', directive=True)
a.text(-600, 480, '.meas TRAN t90 WHEN V(out)=2.9835 RISE=1', directive=True)
a.save(os.path.join(LT, 'sim01a_buckboost_startup_sch.asc'))

# ---------------- SIM04a ----------------
a = Asc()
a.text(-400, -400, 'SIM04a VW-MTC1 Hall front end, one channel (schematic version of sim04a_hall_afe_ac.cir)', size=3)
a.text(-400, -360, 'SS49E modelled as 1.65 V + AC 1 V behind 100 ohm. R50 1 M pull-down, Sallen-Key LPF R51 = R52 = 10 k, C51 100 nF, C52 47 nF')
a.text(-400, -330, 'U6 = MCP6004 class via UniversalOpAmp2 (GBW 1 MHz, 0.6 V/us, Avol 4e5, rail-to-rail). Expected fc 232 Hz, Q 0.73')
a.two('voltage', 'Vs', -360, -100, 'DC 1.65 AC 1', ['hs', '0'])
a.two('res', 'Rsens', -240, -100, '100', ['hs', 'hall'])
a.two('res', 'R50', -120, -100, '1Meg', ['hall', '0'])
a.two('res', 'R51', 0, -100, '10k', ['hall', 'n1'])
a.two('res', 'R52', 120, -100, '10k', ['n1', 'n2'])
a.two('cap', 'C51', 240, -84, '100n', ['n1', 'adc'])
a.two('cap', 'C52', 360, -84, '47n', ['n2', '0'])
a.multi('OpAmps\\UniversalOpAmp2', 'U6', 560, 0, {'In+': 'n2', 'In-': 'adc', 'V+': 'vdd', 'V-': '0', 'OUT': 'adc'},
        ['Value2 Avol=4e5 GBW=1Meg Slew=0.6Meg', 'SpiceLine Ilimit=15m Rail=25m Vos=0',
         'SpiceLine2 En=0 Enk=0 In=0 Ink=0 Rin=500Meg'])
a.two('voltage', 'Vdd', 760, -100, '3.3', ['vdd', '0'])
a.text(-400, 200, '.ac dec 200 1 10Meg', directive=True)
a.text(-400, 230, '.meas AC f3db WHEN mag(V(adc))=0.70711 FALL=1', directive=True)
a.text(-400, 260, '.meas AC g1k FIND mag(V(adc)) AT 1k', directive=True)
a.save(os.path.join(LT, 'sim04a_hall_afe_sch.asc'))
