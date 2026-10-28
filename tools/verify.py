"""Execute actual patched RV32 instructions against stock menu callers.

UI primitives are captured to a software framebuffer. The upstream stock
instruction inventory supplies WCH instruction semantics. No device is opened.
"""
from pathlib import Path
import hashlib, json, re, struct, sys, types, io, os
from PIL import Image, ImageDraw, ImageFont
from common import ROOT, BUILD, UPSTREAM as REPO, ORIGINAL, font_path
sys.path.insert(0,str(REPO/'tools'))
source=(REPO/'tools/rv32_trace.py').read_text()
source=source.replace('from common import ROOT, BUILD, UPSTREAM as REPO, ORIGINAL, font_paths[1]',f'ROOT=Path({str(REPO)!r})')
source=source.replace("(ROOT/'DMT-99_V2.4_20240306.bin')",f'Path({str(ORIGINAL)!r})')
module=types.ModuleType('stock_trace');module.__file__=str(REPO/'tools/rv32_trace.py')
exec(compile(source,module.__file__,'exec'),module.__dict__)
TraceMachine=module.TraceMachine
STOCK=dict(module.INSTRUCTIONS)
original=ORIGINAL.read_bytes()
candidate=(BUILD/'DMT99RU.BIN').read_bytes()
manifest=json.loads((ROOT/'build/manifest.json').read_text())

def compiled_inventory():
 rows={}
 for line in (BUILD/'overlay.disasm').read_text().splitlines():
  m=re.match(r'\s*([0-9a-f]+):\s+([0-9a-f]{8})\s+(\S+)\s*(.*)',line)
  if not m:continue
  addr=int(m[1],16);op=m[3];args=m[4].split('#')[0].split('<')[0].strip()
  a=[p.strip() for p in args.split(',')] if args else []
  if op=='zext.b':op='andi';a=[a[0],a[1],'255']
  elif op=='seqz':op='sltiu';a=[a[0],a[1],'1']
  elif op=='snez':op='sltu';a=[a[0],'zero',a[1]]
  elif op=='bgtu':op='bltu';a=[a[1],a[0],a[2]]
  elif op=='bgt':op='blt';a=[a[1],a[0],a[2]]
  elif op=='bleu':op='bgeu';a=[a[1],a[0],a[2]]
  elif op=='ble':op='bge';a=[a[1],a[0],a[2]]
  elif op=='blez':op='bge';a=['zero',a[0],a[1]]
  elif op=='bgez':op='bge';a=[a[0],'zero',a[1]]
  elif op=='bltz':op='blt';a=[a[0],'zero',a[1]]
  elif op=='bgtz':op='blt';a=['zero',a[0],a[1]]
  elif op=='jalr':
   mm=re.fullmatch(r'(-?\d+)\((\w+)\)',a[-1])
   if mm:a=[a[0] if len(a)>1 else 'ra',mm[2],mm[1]]
   elif len(a)==1:a=['ra',a[0],'0']
   elif len(a)==2:a=[a[0],a[1],'0']
  if op in ['beq','bne','bge','bgeu','blt','bltu','beqz','bnez','j','jal']:
   a[-1]='0x'+a[-1]
  for i,s in enumerate(a):
   mm=re.fullmatch(r'(-?\d+)\((\w+)\)',s)
   if mm:a[i]=hex(int(mm[1]))+'('+mm[2]+')'
  rows[addr]={'address':hex(addr),'text':op+(' '+','.join(a) if a else ''),'length':4,'bytes':struct.pack('<I',int(m[2],16)).hex()}
 for p in manifest['patches']:
  rows[int(p['address'],16)]={'address':p['address'],'text':'j '+p['target'],'length':4,'bytes':p['after']}
 return rows

PATCHED={**STOCK,**compiled_inventory()}
flash=(REPO/'artifacts/flash/original/dmt99_flash_1.bin').read_bytes()
assets={}
for f in json.loads((REPO/'analysis/flash_files.json').read_text())['active']:
 if f['path'].lower().endswith('.jpg'):
  raw=b''.join(flash[e['offset']:e['offset']+e['size']] for e in f['physical_extents'])[:f['size']]
  assets[f['path'].lower()]=Image.open(io.BytesIO(raw)).convert('RGB')
font_path=font_path()

