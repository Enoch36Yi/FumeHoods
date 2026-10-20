"""Independent checks of the routed Firefly_pcb2 board against the exported schematic netlist.

Read-only for CAD files; writes reports/pcb_verification.json. Run after the native checks:
    & $kc sch export netlist --format kicadxml --output reports\\netlist.xml Firefly_pcb2.kicad_sch
    & $kc sch erc --format json --severity-all --output reports\\erc.json Firefly_pcb2.kicad_sch
    & $kc pcb drc --schematic-parity --refill-zones --save-board --severity-all --format json --units mm --output reports\\drc.json Firefly_pcb2.kicad_pcb
    & $kp scripts\\verify_pcb.py
"""
from cad_common import *
import math, collections
import xml.etree.ElementTree as ET
import pcbnew as pcb

b = pcb.LoadBoard(str(ROOT/(NAME+'.kicad_pcb')))
xml = ET.parse(ROOT/'reports'/'netlist.xml')
def mmv(v): return pcb.ToMM(v)
def pt(v): return (mmv(v.x), mmv(v.y))

checks, errors, info = [], [], {}
def ck(ok, desc):
    checks.append(desc)
    if not ok: errors.append(desc)
    return ok

# ---------------------------------------------------------------- native reports
drc = json.loads((ROOT/'reports'/'drc.json').read_text())
erc = json.loads((ROOT/'reports'/'erc.json').read_text())
sev = collections.Counter(v['severity'] for v in drc.get('violations', []))
ck(len(drc.get('violations', [])) == 0, f"Native DRC (all severities): {len(drc.get('violations', []))} violations {dict(sev)}")
ck(len(drc.get('unconnected_items', [])) == 0, f"Native DRC unrouted connections: {len(drc.get('unconnected_items', []))}")
ck(len(drc.get('schematic_parity', [])) == 0, f"Native DRC schematic parity issues: {len(drc.get('schematic_parity', []))}")
ercv = [v for s in erc.get('sheets', []) for v in s.get('violations', [])]
ck(len(ercv) == 0, f'Native ERC (all severities): {len(ercv)} violations')
info['drc_source'] = {'kicad_version': drc.get('kicad_version'), 'date': drc.get('date'), 'severity_counts': dict(sev)}

# ---------------------------------------------------------------- outline
edges = [d for d in b.GetDrawings() if d.GetLayer() == pcb.Edge_Cuts]
edges += [g for f in b.GetFootprints() for g in f.GraphicalItems() if g.GetLayer() == pcb.Edge_Cuts]
ok = ck(len(edges) == 1 and edges[0].GetShape() == pcb.SHAPE_T_RECT, 'Edge.Cuts contains exactly one closed rectangle')
s, e = edges[0].GetStart(), edges[0].GetEnd()
w_nm, h_nm = abs(e.x-s.x), abs(e.y-s.y)
x0, y0, x1, y1 = min(pt(s)[0], pt(e)[0]), min(pt(s)[1], pt(e)[1]), max(pt(s)[0], pt(e)[0]), max(pt(s)[1], pt(e)[1])
W_NM, H_NM = round((OUTLINE_MM[2]-OUTLINE_MM[0])*1e6), round((OUTLINE_MM[3]-OUTLINE_MM[1])*1e6)
ck(w_nm == W_NM and h_nm == H_NM and (x0, y0) == OUTLINE_MM[:2],
   f'Outline is exactly {W_NM/1e6:.6f} x {H_NM/1e6:.6f} mm at ({OUTLINE_MM[0]}, {OUTLINE_MM[1]}) (measured {w_nm/1e6:.6f} x {h_nm/1e6:.6f} mm, 1 nm resolution)')
info['outline_mm'] = {'x0': x0, 'y0': y0, 'x1': x1, 'y1': y1, 'width': w_nm/1e6, 'height': h_nm/1e6, 'edge_line_width': mmv(edges[0].GetWidth())}
def within(bb, m=0.0): return x0+m <= mmv(bb.GetLeft()) and mmv(bb.GetRight()) <= x1-m and y0+m <= mmv(bb.GetTop()) and mmv(bb.GetBottom()) <= y1-m
ck(all(within(p.GetBoundingBox(), 0.3) for f in b.GetFootprints() for p in f.Pads()), 'Every pad lies at least 0.3 mm inside the outline')
ck(all(within(f.GetCourtyard(pcb.F_CrtYd).BBox()) for f in b.GetFootprints() if f.GetReference() != 'U1'),
   'Every courtyard except the module (whose courtyard includes the off-board antenna clearance) lies inside the outline')
