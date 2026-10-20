"""Rebuild the editable Firefly_pcb2 schematic. Run with KiCad Python.

PCB generation is opt-in (--build-pcb) for a later continuation. All writes stay here.
"""
from cad_common import *
import sys
import math, shutil, csv
import pcbnew as pcb

LIBDIR=ROOT/'libraries'; FPDIR=LIBDIR/'SashSense.pretty'
LIBDIR.mkdir(exist_ok=True); FPDIR.mkdir(exist_ok=True)
symbols={}; components=[]
def register(lib,name):
    key=lib+'_'+name
    if key not in symbols:
        raw=symbol_raw(lib,name)
        if '(extends ' in raw: raise ValueError('Use a non-inherited symbol: '+key)
        raw=raw.replace('(symbol '+q(name),'(symbol '+q(key),1)
        raw=raw.replace('(symbol '+q(name+'_'),'(symbol '+q(key+'_')) if False else raw
        # Sub-symbol names must follow the renamed parent.
        raw=raw.replace('"'+name+'_','"'+key+'_')
        symbols[key]=raw
    return key
def add(ref,lib,name,value,fp,nets,xy,sch,mpn='',maker='',angle=0,section=''):
    key=register(lib,name)
    # Footprints are copied, then all schematic and board assignments use the local table.
    flib,fname=fp.split(':')
    local=fname
    src=SHARE/'footprints'/(flib+'.pretty')/(fname+'.kicad_mod')
    if src.exists(): shutil.copyfile(src,FPDIR/(local+'.kicad_mod'))
    elif not (FPDIR/(local+'.kicad_mod')).exists(): raise FileNotFoundError(fp)
    components.append(dict(ref=ref,key=key,value=value,fp='SashSense:'+local,nets={str(k):v for k,v in nets.items()},
                           xy=xy,sch=sch,mpn=mpn,maker=maker,angle=angle,section=section,uuid=uid(ref)))

def custom_symbol(name,pins,width=10.16):
    # pins: (number, name, electrical type, side), on 2.54mm grid.
    left=[p for p in pins if p[3]=='L']; right=[p for p in pins if p[3]=='R']
    height=(max(len(left),len(right))+1)*2.54
    raw=f'(symbol {q(name)} (pin_names (offset 0.508)) (in_bom yes) (on_board yes) '
    raw+=f'(property "Reference" "U" (at 0 {height/2+2.54} 0) (effects (font (size 1.27 1.27)))) '
    raw+=f'(property "Value" {q(name)} (at 0 {-height/2-2.54} 0) (effects (font (size 1.27 1.27)))) '
    raw+=f'(symbol {q(name+"_0_1")} (rectangle (start {-width} {height/2}) (end {width} {-height/2}) (stroke (width 0.254) (type default)) (fill (type background)))) '
    raw+=f'(symbol {q(name+"_1_1")} '
    for side,ps in [('L',left),('R',right)]:
        for i,(num,nm,typ,_) in enumerate(ps):
            x=(-1 if side=='L' else 1)*(width+2.54); y=(len(ps)-1)*1.27-i*2.54
            raw+=f'(pin {typ} line (at {x} {y} {0 if side=="L" else 180}) (length 2.54) (name {q(nm)} (effects (font (size 1.0 1.0)))) (number {q(num)} (effects (font (size 1.0 1.0))))) '
    raw+='))'; symbols[name]=raw
    return name

# Local solder service pads: these are PCB features and do not imply a mating connector.
def solderpads(name,count,pitch=2.54):
    s=f'(footprint {q(name)} (version 20260206) (generator "pcbnew") (layer "F.Cu") (attr through_hole exclude_from_pos_files exclude_from_bom) '
    s+=f'(property "Reference" "REF**" (at 0 -3 0) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15)))) '
    s+=f'(property "Value" {q(name)} (at 0 3 0) (layer "F.Fab") (effects (font (size 1 1) (thickness 0.15)))) '
    s+=f'(fp_rect (start -1.5 -1.5) (end {(count-1)*pitch+1.5} 1.5) (stroke (width 0.05) (type default)) (fill none) (layer "F.CrtYd")) '
    for i in range(count):
        s+=f'(pad {q(i+1)} thru_hole {"rect" if i==0 else "circle"} (at {i*pitch} 0) (size 1.8 1.8) (drill 1.0) (layers "*.Cu" "*.Mask")) '
    (FPDIR/(name+'.kicad_mod')).write_text(s+')',encoding='utf-8')
