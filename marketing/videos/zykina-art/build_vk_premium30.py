#!/usr/bin/env python3
"""30-second original-image VK ad for ZYKINA ART. Self-contained and deterministic.

Run from repo root: python marketing/videos/zykina-art/build_vk_premium30.py
Requires Pillow, numpy, opencv-python-headless, ffmpeg. Does not modify source artwork.
"""
import argparse, math, os, subprocess, wave
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import numpy as np
import cv2

ROOT=Path(__file__).resolve().parents[3] if 'marketing' in Path(__file__).parts else Path.cwd()
# Pick repository root even when run as a standalone file for testing.
if not (ROOT/'public'/'assets').is_dir(): ROOT=Path.cwd()
ASSETS=ROOT/'public'/'assets'
GOLD=(219,179,125); LIGHT=(242,229,208); MUTED=(197,182,161)
DUR=[2.8,3.4,3.6,3.4,3.5,3.3,3.0,3.0,4.0]
assert abs(sum(DUR)-30)<.01
SCENES=[
 {'path':'interiors/2/interior-mwlat1wo-1.webp','kind':'intro','tag':'01 / ИСКУССТВО В ИНТЕРЬЕРЕ', 'title':['ПРОСТРАНСТВО','ЧУВСТВУЕТ'], 'sub':'Иногда достаточно одной детали'},
 {'path':'interiors/2/interior-mwlahicl-1.webp','kind':'photo','tag':'01 / СОВРЕМЕННЫЙ ЛОФТ','title':['Характер','в деталях'], 'sub':'ЗЕМЛЯ И ЗОЛОТО','right':'ГЛУБИНА И ФАКТУРА'},
 {'path':'interiors/1/interior-mwl9pdq7-1.webp','kind':'photo','tag':'02 / СОВРЕМЕННЫЙ МИНИМАЛИЗМ','title':['Баланс','и свет'], 'sub':'ЗОЛОТОЙ ЛИСТ','right':'АРТ КАК АКЦЕНТ'},
 {'path':'interiors/3/interior-mwla75tt-1.webp','kind':'photo','tag':'03 / СОВРЕМЕННАЯ КЛАССИКА','title':['Тепло','золотых линий'], 'sub':'ЗОЛОТОЙ РИТМ','right':'РИТМ • КОМПОЗИЦИЯ'},
 {'path':'interiors/5/interior-mwlaulw0-1.webp','kind':'photo','tag':'04 / СОВРЕМЕННАЯ ЭКЛЕКТИКА','title':['Смелость','формы'], 'sub':'КРЫЛЬЯ','right':'КОМПОЗИЦИЯ И МАСШТАБ'},
 {'path':'interiors/4/interior-mwlangeo-1.webp','kind':'photo','tag':'05 / ВЫРАЗИТЕЛЬНЫЙ АКЦЕНТ','title':['Точка','притяжения'], 'sub':'ЗОЛОТОЕ ПЕРО','right':'ЗОЛОТО • СВЕТ • РЕЛЬЕФ'},
 {'path':'картины/19/detail-mwl1bksv-1.webp','kind':'macro','tag':'06 / ФАКТУРА КРУПНЫМ ПЛАНОМ','title':['Почувствуйте','материал'], 'sub':'ПЛАСТИКА • СВЕТ • ОБЪЁМ','right':'КАЖДАЯ ДЕТАЛЬ ВАЖНА'},
 {'path':'interiors/2/interior-mwlat1wo-1.webp','kind':'choice','tag':'ВЫБЕРИТЕ СВОЁ СОЧЕТАНИЕ','title':['Искусство','для вашего дома'], 'sub':'ПОД БУДУЩИЙ ИНТЕРЬЕР','right':'ИНДИВИДУАЛЬНЫЙ ВЫБОР'},
 {'path':'interiors/5/interior-mwlaulw0-1.webp','kind':'outro','tag':'СТУДИЯ ЕКАТЕРИНЫ ЗЫКИНОЙ','title':['ZYKINA','ART'], 'sub':'ИСКУССТВО, КОТОРОЕ СОЗДАЁТ АТМОСФЕРУ'},
]

def path_font(*names):
    for name in names:
        p=Path(name)
        if p.is_file():return str(p)
    return '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