u1 = b.FindFootprintByReference('U1')
inset = mmv(u1.GetPosition().y)-12.75-y0
ck(abs(inset-0.75) < 1e-6, f'ESP32-S3 module antenna end is {inset:.2f} mm inside the top board edge (antenna on the board edge)')

# ---------------------------------------------------------------- footprint / symbol parity
comps = {c.attrib['ref']: c for c in xml.findall('./components/comp')}
nodes = {}
netnodes = collections.defaultdict(list)
for n in xml.findall('./nets/net'):
    for node in n.findall('node'):
        nodes[(node.attrib['ref'], node.attrib['pin'])] = n.attrib['name']; netnodes[n.attrib['name']].append((node.attrib['ref'], node.attrib['pin']))
fps = {f.GetReference(): f for f in b.GetFootprints()}
schfps = {r: f for r, f in fps.items() if not f.IsBoardOnly()}
ck(set(schfps) == set(comps), f'Board schematic footprints equal netlist components ({len(schfps)} of {len(comps)})')
boardonly = sorted(r for r, f in fps.items() if f.IsBoardOnly())
ck(boardonly == sorted([f'H{i}' for i in range(1, 5)]+['FID1', 'FID2', 'FID3']), 'Board-only items are exactly 4 provisional corner supports and 3 fiducials')
for ref, c in sorted(comps.items()):
    f = schfps.get(ref)
    if not f: continue
    ck(f.GetFPIDAsString() == c.findtext('footprint'), f'{ref} footprint {f.GetFPIDAsString()} matches schematic')
    ck(f.GetValue() == c.findtext('value'), f'{ref} value {f.GetValue()} matches schematic')
    ck(f.GetPath().AsString() == '/'+c.findtext('tstamps'), f'{ref} is linked to its schematic symbol UUID')
    ck(f.GetLayer() == pcb.F_Cu, f'{ref} is on the top side')
    bom_excluded = any(p.attrib['name'] == 'exclude_from_bom' for p in c.findall('property'))
    ck(f.IsExcludedFromBOM() == bom_excluded, f'{ref} BOM inclusion matches schematic ({"excluded" if bom_excluded else "included"})')

# ---------------------------------------------------------------- pad-to-net parity (independent of DRC)
padcount = 0
for ref, f in sorted(schfps.items()):
    for p in f.Pads():
        if not p.GetNumber(): continue
        padcount += 1
        exp = nodes.get((ref, p.GetNumber()))
        ck(exp is not None and p.GetNetname() == exp, f'{ref}.{p.GetNumber()} copper net {p.GetNetname()} equals schematic {exp}')
for (ref, pin), net in sorted(nodes.items()):
    ck(any(p.GetNumber() == pin for p in schfps[ref].Pads()), f'Schematic pin {ref}.{pin} has a board pad')
info['pads_compared'] = padcount

# ---------------------------------------------------------------- no-connect pins stay isolated
items_by_net = collections.Counter(t.GetNetname() for t in b.GetTracks())
zone_nets = {z.GetNetname() for z in b.Zones() if not z.GetIsRuleArea()}
for ref, pins in [('U2', ['8']), ('U3', ['1', '7', '8', '11', '14'])]:
    for pin in pins:
        net = nodes[(ref, pin)]
        ck(net.startswith('unconnected-') and len(netnodes[net]) == 1 and items_by_net[net] == 0 and net not in zone_nets,
           f'{ref}.{pin} (manufacturer NC/DNC) has no track, via or zone')
single = [n for n, v in netnodes.items() if len(v) == 1]
ck(all(items_by_net[n] == 0 and n not in zone_nets for n in single), f'All {len(single)} single-pin unconnected nets carry no copper')

# ---------------------------------------------------------------- manufacturer-required bypass networks
def P(ref, num):
    ps = [p for p in fps[ref].Pads() if p.GetNumber() == str(num)]
    return pt(max(ps, key=lambda q: q.GetSizeX()*q.GetSizeY()).GetPosition())
