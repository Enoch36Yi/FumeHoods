"""Build the placed and routed Firefly_pcb2 board from the exported schematic netlist.

Run with KiCad Python from SashSense_Reconstruction after exporting reports/netlist.xml:
    & $kp scripts\\layout_pcb.py --overwrite
Writes Firefly_pcb2.kicad_pcb only. Placement and every route are explicit below so that
they can be reviewed against the schematic; nothing here is autorouted.
"""
from cad_common import *
import sys, math
import xml.etree.ElementTree as ET
import pcbnew as pcb

BOARD_FILE = ROOT/(NAME+'.kicad_pcb')
FPDIR = ROOT/'libraries'/'SashSense.pretty'
if BOARD_FILE.exists() and '--overwrite' not in sys.argv:
    raise SystemExit(BOARD_FILE.name+' exists; pass --overwrite to regenerate it (manual board edits would be replaced).')

# Outline trimmed to the populated region (160 x 60 mm); the module antenna stays on the top edge.
OUTLINE = OUTLINE_MM
F, B = pcb.F_Cu, pcb.B_Cu
SIG, VIA_D, VIA_H = 0.2, 0.6, 0.3

def mm(v): return pcb.FromMM(v)
def xy(x, y): return pcb.VECTOR2I(mm(x), mm(y))

b = pcb.NewBoard(str(BOARD_FILE)) if hasattr(pcb, 'NewBoard') else pcb.BOARD()
b.SetCopperLayerCount(2)
ds = b.GetDesignSettings()
ds.SetBoardThickness(mm(1.6))
ds.SetAuxOrigin(xy(OUTLINE[0], OUTLINE[3]))   # placement/drill origin: bottom-left board corner
ds.SetGridOrigin(xy(OUTLINE[0], OUTLINE[3]))
tb = b.GetTitleBlock()
W_MM, H_MM = OUTLINE[2]-OUTLINE[0], OUTLINE[3]-OUTLINE[1]
tb.SetTitle('Firefly_pcb2 - SashSense sensor node'); tb.SetRevision('P2'); tb.SetDate('2026-10-20')
tb.SetCompany('SashSense'); tb.SetComment(0, 'PROVISIONAL - NOT RELEASED FOR FABRICATION')
tb.SetComment(1, f'{W_MM:.2f} x {H_MM:.2f} mm, 2 layers, 1.6 mm nominal; mounting/enclosure/host interface unresolved')

# ---------------------------------------------------------------- netlist (single source of truth)
xml = ET.parse(ROOT/'reports'/'netlist.xml')
nets, nodes = {}, {}
for n in xml.findall('./nets/net'):
    item = pcb.NETINFO_ITEM(b, n.attrib['name']); b.Add(item); nets[n.attrib['name']] = item
    for node in n.findall('node'): nodes[(node.attrib['ref'], node.attrib['pin'])] = n.attrib['name']
comps = {}
for c in xml.findall('./components/comp'):
    props = {p.attrib['name']: p.attrib.get('value', '') for p in c.findall('property')}
    fields = {f.attrib['name']: (f.text or '') for f in c.findall('./fields/field')}
    comps[c.attrib['ref']] = dict(value=c.findtext('value'), fp=c.findtext('footprint'), uuid=c.findtext('tstamps'),
                                  fields=fields, sheetname=props.get('Sheetname', ''), sheetfile=props.get('Sheetfile', ''),
                                  in_bom='exclude_from_bom' not in props)