solderpads('ServicePads_1x06',6)

U1nets={'1':'GND','2':'+3V3','3':'EN','4':'BEEP_PWM','33':'AMG_INT','34':'TOF_XSHUT','35':'TOF_INT','36':'UART_RX','37':'UART_TX','38':'I2C_SCL','39':'I2C_SDA','40':'GND','41':'GND','27':'BOOT'}
add('U1','RF_Module','ESP32-S3-WROOM-1','ESP32-S3-WROOM-1-N8','RF_Module:ESP32-S3-WROOM-1',U1nets,(75,46),(75,73),'ESP32-S3-WROOM-1-N8','Espressif')
add('U2','Sensor_Distance','VL53L1CXV0FY1','VL53L1CXV0FY/1','Sensor_Distance:ST_VL53L1x',{'1':'+3V3','2':'GND','3':'GND','4':'GND','5':'TOF_XSHUT','6':'GND','7':'TOF_INT','9':'I2C_SDA','10':'I2C_SCL','11':'+3V3','12':'GND'},(137,55),(180,65),'VL53L1CXV0FY/1','STMicroelectronics')

# Custom Panasonic symbol deliberately exposes all 14 pins and internal-regulator bypass pins.
amg='AMG8833'
custom_symbol(amg,[('1','NC','no_connect','R'),('2','SDA','bidirectional','L'),('3','SCL','input','L'),('4','INT','open_collector','L'),('5','AD_SELECT','input','L'),('6','GND','power_in','L'),('7','NC','no_connect','R'),('8','NC','no_connect','R'),('9','VDD','power_in','R'),('10','AVDD-PC','passive','R'),('11','NC','no_connect','R'),('12','DVDD-PC','passive','R'),('13','VPP','power_in','R'),('14','NC','no_connect','R')],12.7)
components.append(dict(ref='U3',key=amg,value='AMG8833',fp='SashSense:AMG8833',nets={'2':'I2C_SDA','3':'I2C_SCL','4':'AMG_INT','5':'GND','6':'GND','9':'+3V3','10':'AMG_AVDD','12':'AMG_DVDD','13':'+3V3'},xy=(180,55),sch=(300,65),mpn='AMG8833',maker='Panasonic',angle=0,section='',uuid=uid('U3')))

RFP='Resistor_SMD:R_0603_1608Metric'; CFP='Capacitor_SMD:C_0603_1608Metric'
def res(ref,val,nets,xy,sch,mpn,angle=0): add(ref,'Device','R',val,RFP,dict(zip(['1','2'],nets)),xy,sch,mpn,'Yageo',angle)
def cap(ref,val,nets,xy,sch,mpn,fp=CFP,angle=0): add(ref,'Device','C',val,fp,dict(zip(['1','2'],nets)),xy,sch,mpn,'Murata',angle)

