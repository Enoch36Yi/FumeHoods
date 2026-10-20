"""Small KiCad S-expression reader and deterministic identifiers for CAD generation."""
import re, json, uuid, os
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
NAME = 'Firefly_pcb2'
# Board outline (x0, y0, x1, y1) in KiCad mm: 160 x 60 mm, trimmed to the populated region.
OUTLINE_MM = (30.0, 25.0, 190.0, 85.0)
KICAD = Path(os.environ.get('KICAD_ROOT',r'C:\Program Files\KiCad\10.0'))
SHARE = KICAD/'share'/'kicad'
NS = uuid.UUID('76a4583f-a1e5-42ab-a6e1-a7ef95b0dcd0')
def uid(s): return str(uuid.uuid5(NS,s))
def q(s): return json.dumps(str(s),ensure_ascii=False)
def parse(text):
    tokens = re.findall(r'"(?:\\.|[^"\\])*"|[()]|[^\s()]+', text)
    stack=[]; root=None
    for t in tokens:
        if t=='(':
            a=[]
            if stack: stack[-1].append(a)
            else: root=a
            stack.append(a)
        elif t==')': stack.pop()
        else: stack[-1].append(json.loads(t) if t.startswith('"') else t)
    return root
def children(n,key): return [x for x in n if isinstance(x,list) and x and x[0]==key]
def one(n,key,default=None): return next(iter(children(n,key)),default)
def symbol_raw(lib,name):
    text=(SHARE/'symbols'/(lib+'.kicad_sym')).read_text(encoding='utf-8')
    start=text.index('(symbol '+q(name)); depth=0; quoted=False; esc=False
    for i in range(start,len(text)):
        c=text[i]
        if esc: esc=False; continue
        if c=='\\' and quoted: esc=True; continue
        if c=='"': quoted=not quoted
        if not quoted:
            if c=='(': depth+=1
            elif c==')':
                depth-=1
                if depth==0: return text[start:i+1]
    raise ValueError(name)
def pin_data(raw):
    data=parse(raw); pins=[]
    for sub in children(data,'symbol'):
        for pin in children(sub,'pin'):
            at=one(pin,'at')
            pins.append({'num':one(pin,'number')[1],'name':one(pin,'name')[1],
                         'x':float(at[1]),'y':float(at[2]),'angle':float(at[3]),'type':pin[1]})
    return pins