# ---------------------------------------------------------------- placement (mm, degrees)
# Processor at the top edge so its PCB antenna sits on the board edge with the footprint keepout.
# Thermal array about 90 mm from the module; ToF between them on the shared 100 kHz bus.
PLACE = {
    'U1': (80.0, 38.5, 0),
    # module supply / reset (west)
    'C3': (69.0, 34.07, 90), 'C2': (66.6, 33.95, 90), 'R1': (63.8, 35.125, 270), 'C1': (62.5, 40.2, 0),
    'SW1': (62.9, 46.0, 90), 'J1': (44.0, 34.0, 90), 'C4': (51.5, 31.6, 90), 'C5': (54.5, 31.6, 90),
    'TP1': (58.5, 34.6, 0), 'TP2': (48.0, 30.0, 0),
    # beeper (south-west)
    'TP8': (50.5, 45.0, 0), 'R9': (50.5, 52.5, 270), 'R10': (55.0, 53.0, 90), 'BZ1': (52.0, 62.0, 0),
    'Q1': (61.5, 58.5, 0), 'R11': (63.6, 66.0, 90),
    # service pads / boot (east of module)
    'J2': (93.0, 45.9, 0), 'SW2': (94.0, 51.65, 0), 'R2': (104.43, 49.2, 180),
    # bus test points
    'TP3': (120.0, 46.7, 0), 'TP4': (124.0, 48.0, 0), 'TP6': (128.0, 51.2, 0), 'TP5': (131.0, 52.8, 0), 'TP7': (126.0, 59.0, 0),
    # VL53L1X and local parts
    'U2': (140.0, 52.0, 180), 'R6': (144.4, 49.0, 90), 'C7': (144.6, 52.6, 0), 'C6': (144.6, 54.4, 0),
    'R3': (140.5, 55.7, 180), 'R4': (140.5, 57.4, 180),
    # AMG8833 and its manufacturer-required bypass network
    'U3': (172.0, 55.0, 180), 'C10': (170.73, 61.4, 270), 'R8': (170.73, 64.5, 270), 'C11': (173.27, 61.4, 270),
    'C9': (167.8, 61.0, 180), 'C8': (167.6, 63.6, 180), 'R7': (164.4, 52.0, 90), 'R5': (179.6, 52.0, 90),
}
missing = set(comps) ^ set(PLACE)
if missing: raise SystemExit('Placement/netlist mismatch: '+', '.join(sorted(missing)))

fps = {}
for ref, c in sorted(comps.items()):
    lib, name = c['fp'].split(':')
    f = pcb.FootprintLoad(str(FPDIR), name)
    if f is None: raise SystemExit('Missing local footprint '+c['fp'])
    f.SetFPID(pcb.LIB_ID(lib, name)); f.SetReference(ref); f.SetValue(c['value'])
    for k in ('MPN', 'Manufacturer', 'Datasheet', 'Description'):
        if k in c['fields']:
            f.SetField(k, c['fields'][k])
            if k in ('MPN', 'Manufacturer'): f.GetField(k).SetVisible(False)
    f.SetPath(pcb.KIID_PATH('/'+c['uuid']))
    f.SetSheetname(c['sheetname']); f.SetSheetfile(c['sheetfile'])
    if not c['in_bom']: f.SetExcludedFromBOM(True)
    x, y, rot = PLACE[ref]
    f.SetPosition(xy(x, y)); f.SetOrientationDegrees(rot)
    b.Add(f); fps[ref] = f
    for p in f.Pads():
        net = nodes.get((ref, p.GetNumber()))
        if net: p.SetNet(nets[net])
        elif p.GetNumber(): raise SystemExit(f'{ref}.{p.GetNumber()} absent from netlist')

fps['J1'].Value().SetPosition(xy(44.0, 31.6))   # keep its assembly-drawing text inside the outline

def pad(ref, num):
    """Centre of the largest copper pad with this number (duplicate numbers share one land)."""
    ps = [p for p in fps[ref].Pads() if p.GetNumber() == str(num)]
    p = max(ps, key=lambda q: q.GetSizeX()*q.GetSizeY())
    return (round(pcb.ToMM(p.GetPosition().x), 4), round(pcb.ToMM(p.GetPosition().y), 4))

def padnet(ref, num): return nodes[(ref, str(num))]

# ---------------------------------------------------------------- copper helpers
def track(net, layer, w, pts):
    pts = [pad(*p) if isinstance(p[0], str) else p for p in pts]
    for a, c in zip(pts, pts[1:]):
        if math.dist(a, c) < 1e-6: continue
        t = pcb.PCB_TRACK(b); t.SetStart(xy(*a)); t.SetEnd(xy(*c)); t.SetWidth(mm(w)); t.SetLayer(layer)
        t.SetNet(nets[net]); b.Add(t)

