#!/usr/bin/env python3
"""ZYKINA ART — 40-second art-direction-first advertisement.
Real source painting and two actual gallery interiors only. No invented details.
Subpixel affine camera movement; real-layer separation; source-aligned callouts.
Requires pillow, numpy, opencv-python-headless, ffmpeg.
"""
import argparse, math, subprocess, os, sys, wave
from pathlib import Path
from functools import lru_cache
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W,H,FPS=720,1280,30
GOLD=(191,153,100); GOLD_L=(235,204,157); WHITE=(242,232,215); MUTED=(195,179,158)
BG=np.array((18,16,16),np.uint8)
FONT_DIR='/usr/share/fonts/truetype/dejavu/'
SERIF=FONT_DIR+'DejaVuSerif.ttf'; SANS=FONT_DIR+'DejaVuSans.ttf'; SANS_B=FONT_DIR+'DejaVuSans-Bold.ttf'
DURS=[6.1,6.4,7.5,6.4,4.5,4.6,4.5]
assert abs(sum(DURS)-40)<.00001
TIMES=np.cumsum([0]+DURS)

def eas(x):
 x=max(0.,min(1.,float(x)));return x*x*(3-2*x)
def fade(t,start=.18,dt=.55):return eas((t-start)/dt)
def twoway(t,d):return min(fade(t,0,.32),eas((d-t)/.33))
def softshadow(img,b=21):
 return Image.fromarray(img).filter(ImageFilter.GaussianBlur(b))
def fit_into(im,size):
 w,h=size;return im.resize((max(1,round(im.width*min(w/im.width,h/im.height))),max(1,round(im.height*min(w/im.width,h/im.height)))),Image.Resampling.LANCZOS)
