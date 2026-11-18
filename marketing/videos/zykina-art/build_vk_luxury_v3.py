#!/usr/bin/env python3
"""ZYKINA ART premium 30s cinematic VK spot. Source art is never repainted.

Animation: parallax dolly, contour-based travelling highlights, physical light
tracers, staged palette labels, editorial callouts, legible typography and
material options disclaimer. Build original score (no licensed samples).
Requires Pillow, numpy, OpenCV, ffmpeg; exported MP4 H264/AAC 9:16.
"""
import argparse, math, os, subprocess, wave
from pathlib import Path
from functools import lru_cache
import numpy as np
import cv2
from PIL import Image,ImageDraw,ImageFont,ImageFilter,ImageEnhance

ROOT=Path(__file__).resolve().parents[3] if 'marketing' in Path(__file__).parts else Path('/mnt/data/zykina_video_assets/test_repo')
if not (ROOT/'public'/'assets').exists(): ROOT=Path('/mnt/data/zykina_video_assets/test_repo')
ASSETS=ROOT/'public'/'assets'
TITLES=[
 {'file':'interiors/5/interior-mwlaulw0-1.webp','scene':'hero','tag':'01  /  ЗНАКОМСТВО','title':('ИСКУССТВО','МЕНЯЕТ ПРОСТРАНСТВО'),'sub':'КРЫЛЬЯ · АВТОРСКОЕ ПАННО','bbox':(132,43,487,224)},
 {'file':'interiors/2/interior-mwlahicl-1.webp','scene':'trace','tag':'02  /  СОЧЕТАНИЕ','title':('СВЕТ И','ХАРАКТЕР'),'sub':'ЗЕМЛЯ И ЗОЛОТО · СОВРЕМЕННЫЙ ЛОФТ','bbox':(163,25,274,180)},
 {'file':'interiors/4/interior-mwlangeo-1.webp','scene':'trace','tag':'03  /  СВЕТ ПО РЕЛЬЕФУ','title':('КАЖДАЯ ЛИНИЯ','ИМЕЕТ ЗНАЧЕНИЕ'),'sub':'ЗОЛОТОЕ ПЕРО · ОБЪЁМ И ФАКТУРА','bbox':(150,23,314,264)},
 {'file':'interiors/1/interior-mwl9pdq7-1.webp','scene':'palette','tag':'04  /  ГАРМОНИЯ ОТТЕНКОВ','title':('ЦВЕТ СОЗДАЁТ','НАСТРОЕНИЕ'),'sub':'ЗОЛОТОЙ ЛИСТ · СВЕТ И ТЁПЛЫЕ ТОНА','bbox':(178,72,382,189)},
 {'file':'interiors/3/interior-mwla75tt-1.webp','scene':'trace','tag':'05  /  ИСКУССТВО В ИНТЕРЬЕРЕ','title':('СВОЙ РИТМ','У КАЖДОГО ДОМА'),'sub':'ЗОЛОТОЙ РИТМ · СОВРЕМЕННАЯ КЛАССИКА','bbox':(273,39,448,195)},
 {'file':'картины/19/detail-mwl1bksv-1.webp','scene':'materials','tag':'06  /  РАССМОТРИТЕ БЛИЖЕ','title':('МАТЕРИАЛЫ','И ФАКТУРА'),'sub':'ТИХОЕ ТЕЧЕНИЕ · МАКРОДЕТАЛЬ','bbox':(0,0,640,400)},
 {'file':'interiors/2/interior-mwlat1wo-1.webp','scene':'styles','tag':'07  /  ВАШЕ ПРОСТРАНСТВО','title':('ВЫБЕРИТЕ','СВОЁ СОЧЕТАНИЕ'),'sub':'МИНИМАЛИЗМ  ·  ЛОФТ  ·  КЛАССИКА','bbox':(269,44,407,250)},
 {'file':'interiors/5/interior-mwlaulw0-1.webp','scene':'outro','tag':'ZYKINA ART','title':('ZYKINA','ART'),'sub':'Авторское интерьерное искусство','bbox':(132,43,487,224)},
]
DUR=[3.5,3.8,3.7,3.6,3.8,4.0,3.6,4.0]
assert abs(sum(DUR)-30)<1e-5
GOLD=(225,186,128); WHITE=(253,245,227); SOFT=(190,174,152); DARK=(17,13,12)
F_SERIF='/usr/share/fonts/truetype/noto/NotoSerifDisplay-Regular.ttf'
if not Path(F_SERIF).exists():F_SERIF='/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf'
F_SANS='/usr/share/fonts/truetype/lato/Lato-Regular.ttf'
F_BOLD='/usr/share/fonts/truetype/lato/Lato-Semibold.ttf'
@lru_cache(None)
def font(kind,size):return ImageFont.truetype({'serif':F_SERIF,'sans':F_SANS,'bold':F_BOLD}[kind],max(8,int(size)))
def sm(x):
 x=min(1.,max(0.,x));return x*x*(3-2*x)