def via(net, x, y):
    v = pcb.PCB_VIA(b); v.SetPosition(xy(x, y)); v.SetWidth(mm(VIA_D)); v.SetDrill(mm(VIA_H))
    v.SetViaType(pcb.VIATYPE_THROUGH); v.SetLayerPair(F, B); v.SetNet(nets[net]); b.Add(v)

def chamfer(pts, c=0.6):
    """Replace orthogonal corners with 45-degree corners of leg length c."""
    out = [pts[0]]
    for a, m, z in zip(pts, pts[1:], pts[2:]):
        u = (m[0]-a[0], m[1]-a[1]); v = (z[0]-m[0], z[1]-m[1])
        lu, lv = math.hypot(*u), math.hypot(*v)
        if abs(u[0]*v[1]-u[1]*v[0]) < 1e-9 or min(lu, lv) < 2*c:
            out.append(m); continue
        out += [(m[0]-u[0]/lu*c, m[1]-u[1]/lu*c), (m[0]+v[0]/lv*c, m[1]+v[1]/lv*c)]
    return out + [pts[-1]]

def jumper(net, a, c):
    """Short bottom-layer crossing between two vias."""
    via(net, *a); via(net, *c); track(net, B, SIG, [a, c])

GND, V33 = '/GND', '/+3V3'

# ---------------------------------------------------------------- module supply, reset, beeper (west)
track(GND, F, 0.4, [pad('U1', 1), pad('C3', 2), (67.925, 33.1), pad('C2', 2)]); via(GND, 67.925, 33.1)
track(V33, F, 0.6, [pad('U1', 2), (69.0, 34.6), (66.6, 34.6), (63.8, 34.6)])
track(V33, F, 0.8, [(63.8, 34.6), (58.5, 34.6), (54.5, 34.6), (51.5, 34.6), (44.0, 34.6)])
for ref in ('C4', 'C5'):
    x, y = pad(ref, 1); track(V33, F, 0.6, [(x, 34.6), (x, y)])
    gx, gy = pad(ref, 2); via(GND, gx, 28.6); track(GND, F, 0.6, [(gx, gy), (gx, 28.6)])
# EN: R1 pull-up beside the pin, then cross under BEEP_PWM so EN can run inside the beeper branch.
track('/EN', F, 0.25, [pad('U1', 3), (63.8, 35.78), (61.0, 35.78)])
jumper('/EN', (61.0, 35.78), (61.0, 38.6))
en_path = chamfer([(61.0, 38.6), (61.0, 40.2), pad('SW1', 1), (61.0, 49.15), (61.0, 53.5), (86.5, 53.5), (88.5, 55.5), (100.62, 55.5), pad('J2', 4)])
track('/EN', F, 0.25, en_path)
track('/EN', F, 0.25, [(61.0, 40.2), pad('C1', 1)])
cx, cy = pad('C1', 2); track(GND, F, 0.4, [(cx, cy), (64.4, cy)]); via(GND, 64.4, cy)
# both switch terminals of each pair are tied in copper as well as inside the switch
track(GND, F, 0.4, [(64.8, 42.85), (64.8, 49.15)]); via(GND, 64.8, 46.0)
track('/BEEP_PWM', F, 0.25, chamfer([pad('U1', 4), (50.5, 37.05), pad('TP8', 1), pad('R9', 1)]))
track('/BEEP_BASE', F, 0.25, chamfer([pad('R9', 2), (50.5, 54.6), (55.0, 54.6), (59.3, 54.6), (59.3, 57.55), pad('Q1', 1)]))
track('/BEEP_BASE', F, 0.25, [(55.0, 54.6), pad('R10', 1)])
gx, gy = pad('R10', 2); track(GND, F, 0.3, [(gx, gy), (gx, 51.0)]); via(GND, gx, 51.0)
gx, gy = pad('Q1', 2); track(GND, F, 0.4, [(gx, gy), (59.4, 60.7)]); via(GND, 59.4, 60.7)
track('/BEEP_LOW', F, 0.3, [pad('Q1', 3), (63.6, 58.5), (63.6, 62.0), pad('R11', 2)])
track('/BEEP_LOW', F, 0.3, [(63.6, 62.0), pad('BZ1', 2)])
# 3.3 V trunk from J1 round the south of the electronics to the sensors
track(V33, F, 0.6, [(44.0, 34.6), (44.0, 75.0)])
track(V33, F, 0.5, [(44.0, 75.0), (63.6, 75.0), (105.7, 75.0), (143.4, 75.0), (172.0, 75.0)])
track(V33, F, 0.4, [(44.0, 62.0), pad('BZ1', 1)])
track(V33, F, 0.3, [pad('R11', 1), (63.6, 75.0)])