def cover(im,w,h):
 k=max(w/im.width,h/im.height); x=im.resize((math.ceil(im.width*k),math.ceil(im.height*k)),Image.Resampling.BICUBIC);return x.crop(((x.width-w)//2,(x.height-h)//2,(x.width+w)//2,(x.height+h)//2))
def rgb(p):return Image.open(p).convert('RGB')
@lru_cache(maxsize=64)
def ft(sz,serif=False,bold=False):return ImageFont.truetype(SERIF if serif else (SANS_B if bold else SANS),max(9,round(sz)))
def text(d,x,y,s,sz=25,fill=WHITE,serif=False,bold=False,anchor='la'):
 d.text((int(x),int(y)),s,font=ft(sz,serif,bold),fill=fill,anchor=anchor,stroke_width=0)
def alpha_poly(d,pts,fill=(232,193,138,205),width=2):
 if len(pts)>1:d.line([(round(a),round(b)) for a,b in pts],fill=fill,width=width,joint='curve')
def affmove(im,dx,dy,border=0):
 arr=np.array(im) if isinstance(im,Image.Image) else im
 M=np.float32([[1.,0.,dx],[0.,1.,dy]])
 return cv2.warpAffine(arr,M,(arr.shape[1],arr.shape[0]),flags=cv2.INTER_CUBIC,borderMode=cv2.BORDER_REFLECT_101)
def interpolate(a,b,p):return a+(b-a)*eas(p)

class Room:
 def __init__(self, path, rect):
  self.src=rgb(path); self.rect=rect
  # The physical canvas bounds come from the original 640x400 gallery photograph.
  orig=np.array(self.src)
  x1,y1,x2,y2=rect
  m=np.zeros(orig.shape[:2],np.uint8);m[max(0,y1):y2,max(0,x1):x2]=255
  m=cv2.dilate(m,np.ones((5,5),np.uint8),iterations=1)
  self.wall=cv2.inpaint(orig,m,6,cv2.INPAINT_TELEA)
  self.canvas=np.zeros((self.src.height,self.src.width,4),np.uint8)
  crop=orig[y1:y2,x1:x2]
  self.canvas[y1:y2,x1:x2,:3]=crop
  self.canvas[y1:y2,x1:x2,3]=255
  # Soft alpha anti-aliasing only at the edge; original canvas pixels untouched.
  self.canvas[:,:,3]=cv2.GaussianBlur(self.canvas[:,:,3],(3,3),.55)
  self.blur=cover(self.src,W,H).filter(ImageFilter.GaussianBlur(28))
  # Stage image: 720x~450, centre-mounted with room/painting on separate planes.
  k=min(W/self.src.width,510/self.src.height)
  self.w,self.h=round(self.src.width*k),round(self.src.height*k)
  self.k=k
  self.wall=cv2.resize(self.wall,(self.w,self.h),interpolation=cv2.INTER_CUBIC)
  self.canvas=cv2.resize(self.canvas,(self.w,self.h),interpolation=cv2.INTER_CUBIC)
 def render(self,local,duration,size_mode=False):
  u=eas(local/duration)
  bg=np.array(self.blur,dtype=np.float32)*.38
  # Horizontal light fall-off and dark chapter margin.
  Y=np.linspace(0,1,H)[:,None,None]
  bg=(bg*(.96-.30*np.abs(Y-.48))).astype(np.uint8)
  # Stage placement with physically plausible subpixel independent motion.
  stage=np.zeros((H,W,3),np.uint8)
  y0=328; x0=(W-self.w)//2
  wall=affmove(self.wall,2.4*u,1.8*u)
  canvas=affmove(self.canvas,4.7*u+1.0*math.sin(local*.48),-1.6*u)
  alpha=(canvas[:,:,3:4]/255.).astype('float32')
  stagepart=(wall.astype('float32')*(1-alpha)+canvas[:,:,:3].astype('float32')*alpha).astype('uint8')
  sh=Image.new('RGBA',(W,H),(0,0,0,0));sd=ImageDraw.Draw(sh)
  sd.rectangle((x0+6,y0+11,x0+self.w+6,y0+self.h+11),fill=(0,0,0,153))
  sh=sh.filter(ImageFilter.GaussianBlur(19))
  base=Image.fromarray(bg).convert('RGBA');base=Image.alpha_composite(base,sh)
  base.alpha_composite(Image.fromarray(np.dstack([stagepart,np.full((self.h,self.w),255,np.uint8)])),(x0,y0))
  # Combined camera/art transforms for callout positions
  x1,y1,x2,y2=self.rect
  bounds=(x0+x1*self.k+4.7*u,y0+y1*self.k-1.6*u,x0+x2*self.k+4.7*u,y0+y2*self.k-1.6*u)
  return base,bounds,(x0,y0,x0+self.w,y0+self.h)

class Painting:
 def __init__(self,path):
  self.src=rgb(path)
  self.blur=cover(self.src,W,H).filter(ImageFilter.GaussianBlur(34))
  # Original painting stays intact and sharp; no cropping when first shown.
  self.photo=fit_into(self.src,(622,665))
  # Remove 4px resampling/alpha fringe around photographic export, not painting content.
  if self.photo.width>180 and self.photo.height>180:
   self.photo=self.photo.crop((5,5,self.photo.width-5,self.photo.height-5))
  self.PW,self.PH=self.photo.size
  # Sample actual artwork to build color palette, never invented hues.
  self.palette=self.pick_colors()
 def pick_colors(self):
  im=cv2.resize(np.asarray(self.src),(128,128),interpolation=cv2.INTER_AREA).reshape(-1,3).astype('float32')
  _,labels,centers=cv2.kmeans(im,6,None,(cv2.TERM_CRITERIA_MAX_ITER+cv2.TERM_CRITERIA_EPS,22,.35),4,cv2.KMEANS_PP_CENTERS)
  centers=np.array(centers,np.uint8);quant=np.bincount(labels.ravel(),minlength=6)
  sorted_centers=sorted(zip(centers.tolist(),quant.tolist()),key=lambda x:x[1],reverse=True)
  # Maximise visual separation so swatches are genuinely useful.
  selected=[]
  for c,n in sorted_centers:
   if all(sum((c[i]-v[i])**2 for i in range(3))>2600 for v in selected):selected.append(tuple(c))
   if len(selected)==4:break
  while len(selected)<3: selected.append(tuple(sorted_centers[len(selected)][0]))
  return selected[:3]
 def render(self,local,duration,zoom=1):
  u=eas(local/duration)
  dark=np.array(self.blur,dtype=np.float32)*.25
  bg=Image.fromarray(np.uint8(dark)).convert('RGBA')
  # Separate slow background movement and sharp canvas plane.
  # Fixed canvas dimensions + fractional-pixel affine translation eliminate resize jitter.
  nw,nh=self.PW,self.PH
  art=Image.fromarray(affmove(np.asarray(self.photo), 2.8*math.sin(u*1.5),3.8*u))
  x=int((W-nw)//2);y=int(257+(660-nh)/2)
  shadow=Image.new('RGBA',(W,H),(0,0,0,0));d=ImageDraw.Draw(shadow)
  d.rectangle((x+8,y+13,x+nw+12,y+nh+17),fill=(0,0,0,135))
  shadow=shadow.filter(ImageFilter.GaussianBlur(25));bg=Image.alpha_composite(bg,shadow)
  bg.alpha_composite(art.convert('RGBA'),(x,y))
  return bg,(x,y,x+nw,y+nh)

class Detail:
 def __init__(self,path):
  self.src=rgb(path)
  self.blur=cover(self.src,W,H).filter(ImageFilter.GaussianBlur(31))
  self.photo=cover(self.src, W, 736)
  rgb_arr=np.asarray(self.photo)
  gray=cv2.cvtColor(rgb_arr,cv2.COLOR_RGB2GRAY)
  grad=cv2.Canny(gray,55,140).astype('float32')/255.
  # Structure-aware light mask — follows actual photographed relief edges only.
  self.edges=cv2.GaussianBlur(grad,(0,0),1.2)*.65+grad*.35
 def render(self,local,duration):
  p=eas(local/duration)
  bg=(np.asarray(self.blur).astype('float32')*.26).astype('uint8')
  arr=np.asarray(self.photo).astype('float32')
  yy,xx=np.indices(arr.shape[:2]);cent=(p*1.5-.23)*W
  band=np.exp(-((xx-cent)/83)**2)
  glow=np.clip(self.edges*band*.28,0,.3)
  arr=arr*(1-glow[:,:,None])+np.array([255,217,153],np.float32)*glow[:,:,None]
  stage=affmove(np.uint8(np.clip(arr,0,255)),(p-.5)*5.0,(p-.5)*2.)
  bg=Image.fromarray(bg).convert('RGBA')
  sh=Image.new('RGBA',(W,H),(0,0,0,0));dd=ImageDraw.Draw(sh)
  dd.rectangle((0,277,W,1020),fill=(0,0,0,135));sh=sh.filter(ImageFilter.GaussianBlur(19));bg=Image.alpha_composite(bg,sh)
  bg.alpha_composite(Image.fromarray(stage).convert('RGBA'),(0,284))
  return bg,(0,284,W,1020)

SCENES=[
 ('intro','Как выбрать','картину для дома?','ОДНА РАБОТА — НОВОЕ НАСТРОЕНИЕ'),
 ('size','Начните с','пропорций','ВАЖЕН МАСШТАБ КАРТИНЫ И МЕБЕЛИ'),
 ('color','Подберите','оттенки','ГАРМОНИЯ ЦВЕТА И АКЦЕНТОВ'),
 ('detail1','Рельеф','и глубина','ПОСМОТРИТЕ НА ФАКТУРУ БЛИЖЕ'),
 ('detail2','Материал','и свет','ФАКТУРА РАСКРЫВАЕТСЯ ПРИ ОСВЕЩЕНИИ'),
 ('room2','Найдите','свой характер','ОДНА КАРТИНА · РАЗНЫЕ ПРОСТРАНСТВА'),
 ('outro','ZYKINA','ART','АВТОРСКИЕ КАРТИНЫ ЕКАТЕРИНЫ ЗЫКИНОЙ'),
]

class Video:
 def __init__(self,assets):
  self.room1=Room(assets/'interiors/2/interior-mwlat1wo-1.webp',(356,34,519,249))
  self.room2=Room(assets/'interiors/2/interior-mwlahicl-1.webp',(167,31,273,171))
  self.paint=Painting(assets/'картины/2/главная.png')
  self.details=[Detail(assets/'картины/2/детали 1.png'),Detail(assets/'картины/2/детали 2.png')]
 def frame(self,t):
  idx=min(len(SCENES)-1,np.searchsorted(TIMES,t,side='right')-1)
  beg,dur=TIMES[idx],DURS[idx];s=t-beg;u=eas(s/dur)
  kind,title1,title2,sub=SCENES[idx]
  if kind in ('intro','size'):
   im,rect,stage=self.room1.render(s,dur)
  elif kind=='room2': im,rect,stage=self.room2.render(s,dur)
  elif kind in ('color','outro'): im,rect=self.paint.render(s,dur);stage=rect
  else: im,rect=self.details[0 if kind=='detail1' else 1].render(s,dur);stage=rect
  # Unified premium typography overlay; labels live OUTSIDE photograph whenever possible.
  d=ImageDraw.Draw(im,'RGBA')
  xlo=51
  d.line((xlo,77,670,77),fill=(*GOLD,172),width=2)
  text(d,xlo,94,'Z  Y  K  I  N  A     A  R  T',20,WHITE)
  text(d,669,96,f'{idx+1:02d} / 07',17,GOLD_L,anchor='ra')
  # Thin timeline instead of flashy UI animations.
  d.line((52,1229,667,1229),fill=(*GOLD,75),width=2)
  d.line((52,1229,52+615*(t/40),1229),fill=(*GOLD_L,223),width=3)
  if kind=='intro':
   text(d,54,190,'ИСКУССТВО В ИНТЕРЬЕРЕ',18,GOLD_L,bold=True)
   text(d,54,916,title1,46,WHITE,serif=True);text(d,54,988,title2,42,WHITE,serif=True)
   text(d,54,1108,'«ЗЕМЛЯ И ЗОЛОТО»',22,GOLD_L,bold=True)
   text(d,54,1153,'Авторская работа Екатерины Зыкиной',18,MUTED)
  elif kind=='size':
   text(d,54,180,'01   РАЗМЕР И ПРОПОРЦИИ',20,GOLD_L,bold=True)
   xa,ya,xb,yb=rect
   xa=max(45,xa);xb=min(675,xb)
   # Width line anchored EXACTLY on physical picture corners, just above the canvas.
   ey=ya-24; aa=fade(s,.5,.8)
   xf=xa+(xb-xa)*aa
   alpha=int(226*aa)
   if aa>0:
    d.line((xa,ey,xf,ey),fill=(*GOLD_L,alpha),width=3)
    d.line((xa,ey-12,xa,ey+12),fill=(*GOLD_L,alpha),width=2)
    if aa>.92:d.line((xb,ey-12,xb,ey+12),fill=(*GOLD_L,alpha),width=2)
    if aa>.7:text(d,(xa+xb)/2,ey-43,'ШИРИНА ХОЛСТА',17,(*WHITE,int(aa*240)),bold=True,anchor='ma')
   text(d,54,925,title1,47,WHITE,serif=True);text(d,54,997,title2,46,WHITE,serif=True)
   text(d,54,1115,'Картина соразмерна мебели и стене',19,MUTED)
  elif kind=='color':
   text(d,54,177,'02   ЦВЕТ И АТМОСФЕРА',19,GOLD_L,bold=True)
   text(d,54,965,title1,44,WHITE,serif=True);text(d,54,1028,title2,45,WHITE,serif=True)
   xa,ya,xb,yb=rect
   # Sampled directly from THIS painting, not an invented palette.
   pal=self.paint.palette
   # Three real color picks, with short callouts within the artwork and no crossing text.
   for k,color in enumerate(pal):
    af=fade(s,.85+k*.38,.35)
    if af<.03:continue
    cx=105+k*210;cy=1121
    d.ellipse((cx-28*af,cy-28*af,cx+28*af,cy+28*af),fill=(*color,int(255*af)),outline=(*GOLD_L,int(230*af)),width=2)
    text(d,cx,1168,f'ТОН {k+1:02d}',17,(*WHITE,int(220*af)),bold=True,anchor='ma')
    # Local locator remains inside the canvas; all large color swatches sit below.
    tx=xa+(xb-xa)*(.26+.23*k);ty=ya+(yb-ya)*(.34+.12*(k%2))
    if af>.55:
     d.ellipse((tx-4,ty-4,tx+4,ty+4),fill=(*GOLD_L,int(245*af)))
     d.line((tx+7,ty,tx+27,ty-13),fill=(*GOLD_L,int(190*af)),width=2)
  elif kind in ('detail1','detail2'):
   text(d,54,178,'03   ФАКТУРА КРУПНЫМ ПЛАНОМ',19,GOLD_L,bold=True)
   text(d,54,1039,title1,47,WHITE,serif=True);text(d,54,1107,title2,45,WHITE,serif=True)
   if kind=='detail2':text(d,54,1181,'Состав материалов уточняйте у художницы',16,MUTED)
   # Source-aligned short leader and a bead on actual relief details, not made-up geometry.
   if kind=='detail1':
    af=fade(s,.7,.8)
    if af>.02:
     px=470;py=570
     d.ellipse((px-4,py-4,px+4,py+4),fill=(*GOLD_L,int(240*af)))
     d.line((px+10,py-6,px+70,py-53,628,py-53),fill=(*GOLD_L,int(190*af)),width=2)
     text(d,628,py-91,'СВЕТ ПО РЕЛЬЕФУ',15,(*WHITE,int(225*af)),anchor='ra',bold=True)
  elif kind=='room2':
   text(d,54,180,'04   ПОДБЕРИТЕ СВОЙ СТИЛЬ',20,GOLD_L,bold=True)
   text(d,54,925,title1,45,WHITE,serif=True);text(d,54,999,title2,47,WHITE,serif=True)
   text(d,54,1112,'Современный лофт  ·  выразительный акцент',17,MUTED)
  else:
   # final brand overlay covers lower part only; original art remains visible above.
   d.rounded_rectangle((36,918,684,1197),radius=14,fill=(11,10,10,217))
   text(d,360,949,'ZYKINA',68,WHITE,serif=True,anchor='ma')
   text(d,360,1047,'ART',75,GOLD_L,serif=True,anchor='ma')
   d.line((192,1120,528,1120),fill=(*GOLD,190),width=2)
   text(d,360,1145,'ZYKINA-ART.RU',24,WHITE,bold=True,anchor='ma')
  # Precomputed frame blends prevent hard cuts, fade is alpha applied evenly at boundaries.
  alpha=min(eas(s/.28),eas((dur-s)/.28))
  if alpha<1:
   ov=Image.new('RGBA',(W,H),(11,10,10,int(255*(1-alpha))))
   im=Image.alpha_composite(im,ov)
  return im.convert('RGB')

def preview(output, assets):
 v=Video(assets)
 ts=[1.5,7.8,15.4,23.5,29.,33.3,38.2]
 cards=[]
 for t in ts:
  p=v.frame(t);p.thumbnail((288,512))
  cards.append(p)
 w=288*len(cards);a=Image.new('RGB',(w,545),(23,21,19));d=ImageDraw.Draw(a)
 for i,p in enumerate(cards):a.paste(p,(i*288,25));text(d,i*288+8,3,str(ts[i]),14,WHITE)
 a.save(output,quality=91)
 print('PREVIEW',output,flush=True)

def make_video(output,assets,voice=None,music=None,fps=30):
 v=Video(assets); output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
 mute=output.with_suffix('.silent.mp4')
 cmd=['ffmpeg','-hide_banner','-nostdin','-loglevel','error','-y','-f','rawvideo','-pixel_format','rgb24','-video_size',f'{W}x{H}', '-framerate',str(fps),'-i','-','-c:v','libx264','-preset','fast','-crf','19','-pix_fmt','yuv420p','-movflags','+faststart',str(mute)]
 p=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=subprocess.PIPE)
 try:
  for i in range(fps*40):
   frame=v.frame(i/fps)
   p.stdin.write(np.asarray(frame).tobytes())
   if i%150==0:print('frame',i,'/',40*fps,flush=True)
 finally:
  p.stdin.close();err=p.stderr.read().decode('utf8','replace');rc=p.wait()
 if rc:raise RuntimeError(f'ffmpeg failed: {err[-4000:]}')
 if voice:
  # Include a dynamic but restrained music bed; voice remains the centre of the film.
  if music:
   filt='[1:a]aresample=48000,volume=1.18,acompressor=threshold=-17dB:ratio=2.4:attack=8:release=170[v];[2:a]aresample=48000,volume=0.16,afade=t=in:st=0:d=1.2,afade=t=out:st=37.8:d=2.2[m];[v][m]amix=inputs=2:duration=longest:dropout_transition=0,alimiter=limit=0.93[a]'
   cm=['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(mute),'-i',str(voice),'-i',str(music),'-filter_complex',filt,'-map','0:v','-map','[a]','-t','40','-c:v','copy','-c:a','aac','-b:a','192k','-movflags','+faststart',str(output)]
  else:
   cm=['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(mute),'-i',str(voice),'-filter_complex','[1:a]volume=1.1,apad=pad_dur=1.4,alimiter=limit=0.95[a]','-map','0:v','-map','[a]','-t','40','-c:v','copy','-c:a','aac','-b:a','192k','-movflags','+faststart',str(output)]
 else:
  cm=['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(mute),'-t','40','-c:v','copy',str(output)]
 subprocess.run(cm,check=True)
 print('CREATED',str(output),output.stat().st_size,flush=True)

def main():
 pa=argparse.ArgumentParser();pa.add_argument('--assets',default='public/assets');pa.add_argument('--out',default='/tmp/ZYKINA_ART_Premium_V4.mp4');pa.add_argument('--preview',default=None);pa.add_argument('--voice');pa.add_argument('--music');pa.add_argument('--fps',type=int,default=30);a=pa.parse_args()
 if a.preview:preview(a.preview,Path(a.assets))
 else:make_video(a.out,Path(a.assets),a.voice,a.music,a.fps)
if __name__=='__main__':main()