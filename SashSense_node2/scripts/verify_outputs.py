"""Check the exported manufacturing review files against the saved board. Run with KiCad Python.

Read-only for CAD and output files; writes reports/output_verification.json.
"""
from cad_common import *
import csv, re, collections
import pcbnew as pcb

M = ROOT/'outputs'/'manufacturing_P2_PROVISIONAL'
b = pcb.LoadBoard(str(ROOT/(NAME+'.kicad_pcb')))
checks, errors, info = [], [], {}
def ck(ok, desc):
    checks.append(desc)
    if not ok: errors.append(desc)
    return ok
OX, OY = OUTLINE_MM[0], OUTLINE_MM[3]        # auxiliary (drill/place) origin: bottom-left board corner
BW, BH = OUTLINE_MM[2]-OUTLINE_MM[0], OUTLINE_MM[3]-OUTLINE_MM[1]

# ---------------------------------------------------------------- Gerbers
def gerber_xy(path):
    txt = path.read_text(errors='replace'); fs = re.search(r'%FSLAX(\d)(\d)Y(\d)(\d)\*%', txt)
    div = 10**int(fs.group(2)); pts = []; x = y = None
    for m in re.finditer(r'(?:X(-?\d+))?(?:Y(-?\d+))?D0?[123]\*', txt):
        if m.group(1) is not None: x = int(m.group(1))/div
        if m.group(2) is not None: y = int(m.group(2))/div
        if x is not None and y is not None and (m.group(1) or m.group(2)): pts.append((x, y))
    return txt, pts
gdir = M/'gerbers'
want = {'F_Cu': 'gtl', 'B_Cu': 'gbl', 'F_Paste': 'gtp', 'B_Paste': 'gbp', 'F_Silkscreen': 'gto', 'B_Silkscreen': 'gbo', 'F_Mask': 'gts', 'B_Mask': 'gbs', 'Edge_Cuts': 'gm1'}
files = {k: next(iter(gdir.glob(f'*-{k}.*')), None) for k in want}
ck(all(files.values()), 'Gerbers present for F/B copper, paste, silkscreen, mask and Edge.Cuts: '+', '.join(sorted(k for k, v in files.items() if v)))
txt, pts = gerber_xy(files['Edge_Cuts'])
xs, ys = [p[0] for p in pts], [p[1] for p in pts]
ew, eh = max(xs)-min(xs), max(ys)-min(ys)
ck(abs(ew-BW) < 1e-6 and abs(eh-BH) < 1e-6 and abs(min(xs)) < 1e-6 and abs(min(ys)) < 1e-6,
   f'Edge.Cuts Gerber outline spans {ew:.6f} x {eh:.6f} mm from the bottom-left origin')
info['edge_cuts_gerber_extent_mm'] = [round(ew, 6), round(eh, 6)]
for k in ('F_Cu', 'B_Cu'):
    t, p = gerber_xy(files[k])
    ck(p and all(-1e-6 <= x <= BW+1e-6 and -1e-6 <= y <= BH+1e-6 for x, y in p), f'{k} Gerber coordinates all lie within the {BW:g} x {BH:g} mm outline ({len(p)} coordinates)')
job = json.loads(next(gdir.glob('*.gbrjob')).read_text())
gs = job.get('GeneralSpecs', {})
edge_w = next(pcb.ToMM(d.GetWidth()) for d in b.GetDrawings() if d.GetLayer() == pcb.Edge_Cuts)
# The job file reports the outline bounding box including the 0.05 mm drawing line; the cut path is its centreline.
ck(abs(gs.get('Size', {}).get('X', 0)-BW-edge_w) < 1e-6 and abs(gs.get('Size', {}).get('Y', 0)-BH-edge_w) < 1e-6 and gs.get('LayerNumber') == 2,
   f"Gerber job file: {gs.get('Size')} mm bounding box = {BW:g} x {BH:g} mm centreline + {edge_w} mm outline line, {gs.get('LayerNumber')} layers, thickness {gs.get('BoardThickness')} mm")
info['gerber_job_general_specs'] = gs

# ---------------------------------------------------------------- Drill files
def drill_hits(path):
    tools, hits, cur = {}, collections.Counter(), None
    for line in path.read_text().splitlines():
        m = re.match(r'^T(\d+)C([\d.]+)', line)
        if m: tools[m.group(1)] = float(m.group(2)); continue
        m = re.match(r'^T(\d+)$', line)
        if m: cur = m.group(1); continue
        if cur and re.match(r'^X-?[\d.]+Y-?[\d.]+', line): hits[tools[cur]] += 1
    return hits
pth = next((M/'drill').glob('*-PTH.drl')); npth = next((M/'drill').glob('*-NPTH.drl'))
ph, nh = drill_hits(pth), drill_hits(npth)
board_pth, board_npth = collections.Counter(), collections.Counter()
for t in b.GetTracks():
    if t.GetClass() == 'PCB_VIA': board_pth[round(pcb.ToMM(t.GetDrill()), 3)] += 1