res('R1','10k',['+3V3','EN'],(58,44),(34,130),'RC0603FR-0710KL')
cap('C1','1uF',['EN','GND'],(58,49),(49,130),'GRM188R61A105KA61D')
res('R2','10k',['+3V3','BOOT'],(91,61),(68,130),'RC0603FR-0710KL')
res('R3','10k',['+3V3','TOF_XSHUT'],(143,61),(153,116),'RC0603FR-0710KL')
res('R4','10k',['+3V3','TOF_INT'],(143,66),(172,116),'RC0603FR-0710KL')
res('R5','4.7k',['+3V3','I2C_SDA'],(100,47),(211,116),'RC0603FR-074K7L')
res('R6','4.7k',['+3V3','I2C_SCL'],(100,52),(231,116),'RC0603FR-074K7L')
res('R7','10k',['+3V3','AMG_INT'],(169,64),(271,116),'RC0603FR-0710KL')
cap('C2','10uF',['+3V3','GND'],(61,47),(30,170),'GRM21BR61A106KE19L',fp='Capacitor_SMD:C_0805_2012Metric')
cap('C3','100nF',['+3V3','GND'],(63,43),(49,170),'GRM188R71C104KA01D')
cap('C4','47uF',['+3V3','GND'],(54,61),(68,170),'GRM31CR60J476ME19L',fp='Capacitor_SMD:C_1206_3216Metric')
cap('C5','47uF',['+3V3','GND'],(54,67),(87,170),'GRM31CR60J476ME19L',fp='Capacitor_SMD:C_1206_3216Metric')
cap('C6','100nF',['+3V3','GND'],(134.5,52.6),(151,151),'GRM188R71C104KA01D')
cap('C7','4.7uF',['+3V3','GND'],(131.5,55),(170,151),'GRM188R60J475KE19D')
cap('C8','10uF',['+3V3','GND'],(184.5,48),(264,151),'GRM21BR61A106KE19L',fp='Capacitor_SMD:C_0805_2012Metric')
cap('C9','100nF',['+3V3','GND'],(188,52),(283,151),'GRM188R71C104KA01D')
cap('C10','1uF',['AMG_AVDD','AMG_AVCAP_RETURN'],(181.27,47.5),(302,151),'GRM188R61A105KA61D')
res('R8','20R',['AMG_AVCAP_RETURN','GND'],(181.27,43.8),(321,151),'RC0603FR-0720RL')
cap('C11','1.5uF',['AMG_DVDD','GND'],(177.46,48),(340,151),'GRM188R61A155KA61D')
add('SW1','Switch','SW_Push','RESET','Button_Switch_SMD:SW_SPST_TL3342',{'1':'EN','2':'GND'},(52,48),(35,210),'TL3342F160QG','E-Switch')
add('SW2','Switch','SW_Push','BOOT','Button_Switch_SMD:SW_SPST_TL3342',{'1':'BOOT','2':'GND'},(93,67),(68,210),'TL3342F160QG','E-Switch')
add('J1','Connector_Generic','Conn_01x02','REGULATED 3.3V IN','Connector_Wire:SolderWire-0.75sqmm_1x02_P4.8mm_D1.25mm_OD2.3mm',{'1':'+3V3','2':'GND'},(44,61),(29,245),'PCB FEATURE','PCB')
add('J2','Connector_Generic','Conn_01x06','UART / BOOT SERVICE','SashSense:ServicePads_1x06',{'1':'GND','2':'UART_RX','3':'UART_TX','4':'EN','5':'BOOT','6':'+3V3'},(90,78),(117,239),'PCB FEATURE','PCB')

# Externally driven piezo, not a magnetic coil. R11 resets the piezo charge each PWM cycle.
add('BZ1','Device','Buzzer','PKLCS1212E4001-R1','Buzzer_Beeper:Buzzer_Murata_PKLCS1212E',{'1':'+3V3','2':'BEEP_LOW'},(53,90),(242,213),'PKLCS1212E4001-R1','Murata')
add('Q1','Transistor_BJT','Q_NPN_BEC','MMBT3904LT1G','Package_TO_SOT_SMD:SOT-23',{'1':'BEEP_BASE','2':'GND','3':'BEEP_LOW'},(68,86),(275,218),'MMBT3904LT1G','onsemi')
res('R9','1k',['BEEP_PWM','BEEP_BASE'],(68,80),(310,213),'RC0603FR-071KL')
res('R10','100k',['BEEP_BASE','GND'],(73,86),(332,213),'RC0603FR-07100KL')
res('R11','1k',['+3V3','BEEP_LOW'],(53,101),(218,213),'RC0603FR-071KL')