# ---------------------------------------------------------------- service pads, boot, UART (east of module)
track(GND, F, 0.4, [pad('U1', 40), (90.4, 33.24)]); via(GND, 90.4, 33.24)
# UART pair drops to short bottom traces that land directly on J2's plated pads.
track('/UART_TX', F, SIG, [pad('U1', 37), (93.6, 37.05)]); via('/UART_TX', 93.6, 37.05)
track('/UART_TX', B, SIG, [(93.6, 37.05), (93.6, 38.5), (98.08, 42.98), pad('J2', 3)])
track('/UART_RX', F, SIG, [pad('U1', 36), (91.2, 38.32)]); via('/UART_RX', 91.2, 38.32)
track('/UART_RX', B, SIG, [(91.2, 38.32), (91.2, 41.56), pad('J2', 2)])
track('/BOOT', F, 0.25, [pad('U1', 27), (90.05, 49.75), pad('SW2', 1), (97.15, 49.75)])
track('/BOOT', F, 0.25, chamfer([(90.05, 49.75), (90.05, 43.9), (103.16, 43.9), pad('J2', 5)], 0.5))
track('/BOOT', F, 0.25, [pad('R2', 2), (103.16, 48.75), pad('J2', 5)])
track(GND, F, 0.4, [(90.85, 53.55), (97.15, 53.55)]); via(GND, 94.0, 53.55)
track(V33, F, 0.4, [(105.7, 75.0), (105.7, 49.2), pad('J2', 6)])
track(V33, F, 0.3, [pad('R2', 1), (105.7, 49.2)])

# ---------------------------------------------------------------- sensor bus (module -> ToF -> AMG)
SDA_Y, SCL_Y, AINT_Y = 46.7, 48.0, 49.3
track('/I2C_SDA', F, SIG, chamfer([pad('U1', 39), (114.0, 34.51), (114.0, SDA_Y), pad('TP3', 1), (140.0, SDA_Y),
                                   (174.54, SDA_Y), (179.6, SDA_Y), pad('R5', 2)]))
track('/I2C_SDA', F, SIG, [(174.54, SDA_Y), pad('U3', 2)])
track('/I2C_SCL', F, SIG, chamfer([pad('U1', 38), (112.5, 35.78), (112.5, SCL_Y), pad('TP4', 1), (140.8, SCL_Y),
                                   (144.4, SCL_Y), (173.27, SCL_Y), pad('U3', 3)]))
track('/I2C_SCL', F, SIG, [(140.8, SCL_Y), pad('U2', 10)])
track('/I2C_SCL', F, SIG, [(144.4, SCL_Y), pad('R6', 2)])
# ToF SDA tap crosses under SCL (the module and ToF pin orders are mirror images).
jumper('/I2C_SDA', (140.0, SDA_Y), (140.0, 50.0)); track('/I2C_SDA', F, SIG, [(140.0, 50.0), pad('U2', 9)])
track('/TOF_INT', F, SIG, chamfer([pad('U1', 35), (111.0, 39.59), (111.0, 51.2), pad('TP6', 1), (135.8, 51.2), pad('U2', 7)]))
jumper('/TOF_INT', (135.8, 51.2), (135.8, 57.4)); track('/TOF_INT', F, SIG, [(135.8, 57.4), pad('R4', 2)])
track('/TOF_XSHUT', F, SIG, chamfer([pad('U1', 34), (109.5, 40.86), (109.5, 52.8), pad('TP5', 1), (137.2, 52.8), pad('U2', 5)]))
track('/TOF_XSHUT', F, SIG, [(137.2, 52.8), (137.2, 55.7), pad('R3', 2)])
track('/AMG_INT', F, SIG, chamfer([pad('U1', 33), (108.0, 42.13), (108.0, 59.0), pad('TP7', 1), (142.2, 59.0)]))
jumper('/AMG_INT', (142.2, 59.0), (144.6, 59.0))
track('/AMG_INT', F, SIG, chamfer([(144.6, 59.0), (150.0, 59.0), (150.0, AINT_Y), (164.4, AINT_Y), (172.0, AINT_Y), pad('U3', 4)]))
track('/AMG_INT', F, SIG, [(164.4, AINT_Y), pad('R7', 2)])