for f in b.GetFootprints():
    for p in f.Pads():
        if p.HasHole():
            (board_pth if p.GetAttribute() == pcb.PAD_ATTRIB_PTH else board_npth)[round(pcb.ToMM(p.GetDrillSize().x), 3)] += 1
ck(dict(ph) == dict(board_pth), f'PTH drill file hits {dict(ph)} equal board plated holes {dict(board_pth)}')
ck(dict(nh) == dict(board_npth), f'NPTH drill file hits {dict(nh)} equal board unplated holes {dict(board_npth)}')
info['drill_hits_by_diameter_mm'] = {'PTH': {str(k): v for k, v in sorted(ph.items())}, 'NPTH': {str(k): v for k, v in sorted(nh.items())}}
ck(min(ph) >= 0.2, f'Smallest plated drill {min(ph)} mm (module thermal vias; check fabricator minimum)')

# ---------------------------------------------------------------- Placement (CPL) and BOM
rows = list(csv.DictReader((M/'assembly'/'Firefly_pcb2_CPL_top.csv').open(encoding='utf-8-sig')))
placed = {f.GetReference(): f for f in b.GetFootprints() if not f.IsBoardOnly() and not f.IsExcludedFromPosFiles() and not f.IsDNP()}
ck({r['Ref'] for r in rows} == set(placed), f'CPL lists exactly the {len(placed)} placed (non-pad) parts')
bad = []
for r in rows:
    f = placed.get(r['Ref'])
    if not f: continue
    x, y = pcb.ToMM(f.GetPosition().x)-OX, OY-pcb.ToMM(f.GetPosition().y)
    if abs(float(r['PosX'])-x) > 1e-3 or abs(float(r['PosY'])-y) > 1e-3 or r['Side'].lower() != 'top': bad.append(r['Ref'])
ck(not bad, 'CPL coordinates equal board positions relative to the bottom-left origin, all top side'+(f' (mismatch {bad})' if bad else ''))
bom = list(csv.DictReader((M/'assembly'/'Firefly_pcb2_BOM.csv').open(encoding='utf-8-sig')))
def expand(field):
    out = []
    for part in (p.strip() for p in field.split(',') if p.strip()):
        m = re.fullmatch(r'([A-Z]+)(\d+)-\1?(\d+)', part)
        out += [f'{m.group(1)}{i}' for i in range(int(m.group(2)), int(m.group(3))+1)] if m else [part]
    return out
refs = [r for row in bom for r in expand(row['Reference'])]
inbom = {f.GetReference() for f in b.GetFootprints() if not f.IsBoardOnly() and not f.IsExcludedFromBOM()}
ck(sorted(refs) == sorted(inbom) and len(refs) == len(set(refs)), f'BOM covers each of the {len(inbom)} purchased parts exactly once')
ck(all(row['MPN'].strip() and row['Manufacturer'].strip() for row in bom), 'Every BOM line has a manufacturer and MPN')
ck(sum(int(row['Qty']) for row in bom) == len(inbom), 'BOM quantities sum to the placed part count')
ck(set(placed) == inbom, 'CPL and BOM describe the same parts')
info['bom_lines'] = len(bom); info['placed_parts'] = len(placed)

# ---------------------------------------------------------------- other artefacts
ipc = (M/'netlist'/'Firefly_pcb2.ipc').read_text(errors='replace')
nets = {l[3:17].strip() for l in ipc.splitlines() if l.startswith(('317', '327'))}
ck(len(ipc) > 1000 and len(nets) >= 17, f'IPC-D-356 netlist present ({len(nets)} named nets in test records)')
step = M/'3d'/'Firefly_pcb2.step'
ck(step.is_file() and step.stat().st_size > 100_000, f'STEP model present ({step.stat().st_size//1024} KiB)')
for p in [M/'assembly'/'Firefly_pcb2_assembly_top.pdf', ROOT/'outputs'/'Firefly_pcb2_board_layers.pdf']:
    ck(p.is_file() and p.read_bytes()[:4] == b'%PDF', f'{p.name} is a PDF')
pv = ROOT/'outputs'/'previews'
for n in ['3D_top', '3D_bottom', '3D_iso', 'copper_top', 'copper_bottom']:
    p = pv/f'Firefly_pcb2_{n}.png'
    ck(p.is_file() and p.stat().st_size > 20_000, f'Preview {p.name} present')

report = {'status': 'PASS' if not errors else 'FAIL', 'checks_executed': len(checks), 'errors': errors, 'info': info, 'checks': checks,
          'scope': 'Consistency of exported files with the saved board. Not a fabricator DFM review or release approval.'}
(ROOT/'reports'/'output_verification.json').write_text(json.dumps(report, indent=2))
print(report['status'], len(checks), 'checks;', len(errors), 'errors')
if errors: print('\n'.join(errors)); raise SystemExit(1)