for i,(net,xy,sch) in enumerate([('+3V3',(61,72),(157,243)),('GND',(66,72),(177,243)),('I2C_SDA',(115,62),(197,243)),('I2C_SCL',(120,62),(217,243)),('TOF_XSHUT',(147,72),(237,243)),('TOF_INT',(152,72),(257,243)),('AMG_INT',(165,72),(277,243)),('BEEP_PWM',(78,86),(297,243))],1):
    add('TP'+str(i),'Connector','TestPoint',net,'TestPoint:TestPoint_Pad_D1.5mm',{'1':net},xy,sch,'PCB FEATURE','PCB')

# Power flags express the external regulated input (both supply and return).
for ref,net,xy in [('#FLG01','+3V3',(35,257)),('#FLG02','GND',(68,257))]:
    k=register('power','PWR_FLAG')
    components.append(dict(ref=ref,key=k,value='PWR_FLAG',fp='',nets={'1':net},xy=(0,0),sch=xy,mpn='',maker='',angle=0,section='',uuid=uid(ref)))

# One native schematic. Connections are local net labels on deliberately short wires.
rootid=uid('schematic'); sch=[f'(kicad_sch (version 20250114) (generator "eeschema") (uuid {q(rootid)}) (paper "A3")',
 '(title_block (title "Firefly_pcb2 - SashSense sensor node") (date "2026-10-19") (rev "P1") (company "SashSense") (comment 1 "PROVISIONAL - 500 x 500 mm - mechanical/system integration unresolved"))',
 '(lib_symbols '+' '.join(raw.replace('(symbol '+q(k),'(symbol '+q('SashSense:'+k),1) for k,raw in symbols.items())+')']
def effect(size=1.0,justify=''): return f'(effects (font (size {size} {size})) {justify})'
def wire(x,y,x2,y2,tag): return f'(wire (pts (xy {x:.4f} {y:.4f}) (xy {x2:.4f} {y2:.4f})) (stroke (width 0) (type default)) (uuid {q(uid(tag))}))'
for c in components:
    x,y=[round(v/1.27)*1.27 for v in c['sch']]; ref=c['ref']; pins=pin_data(symbols[c['key']]); seen=set()
    for p in pins:
        px=x+p['x']; py=y-p['y']; key=(px,py)
        net=c['nets'].get(p['num'])
        if key in seen: continue
        seen.add(key)
        if not net:
            if p['type']!='no_connect': sch.append(f'(no_connect (at {px} {py}) (uuid {q(uid(ref+"NC"+p["num"]))}))')
            continue
        a=math.radians(p['angle']); dx=-math.cos(a)*5.08; dy=math.sin(a)*5.08
        ex=px+dx; ey=py+dy
        sch.append(wire(px,py,ex,ey,ref+'wire'+p['num']))
        ang=90 if abs(dy)>1 else 0
        just='(justify right bottom)' if dx < -1 or dy > 1 else '(justify left bottom)'
        sch.append(f'(label {q(net)} (at {ex:.4f} {ey:.4f} {ang}) {effect(0.95,just)} (uuid {q(uid(ref+"label"+p["num"]))}))')
    raw=symbols[c['key']]; parsed=parse(raw)
    v=one(next(p for p in children(parsed,'property') if p[1]=='Reference'),'at')
    vx=float(v[1]); vy=float(v[2])
    sch.append(f'(symbol (lib_id {q("SashSense:"+c["key"])}) (at {x} {y} 0) (unit 1) (in_bom {"no" if ref.startswith(("#","TP","J")) else "yes"}) (on_board {"no" if ref.startswith("#") else "yes"}) (dnp no) (uuid {q(c["uuid"])})')
    if c['key'] in ('Device_R','Device_C'):
        vx,vy=2.54,1.27
    if ref=='BZ1':vx,vy=5.08,3.81
    reffx=effect(1.1,'(justify left)' if c['key'] in ('Device_R','Device_C') else '')
    if ref.startswith('#'):reffx='(effects (font (size 1 1)) (hide yes))'
    sch.append(f'(property "Reference" {q(ref)} (at {x+vx} {y-vy} 0) {reffx})')
    # Long part names are more legible above/below the symbol than on top of it.
    valat=one(next(p for p in children(parsed,'property') if p[1]=='Value'),'at')
    valx,valy=x+float(valat[1]),y-float(valat[2])
    valjust=''
    if c['key'] in ('Device_R','Device_C'):
        valx,valy=x+2.54,y+1.27;valjust='(justify left)'
    if ref=='BZ1':valx,valy=x,y+7.62
    if ref=='Q1':valx,valy=x+7.62,y+2.54;valjust='(justify left)'
    sch.append(f'(property "Value" {q(c["value"])} (at {valx} {valy} 0) {effect(1.0,valjust)})')
    for field,value in [('Footprint',c['fp']),('MPN',c['mpn']),('Manufacturer',c['maker'])]:
        sch.append(f'(property {q(field)} {q(value)} (at {x} {y} 0) (effects (font (size 1 1)) (hide yes)))')
    for p in pins: sch.append(f'(pin {q(p["num"])} (uuid {q(uid(ref+"pin"+p["num"]))}))')
    sch.append(f'(instances (project {q(NAME)} (path {q("/"+rootid)} (reference {q(ref)}) (unit 1)))) )')