def alpha(t,start,fade=.48):return sm((t-start)/fade)
def txt(d,xy,s,size,fill=WHITE,kind='sans',anchor=None):d.text(xy,s,font=font(kind,size),fill=fill,anchor=anchor)

def music(path,seconds=30,sr=44100):
 """Original ambient score: slow pad + soft glass-piano plucks and subtle impacts."""
 t=np.arange(int(seconds*sr))/sr;waveform=np.zeros_like(t)
 chords=[[146.83,174.61,220.0],[130.81,164.81,196.0],[146.83,185,220],[110,164.81,196]]
 for step in range(8):
  start=step*3.75
  for freq in chords[step%4]:
   a=int(start*sr);b=min(len(t),int((start+4)*sr));tt=np.arange(b-a)/sr
   env=np.minimum(tt/.6,1.)*np.minimum((4-tt)/1.2,1.)
   waveform[a:b]+=.039*env*(np.sin(2*np.pi*freq*tt)+.19*np.sin(2*np.pi*2.01*freq*tt))
  for beat in range(4):
   st=start+beat*.9375; a=int(st*sr);b=min(len(t),int((st+1.3)*sr));tt=np.arange(b-a)/sr
   f=[293.66,349.23,440,369.99][(step+beat)%4]
   env=(1-np.exp(-tt*90))*np.exp(-tt*2.8)
   waveform[a:b]+=.047*env*(np.sin(2*np.pi*f*tt)+.1*np.sin(2*np.pi*2*f*tt))
 # subtle transient sparkle on cuts
 rng=np.random.default_rng(218)
 for st in np.cumsum(DUR)[:-1]:
  a=int((st-.11)*sr);b=int((st+.35)*sr);n=b-a
  if a>=0 and b<=len(t):
   noise=rng.normal(0,1,n);noise=np.cumsum(noise);noise-=noise.mean();noise/=max(noise.std(),1e-6)
   env=np.sin(np.linspace(0,np.pi,n))**2
   waveform[a:b]+noise*env*.009
 waveform=np.tanh(waveform*1.9)*np.minimum(1,t/.6)*np.minimum(1,(seconds-t)/2)
 # stereo stereo reflection
 delay=round(sr*.012);a=np.roll(waveform,delay)
 stereo=np.stack([waveform,a*.96],axis=1)
 stereo=(stereo*27000).clip(-32767,32767).astype('<i2')
 with wave.open(str(path),'wb') as w:
  w.setframerate(sr);w.setsampwidth(2);w.setnchannels(2);w.writeframes(stereo.tobytes())

