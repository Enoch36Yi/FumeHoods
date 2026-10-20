"""Render a 2-D copper review image (one layer) of a board region. Run with KiCad Python.

    & $kp scripts\\render_copper.py <F|B> <out.png> [x0 y0 x1 y1 px_per_mm]
Shows filled zones, tracks, vias, pads, courtyards and reference designators from the saved board,
so layer usage (including the short bottom-layer crossings) can be reviewed without opening KiCad.
"""
from cad_common import *
import sys
import pcbnew as pcb
from PIL import Image, ImageDraw, ImageFont

side, out = sys.argv[1].upper(), Path(sys.argv[2])
x0, y0, x1, y1, s = map(float, sys.argv[3:8]) if len(sys.argv) >= 8 else (27.0, 27.0, 190.0, 82.0, 12.0)
L = pcb.F_Cu if side == 'F' else pcb.B_Cu
b = pcb.LoadBoard(str(ROOT/(NAME+'.kicad_pcb')))
W, H = int((x1-x0)*s), int((y1-y0)*s)
mirror = side == 'B'                     # bottom drawn as seen from below
def P(x, y): return (((x1-x) if mirror else (x-x0))*s, (y-y0)*s)
def mmv(v): return pcb.ToMM(v)
img = Image.new('RGBA', (W, H), (14, 16, 20, 255)); d = ImageDraw.Draw(img)
copper = (205, 70, 55) if side == 'F' else (70, 120, 225)
def polyset(ps, fill):
    for i in range(ps.OutlineCount()):
        o = ps.Outline(i); d.polygon([P(mmv(o.CPoint(j).x), mmv(o.CPoint(j).y)) for j in range(o.PointCount())], fill=fill)
        for h in range(ps.HoleCount(i)):
            hh = ps.Hole(i, h); d.polygon([P(mmv(hh.CPoint(j).x), mmv(hh.CPoint(j).y)) for j in range(hh.PointCount())], fill=(14, 16, 20, 255))
for z in b.Zones():
    if z.GetIsRuleArea():
        if z.IsOnLayer(L):
            o = z.Outline().Outline(0); d.polygon([P(mmv(o.CPoint(j).x), mmv(o.CPoint(j).y)) for j in range(o.PointCount())], outline=(200, 190, 60))
    elif z.IsOnLayer(L) and z.HasFilledPolysForLayer(L):
        polyset(z.GetFilledPolysList(L), tuple(int(c*0.45) for c in copper)+(255,))
for t in b.GetTracks():
    if t.GetClass() == 'PCB_TRACK' and t.GetLayer() == L:
        a, e, w = t.GetStart(), t.GetEnd(), mmv(t.GetWidth())*s
        d.line([P(mmv(a.x), mmv(a.y)), P(mmv(e.x), mmv(e.y))], fill=copper, width=max(1, round(w)))
        for q in (a, e):
            px, py = P(mmv(q.x), mmv(q.y)); d.ellipse([px-w/2, py-w/2, px+w/2, py+w/2], fill=copper)
for f in b.GetFootprints():
    for p in f.Pads():
        if not p.IsOnLayer(L): continue
        polyset(p.GetEffectivePolygon(L, pcb.ERROR_INSIDE), (225, 185, 70, 255) if p.GetNetname() else (140, 140, 140, 255))
        if p.HasHole():
            px, py = P(mmv(p.GetPosition().x), mmv(p.GetPosition().y)); r = mmv(p.GetDrillSize().x)*s/2
            d.ellipse([px-r, py-r, px+r, py+r], fill=(14, 16, 20, 255))
for t in b.GetTracks():
    if t.GetClass() == 'PCB_VIA':
        px, py = P(mmv(t.GetPosition().x), mmv(t.GetPosition().y)); r = mmv(t.GetWidth(L))*s/2; rh = mmv(t.GetDrill())*s/2
        d.ellipse([px-r, py-r, px+r, py+r], fill=(200, 200, 200)); d.ellipse([px-rh, py-rh, px+rh, py+rh], fill=(14, 16, 20))
try: font = ImageFont.truetype('arial.ttf', max(10, int(s*0.95)))
except Exception: font = ImageFont.load_default()
for f in b.GetFootprints():
    cy = f.GetCourtyard(pcb.F_CrtYd)
    if cy.OutlineCount() and not f.IsBoardOnly():
        o = cy.Outline(0); d.polygon([P(mmv(o.CPoint(j).x), mmv(o.CPoint(j).y)) for j in range(o.PointCount())], outline=(110, 200, 110))
        bb = cy.BBox(); px, py = P(mmv(bb.GetLeft() if not mirror else bb.GetRight()), mmv(bb.GetTop()))
        d.text((px+2, py+1), f.GetReference(), fill=(150, 240, 240), font=font)
d.text((8, 6), f"Firefly_pcb2 P2 - {'TOP (F.Cu)' if side == 'F' else 'BOTTOM (B.Cu, viewed from below)'} - region x {x0:g}-{x1:g} mm, y {y0:g}-{y1:g} mm",
       fill=(255, 255, 255), font=font)
out.parent.mkdir(parents=True, exist_ok=True); img.convert('RGB').save(out)
print('wrote', out)