for text,x,y,size in [('PROCESSOR / RESET',25,22,2),('TIME OF FLIGHT - +Z optical axis',143,25,1.7),('THERMAL ARRAY - +Z optical axis',263,25,1.7),('RESET / BOOT BIAS',25,111,1.5),('I2C - 100 kHz initial bring-up',205,99,1.5),('POWER / BYPASS',25,151,1.5),('TOF LOCAL DECOUPLING',145,135,1.5),('AMG INTERNAL REGULATOR BYPASS',261,135,1.5),('BEEPER - PWM approximately 4 kHz',205,190,1.5),('SERVICE PADS / TEST ACCESS',105,264,1.5),('3.3 V REGULATED INPUT ONLY; >=1 A transient source. NO 5 V.',20,271,1.1),('P1: mounting / enclosure / host protocol remain provisional. No external I2C cable is designed.',20,277,1.0),('AMG: VPP tied VDD; AD_SELECT low -> 0x68. TOF: 7-bit 0x29, 2V8 I/O mode.',20,283,1.0)]:
    sch.append(f'(text {q(text)} (at {x} {y} 0) {effect(size,"(justify left)")} (uuid {q(uid(text))}))')
sch+=['(embedded_fonts no))']
(ROOT/(NAME+'.kicad_sch')).write_text('\n'.join(sch),encoding='utf-8')
(LIBDIR/'SashSense.kicad_sym').write_text('(kicad_symbol_lib (version 20250114) (generator "kicad_symbol_editor")\n'+'\n'.join(symbols.values())+'\n)',encoding='utf-8')
(ROOT/'sym-lib-table').write_text('(sym_lib_table (lib (name "SashSense")(type "KiCad")(uri "${KIPRJMOD}/libraries/SashSense.kicad_sym")(options "")(descr "Project-local parts")))',encoding='utf-8')
(ROOT/'fp-lib-table').write_text('(fp_lib_table (lib (name "SashSense")(type "KiCad")(uri "${KIPRJMOD}/libraries/SashSense.pretty")(options "")(descr "Project-local footprints")))',encoding='utf-8')