class Media:
 def __init__(self,W,H):
  self.W,self.H=W,H;self.data=[]
  for item in TITLES:
   p=ASSETS/item['file'];assert p.is_file(),str(p)
   img=Image.open(p).convert('RGB')
   sw,sh=img.size
   # large but complete original photo with no deformation
   fit=min(W*.95/sw,H*.485/sh)
   iw,ih=int(sw*fit),int(sh*fit)
   backscale=max((W+100)/sw,(H+100)/sh)
   bg=img.resize((math.ceil(sw*backscale),math.ceil(sh*backscale)),Image.Resampling.BICUBIC)
   bg=bg.crop(((bg.width-W-100)//2,(bg.height-H-100)//2,(bg.width+W+100)//2,(bg.height+H+100)//2))
   bg=ImageEnhance.Brightness(bg.filter(ImageFilter.GaussianBlur(max(14,int(W*.035))))).enhance(.34 if item['scene']=='outro' else .38)
   # palette matte from exact original
   raw=np.array(img)
   edges=cv2.Canny(cv2.cvtColor(raw,cv2.COLOR_RGB2GRAY),40,112)
   mask=np.zeros((sh,sw),dtype=np.uint8)
   x1,y1,x2,y2=item['bbox'];mask[y1:y2,x1:x2]=edges[y1:y2,x1:x2]
   mask=cv2.dilate(mask,np.ones((2,2),np.uint8),iterations=1).astype('float32')/255
   self.data.append((img,bg,mask,iw,ih))
 def show(self,k,tt):
  W,H=self.W,self.H
  item=TITLES[k];scene=item['scene'];duration=DUR[k];p=min(1,tt/duration)
  src,bg,edges,iw,ih=self.data[k]
  # counter parallax of blurred background
  mx=int(33*(p-.5));my=int(22*math.cos(math.pi*p));out=bg.crop((50+mx,50+my,50+mx+W,50+my+H)).convert('RGBA')
  d=ImageDraw.Draw(out,'RGBA')
  d.rectangle((0,0,W,int(H*.15)),fill=(17,13,11,135))
  d.rectangle((0,int(H*.66),W,H),fill=(17,13,11,173))
  d.rectangle((0,int(H*.91),W,H),fill=(13,11,10,145))
  # photo slow dolly forward, slight lateral camera drift, no painterly alteration
  zoom=1+.052*sm(p)
  pw,ph=round(iw*zoom),round(ih*zoom)
  photo=src.resize((pw,ph),Image.Resampling.LANCZOS)
  fx=round((W-pw)/2+W*.017*(p-.5)); fy=round(H*.234-H*.019*sm(p))
  # direct source-based highlight on contour edges ONLY inside verified artwork ROI
  if scene in ('hero','trace','materials','styles'):
   e=cv2.resize(edges,(pw,ph),interpolation=cv2.INTER_LINEAR)
   bandX=np.arange(pw,dtype=np.float32)
   ctr=-pw*.12+pw*1.25*sm((p-.15)/.72)
   band=np.exp(-((bandX-ctr)/(pw*.16))**2)[None,:]
   glow=np.clip(cv2.GaussianBlur(e,(0,0),1.9)*.24+e*.18,0,.4)*band*min(1.,tt/.42,(duration-tt)/.55)
   if glow.max()>.002:
    ar=np.asarray(photo).astype(np.float32)
    ar=ar*(1-glow[:,:,None])+np.array([255,219,153])[None,None,:]*glow[:,:,None]
    photo=Image.fromarray(np.uint8(np.clip(ar,0,255)))
  sh=Image.new('RGBA',(pw+34,ph+34),(0,0,0,0));sd=ImageDraw.Draw(sh)
  sd.rectangle((16,16,pw+18,ph+18),fill=(0,0,0,220))
  out.alpha_composite(sh.filter(ImageFilter.GaussianBlur(max(8,int(W*.018)))),(fx-17,fy-17))
  out.paste(photo,(fx,fy));d=ImageDraw.Draw(out,'RGBA')
  d.rectangle((fx,fy,fx+pw,fy+ph),outline=(*GOLD,180),width=max(1,W//700))
  # brand and actual work name are stable; generous phone-safe margins
  L=int(W*.072);R=W-L
  d.line((L,int(H*.078),int(L+(R-L)*sm(tt/.85)),int(H*.078)),fill=(*GOLD,190),width=2)
  txt(d,(L,int(H*.096)),'ZYKINA ART',W*.045,WHITE,'serif')
  txt(d,(L,int(H*.156)),item['tag'],W*.026,GOLD,'bold')
  d.line((L,int(H*.914),R,int(H*.914)),fill=(*GOLD,110),width=2)
  # key art + annotation -> tracked source art position, dynamic engraved illumination
  if scene in ('hero','trace','styles'):
   x1,y1,x2,y2=item['bbox']
   px=fx+(x1+((x2-x1)*(.37 if scene=='hero' else .52)))/640*pw
   py=fy+(y1+(y2-y1)*.43)/400*ph
   drawprog=sm((tt-.45)/.7)
   bx=int(W*.22);by=fy-25
   # moving luminous path from a real point on the canvas to a minimal label
   if drawprog>0:
    path=[(int(px),int(py)),(int(px+W*.068*drawprog),int(py-W*.06*drawprog)),(int(px+W*.23*drawprog),int(py-W*.06*drawprog))]
    layer=Image.new('RGBA',(W,H),(0,0,0,0));ld=ImageDraw.Draw(layer,'RGBA')
    ld.line(path,fill=(*GOLD,int(210*drawprog)),width=max(2,int(W*.0028)),joint='curve');ld.ellipse((px-5,py-5,px+5,py+5),fill=(*GOLD,220))
    glow_layer=layer.filter(ImageFilter.GaussianBlur(7));out=Image.alpha_composite(out,glow_layer);out=Image.alpha_composite(out,layer);d=ImageDraw.Draw(out,'RGBA')
    label={'hero':'СВЕТ · КОМПОЗИЦИЯ','trace':'СВЕТ СКОЛЬЗИТ ПО РЕЛЬЕФУ','styles':'АРТ — ГЛАВНЫЙ АКЦЕНТ'}[scene]
    if tt>.9:
     tw=d.textbbox((0,0),label,font=font('bold',W*.019))[2]
     tx=min(R-tw,int(px+W*.23*drawprog))
     d.rounded_rectangle((tx-12,int(py-W*.06)-W*.048,tx+tw+16,int(py-W*.06)-5),radius=6,fill=(16,13,11,210),outline=(*GOLD,100),width=1)
     txt(d,(tx,int(py-W*.06)-W*.041),label,W*.019,WHITE,'bold')
  # large anchored title, animated opening from below and golden accent
  if scene!='outro':
   titleY=int(H*.744+H*.025*(1-sm((tt-.06)/.56)))
   fade=alpha(tt,.12,.55)
   d.line((L,titleY-32,L+int(W*.37*fade),titleY-32),fill=(*GOLD,int(230*fade)),width=3)
   lines=item['title']
   for j,line in enumerate(lines):
    width=d.textbbox((0,0),line,font=font('serif',W*(.068 if len(line)>15 else .078)))[2]
    fsize=W*(.066 if width>W*.88 else (.068 if len(line)>15 else .078))
    txt(d,(L,titleY+j*int(H*.067)),line,fsize,(*WHITE,int(248*fade)),'serif')
   txt(d,(L,int(H*.889)),item['sub'],W*.024,(*SOFT,int(235*fade)),'bold')
  # authentic palette linked to painting: drawn after main photo, no invented exact hex values
  if scene=='palette':
   f=alpha(tt,.38,.58);yy=int(H*.618)
   txt(d,(L,yy-60),'ПАЛИТРА РАБОТЫ',W*.026,(*WHITE,int(240*f)),'bold')
   colors=[('#D5C8AD','СЛОНОВАЯ КОСТЬ'),('#C49B55','ЗОЛОТИСТЫЙ'),('#38322B','ГРАФИТ'),('#B3A18C','БЕЖ')]
   for j,(c,name) in enumerate(colors):
    fi=alpha(tt,.5+j*.17,.25);x=L+j*int(W*.225);r=int(W*.034*fi)
    if r<1:continue
    d.ellipse((x,yy,x+2*r,yy+2*r),fill=c,outline=(*WHITE,170),width=2)
    txt(d,(x,yy+int(W*.09)),name,W*.014,(*WHITE,int(235*fi)),'bold')
  if scene=='materials':
   # label options, never attribute specific materials to a particular work
   y=int(H*.606);f=alpha(tt,.28,.4)
   d.rounded_rectangle((L-12,y-45,R+7,y+197),radius=15,fill=(20,15,13,int(205*f)),outline=(*GOLD,int(130*f)),width=2)
   txt(d,(L,y-29),'ВОЗМОЖНЫЕ МАТЕРИАЛЫ',W*.025,(*WHITE,int(240*f)),'bold')
   material=['АКРИЛ','МАСЛО','ГИПС','ТЕКСТУРНАЯ ПАСТА','ТКАНЬ','ПОТАЛЬ']
   widths=[.24,.25,.22,.44,.24,.21]
   for j,word in enumerate(material):
    a=alpha(tt,.5+j*.15,.28);col=j%3;row=j//3
    xx=L+col*int(W*.292);cy=y+15+row*int(W*.095)
    cw=int(W*widths[j])
    d.rounded_rectangle((xx,cy,xx+cw,cy+int(W*.065)),radius=8,fill=(66,49,34,int(235*a)),outline=(*GOLD,int(165*a)),width=2)
    txt(d,(xx+11,cy+int(W*.016)),word,W*.017,(*WHITE,int(245*a)),'bold')
   txt(d,(L,y+180),'Состав конкретной работы уточняется у автора',W*.018,(*SOFT,int(235*f)),'sans')
  if scene=='styles':
   y=int(H*.63);fs=alpha(tt,.2,.5)
   for j,label in enumerate(['МИНИМАЛИЗМ','ЛОФТ','СОВРЕМЕННАЯ КЛАССИКА']):
    x=L if j==0 else L+int(W*(.35 if j==1 else .51)); w=int(W*(.34 if j==0 else .15 if j==1 else .40))
    a=alpha(tt,.42+j*.14,.3)
    d.rounded_rectangle((x,y,x+w,y+int(W*.065)),radius=8,fill=(42,32,25,int(220*a)),outline=(*GOLD,int(170*a)),width=1)
    txt(d,(x+9,y+int(W*.019)),label,W*.0145,(*WHITE,int(245*a)),'bold')
  if scene=='outro':
   # one brand hero photograph followed by editorial title, bronze line, CTA
   d.rectangle((0,int(H*.59),W,H),fill=(12,10,9,225));f=alpha(tt,.3,.8)
   txt(d,(W//2,int(H*.645)),'ZYKINA',W*.105,(*WHITE,int(250*f)),'serif','mt')
   txt(d,(W//2,int(H*.733)),'ART',W*.121,(*GOLD,int(250*f)),'serif','mt')
   txt(d,(W//2,int(H*.807)),'ИСКУССТВО, КОТОРОЕ СОЗДАЁТ АТМОСФЕРУ',W*.020,(*WHITE,int(232*f)),'bold','mt')
   btn=(int(W*.16),int(H*.833),int(W*.84),int(H*.89));d.rounded_rectangle(btn,14,fill=(*GOLD,int(235*f)))
   txt(d,(W//2,int(H*.862)),'СМОТРЕТЬ КОЛЛЕКЦИЮ',W*.026,(22,16,13,int(250*f)),'bold','mm')
   txt(d,(W//2,int(H*.934)),'zykina-art.ru',W*.042,(*WHITE,int(253*f)),'sans','mt')
  # progress and purposeful short fade between scenes
  ty=int(H*.957);start=L;gap=W*.012;lw=(W-2*L-gap*(len(TITLES)-1))/len(TITLES)
  for j in range(len(TITLES)):
   color=(*GOLD,240) if j==k else (*SOFT,82)
   d.rounded_rectangle((int(start+j*(lw+gap)),ty,int(start+j*(lw+gap)+lw),ty+5),radius=2,fill=color)
  fadein=sm(tt/.24);fadeout=sm((duration-tt)/.22);fade=min(fadein,fadeout)
  if fade<.999:out=Image.alpha_composite(out,Image.new('RGBA',(W,H),(11,8,7,int(255*(1-fade)))))
  return out.convert('RGB')

def build(outdir,W,H,fps,preview=False):
 outdir.mkdir(parents=True,exist_ok=True)
 media=Media(W,H)
 soundtrack=outdir/'ZYKINA_ART_original_music.wav';music(soundtrack)
 frames=int((6 if preview else 30)*fps)
 out=outdir/('preview.mp4' if preview else 'ZYKINA_ART_LUXURY_v3_NO_VOICE.mp4')
 cmd=['ffmpeg','-nostdin','-v','error','-y','-f','rawvideo','-pixel_format','rgb24','-video_size',f'{W}x{H}','-framerate',str(fps),'-i','-','-i',str(soundtrack),'-map','0:v','-map','1:a','-c:v','libx264','-preset','veryfast','-crf','20','-pix_fmt','yuv420p','-c:a','aac','-b:a','160k','-t',str(frames/fps),'-movflags','+faststart',str(out)]
 p=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=subprocess.PIPE)
 bounds=np.cumsum([0]+DUR)
 try:
  for i in range(frames):
   t=i/fps;k=min(7,int(np.searchsorted(bounds,t,side='right')-1))
   img=media.show(k,t-bounds[k]);p.stdin.write(np.asarray(img,dtype=np.uint8).tobytes())
   if i%(fps*3)==0:print(f'{i}/{frames} frames',flush=True)
  p.stdin.close();err=p.stderr.read().decode();ret=p.wait()
  if ret:raise RuntimeError(err[-2200:])
 finally:
  if p.poll() is None:p.kill()
 print('SAVED',out,out.stat().st_size,flush=True)
 return out
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--outdir',default='/mnt/data/zykina-v3');p.add_argument('--width',type=int,default=1080);p.add_argument('--height',type=int,default=1920);p.add_argument('--fps',type=int,default=25);p.add_argument('--preview',action='store_true');a=p.parse_args()
 build(Path(a.outdir),a.width,a.height,a.fps,a.preview)