# ---------------------------------------------------------------- VL53L1X supply, bypass and pull-ups
track(V33, F, 0.4, [(143.4, 75.0), (143.4, 57.4)])
track(V33, F, 0.3, [(143.4, 57.4), (143.4, 55.7), (143.4, 54.4), (143.4, 52.8), (143.4, 52.6), (143.4, 51.2), (144.4, 51.2), pad('R6', 1)])
for ref in ('R4', 'R3'): track(V33, F, 0.3, [pad(ref, 1), (143.4, pad(ref, 1)[1])])
for ref in ('C6', 'C7'): track(V33, F, 0.3, [(143.4, pad(ref, 1)[1]), pad(ref, 1)])
track(V33, F, 0.3, [pad('U2', 1), (143.4, 52.8)])
track(V33, F, 0.3, [pad('U2', 11), (143.4, 51.2)])
track(GND, F, SIG, [pad('U2', 6), (137.4, 52.0)]); via(GND, 137.4, 52.0)
track(GND, F, SIG, [pad('U2', 12), (142.55, 52.0)]); via(GND, 142.55, 52.0)
for n in (2, 3, 4):
    x, y = pad('U2', n); track(GND, F, 0.25, [(x, y), (x, 53.9)])
track(GND, F, 0.3, [(139.2, 53.9), (140.8, 53.9)])
for x in (139.4, 140.6): track(GND, F, 0.3, [(x, 53.9), (x, 54.6)]); via(GND, x, 54.6)
for ref in ('C7', 'C6'):
    gx, gy = pad(ref, 2); track(GND, F, 0.4, [(gx, gy), (146.6, gy)]); via(GND, 146.6, gy)

# ---------------------------------------------------------------- AMG8833 supply and internal-regulator bypass
track(GND, F, 0.3, [pad('U3', 6), (169.46, 50.25), (170.73, 50.25), pad('U3', 5)])
track(GND, F, 0.3, [(169.46, 50.25), (168.2, 50.25)]); via(GND, 168.2, 50.25)
track(V33, F, 0.3, [pad('U3', 9), (169.46, 61.0), (169.46, 63.6), (169.46, 67.5)])
track(V33, F, 0.3, [(169.46, 61.0), pad('C9', 1)]); track(V33, F, 0.3, [(169.46, 63.6), pad('C8', 1)])
track(V33, F, 0.3, [pad('U3', 13), (174.54, 67.5)])
track(V33, F, 0.4, [(164.4, 67.5), (169.46, 67.5), (172.0, 67.5), (174.54, 67.5), (179.6, 67.5)])
track(V33, F, 0.4, [(172.0, 75.0), (172.0, 67.5)])
track(V33, F, 0.3, [pad('R7', 1), (164.4, 67.5)]); track(V33, F, 0.3, [pad('R5', 1), (179.6, 67.5)])
track('/AMG_AVDD', F, 0.3, [pad('U3', 10), pad('C10', 1)])
track('/AMG_AVCAP_RETURN', F, 0.3, [pad('C10', 2), pad('R8', 1)])
gx, gy = pad('R8', 2); track(GND, F, 0.3, [(gx, gy), (gx, 66.55)]); via(GND, gx, 66.55)
track('/AMG_DVDD', F, 0.3, [pad('U3', 12), pad('C11', 1)])
gx, gy = pad('C11', 2); track(GND, F, 0.3, [(gx, gy), (gx, 63.4)]); via(GND, gx, 63.4)
gx, gy = pad('C9', 2); track(GND, F, 0.3, [(gx, gy), (165.8, gy)]); via(GND, 165.8, gy)
gx, gy = pad('C8', 2); track(GND, F, 0.4, [(gx, gy), (165.5, gy)]); via(GND, 165.5, gy)