def dist(a, c): return math.dist(P(*a), P(*c))
for net, want in [('/AMG_AVDD', {('U3', '10'), ('C10', '1')}), ('/AMG_AVCAP_RETURN', {('C10', '2'), ('R8', '1')}), ('/AMG_DVDD', {('U3', '12'), ('C11', '1')})]:
    ck(set(netnodes[net]) == want, f'{net} connects only {sorted(want)} (not tied to +3V3)')
ck(nodes[('R8', '2')] == '/GND' and nodes[('C11', '2')] == '/GND', 'AMG bypass returns: R8.2 and C11.2 on GND (pin10 -> 1 uF -> 20 ohm -> GND series order)')
ck(nodes[('U3', '13')] == '/+3V3' and nodes[('U3', '9')] == '/+3V3' and nodes[('U3', '5')] == '/GND', 'AMG VPP=VDD=+3V3, AD_SELECT=GND')
prox = {}
for a, c, lim in [(('C10', 1), ('U3', 10), 3.5), (('R8', 1), ('C10', 2), 2.5), (('C11', 1), ('U3', 12), 3.5),
                  (('C9', 1), ('U3', 9), 4.0), (('C8', 1), ('U3', 9), 6.0),
                  (('C7', 1), ('U2', 11), 3.0), (('C6', 1), ('U2', 1), 3.0),
                  (('C3', 1), ('U1', 2), 3.0), (('C2', 1), ('U1', 2), 5.5), (('C1', 1), ('U1', 3), 12.0)]:
    d = dist(a, c); prox[f'{a[0]}.{a[1]}-{c[0]}.{c[1]}'] = round(d, 3)
    ck(d <= lim, f'{a[0]} pad {a[1]} is {d:.2f} mm from {c[0]} pad {c[1]} (limit {lim} mm)')
info['bypass_pad_distances_mm'] = prox

# ---------------------------------------------------------------- antenna keepout, supports, vias
keep = [z for z in u1.Zones() if z.GetIsRuleArea()]
ck(len(keep) == 1, 'Module antenna keepout from the manufacturer footprint is present')
ko = keep[0].Outline().BBox()
kx0, ky0, kx1, ky1 = mmv(ko.GetLeft()), mmv(ko.GetTop()), mmv(ko.GetRight()), mmv(ko.GetBottom())
def in_ko(p, m=0.0): return kx0-m < p[0] < kx1+m and ky0-m < p[1] < ky1+m
bad = [t for t in b.GetTracks() if in_ko(pt(t.GetStart()), 0.3) or in_ko(pt(t.GetEnd()), 0.3)]
ck(not bad, 'No track or via inside the antenna keepout')
fillpts = 0
for z in b.Zones():
    if z.GetIsRuleArea(): continue
    for L in (pcb.F_Cu, pcb.B_Cu):
        if z.IsOnLayer(L) and z.HasFilledPolysForLayer(L):
            ps = z.GetFilledPolysList(L)
            for i in range(ps.OutlineCount()):
                o = ps.Outline(i); fillpts += sum(1 for j in range(o.PointCount()) if in_ko(pt(o.CPoint(j)), -0.001))
ck(fillpts == 0, 'No zone fill vertex inside the antenna keepout')
holes = [f for r, f in fps.items() if r.startswith('H')]
corners = sorted((x, y) for y in (y0+5.0, y1-5.0) for x in (x0+5.0, x1-5.0))
ck(len(holes) == 4 and sorted(pt(f.GetPosition()) for f in holes) == corners and
   all(len(list(f.Pads())) == 1 and next(iter(f.Pads())).GetAttribute() == pcb.PAD_ATTRIB_NPTH and
       abs(mmv(next(iter(f.Pads())).GetDrillSize().x)-3.2) < 1e-6 for f in holes), '4 provisional M3 supports are 3.2 mm NPTH, 5 mm in from each corner')
hko = [z for z in b.Zones() if z.GetIsRuleArea() and z.GetZoneName().endswith('_support_keepout')]
ck(len(hko) == 4, '4 copper keepouts (4 mm radius) surround the supports')
smd = [p for f in schfps.values() for p in f.Pads() if p.GetAttribute() == pcb.PAD_ATTRIB_SMD]
vip = [t for t in b.GetTracks() if t.GetClass() == 'PCB_VIA' and any(p.HitTest(t.GetPosition()) for p in smd)]
ck(not vip, 'No via inside an SMD land')

