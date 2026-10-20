"""Check the exported schematic netlist against the circuit manifest and sensor package maps.

Read-only with respect to schematic/PCB; writes only the verification JSON report.
"""
from cad_common import *
import xml.etree.ElementTree as ET
import collections
m=json.loads((ROOT/'design_manifest.json').read_text())
x=ET.parse(ROOT/'reports'/'netlist.xml')
actual={};groups={}
for n in x.findall('./nets/net'):
    name=n.attrib['name'];groups[name]=[(v.attrib['ref'],v.attrib['pin']) for v in n.findall('node')]
    for node in n.findall('node'):actual[node.attrib['ref'],node.attrib['pin']]=name
errors=[];checks=[]
def ck(ok,desc):
    checks.append(desc)
    if not ok:errors.append(desc)
for c in m['components']:
    if c['ref'].startswith('#'):continue  # Power flags are ERC markers, absent from PCB netlist nodes.
    for num,net in c['nets'].items():
        ck(actual.get((c['ref'],num))=='/'+net,f"{c['ref']}.{num} -> /{net}")
    if c['fp']:
        ck((ROOT/'libraries'/'SashSense.pretty'/(c['fp'].split(':')[1]+'.kicad_mod')).is_file(),f"Local footprint exists: {c['fp']}")
for ref,pins in [('U2',['8']),('U3',['1','7','8','11','14'])]:
    for pin in pins:
        net=actual.get((ref,pin))
        ck(net is None or (net.startswith('unconnected-') and len(groups[net])==1),f'{ref}.{pin} is electrically unconnected')
amg=json.loads((ROOT/'libraries'/'AMG8833_manifest.json').read_text())
fp=parse((ROOT/'libraries'/'SashSense.pretty'/'AMG8833.kicad_mod').read_text())
padmap={p[1]:p for p in children(fp,'pad')}
ck(len(padmap)==14,'AMG8833 has 14 numbered lands')
for p in amg['pads']:
    a=one(padmap[p['number']],'at');s=one(padmap[p['number']],'size')
    ck(all(abs(float(g)-e)<1e-6 for g,e in zip(a[1:3]+s[1:3],[p['x'],p['y'],p['width'],p['height']])),f"AMG8833 pad {p['number']} matches drawing-derived coordinates and dimensions")
vl=parse((ROOT/'libraries'/'SashSense.pretty'/'ST_VL53L1x.kicad_mod').read_text())
vlpads=children(vl,'pad')
ck(set(p[1] for p in vlpads)==set(map(str,range(1,13))),'VL53L1X pads cover exactly 1..12')
expected=[(1,-1.6,-.8),(2,-.8,-.8),(3,0,-.8),(4,.8,-.8),(5,1.6,-.8),(6,1.6,0),(7,1.6,.8),(8,.8,.8),(9,0,.8),(10,-.8,.8),(11,-1.6,.8),(12,-1.6,0)]
for num,xx,yy in expected:
    ck(any(p[1]==str(num) and abs(float(one(p,'at')[1])-xx)<1e-6 and abs(float(one(p,'at')[2])-yy)<1e-6 for p in vlpads),f'VL53L1X main land {num} matches manufacturer top-view numbering')
lib=parse((ROOT/'libraries'/'SashSense.kicad_sym').read_text())
syms={s[1]:s for s in children(lib,'symbol')}
def sympins(s):
    return {one(p,'number')[1]:one(p,'name')[1] for sub in children(s,'symbol') for p in children(sub,'pin')}
up=sympins(syms['RF_Module_ESP32-S3-WROOM-1'])
for pin,name in [('4','IO4'),('33','IO40'),('34','IO41'),('35','IO42'),('36','RXD0'),('37','TXD0'),('38','IO2'),('39','IO1')]:
    ck(up.get(pin)==name,f'ESP32-S3 module pad {pin} is {name}')
qp=sympins(syms['Transistor_BJT_Q_NPN_BEC'])
ck(qp=={'1':'B','2':'E','3':'C'},'MMBT3904 symbol pins are 1 base, 2 emitter, 3 collector')
erc=json.loads((ROOT/'reports'/'erc.json').read_text())
violations=[v for s in erc.get('sheets',[]) for v in s.get('violations',[])]
ck(len(violations)==0,'Fresh native KiCad ERC reports zero findings')
report={'status':'PASS' if not errors else 'FAIL','checks_executed':len(checks),'errors':errors,'checks':checks,'erc_findings':len(violations),'scope':'Schematic and local sensor footprint mappings only. No final PCB acceptance.'}
(ROOT/'reports'/'schematic_verification.json').write_text(json.dumps(report,indent=2))
print(report['status'],len(checks),'checks;',len(errors),'errors')
if errors:print('\n'.join(errors));raise SystemExit(1)