def rgb(c):return ((c>>11&31)*255//31,(c>>5&63)*255//63,(c&31)*255//31)

class Canvas:
 def __init__(self,patched=True,lang=0):
  module.INSTRUCTIONS=PATCHED if patched else STOCK
  self.m=TraceMachine();self.m.image=candidate if patched else original
  self.m.write(0x2000003e,2,lang);self.m.write(0x20000205,1,0)
  pref=b'menu/english/' if lang else b'menu/chinese/'
  self.m.ram[0x298:0x298+len(pref)+1]=pref+b'\0'
  self.im=Image.new('RGB',(320,240));self.d=ImageDraw.Draw(self.im)
  self.chinese=[];self.events=[];self.out_of_bounds=[];self.ru=[]
  if patched:
   def observe(machine):
    if machine.pc==manifest['symbols']['ru_text']:
     x,y,p,h,w,color=machine.r[10:16]
     self.ru.append((x,y,machine.string(p).encode('latin1').decode('utf-8'),h,w,color))
   self.m.instruction_hook=observe
  self.m.hooks.update({0x7f00:self.pixel,0x8a02:self.fill,0x8050:self.line,0x8194:self.border,0x80d4:self.cutfill,0x81ce:self.cutborder,
   0x8266:self.char,0x8588:self.ascii,0x85cc:self.text,0x1a360:self.bitmap,0x14408:lambda *_:0,0x143e0:lambda *_:0})
  # Keep patched entry points executable. Unpatched font/icon primitives are
  # software-rendered; original JPEG decompression is substituted by the exact
  # resource bytes only after execution reaches its stock trampoline/body.
  for addr in [0x8a5a,0x8b5c,0x8c64,0x8d6c]:self.m.hooks[addr]=self.cn_glyph
  if patched:self.m.hooks[manifest['symbols']['original_image']]=self.jpeg
  else:self.m.hooks[0x678c]=self.jpeg
  self.m.hooks[0x83d6 if not patched else manifest['symbols']['original_ascii_char']]=self.ascii_char
 def pixel(self,m,x,y,c,*_):
  if x<320 and y<240:self.im.putpixel((x,y),rgb(c))
  else:self.out_of_bounds.append((x,y))
  return 0
 def fill(self,m,x,y,x1,y1,c,*_):
  self.events.append(('fill',x,y,x1,y1,c))
  if x<=x1 and y<=y1:self.d.rectangle((x,y,min(x1,319),min(y1,239)),fill=rgb(c))
  return 0
 def line(self,m,x,y,x1,y1,c,*_):self.d.line((x,y,x1,y1),fill=rgb(c));return 0
 def border(self,m,x,y,x1,y1,c,*_):self.d.rectangle((x,y,x1,y1),outline=rgb(c));return 0
 def cutfill(self,m,x,y,x1,y1,cut,c,*_):return self.fill(m,x,y,x1,y1,c)
 def cutborder(self,m,x,y,x1,y1,cut,c,*_):return self.border(m,x,y,x1,y1,c)
 def ascii_char(self,m,x,y,ch,size,fg,bg,trans,*_):
  if 32<=ch<127:self.d.text((x,y),chr(ch),font=ImageFont.truetype(font_path,max(8,size-2)),fill=rgb(fg))
  return 0
 def char(self,m,x,y,ch,size,c,trans,*_):
  if size==16 and (ch in [ord('X'),ord('Y'),ord('Z'),ord('J')]):
   special=3 if ch==ord('J') else ch-ord('X');at=0x1f820-0x6400+special*32
   data=original[at:at+32]
   for xx in range(16):
    for yy in range(16):
     if data[xx*2+yy//8]&(0x80>>(yy%8)) and x+xx<320 and y+yy<240:self.im.putpixel((x+xx,y+yy),rgb(c))
   return 0
  return self.ascii_char(m,x,y,ch,size,c,0,trans)
 def ascii(self,m,x,y,p,fg,bg,size,trans,*_):
  s=m.string(p);self.events.append(('ascii',x,y,s,fg,size))
  self.d.text((x,y),s,font=ImageFont.truetype(font_path,max(8,size-2)),fill=rgb(fg));return 0
 def text(self,m,x,y,w,h,size,c,p,*_):return self.ascii(m,x,y,p,c,c,size,1)
 def cn_glyph(self,m,x,y,p,fg,bg,size=16,trans=1,*_):
  raw=bytes([m.read(p,1),m.read(p+1,1)])
  if raw not in [b'\xa1\xe6',b'\xa1\xf8',b'\xa8\x48']:
   self.chinese.append((hex(p),raw.hex(),x,y))
  # Preserve Celsius/Fahrenheit and triangle symbols in preview screenshots.
  offsets={12:(0x21dbc,12,26),16:(0x21ef4,63,34),24:(0x22754,49,74),32:(0x23580,1,130)}
  if size in offsets:
   start,count,stride=offsets[size]
   for n in range(count):
    at=start+n*stride-0x6400
    if original[at:at+2]==raw:
     data=original[at+2:at+stride]
     for yy in range(size):
      for xx in range(size):
       if data[yy*((size+7)//8)+xx//8]&(1<<(xx%8)) and x+xx<320 and y+yy<240:self.im.putpixel((x+xx,y+yy),rgb(fg))
     break
  return 0
 def bitmap(self,*_):return 0
 def jpeg(self,m,p,x,y,*_):
  s=m.string(p).lower();self.events.append(('image',s,x,y))
  if len(s)>2 and s[1]==':':s=s[3:] if s[2]=='/' else s[2:]
  if s in assets:self.im.paste(assets[s],(x,y))
  return 0
 def call(self,addr,*args):
  sp=self.m.r[2];gp=self.m.r[3]
  saved=self.m.r[8:10]+self.m.r[18:28]
  result=self.m.call(addr,*args,limit=3000000)
  assert self.m.r[2]==sp,('stack',hex(addr),hex(sp),hex(self.m.r[2]))
  assert self.m.r[3]==gp,('gp',hex(addr))
  assert self.m.r[8:10]+self.m.r[18:28]==saved,('callee-saved',hex(addr))
  return result
 def save(self,name):
  out=ROOT/'build/previews';out.mkdir(exist_ok=True);self.im.save(out/(name+'.png'))

def main():
 checks=[]
 # Only explicitly reviewed entry jumps and the version label may differ in
 # the original application area; everything else, including ASIC logic,
 # setting persistence and numeric rendering, must remain byte-identical.
 allowed=set()
 for p in manifest['patches']:allowed.update(range(p['offset'],p['offset']+4))
 v=manifest['version_edit'];allowed.update(range(v['offset'],v['offset']+len(v['before'])))
 diff={i for i,(a,b) in enumerate(zip(original,candidate)) if a!=b}
 assert diff<=allowed;assert candidate[:0x1d8]==original[:0x1d8]
 checks.append('original code unchanged outside five UI entry jumps and version label')
 # Settings scenes execute stock code, then route text through real RV32 overlay.
 for layout in [0,1]:
  for pc,name in [(0x153d0,'language'),(0x15e9e,'brightness'),(0x16242,'auto-off')]:
   c=Canvas();c.m.write(0x20000205,1,layout);c.call(pc);c.save(f'ru-{layout}-{name}')
   assert not c.chinese,(name,c.chinese);assert not c.out_of_bounds
  c=Canvas();c.call(0x18ad2 if not layout else 0x19366,1,1,0);c.save(f'ru-{layout}-categories')
  assert not c.chinese
 checks.append('stock settings scenes and category rendering execute in both layouts without Chinese glyph calls')
 # Both native string and original save/restore trampoline are executed.
 for lang in [0,1]:
  c=Canvas(lang=lang);c.call(0x8e46,160,40,0x247c0,0xffff,0xffff,16,1)
  if lang==0:assert not c.chinese
  else:assert c.chinese
 checks.append('Russian text path and original English fallback preserve stack, gp, and callee-saved registers')
 # English category operation must issue exactly the stock drawing requests.
 for layout in [0,1]:
  for initial,selected,previous in [(1,1,0),(0,4,3),(0,2,1)]:
   a=Canvas(patched=False,lang=1);a.call(0x18ad2 if not layout else 0x19366,initial,selected,previous)
   b=Canvas(patched=True,lang=1);b.call(0x18ad2 if not layout else 0x19366,initial,selected,previous)
   assert a.events==b.events and a.chinese==b.chinese
 checks.append('English category drawing calls are identical to stock')
 # Image hook, overlays and untouched English delegation.
 paths=['menu/chinese/close.jpg','menu/chinese/recharge1.jpg','menu/chinese/recover1.jpg','mode/dc_v_c.jpg','mode/mode2_cap_c.jpg','history/cap_c.jpg','menu/english/recover1.jpg']
 for n,path in enumerate(paths):
  c=Canvas();c.m.ram[0x500:0x500+len(path)+1]=path.encode()+b'\0';x=131 if 'recover1' in path else 0
  c.call(0x678c,0x20000500,x,0);c.save('asset-'+str(n));assert not c.out_of_bounds
 checks.append('Russian notices and mode labels render through the patched image entry')
 for filename,reset_color,return_color in [('recover1_1.jpg',0xffff,0xfd40),('recover1_2.jpg',0xfd40,0xffff)]:
  path='menu/chinese/'+filename;c=Canvas();c.m.ram[0x500:0x500+len(path)+1]=path.encode()+b'\0';c.call(0x678c,0x20000500,143,147)
  assert next(t[-1] for t in c.ru if t[2]=='Сбросить')==reset_color
  assert next(t[-1] for t in c.ru if t[2]=='Назад')==return_color
 checks.append('reset confirmation highlights preserve Return/Reset semantics')
 # Run the real original JPEG prologue/body/epilogue on the file-not-found
 # branch, rather than stubbing the trampoline. No file system is accessed.
 c=Canvas(lang=1);del c.m.hooks[manifest['symbols']['original_image']]
 c.m.hooks[0xf54a]=lambda *_:1
 c.m.ram[0x500:0x509]=b'none.jpg\0'
 assert c.call(0x678c,0x20000500,0,0)==1
 c=Canvas(lang=1);del c.m.hooks[manifest['symbols']['original_ascii_char']]
 c.call(0x83d6,10,10,ord('E'),16,0xffff,0,1)
 checks.append('original JPEG and ASCII trampolines execute their stock save/restore code correctly')
 resource_cases=0
 for path in assets:
  if not (path.startswith('menu/chinese/') or ('_c.' in path and path.startswith(('mode/','history/')))):continue
  c=Canvas();c.m.ram[0x500:0x500+len(path)+1]=path.encode()+b'\0';c.call(0x678c,0x20000500,0,0)
  assert not [e for e in c.events if e[0]=='image'],('untranslated image',path)
  assert not c.out_of_bounds
  resource_cases+=1
 checks.append(f'{resource_cases} Chinese-specific stock image labels replaced without external Flash writes')
 # Complete stock menu state rendering, including reset warning and threshold
 # pages. Blocking editor/history/system actions are isolated UI boundaries.
 menu_cases=0
 for layout in [0,1]:
  for lang in [0,1]:
   for state in range(1,33):
    c=Canvas(lang=lang);c.m.write(0x20000205,1,layout)
    for a,n,v in [(0x1d8,1,state),(0x1da,1,255),(0x1dd,1,1),(0x1de,1,1),(0x1ee,1,0),(0x40,1,0)]:c.m.write(0x20000000+a,n,v)
    c.m.stub(0x126d8,0x14578,0x8016,0x14a92,0x11086,0xdc46,0x8ed4)
    c.m.hooks[0x876a]=lambda *_:0
    c.call(0x169d4)
    if lang==0:assert not c.chinese,('menu',layout,state,c.chinese)
    assert not c.out_of_bounds,('bounds',layout,state,c.out_of_bounds[:3])
    if lang==0 and state in [1,5,13,29,32]:c.save(f'menu-{layout}-{state}')
    menu_cases+=1
 checks.append(f'{menu_cases} stock menu-state/layout/language renders passed')
 # Execute actual language-selection handlers in both directions. These must
 # preserve every stock settings and menu effect despite the rendering hooks.
 transition_cases=0
 for layout in [0,1]:
  for lang,state in [(0,15),(1,14)]:
   states=[]
   for patched in [False,True]:
    c=Canvas(patched=patched,lang=lang);c.m.write(0x20000205,1,layout)
    for a,n,v in [(0x1d8,1,state),(0x1dd,1,1),(0x1ee,1,5)]:c.m.write(0x20000000+a,n,v)
    c.call(0x15af6)
    states.append((c.m.read(0x2000003e,2),c.m.read(0x200001ee,1),bytes(c.m.ram[0x298:0x2ac])))
   assert states[0]==states[1],('language selection effects',layout,lang,states)
   transition_cases+=1
 checks.append(f'{transition_cases} actual language-change handlers preserve stock settings effects')
 # Useful composed previews: the exact patched category and settings functions.
 for layout in [0,1]:
  c=Canvas();c.m.write(0x20000205,1,layout)
  c.call(0x18ad2 if not layout else 0x19366,1,4,0);c.call(0x153d0);c.save(f'full-settings-{layout}')
 report={'candidate_sha256':hashlib.sha256(candidate).hexdigest(),'checks':checks,'hardware_validated':False,'scope':'actual RV32 overlay + stock callers; hardware primitives replaced by software canvas; not an analog or bootloader validation'}
 (ROOT/'build/verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