# ---------------------------------------------------------------- outline and provisional supports
r = pcb.PCB_SHAPE(b); r.SetShape(pcb.SHAPE_T_RECT); r.SetStart(xy(OUTLINE[0], OUTLINE[1])); r.SetEnd(xy(OUTLINE[2], OUTLINE[3]))
r.SetLayer(pcb.Edge_Cuts); r.SetWidth(mm(0.05)); b.Add(r)
CU2 = pcb.LSET(); CU2.AddLayer(F); CU2.AddLayer(B)
def rule_area(name, pts):
    z = pcb.ZONE(b); z.SetIsRuleArea(True); z.SetZoneName(name); z.SetLayerSet(CU2)
    z.SetDoNotAllowZoneFills(True); z.SetDoNotAllowTracks(True); z.SetDoNotAllowVias(True)
    z.SetDoNotAllowPads(False); z.SetDoNotAllowFootprints(False)
    o = z.Outline(); o.NewOutline()
    for x, y in pts: o.Append(mm(x), mm(y))
    b.Add(z)
def circle(cx, cy, rad, n=32): return [(cx+rad*math.cos(2*math.pi*i/n), cy+rad*math.sin(2*math.pi*i/n)) for i in range(n)]
# Four provisional M3 supports, 5 mm in from each corner. Copper-free 4 mm radius allows for screw heads/washers.
HOLE_FP, HOLE_KEEPOUT = 'MountingHole_3.2mm_M3', 4.0
HOLES = [(x, y) for y in (OUTLINE[1]+5.0, OUTLINE[3]-5.0) for x in (OUTLINE[0]+5.0, OUTLINE[2]-5.0)]
for i, (xx, yy) in enumerate(HOLES, 1):
    f = pcb.FootprintLoad(str(FPDIR), HOLE_FP); f.SetFPID(pcb.LIB_ID('SashSense', HOLE_FP))
    f.SetReference(f'H{i}'); f.SetValue('M3 SUPPORT - PROVISIONAL')
    f.SetBoardOnly(True); f.SetExcludedFromBOM(True); f.SetExcludedFromPosFiles(True)
    f.SetPosition(xy(xx, yy)); f.Reference().SetVisible(False); f.Value().SetVisible(False); b.Add(f)
    rule_area(f'H{i}_support_keepout', circle(xx, yy, HOLE_KEEPOUT))
# Global fiducials round the populated area; board-only, not placed parts.
FIDUCIALS = [(38.0, 50.0), (176.0, 40.0), (120.0, 70.0)]
for i, (xx, yy) in enumerate(FIDUCIALS, 1):
    f = pcb.FootprintLoad(str(FPDIR), 'Fiducial_1mm_Mask2mm'); f.SetFPID(pcb.LIB_ID('SashSense', 'Fiducial_1mm_Mask2mm'))
    f.SetReference(f'FID{i}'); f.SetValue('Fiducial'); f.SetBoardOnly(True); f.SetExcludedFromBOM(True); f.SetExcludedFromPosFiles(True)
    f.SetPosition(xy(xx, yy)); f.Reference().SetVisible(False); f.Value().SetVisible(False); b.Add(f)

# ---------------------------------------------------------------- ground pours on both layers (balanced copper)
POUR = (OUTLINE[0]+2.0, OUTLINE[1]+2.0, OUTLINE[2]-2.0, OUTLINE[3]-2.0)
for layer in (B, F):
    z = pcb.ZONE(b); z.SetLayer(layer); z.SetNet(nets[GND]); z.SetAssignedPriority(0); z.SetZoneName('GND_'+('top' if layer == F else 'bottom'))
    z.SetLocalClearance(mm(0.25)); z.SetMinThickness(mm(0.25))
    z.SetPadConnection(pcb.ZONE_CONNECTION_THT_THERMAL)
    z.SetThermalReliefGap(mm(0.3)); z.SetThermalReliefSpokeWidth(mm(0.4))
    z.SetIslandRemovalMode(pcb.ISLAND_REMOVAL_MODE_ALWAYS)
    o = z.Outline(); o.NewOutline()
    for x, y in [(POUR[0], POUR[1]), (POUR[2], POUR[1]), (POUR[2], POUR[3]), (POUR[0], POUR[3])]: o.Append(mm(x), mm(y))
    b.Add(z)