# Default execution is schematic-only. The user stopped this task before PCB completion.
# Resuming PCB creation requires a separate explicit invocation by the next engineer.
(ROOT/'design_manifest.json').write_text(json.dumps({'name':NAME,'outline_mm':[25,25,525,525],'schematic_uuid':rootid,'components':components},indent=2),encoding='utf-8')
with (ROOT/'outputs'/'BOM.csv').open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.writer(f);w.writerow(['Reference','Value','Manufacturer','MPN','Footprint','Quantity','Status'])
    for c in components:
        if not c['ref'].startswith('#'):w.writerow([c['ref'],c['value'],c['maker'],c['mpn'],c['fp'],1,'SCHEMATIC P1 - PCB NOT COMPLETED'])
if '--build-pcb' not in sys.argv:
    print('Created',NAME,'schematic and local libraries. PCB generation disabled by default.')
    sys.exit(0)

# PCB with copied local footprint definitions and the exact required board outline.
b=pcb.BOARD(); b.SetCopperLayerCount(2)
ds=b.GetDesignSettings(); ds.SetCopperLayerCount(2); ds.SetBoardThickness(pcb.FromMM(1.6))
netnames=sorted({n for c in components for n in c['nets'].values()})
nets={}
for i,name in enumerate(netnames,1):
    n=pcb.NETINFO_ITEM(b,'/'+name,i);b.Add(n);nets[name]=n
for c in components:
    if not c['fp']: continue
    name=c['fp'].split(':')[1]; f=pcb.FootprintLoad(str(FPDIR),name)
    if not f: raise RuntimeError('Missing footprint '+name)
    f.SetReference(c['ref']); f.SetValue(c['value']); f.SetFPID(pcb.LIB_ID('SashSense',name))
    f.SetField('MPN',c['mpn']); f.SetField('Manufacturer',c['maker'])
    for fn in ['MPN','Manufacturer']: f.GetField(fn).SetVisible(False)
    if c['ref'].startswith(('TP','J')): f.SetExcludedFromBOM(True)
    f.SetPath(pcb.KIID_PATH('/'+rootid+'/'+c['uuid']))
    f.SetPosition(pcb.VECTOR2I(pcb.FromMM(c['xy'][0]),pcb.FromMM(c['xy'][1])))
    f.SetOrientationDegrees(c['angle']); b.Add(f)
    f.Reference().SetTextSize(pcb.VECTOR2I(pcb.FromMM(1),pcb.FromMM(1))); f.Reference().SetTextThickness(pcb.FromMM(.15))
    for p in f.Pads():
        n=c['nets'].get(p.GetNumber())
        if n: p.SetNet(nets[n])
    f.Models().clear()
    # Preserve the original package/reference geometry; only values are hidden.
    f.Value().SetVisible(False)
for p1,p2 in [((25,25),(525,25)),((525,25),(525,525)),((525,525),(25,525)),((25,525),(25,25))]:
    s=pcb.PCB_SHAPE();s.SetShape(pcb.SHAPE_T_SEGMENT);s.SetStart(pcb.VECTOR2I(*[pcb.FromMM(v) for v in p1]));s.SetEnd(pcb.VECTOR2I(*[pcb.FromMM(v) for v in p2]));s.SetLayer(pcb.Edge_Cuts);s.SetWidth(pcb.FromMM(.05));b.Add(s)

# 25 provisional M3 support positions at 120mm pitch. No existing enclosure fit is implied.
for yi,y in enumerate([35,155,275,395,515]):
    for xi,x in enumerate([35,155,275,395,515]):
        name='MountingHole_3.2mm_M3'; shutil.copyfile(SHARE/'footprints'/'MountingHole.pretty'/(name+'.kicad_mod'),FPDIR/(name+'.kicad_mod'))
        f=pcb.FootprintLoad(str(FPDIR),name); f.SetReference(f'H{yi*5+xi+1}');f.SetValue('M3 SUPPORT - PROVISIONAL');f.SetFPID(pcb.LIB_ID('SashSense',name));f.SetPosition(pcb.VECTOR2I(pcb.FromMM(x),pcb.FromMM(y)));f.SetBoardOnly(True);f.Value().SetVisible(False);b.Add(f)