# ---------------------------------------------------------------- zones and connectivity
pours = [z for z in b.Zones() if not z.GetIsRuleArea()]
areas = {}
for z in pours:
    L = z.GetLayer(); a = 0.0
    if z.HasFilledPolysForLayer(L): a = z.GetFilledPolysList(L).Area()/1e12
    areas[z.GetZoneName() or z.GetLayerName()] = round(a, 1)
    ck(z.IsFilled() and a > 1000, f'Zone {z.GetZoneName()} on {z.GetLayerName()} is filled ({a:.0f} mm2)')
info['zone_fill_area_mm2'] = areas
b.BuildConnectivity()
unrouted = b.GetConnectivity().GetUnconnectedCount(False)
ck(unrouted == 0, f'pcbnew connectivity (independent of the DRC report) counts {unrouted} unrouted connections')

# ---------------------------------------------------------------- statistics recorded for review
length = collections.defaultdict(float); bottom = []
for t in b.GetTracks():
    if t.GetClass() != 'PCB_TRACK': continue
    l = mmv(t.GetLength()); length[t.GetNetname()] += l
    if t.GetLayer() == pcb.B_Cu: bottom.append((t.GetNetname(), round(l, 2)))
widths = sorted({round(mmv(t.GetWidth()), 3) for t in b.GetTracks() if t.GetClass() == 'PCB_TRACK'})
vias = [t for t in b.GetTracks() if t.GetClass() == 'PCB_VIA']
ck(min(widths) >= 0.2 and all(abs(mmv(v.GetWidth(pcb.F_Cu))-0.6) < 1e-6 and abs(mmv(v.GetDrill())-0.3) < 1e-6 for v in vias),
   'All tracks >= 0.2 mm; all vias 0.6 mm / 0.3 mm drill')
bcount = collections.Counter(n for n, _ in bottom)
info['bottom_layer_segments'] = {n: {'segments': bcount[n], 'length_mm': round(sum(l for m, l in bottom if m == n), 2)} for n in bcount}
info['track_widths_mm'] = widths
info['via_count'] = {'total': len(vias), 'gnd': sum(1 for v in vias if v.GetNetname() == '/GND')}
info['net_track_length_mm'] = {n: round(v, 1) for n, v in sorted(length.items())}
def centre(ref): return pt(fps[ref].GetPosition())
u3 = fps['U3']; ang = math.radians(u3.GetOrientationDegrees()); cx, cy = centre('U3')
lens = (cx+2.0*math.cos(ang), cy-2.0*math.sin(ang))
info['sensors_mm'] = {
    'U2_VL53L1X_centre': centre('U2'), 'U2_rotation_deg': fps['U2'].GetOrientationDegrees(),
    'U3_AMG8833_centre': centre('U3'), 'U3_rotation_deg': u3.GetOrientationDegrees(), 'U3_lens_centre': [round(v, 3) for v in lens],
    'U1_to_U2_centre_distance': round(math.dist(centre('U1'), centre('U2')), 1),
    'U1_to_U3_centre_distance': round(math.dist(centre('U1'), centre('U3')), 1),
    'BZ1_to_U3_centre_distance': round(math.dist(centre('BZ1'), centre('U3')), 1),
    'note': f'KiCad board coordinates (mm, +y down; outline top-left at {OUTLINE_MM[:2]}); provisional until enclosure/apertures are defined.'}
i2c = length['/I2C_SDA'], length['/I2C_SCL']
info['i2c_estimate'] = {'routed_length_mm': {'SDA': round(i2c[0], 1), 'SCL': round(i2c[1], 1)},
                        'trace_capacitance_pF_assumed_0.5_to_1.2_pF_per_cm': [round(min(i2c)/10*0.5, 1), round(max(i2c)/10*1.2, 1)],
                        'note': 'Order-of-magnitude trace estimate only; add device/test-point capacitance and measure rise time on hardware.'}

report = {'status': 'PASS' if not errors else 'FAIL', 'checks_executed': len(checks), 'errors': errors, 'info': info, 'checks': checks,
          'scope': 'Digital board/netlist checks only. Does not establish mechanical fit, optics, thermal behaviour, RF, assembly yield or hardware function.'}
(ROOT/'reports'/'pcb_verification.json').write_text(json.dumps(report, indent=2))
print(report['status'], len(checks), 'checks;', len(errors), 'errors')
if errors: print('\n'.join(errors)); raise SystemExit(1)