# Stitching vias tie the top pour to the bottom plane wherever there is open space.
def seg_dist(p, a, c):
    vx, vy = c[0]-a[0], c[1]-a[1]; L = vx*vx+vy*vy
    t = 0 if L == 0 else max(0, min(1, ((p[0]-a[0])*vx+(p[1]-a[1])*vy)/L))
    return math.dist(p, (a[0]+t*vx, a[1]+t*vy))
def box(bb, grow): return (pcb.ToMM(bb.GetLeft())-grow, pcb.ToMM(bb.GetTop())-grow, pcb.ToMM(bb.GetRight())+grow, pcb.ToMM(bb.GetBottom())+grow)
def inbox(p, q): return q[0] <= p[0] <= q[2] and q[1] <= p[1] <= q[3]
segs = [((pcb.ToMM(t.GetStart().x), pcb.ToMM(t.GetStart().y)), (pcb.ToMM(t.GetEnd().x), pcb.ToMM(t.GetEnd().y)), pcb.ToMM(t.GetWidth()))
        for t in b.GetTracks() if t.GetClass() == 'PCB_TRACK']
vias = [(pcb.ToMM(t.GetPosition().x), pcb.ToMM(t.GetPosition().y)) for t in b.GetTracks() if t.GetClass() == 'PCB_VIA']
blocked = [box(p.GetBoundingBox(), 1.0) for f in b.GetFootprints() for p in f.Pads()]
blocked += [box(f.GetCourtyard(pcb.F_CrtYd).BBox(), 0.4) for f in fps.values() if f.GetCourtyard(pcb.F_CrtYd).OutlineCount()]
blocked.append((56.0-1.0, 0.0, 104.0+1.0, 31.75+1.0))   # module antenna keepout
blocked += [(x-3.0, y-3.0, x+3.0, y+3.0) for x, y in FIDUCIALS]
stitched = 0
for gx in [POUR[0]+3.0+5.0*i for i in range(int((POUR[2]-POUR[0]-6.0)/5.0)+1)]:
    for gy in [POUR[1]+3.0+5.0*j for j in range(int((POUR[3]-POUR[1]-6.0)/5.0)+1)]:
        p = (round(gx, 3), round(gy, 3))
        if any(inbox(p, q) for q in blocked): continue
        if any(math.dist(p, h) < HOLE_KEEPOUT+1.0 for h in HOLES): continue
        if any(seg_dist(p, a, c)-w/2 < 0.9 for a, c, w in segs): continue
        if any(math.dist(p, v) < 2.0 for v in vias): continue
        via(GND, *p); vias.append(p); stitched += 1

# ---------------------------------------------------------------- silkscreen
def text(s, x, y, size=1.0, layer=pcb.F_SilkS, thick=0.15, angle=0):
    t = pcb.PCB_TEXT(b); t.SetText(s); t.SetPosition(xy(x, y)); t.SetTextSize(xy(size, size))
    t.SetTextThickness(mm(thick)); t.SetLayer(layer); t.SetTextAngleDegrees(angle)
    if layer in (pcb.B_SilkS, pcb.B_Fab): t.SetMirrored(True)
    b.Add(t); return t

LABELS = [  # (text, x, y, size[, angle]) - placed in measured free space; checked again by DRC
    ('+', 41.0, 34.0, 1.0), ('GND', 40.4, 29.2, 0.8), ('J1: REGULATED 3.3 V ONLY - NO 5 V', 43.0, 41.5, 0.8),
    ('RESET', 67.3, 46.0, 0.8, 90), ('BOOT', 94.0, 56.8, 0.8),
    ('J2: 1 GND  2 RX(in)  3 TX(out)  4 EN  5 BOOT  6 3V3', 99.0, 64.5, 0.8),
    ('VL53L1X 0x29  +Z', 140.0, 44.6, 0.8), ('AMG8833 0x68  +Z', 172.0, 44.6, 0.8),
    ('BEEPER', 52.0, 70.0, 0.8),
    ('Firefly_pcb2  |  SashSense sensor node  |  P2 PROVISIONAL', 108.0, 79.0, 1.2),
    ('NOT RELEASED FOR FABRICATION - mounting, apertures and host interface unresolved', 108.0, 81.6, 0.8),
]
placed_text = []
if '--no-text' not in sys.argv:
    for s, x, y, size, *ang in LABELS:
        t = text(s, x, y, size, thick=0.15, angle=ang[0] if ang else 0); placed_text.append(t)
    text(f'Firefly_pcb2 P2 - BOTTOM  |  {W_MM:.0f} x {H_MM:.0f} mm', 110.0, 66.0, 1.5, pcb.B_SilkS, 0.2)