def boardtext(txt,x,y,size=1.2,layer=pcb.F_SilkS):
    t=pcb.PCB_TEXT(b);t.SetText(txt);t.SetPosition(pcb.VECTOR2I(pcb.FromMM(x),pcb.FromMM(y)));t.SetTextSize(pcb.VECTOR2I(pcb.FromMM(size),pcb.FromMM(size)));t.SetTextThickness(pcb.FromMM(.15));t.SetLayer(layer);t.SetMirrored(layer==pcb.B_SilkS);b.Add(t)
boardtext('Firefly_pcb2 | SashSense | P1 PROVISIONAL',117,115,1.5)
boardtext('3.3 V ONLY',44,55,1)
boardtext('+     GND',46,66,1)
boardtext('J2: GND RX TX EN BOOT 3V3',97,83,1)
boardtext('NO HOST CONNECTOR PINOUT ASSUMED',117,119,1)
boardtext('VL53L1X 0x29',137,46,1)
boardtext('AMG8833 0x68',180,66,1)
boardtext('OPEN OPTICAL PATH +Z',176,33,1.2)
boardtext('BEEPER',53,109,1)
boardtext('500 x 500 mm | SUPPORT GRID PROVISIONAL',275,295,4)
boardtext('NOT RELEASED FOR FABRICATION',275,306,3)
boardtext('BOTTOM | Firefly_pcb2 P1',275,320,3,pcb.B_SilkS)
# Zone only beneath the active circuit: mechanical carrier remainder has no unnecessary copper.
z=pcb.ZONE(b);z.SetLayer(pcb.B_Cu);z.SetNet(nets['GND']);z.SetLocalClearance(pcb.FromMM(.2));z.SetThermalReliefGap(pcb.FromMM(.25));z.SetThermalReliefSpokeWidth(pcb.FromMM(.3));z.SetPadConnection(pcb.ZONE_CONNECTION_THERMAL)
o=z.Outline();o.NewOutline()
for x,y in [(27,27),(203,27),(203,123),(27,123)]:o.Append(pcb.FromMM(x),pcb.FromMM(y))
b.Add(z)
pcb.SaveBoard(str(ROOT/(NAME+'.kicad_pcb')),b)

project={'meta':{'filename':NAME+'.kicad_pro','version':1},'board':{'design_settings':{'rules':{'min_clearance':0.15,'min_track_width':0.15,'min_via_diameter':0.6,'min_through_hole_diameter':0.2,'min_copper_edge_clearance':0.3,'solder_mask_to_copper_clearance':0.0,'min_silk_clearance':0.1,'min_silk_text_height':0.8,'min_silk_text_thickness':0.12},'rule_severities':{}}},'net_settings':{'classes':[{'name':'Default','clearance':0.2,'track_width':0.2,'via_diameter':0.6,'via_drill':0.3,'microvia_diameter':0.3,'microvia_drill':0.1,'diff_pair_width':0.2,'diff_pair_gap':0.25,'diff_pair_via_gap':0.25}],'net_colors':None,'netclass_assignments':None,'netclass_patterns':[]},'schematic':{'erc_exclusions':[]},'text_variables':{}}
(ROOT/(NAME+'.kicad_pro')).write_text(json.dumps(project,indent=2),encoding='utf-8')
(ROOT/'design_manifest.json').write_text(json.dumps({'name':NAME,'outline_mm':[25,25,525,525],'schematic_uuid':rootid,'components':components,'nets':netnames},indent=2),encoding='utf-8')
with (ROOT/'outputs'/'BOM.csv').open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.writer(f); w.writerow(['Reference','Value','Manufacturer','MPN','Footprint','Quantity','Status'])
    for c in components:
        if not c['ref'].startswith('#'): w.writerow([c['ref'],c['value'],c['maker'],c['mpn'],c['fp'],1,'P1 PROVISIONAL'])
print('Created',NAME,'schematic and placed PCB;',len(components),'schematic items;',len(netnames),'nets')
