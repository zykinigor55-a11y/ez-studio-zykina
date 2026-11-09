/* E·Z STUDIO — pixel-registered GPU lunar bas-relief.
   The approved backdrop is loaded unchanged. Only pixels inside the actual
   lamp are relit, and the original floor reflection remains in place. */
(()=>{
'use strict';
const moon=document.getElementById('moon');if(!moon||!moon.classList.contains('ez-moon-approved'))return;
const $=id=>document.getElementById(id), scene=$('ezMoonScene'),canvas=$('ezMoonRelief');
const bright=$('moonBrightness'),temp=$('moonTemp'),power=$('moonPower'),obj=$('moonObject');
const kalvinFine=$('ezKelvinFine'),kalvinPopup=$('ezKelvinPopup');
const mb=$('ezMobileBrightness'),mk=$('ezMobileKelvin');
let kelvin=+temp.value||2700,level=(+bright.value)/100,on=true,render=()=>{},lastState='';
const BASE=(document.currentScript?.src||location.href).replace(/[^/]*$/,'');
function sync(){
  const percent=Math.min(100,Math.max(0,level*100));
  bright.value=String(Math.round(percent)); mb.value=bright.value;
  temp.value=String(kelvin);kalvinFine.value=String(kelvin);mk.value=String(kelvin);
  $('ezBrightnessValue').textContent=Math.round(percent)+' %';
  $('ezMobileValue').textContent=Math.round(percent)+' %';
  $('ezMobileDockValue').textContent=Math.round(percent)+' %';
  $('ezKelvinLabel').textContent=kelvin+' К';$('ezMobileKelvinValue').textContent=kelvin+' К';
  power.setAttribute('aria-pressed',String(on));obj.setAttribute('aria-pressed',String(on));
  power.classList.toggle('is-on',on);power.classList.toggle('is-off',!on);
  power.setAttribute('aria-label',on?'Выключить подсветку':'Включить подсветку');
  scene.style.setProperty('--ez-lamp-dim',(on ? (1-Math.min(1,level))*.42 : .82).toFixed(3));
  const t=$('moonPowerText');if(t)t.textContent=on?'ВКЛ':'ВЫКЛ';
  $('ezMobilePower').textContent=on?'ВКЛ':'ВЫКЛ';
  document.querySelectorAll('#moon [data-kelvin]').forEach(x=>x.setAttribute('aria-pressed',String(+x.dataset.kelvin===kelvin)));
  // original slider thumb at 442 px; first render keeps the approved position.
  // Match the approved 78% thumb location, yet reach full endpoints at 0% and 100%.
  const x=percent<=78 ? 98+(percent/78)*(442-98) : 442+((percent-78)/22)*(574-442);
  scene.style.setProperty('--ez-thumb-x',(x/1536*100).toFixed(4)+'%');
  scene.style.setProperty('--ez-bright-percent',((x-98)/(574-98)*100).toFixed(3)+'%');
  scene.style.setProperty('--ez-power',on?'1':'0');
  const cold=Math.max(0,(kelvin-3800)/2700);
  scene.style.setProperty('--ez-blue',on?String(Math.min(.9,cold*.6*level)):'.0');
  moon.style.setProperty('--ez-light-strength',on?String(level):'0');
  const state=[on,kelvin,level].join('|');if(state!==lastState){lastState=state;render();}
}
const setPower=(value)=>{on=!!value;sync();};
power.addEventListener('click',()=>{on=!on;sync()});
obj.addEventListener('click',()=>{on=!on;sync()});
$('ezMobilePower').addEventListener('click',()=>{on=!on;sync()});
const mobileSettings=$('ezMobileSettings'),mobileControls=$('ezMobileControls');
mobileSettings.addEventListener('click',()=>{
  const next=mobileControls.hidden;
  mobileControls.hidden=!next;
  mobileSettings.setAttribute('aria-expanded',String(next));
  mobileSettings.setAttribute('aria-label',next?'Скрыть настройку яркости и температуры':'Раскрыть настройку яркости и температуры');
});
document.addEventListener('pointerdown',e=>{
  if(!mobileControls.hidden && !e.target.closest('.ez-moon-mobile-panel')){
    mobileControls.hidden=true;mobileSettings.setAttribute('aria-expanded','false');
  }
});

bright.addEventListener('input',()=>{level=bright.value/100;sync()});mb.addEventListener('input',()=>{level=mb.value/100;sync()});
const updateKelvin=(k)=>{kelvin=Math.max(2700,Math.min(6500,Math.round(k/100)*100));sync();};
kalvinFine.addEventListener('input',()=>updateKelvin(+kalvinFine.value));mk.addEventListener('input',()=>updateKelvin(+mk.value));
document.querySelectorAll('#moon [data-kelvin]').forEach(btn=>btn.addEventListener('click',()=>updateKelvin(+btn.dataset.kelvin)));
$('ezKelvinOpener').addEventListener('click',()=>{kalvinPopup.hidden=!kalvinPopup.hidden;if(!kalvinPopup.hidden)kalvinFine.focus()});
document.addEventListener('keydown',e=>{if(e.key==='Escape'){kalvinPopup.hidden=true;mobileControls.hidden=true;mobileSettings.setAttribute('aria-expanded','false');}});
function loadImage(src){return new Promise((resolve,reject)=>{const img=new Image();img.onload=()=>resolve(img);img.onerror=()=>reject(new Error('Не удалось загрузить '+src));img.src=BASE+'assets/'+src;});}
async function makeRenderer(){
  let [photo,normals,height]=await Promise.all(['ez-moon-crop.png','ez-moon-normal.png','ez-moon-height.png'].map(loadImage));
  const gl=canvas.getContext('webgl2',{alpha:true,premultipliedAlpha:false,antialias:true,preserveDrawingBuffer:true});
  if(!gl){return makeCanvasRenderer(photo,normals);}
  const vert=`#version 300 es
    precision highp float;
    in vec3 aPos;
    out vec2 vUV;
    void main(){vUV=aPos.xy*.5+.5;gl_Position=vec4(aPos,1.0);}`;
  const frag=`#version 300 es
    precision highp float;
    in vec2 vUV;uniform sampler2D uPhoto;uniform sampler2D uNormal;
    uniform float uKelvin;uniform float uLevel;uniform float uPower;
    out vec4 frag;
    void main(){
      vec2 xy=vec2(635.0+vUV.x*774.0,64.0+(1.0-vUV.y)*812.0);
      float r=length((xy-vec2(1019.0,471.0))/vec2(348.0,366.0));
      float alpha=1.0-smoothstep(.985,1.017,r);
      if(alpha<=.005)discard;
      vec3 pic=texture(uPhoto,vUV).rgb;
      vec3 n=normalize(texture(uNormal,vUV).rgb*2.0-1.0);
      float diffuse=max(.0,dot(n,normalize(vec3(-.34,.42,.84))));
      float rake=max(.0,dot(n,normalize(vec3(.77,.16,.41))));
      float relief=clamp((diffuse-.76)*.42+(rake-.45)*.13,-.19,.23);
      float gray=dot(pic,vec3(.2126,.7152,.0722));
      float cold=clamp((uKelvin-2700.0)/3800.0,0.0,1.0);
      // Under cool light the authentic warm source is normalized, preserving its crater details.
      vec3 neutral=vec3(gray*.94,gray*1.025,gray*1.15);
      vec3 color=mix(pic,neutral,cold*.87);
      color*=1.0+relief*(.12+cold*.95);
      float pct=clamp(uLevel/.78,0.0,1.35);
      vec3 dark=vec3(gray*.13,gray*.108,gray*.089)+pic*.027;
      vec3 lit=color*(.55+.45*min(pct,1.0))*(1.0+max(pct-1.0,0.0)*.66);
      float energy=clamp(uLevel/.78,0.,1.)*uPower;
      vec3 result=mix(dark,lit,energy);
      // LED falloff at the actual inner rim, not a second floating ring.
      float rim=smoothstep(.91,.975,r);
      if(uPower<.5)result*=1.0-.24*rim;
      frag=vec4(clamp(result,0.0,1.0),alpha);
    }`;
  const shader=(type,source)=>{const sh=gl.createShader(type);gl.shaderSource(sh,source);gl.compileShader(sh);if(!gl.getShaderParameter(sh,gl.COMPILE_STATUS))throw Error('Moon shader: '+gl.getShaderInfoLog(sh));return sh;};
  const p=gl.createProgram();gl.attachShader(p,shader(gl.VERTEX_SHADER,vert));gl.attachShader(p,shader(gl.FRAGMENT_SHADER,frag));gl.linkProgram(p);
  if(!gl.getProgramParameter(p,gl.LINK_STATUS))throw Error('Moon linking: '+gl.getProgramInfoLog(p));gl.useProgram(p);
  // Gridded orthographic 3D relief: height samples deform Z without shifting approved UVs.
  const heightImg=document.createElement('canvas');heightImg.width=774;heightImg.height=812;
  const hc=heightImg.getContext('2d');hc.drawImage(height,0,0);const hdata=hc.getImageData(0,0,774,812).data;
  const verts=[];const cols=54,rows=54;
  const push=(ix,iy)=>{const u=ix/cols,v=iy/rows,x=Math.min(773,Math.floor(u*773)),y=Math.min(811,Math.floor((1-v)*811));const h=hdata[(y*774+x)*4]/255;verts.push(u*2-1,v*2-1,(h-.5)*.065);};
  for(let y=0;y<rows;y++)for(let x=0;x<cols;x++){push(x,y);push(x+1,y);push(x,y+1);push(x+1,y);push(x+1,y+1);push(x,y+1);}
  const buf=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buf);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(verts),gl.STATIC_DRAW);
  const loc=gl.getAttribLocation(p,'aPos');gl.enableVertexAttribArray(loc);gl.vertexAttribPointer(loc,3,gl.FLOAT,false,0,0);
  gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL,true);
  [photo,normals].forEach((img,i)=>{const tex=gl.createTexture();gl.activeTexture(gl.TEXTURE0+i);gl.bindTexture(gl.TEXTURE_2D,tex);gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,gl.RGBA,gl.UNSIGNED_BYTE,img);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.LINEAR);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.LINEAR);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);gl.uniform1i(gl.getUniformLocation(p,i?'uNormal':'uPhoto'),i);});
  const k=gl.getUniformLocation(p,'uKelvin'),b=gl.getUniformLocation(p,'uLevel'),o=gl.getUniformLocation(p,'uPower');
  gl.enable(gl.BLEND);gl.blendFunc(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA);
  canvas.dataset.renderer='webgl2-displaced-relief';
  return ()=>{gl.viewport(0,0,774,812);gl.clearColor(0,0,0,0);gl.clear(gl.COLOR_BUFFER_BIT);gl.uniform1f(k,kelvin);gl.uniform1f(b,level);gl.uniform1f(o,on?1:0);gl.drawArrays(gl.TRIANGLES,0,verts.length/3);};
}
function makeCanvasRenderer(photo,normal){
 const ctx=canvas.getContext('2d',{willReadFrequently:true});const staging=document.createElement('canvas');staging.width=774;staging.height=812;const c=staging.getContext('2d',{willReadFrequently:true});
 c.drawImage(photo,0,0);const a=c.getImageData(0,0,774,812).data;c.clearRect(0,0,774,812);c.drawImage(normal,0,0);const ns=c.getImageData(0,0,774,812).data;
 const out=ctx.createImageData(774,812);canvas.dataset.renderer='cpu-normal-map';
 return ()=>{const d=out.data,cold=Math.max(0,(kelvin-2700)/3800),energy=on?Math.min(1,level/.78):0;
 for(let y=0;y<812;y++)for(let x=0;x<774;x++){
 const i=(y*774+x)*4,r=Math.hypot((x+635-1019)/348,(y+64-471)/366);if(r>1.018){d[i+3]=0;continue;}
 const gray=(a[i]*.2126+a[i+1]*.7152+a[i+2]*.0722)/255;
 const n=[ns[i]/127.5-1,ns[i+1]/127.5-1,ns[i+2]/127.5-1];const relief=(Math.max(0,n[0]*-.34+n[1]*.42+n[2]*.84)-.76)*.42;
 const neutral=[gray*.94,gray*1.025,gray*1.15];
 for(let j=0;j<3;j++){const pic=a[i+j]/255,lit=(pic*(1-cold*.87)+neutral[j]*cold*.87)*(1+relief*(.12+cold*.95))*(.55+.45*Math.min(1,level/.78));const dark=gray*[.13,.108,.089][j]+pic*.027;d[i+j]=Math.max(0,Math.min(255,255*(dark*(1-energy)+lit*energy)));}d[i+3]=Math.round(255*Math.max(0,Math.min(1,(1.017-r)/.032)));
 }
 ctx.putImageData(out,0,0);
 };
}
makeRenderer().then(fn=>{render=fn;sync();window.ezMoon={getState:()=>({kelvin,brightness:Math.round(level*100),on,renderer:canvas.dataset.renderer}),setPower,setKelvin:updateKelvin,setBrightness:(v)=>{level=v/100;sync()}};}).catch(e=>{console.warn('Moon 3D error',e);window.ezMoon={getState:()=>({error:String(e)})};});
sync();
})();