# Reference designators: first free spot around each courtyard, clear of pads, silk and other text.
silk_obst = [box(p.GetBoundingBox(), 0.25) for f in b.GetFootprints() for p in f.Pads() if p.IsOnLayer(F) or p.HasHole()]
silk_obst += [box(g.GetBoundingBox(), 0.12) for f in fps.values() for g in f.GraphicalItems() if g.GetLayer() == pcb.F_SilkS]
silk_obst += [box(t.GetBoundingBox(), 0.2) for t in placed_text]
def overlaps(q): return any(q[0] < o[2] and o[0] < q[2] and q[1] < o[3] and o[1] < q[3] for o in silk_obst)
unplaced = []
for ref in sorted(fps, key=lambda r: -fps[r].GetCourtyard(pcb.F_CrtYd).BBox().GetArea()):
    f = fps[ref]; fld = f.Reference(); small = f.GetCourtyard(pcb.F_CrtYd).BBox().GetArea() < pcb.FromMM(5)*pcb.FromMM(5)
    size = 0.8 if small else 1.0
    fld.SetTextSize(xy(size, size)); fld.SetTextThickness(mm(0.12 if small else 0.15)); fld.SetTextAngleDegrees(0); fld.SetKeepUpright(True)
    cx0, cy0, cx1, cy1 = box(f.GetCourtyard(pcb.F_CrtYd).BBox(), 0)
    mx, my = (cx0+cx1)/2, (cy0+cy1)/2
    fld.SetPosition(xy(mx, my)); w0 = box(fld.GetBoundingBox(), 0); hw, hh = (w0[2]-w0[0])/2, (w0[3]-w0[1])/2
    cands = []
    for gap in (0.25, 0.8, 1.5, 2.5):
        cands += [(mx, cy0-hh-gap), (mx, cy1+hh+gap), (cx1+hw+gap, my), (cx0-hw-gap, my),
                  (cx1+hw+gap, cy0-hh-gap), (cx0-hw-gap, cy0-hh-gap), (cx1+hw+gap, cy1+hh+gap), (cx0-hw-gap, cy1+hh+gap)]
    for x, y in cands:
        fld.SetPosition(xy(x, y)); q = box(fld.GetBoundingBox(), 0.1)
        if not overlaps(q) and q[0] > OUTLINE[0]+0.5 and q[1] > OUTLINE[1]+0.5 and q[2] < OUTLINE[2]-0.5 and q[3] < OUTLINE[3]-0.5:
            silk_obst.append(q); break
    else:
        unplaced.append(ref); fld.SetPosition(xy(mx, my))
if unplaced: print('WARNING: references without a free silkscreen position:', unplaced)

filler = pcb.ZONE_FILLER(b); filler.Fill(b.Zones())
b.BuildConnectivity()
pcb.SaveBoard(str(BOARD_FILE), b, True)
# PAGE_INFO is not exposed to Python; A4 landscape holds the board plus title block.
raw = BOARD_FILE.read_text(encoding='utf-8')
BOARD_FILE.write_text(re.sub(r'\(paper "[^"]*"( portrait)?\)', '(paper "A4")', raw, count=1), encoding='utf-8')
print('Saved', BOARD_FILE.name, len(fps), 'schematic footprints,', stitched, 'stitching vias,',
      len(list(b.GetTracks())), 'tracks/vias; pcbnew unrouted', b.GetConnectivity().GetUnconnectedCount(True))