SERIF=path_font('/usr/share/fonts/truetype/liberation2/LiberationSerif-Regular.ttf','/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf')
ITAL=path_font('/usr/share/fonts/truetype/liberation2/LiberationSerif-Italic.ttf','/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf')
SANS=path_font('/usr/share/fonts/truetype/lato/Lato-Regular.ttf','/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
BOLD=path_font('/usr/share/fonts/truetype/lato/Lato-Semibold.ttf','/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf')

def font(sz,kind='sans'):
    return ImageFont.truetype({'sans':SANS,'bold':BOLD,'serif':SERIF,'italic':ITAL}[kind],max(6,int(sz)))

def ease(x):
    x=max(0.,min(1.,x));return x*x*(3-2*x)

def outtext(d,at,txt,f,fill,anchor=None,spacing=None,stroke_width=0,stroke_fill=None):
    params={'font':f,'fill':fill}
    if anchor:params['anchor']=anchor
    if spacing is not None:params['spacing']=spacing
    if stroke_width:params.update(stroke_width=stroke_width,stroke_fill=stroke_fill)
    d.text(at,txt,**params)

def fit_foreground(im,W,H,zoom=1.0,offset=0):
    # Always show the COMPLETE original work and furniture scene, preserving proportions.
    maxw=int(W*.98*zoom);maxh=int(H*.61*zoom)
    ratio=min(maxw/im.width,maxh/im.height)
    dest=(max(1,int(im.width*ratio)),max(1,int(im.height*ratio)))
    return im.resize(dest,Image.Resampling.LANCZOS)

class SceneAssets:
 def __init__(self,W,H):
    self.W,self.H=W,H;self.paths=[];self.back=[];self.fore=[]
    for sc in SCENES:
      p=ASSETS/sc['path']
      if not p.is_file():raise FileNotFoundError('Missing original art / interior image: '+str(p))
      src=Image.open(p).convert('RGB');self.paths.append(str(p))
      # Blur-only background. True original in the sharp inset stays unchanged.
      rs=max(W/src.width,H/src.height)
      bg=src.resize((math.ceil(src.width*rs),math.ceil(src.height*rs)),Image.Resampling.LANCZOS)
      x=(bg.width-W)//2;y=(bg.height-H)//2
      bg=bg.crop((x,y,x+W,y+H)).filter(ImageFilter.GaussianBlur(max(20,int(W*.045))))
      bg=ImageEnhance.Brightness(bg).enhance(.38 if sc['kind']=='outro' else .49)
      self.back.append(np.asarray(bg,dtype=np.uint8))
      self.fore.append(src)

 def frame(self,k,t):
    W,H=self.W,self.H;sc=SCENES[k];duration=DUR[k];p=t/duration
    out=Image.fromarray(self.back[k]).convert('RGBA');d=ImageDraw.Draw(out,'RGBA')
    # Fine gold top/bottom rules with a subtle linear reveal.
    a=ease(min(1.,t/.8));top=int(H*.084);xx=int(W*.075);rw=int(W*.85)
    d.line((xx,top,xx+int(rw*a),top),fill=(*GOLD,190),width=max(1,int(W*.0014)))
    d.line((xx,int(H*.926),xx+rw,int(H*.926)),fill=(*GOLD,105),width=max(1,int(W*.001)))
    if sc['kind']=='outro':
       # Quiet outro with a subtle framed real-life work, small enough for large type.
       pic=fit_foreground(self.fore[k],W,H,zoom=.73)
       px=(W-pic.width)//2;py=int(H*.16)
       shadow=Image.new('RGBA',(pic.width+30,pic.height+30),(0,0,0,0));sd=ImageDraw.Draw(shadow)
       sd.rounded_rectangle((14,14,pic.width+16,pic.height+16),radius=10,fill=(0,0,0,155))
       shadow=shadow.filter(ImageFilter.GaussianBlur(18));out.alpha_composite(shadow,(px-15,py-15))
       out.paste(pic,(px,py));d=ImageDraw.Draw(out,'RGBA')
       d.rectangle((0,int(H*.49),W,H),fill=(15,12,10,243))
       outtext(d,(W//2,int(H*.535)),'ZYKINA',font(W*.090,'serif'),LIGHT,anchor='mt')
       outtext(d,(W//2,int(H*.612)),'ART',font(W*.108,'serif'),GOLD,anchor='mt')
       d.line((int(W*.25),int(H*.71),int(W*.75),int(H*.71)),fill=(*GOLD,165),width=2)
       outtext(d,(W//2,int(H*.73)),'Авторское искусство для интерьера',font(W*.026,'sans'),LIGHT,anchor='mt')
       outtext(d,(W//2,int(H*.798)),'ПОДПИСАТЬСЯ',font(W*.028,'bold'),(28,23,18),anchor='mt',stroke_width=0)
       # Gold CTA pill.
       x1=int(W*.18);x2=int(W*.82);y1=int(H*.782);y2=int(H*.844)
       d.rounded_rectangle((x1,y1,x2,y2),radius=16,fill=(*GOLD,245))
       outtext(d,(W//2,(y1+y2)//2),'ПОДПИСАТЬСЯ',font(W*.023,'bold'),(29,22,15),anchor='mm')
       outtext(d,(W//2,int(H*.873)),'vk.ru/club243380288',font(W*.035,'sans'),LIGHT,anchor='mt')
       return out.convert('RGB')

    # Foreground: preserved art with restrained Ken Burns camera movement.
    photo=fit_foreground(self.fore[k],W,H,zoom=1+.052*ease(p))
    fx=(W-photo.width)//2+int((p-.5)*W*.025);fy=int(H*.193)-int(p*H*.015)
    shadow=Image.new('RGBA',(photo.width+28,photo.height+28),(0,0,0,0));sd=ImageDraw.Draw(shadow)
    sd.rectangle((14,14,14+photo.width,14+photo.height),fill=(0,0,0,156))
    shadow=shadow.filter(ImageFilter.GaussianBlur(20));out.alpha_composite(shadow,(fx-14,fy-14))
    out.paste(photo,(fx,fy))
    d=ImageDraw.Draw(out,'RGBA')
    d.rectangle((fx,fy,fx+photo.width,fy+photo.height),outline=(*GOLD,135),width=max(1,int(W*.0014)))
    # Header and shot marker.
    outtext(d,(xx,int(H*.095)),'ZYKINA  ART',font(W*.038,'serif'),LIGHT)
    d.text((W-xx,int(H*.095)),'•',font=font(W*.031,'sans'),fill=GOLD,anchor='ra')
    outtext(d,(xx,int(H*.139)),sc['tag'],font(W*.021,'bold'),GOLD)
    # Dynamic information accents with animated traced lines.
    if sc['kind'] not in ('intro',):
      ty=int(H*.755);left=int(W*.09)
      d.line((left,ty-17,left+int(W*.15*ease((t-.15)/.7)),ty-17),fill=(*GOLD,230),width=3)
      tit=sc['title'];outtext(d,(left,ty),tit[0],font(W*.072,'serif'),LIGHT)
      outtext(d,(left,ty+int(H*.06)),tit[1],font(W*.072,'italic'),GOLD)
      outtext(d,(left,ty+int(H*.128)),sc['sub'],font(W*.022,'bold'),LIGHT)
      if sc.get('right'):
       outtext(d,(left,ty+int(H*.153)),sc['right'],font(W*.017,'sans'),MUTED)
      # Callout near the art itself: moving pin, thin line, transparent plate.
      if p>.27:
       phase=ease((p-.27)/.27);cx=int(W*.65);cy=fy+int(photo.height*.26)
       tx=int(W*.83);ty2=fy+int(photo.height*.16)
       d.ellipse((cx-4,cy-4,cx+4,cy+4),fill=(*GOLD,245))
       d.line((cx,cy, cx+int((tx-cx)*phase),cy+int((ty2-cy)*phase)),fill=(*GOLD,int(190*phase)),width=2)
       d.rounded_rectangle((int(W*.61),ty2-21,int(W*.96),ty2+19),radius=5,fill=(24,19,17,int(185*phase)))
       outtext(d,(int(W*.626),ty2-14),'СВЕТ · ФАКТУРА',font(W*.016,'bold'),(*LIGHT,int(235*phase)))
    else:
      # Intro editorial typography. Kept large and phone-readable.
      z=ease((t-.1)/.85)
      barY=int(H*.71);d.line((int(W*.11),barY,int(W*(.11+.42*z)),barY),fill=(*GOLD,236),width=3)
      outtext(d,(int(W*.1),int(H*.755)),'ИСКУССТВО',font(W*.084,'serif'),LIGHT)
      outtext(d,(int(W*.1),int(H*.823)),'МЕНЯЕТ ПРОСТРАНСТВО',font(W*.048,'italic'),GOLD)
      outtext(d,(int(W*.1),int(H*.893)),'Авторские картины для вашего дома',font(W*.020,'sans'),LIGHT)
    # Bottom subtle chapter progress.
    y=int(H*.944);start=int(W*.1);gap=int(W*.013);length=(int(W*.8)-8*gap)//9
    for i in range(9):
      col=(*GOLD,240) if i==k else (*MUTED,85)
      d.rounded_rectangle((start+i*(length+gap),y,start+i*(length+gap)+length,y+4),radius=2,fill=col)
    # Scene fade, editorial not flashy.
    alpha=min(1.,t/.25,(duration-t)/.23)
    if alpha<1.0:
     dim=Image.new('RGBA',(W,H),(11,8,7,int(255*(1-max(0,alpha)))))
     out=Image.alpha_composite(out,dim)
    return out.convert('RGB')

def music(path,seconds=30,sr=44100):
    t=np.arange(seconds*sr,dtype=np.float64)/sr
    y=np.zeros(len(t),np.float64)
    def add_note(freq,start,dur,vol=.07,pad=False):
      a=int(start*sr);b=min(len(y),int((start+dur)*sr));n=max(0,b-a)
      if not n:return
      tt=np.arange(n)/sr
      if pad:
        env=(1-np.exp(-tt*3))*(np.minimum(1.,(dur-tt)/.8).clip(0,1))
        wave1=np.sin(2*np.pi*freq*tt)+.33*np.sin(2*np.pi*(freq*1.003)*tt)
      else:
        env=(1-np.exp(-tt*60))*np.exp(-tt*2.9)
        wave1=np.sin(2*np.pi*freq*tt)+.18*np.sin(2*np.pi*freq*2*tt)
      y[a:b]+=vol*env*wave1
    chords=[[146.83,174.61,220.0],[130.81,164.81,196.0],[146.83,185.0,220.0],[110,164.81,196.0]]
    for bar in range(8):
      start=bar*3.75
      for n in chords[bar%4]:add_note(n,start,4.15,.045,True)
      for beat in range(4):
       st=start+beat*.9375
       for n in [293.66,349.23,440][(bar+beat)%3:(bar+beat)%3+1]:add_note(n,st,.9,.042)
    rng=np.random.default_rng(3401)
    # Airy impacts, hand-crafted gentle swish, no licensed audio samples.
    for st in np.cumsum(DUR)[:-1]:
      a=int(max(0,st-.24)*sr);b=min(len(y),int((st+.08)*sr))
      nn=b-a
      if nn>0:
        noise=rng.normal(size=nn)
        env=np.sin(np.linspace(0,np.pi,nn))**2
        y[a:b]+=noise*env*.012
    y*=np.minimum(1.,t/1.0)*np.minimum(1.,(30-t)/1.8)
    # Gentle peak and stereo width with a subtle delay.
    y=np.tanh(y*1.45);lat=int(.014*sr)
    left=y;right=np.roll(y,lat)*.95
    pcm=(np.stack([left,right],axis=1)*26000).clip(-32768,32767).astype('<i2')
    with wave.open(str(path),'wb') as w:
      w.setnchannels(2);w.setsampwidth(2);w.setframerate(sr);w.writeframes(pcm.tobytes())


# Brand-safe art animation: time-varying highlights derived ONLY from original
# photograph edges; no painting reconstruction, invention or geometry changes.
PAINT_BBOX=[
 (270,45,410,250),(162,22,277,188),(175,70,385,192),
 (269,35,449,202),(129,39,492,232),(145,20,317,270),
 (0,0,640,400),(270,45,410,250),None]
class PremiumAssets(SceneAssets):
 def __init__(self,W,H):
  super().__init__(W,H);self.edges=[]
  for k,im in enumerate(self.fore):
   src=np.asarray(im.convert('RGB'))
   gray=cv2.cvtColor(src,cv2.COLOR_RGB2GRAY)
   edge=cv2.Canny(cv2.GaussianBlur(gray,(3,3),.5),55,143).astype('float32')/255
   area=np.zeros_like(edge)
   if PAINT_BBOX[k]:
    x1,y1,x2,y2=PAINT_BBOX[k];area[y1:y2,x1:x2]=edge[y1:y2,x1:x2]
   self.edges.append(area)
 def frame(self,k,t):
  W,H=self.W,self.H;sc=SCENES[k];duration=DUR[k];p=t/duration
  out=super().frame(k,t).convert('RGBA')
  if k==8:return out.convert('RGB')
  photo=fit_foreground(self.fore[k],W,H,zoom=1+.052*ease(p))
  fw,fh=photo.size;fx=(W-fw)//2+int((p-.5)*W*.025);fy=int(H*.193)-int(p*H*.015)
  bbox=PAINT_BBOX[k]
  if bbox:
   edge=cv2.resize(self.edges[k],(fw,fh),interpolation=cv2.INTER_LINEAR)
   gx=np.arange(fw,dtype='float32');center=-fw*.13+fw*1.28*ease((p-.12)/.72)
   band=np.exp(-((gx-center)/(fw*.16))**2)[None,:]
   fade=max(0.,min(1.,t/.6,(duration-t)/.45))
   mask=np.clip((edge*.31+cv2.GaussianBlur(edge,(0,0),2)*.26)*band*fade,0,.38)
   light=np.zeros((fh,fw,4),dtype='uint8')
   light[:,:,:3]=[255,208,139];light[:,:,3]=(mask*255).astype('uint8')
   out.alpha_composite(Image.fromarray(light,'RGBA'),(fx,fy))
  d=ImageDraw.Draw(out,'RGBA')
  if k in (1,2,3,4,5,7) and bbox:
   x1,y1,x2,y2=bbox
   px=int(fx+(x1+(x2-x1)*.46)*fw/self.fore[k].width)
   py=int(fy+(y1+(y2-y1)*.33)*fh/self.fore[k].height)
   a=ease((t-.55)/.62)
   if a:
    xx=min(W-70,int(px+W*.20*a));yy=max(120,int(py-H*.038*a))
    line=Image.new('RGBA',(W,H),(0,0,0,0));ld=ImageDraw.Draw(line,'RGBA')
    ld.line([(px,py),(int(px+W*.052*a),yy),(xx,yy)],fill=(*GOLD,int(222*a)),width=max(2,int(W*.0025)),joint='curve')
    ld.ellipse((px-5,py-5,px+5,py+5),fill=(*GOLD,int(235*a)))
    out=Image.alpha_composite(out,line.filter(ImageFilter.GaussianBlur(6)))
    out=Image.alpha_composite(out,line);d=ImageDraw.Draw(out,'RGBA')
  if k==2:
   y=int(H*.60);f=ease((t-.5)/.5)
   d.rounded_rectangle((int(W*.075),y-48,int(W*.925),y+130),radius=12,fill=(22,16,14,int(197*f)),outline=(*GOLD,int(129*f)),width=1)
   d.text((int(W*.10),y-36),'ПАЛИТРА ПРОИЗВЕДЕНИЯ',font=font(W*.024,'bold'),fill=(*LIGHT,int(242*f)))
   for j,(label,color) in enumerate([('СЛИВОЧНЫЙ','#E6DFD0'),('ЗОЛОТО','#B99A60'),('ГРАФИТ','#2F2A26'),('ТАУП','#B7A69A')]):
    a=ease((t-.68-j*.15)/.35);x=int(W*(.105+j*.204));cy=y+22;r=int(W*.032*a)
    if r<1:continue
    d.ellipse((x,cy,x+2*r,cy+2*r),fill=color,outline=(*LIGHT,180),width=2)
    d.text((x,cy+2*r+14),label,font=font(W*.017,'bold'),fill=(*LIGHT,int(228*a)))
  if k==6:
   y=int(H*.60);f=ease((t-.24)/.5)
   d.rounded_rectangle((int(W*.072),y-48,int(W*.928),y+207),radius=13,fill=(20,15,13,int(206*f)),outline=(*GOLD,int(138*f)),width=2)
   d.text((int(W*.099),y-34),'ВОЗМОЖНЫЕ МАТЕРИАЛЫ И ТЕХНИКИ',font=font(W*.022,'bold'),fill=(*LIGHT,int(240*f)))
   for j,name in enumerate(['АКРИЛ','МАСЛО','ГИПС','ТЕКСТУРНАЯ ПАСТА','ТКАНЬ','ПОТАЛЬ']):
    a=ease((t-.5-j*.11)/.32);x=int(W*(.102+(j%3)*.274));yy=y+18+(j//3)*int(W*.095);ww=int(W*(.16 if len(name)<8 else .25))
    d.rounded_rectangle((x,yy,x+ww,yy+int(W*.069)),radius=7,fill=(80,59,38,int(205*a)),outline=(*GOLD,int(177*a)),width=1)
    d.text((x+9,yy+int(W*.019)),name,font=font(W*(.014 if len(name)>9 else .019),'bold'),fill=(*LIGHT,int(238*a)))
   d.text((int(W*.102),y+185),'Материалы конкретной картины уточняются у автора',font=font(W*.017,'sans'),fill=(*MUTED,int(220*f)))
  if k==7:
   y=int(H*.615);f=ease((t-.48)/.6)
   d.rounded_rectangle((int(W*.080),y-32,int(W*.920),y+117),radius=9,fill=(23,17,14,int(191*f)),outline=(*GOLD,int(115*f)),width=2)
   d.text((int(W*.103),y-20),'В КАКОМ ИНТЕРЬЕРЕ?',font=font(W*.024,'bold'),fill=(*LIGHT,int(239*f)))
   for j,name in enumerate(['МИНИМАЛИЗМ','ЛОФТ','КЛАССИКА']):
    a=ease((t-.6-j*.17)/.31);x=int(W*(.103+j*.27));ww=int(W*.244)
    d.rounded_rectangle((x,y+33,x+ww,y+int(W*.088)),radius=7,fill=(75,55,39,int(211*a)),outline=(*GOLD,int(165*a)),width=1)
    d.text((x+8,y+int(W*.05)),name,font=font(W*.017,'bold'),fill=(*LIGHT,int(240*a)))
  return out.convert('RGB')

def render(outdir,W,H,fps,short=False):
    outdir.mkdir(parents=True,exist_ok=True)
    assets=PremiumAssets(W,H)
    wav=outdir/'ZYKINA_ART_Original_Music.wav';music(wav,seconds=30)
    out=outdir/'ZYKINA_ART_VK_Premium_30s_1080x1920.mp4'
    frames=round((2.6 if short else 30.0)*fps)
    cmd=['ffmpeg','-hide_banner','-loglevel','error','-y','-f','rawvideo','-pixel_format','rgb24','-video_size',f'{W}x{H}','-framerate',str(fps),'-i','-','-i',str(wav),'-map','0:v','-map','1:a','-t',str(frames/fps),'-c:v','libx264','-preset','medium','-crf','21','-pix_fmt','yuv420p','-colorspace','bt709','-color_primaries','bt709','-color_trc','bt709','-c:a','aac','-b:a','160k','-movflags','+faststart',str(out)]
    proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=subprocess.PIPE)
    bounds=np.cumsum([0]+DUR)
    try:
     for j in range(frames):
      t=j/fps;k=int(np.searchsorted(bounds,t,side='right')-1);k=min(k,len(DUR)-1)
      frame=assets.frame(k,max(0,t-bounds[k]));proc.stdin.write(np.asarray(frame,dtype=np.uint8).tobytes())
      if j%(fps*5)==0:print('frame',j,'/',frames,flush=True)
     proc.stdin.close();err=proc.stderr.read().decode('utf-8','replace')
     rc=proc.wait()
     if rc!=0:raise RuntimeError('ffmpeg encode: '+err[-1500:])
    except Exception:
     proc.kill();raise
    print('RENDERED',out,'BYTES',out.stat().st_size,flush=True)
    return out

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--outdir',default='marketing/videos/zykina-art/output');parser.add_argument('--width',type=int,default=1080);parser.add_argument('--height',type=int,default=1920);parser.add_argument('--fps',type=int,default=25);parser.add_argument('--short',action='store_true');args=parser.parse_args()
    render(Path(args.outdir),args.width,args.height,args.fps,args.short)