'use strict';
/* ZYKINA ART editor — GitHub writes use a user token; optional encrypted browser vault. */
(function(){
const OWNER='zykinigor55-a11y', REPO='ez-studio-zykina', BRANCH='main';
const ROOT='https://api.github.com/repos/'+OWNER+'/'+REPO;
const ASSETS='/assets/';
const CATS={plastic:'Пластика',abstract:'Абстракция',images:'Образы',stories:'Истории'};
const VIDEO_MAX_BYTES=25*1024*1024;
const previewUrlCache=new WeakMap();
function localPreviewURL(file){if(!file)return '';if(!previewUrlCache.has(file))previewUrlCache.set(file,URL.createObjectURL(file));return previewUrlCache.get(file)}
function assetLink(path){return '/assets/'+String(path||'').replace(/^\/?assets\//,'').replace(/^\//,'')}
let token='', works=[], originals={}, pending=new Map(), touched=new Set(), dirty=false, current=null, draft=null, preview=false, busy=false;
const $=id=>document.getElementById(id);
const esc=s=>String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const numberOf=w=>Number(String(w.id||'').replace(/^art-/,''))||0;
const fileURL=p=>ASSETS+(p||'');
const shortText=s=>String(s||'').trim();
function toast(s){$('toast').textContent=s;$('toast').classList.remove('hide');clearTimeout(toast.timer);toast.timer=setTimeout(()=>$('toast').classList.add('hide'),5500)}
function screen(name){for(const id of ['catalogView','editorView','connectView','analyticsView','visitorsView'])$(id).classList.toggle('hide',id!==name+'View');$('navList').classList.toggle('active',name==='catalog');$('navCreate').classList.toggle('active',name==='editor');$('navConnect').classList.toggle('active',name==='connect');$('navAnalytics').classList.toggle('active',name==='analytics');$('navVisitors').classList.toggle('active',name==='visitors')}
function busyState(b){busy=b;$('publishBtn').disabled=b||!token;$('exportBtn').disabled=b;$('saveArtwork').disabled=b;$('loginBtn').disabled=b;$('connectBtn').disabled=b;}
function markDirty(){dirty=true;$('saveBar').classList.remove('hide');$('pendingText').textContent='Есть несохранённые изменения · '+works.length+' работ';$('publishBtn').disabled=!token;renderStats()}
function resetDirty(){dirty=false;$('saveBar').classList.add('hide');pending.clear();touched.clear()}
function renderStats(){$('countAll').textContent=works.length;$('countShown').textContent=works.filter(w=>w.visible!==false).length;$('countHidden').textContent=works.filter(w=>w.visible===false).length}

/* Popularity dashboard; read only after admin GitHub login. */
const STATS_URL='https://lxwqpoakdsbpshfyfqih.supabase.co/functions/v1/zykina-art-analytics';
let statsRows=[],statsPeriod='month',statsLoaded=false;
const statsColumns={today:'today_views',week:'week_views',month:'month_views',all:'total_views'};
const viewFmt=n=>new Intl.NumberFormat('ru-RU').format(n);
function setupArtworkThumbFallback(img,path){
 const relative=String(path||'').replace(/^\/?(?:assets\/)?/,'');
 const origins=[location.origin,'https://ez-studio-zykina.onrender.com','https://zykina-art.ru'];
 let i=0;
 img.onerror=()=>{i++;if(i<origins.length)img.src=origins[i]+'/assets/'+relative;else{img.onerror=null;img.alt='Изображение временно недоступно';}};
 img.src=origins[0]+'/assets/'+relative;
}
function renderStatsBoard(){
 const col=statsColumns[statsPeriod]||statsColumns.month;
 const counts=new Map(statsRows.map(x=>[x.artwork_id,x]));
 const items=works.map(w=>({w,count:Math.max(0,Number(counts.get(w.id)?.[col])||0)})).sort((a,b)=>b.count-a.count);
 const total=items.reduce((a,r)=>a+r.count,0),top=items.find(x=>x.count>0),max=Math.max(1,...items.map(x=>x.count));
 $('analyticsTotal').textContent=viewFmt(total);
 $('analyticsTop').textContent=top?.w.title||'Пока нет';
 $('analyticsWorks').textContent=viewFmt(items.filter(x=>x.count>0).length);
 const rank=$('analyticsRank');rank.replaceChildren();
 if(!items.length){const empty=document.createElement('div');empty.className='analytics-empty';empty.textContent='Каталог ещё не загружен. Войдите в админку.';rank.append(empty);return;}
 for(let i=0;i<items.length;i++){
  const {w,count}=items[i],cell=document.createElement('div');cell.className='analytics-row';
  const pos=document.createElement('span');pos.className='analytics-pos';pos.textContent=String(i+1).padStart(2,'0');
  const img=document.createElement('img');img.loading='lazy';img.alt=w.title||'Картина';setupArtworkThumbFallback(img,w.thumb||w.img);
  const title=document.createElement('div');title.className='analytics-title';title.textContent=w.title||'Без названия';
  const hint=document.createElement('small');hint.className='analytics-id';hint.textContent=(CATS[w.cat]||'Работа')+' · '+w.id;title.append(hint);
  const bar=document.createElement('div');bar.className='analytics-bar';bar.setAttribute('role','img');bar.setAttribute('aria-label','Просмотров: '+count);
  const fill=document.createElement('i');fill.style.width=(count/max*100).toFixed(2)+'%';bar.append(fill);
  const value=document.createElement('strong');value.className='analytics-number';value.textContent=viewFmt(count);
  cell.append(pos,img,title,bar,value);rank.append(cell);
 }
}
async function fetchArtworkStats(){
 $('analyticsStatus').textContent='Загрузка просмотров…';$('analyticsRefresh').disabled=true;
 try{
  if(!token)throw Error('Для просмотра статистики необходимо войти в GitHub');
  const r=await fetch(STATS_URL,{headers:{Authorization:'Bearer '+token},credentials:'omit',cache:'no-store'});
  if(!r.ok)throw Error(r.status===403?'Токен GitHub не имеет доступа к статистике':'Ошибка сервера '+r.status);
  const body=await r.json();
  if(!body.ok||!Array.isArray(body.rows))throw Error('Неверный ответ статистики');
  statsRows=body.rows;statsLoaded=true;renderStatsBoard();
  $('analyticsStatus').textContent='Обновлено '+new Date().toLocaleString('ru-RU')+' · статистика по московскому времени';
 }catch(e){
  $('analyticsStatus').textContent='Не удалось загрузить: '+String(e.message||e);
  if(!statsLoaded)$('analyticsRank').innerHTML='<div class="analytics-empty">Рейтинг станет доступен после входа и получения данных.</div>';
 }finally{$('analyticsRefresh').disabled=false;}
}
function openArtworkStats(){screen('analytics');if(statsLoaded)renderStatsBoard();fetchArtworkStats();}


/* Site-wide visitors report: real counters from protected server endpoint. */
let trafficPeriod=30,trafficReport=null;
const trafficLabels={direct:'Прямые заходы',search:'Поисковые системы',social:'Социальные сети',referral:'Другие сайты',mobile:'Телефоны',desktop:'Компьютеры',tablet:'Планшеты',other:'Прочие'};
const trafficNames={
  art_open:'Открытия картин',gallery:'Просмотр галереи',interior:'Вкладка «В интерьере»',
  macro:'Макродетали',order:'Переходы к заказу',contact:'Переходы к контактам'
};
function trafficN(v){const n=Number(v);return new Intl.NumberFormat('ru-RU').format(Number.isFinite(n)?n:0)}
function trafficEmpty(id,message){
 const el=$(id);el.replaceChildren();
 const empty=document.createElement('p');empty.className='traffic-muted';empty.textContent=message;el.append(empty);
}
function trafficRows(id,rows,titleFn,valueFn){
 const container=$(id);container.replaceChildren();
 if(!Array.isArray(rows)||!rows.length){trafficEmpty(id,'Данные пока не накоплены');return}
 const maximum=Math.max(1,...rows.map(r=>Number(valueFn(r))||0));
 for(const item of rows){
  const v=Math.max(0,Number(valueFn(item))||0);
  const line=document.createElement('div');line.className='traffic-list-item';
  const name=document.createElement('span');name.className='traffic-item-name';name.textContent=String(titleFn(item));
  const count=document.createElement('strong');count.className='traffic-item-number';count.textContent=trafficN(v);
  const track=document.createElement('span');track.className='traffic-list-track';
  const fill=document.createElement('i');fill.style.width=(v/maximum*100).toFixed(1)+'%';track.append(fill);
  line.append(name,count,track);container.append(line);
 }
}
function trafficPageName(p){
 if(p==='/')return 'Главная страница';
 if(p==='/kartiny/')return 'Каталог картин';
 if(p==='/kartiny-v-interere/')return 'Картины в интерьере';
 if(p==='/privacy.html')return 'Политика конфиденциальности';
 const m=String(p||'').match(/^\/kartiny\/work-(\d+)\/$/);
 if(m){const work=works.find(w=>w.id==='art-'+m[1]);return work?work.title+' · Картина':p}
 return p;
}
function drawTrafficReport(data){
 const s=data||{};trafficReport=s;
 $('trafficVisitors').textContent=trafficN(s.unique_sessions);
 $('trafficVisits').textContent=trafficN(s.visits);
 $('trafficPageViews').textContent=trafficN(s.page_views);
 $('trafficPagesPerVisit').textContent=(Number(s.avg_pages)||0).toLocaleString('ru-RU',{maximumFractionDigits:2});
 const days=Array.isArray(s.trend)?s.trend.slice(-45):[];
 const chart=$('trafficTrend');chart.replaceChildren();
 if(!days.length){trafficEmpty('trafficTrend','Данных пока нет. Счётчик начал собирать статистику после публикации.');}
 else{
  const top=Math.max(1,...days.map(x=>Number(x.visits)||0));
  for(let i=0;i<days.length;i++){
   const x=days[i],n=Number(x.visits)||0;
   const item=document.createElement('div');item.className='traffic-trend-col';
   const bar=document.createElement('div');bar.className='traffic-trend-bar';
   bar.style.height=Math.max(2,n/top*138)+'px';
   const day=document.createElement('span');day.textContent=(i===0||i===days.length-1||i%7===0)?String(x.day).slice(5):'';
   item.title=x.day+': '+trafficN(n)+' визитов, '+trafficN(x.views)+' просмотров';
   item.append(bar,day);chart.append(item);
  }
 }
 trafficRows('trafficCities',s.cities,x=>x.city+(x.city==='Не определён'?'':', '+x.country),x=>x.visitors);
 trafficRows('trafficCountries',s.countries,x=>x.name,x=>x.visitors);
 trafficRows('trafficSources',s.sources,x=>trafficLabels[x.name]||x.name,x=>x.visitors);
 trafficRows('trafficDevices',s.devices,x=>trafficLabels[x.name]||x.name,x=>x.visitors);
 trafficRows('trafficTopPages',s.top_pages,x=>trafficPageName(x.path),x=>x.views);
 const events=$('trafficEvents');events.replaceChildren();
 for(const [key,label] of Object.entries(trafficNames)){
  const box=document.createElement('div');
  const num=document.createElement('strong');num.textContent=trafficN(s.events?.[key]);
  const name=document.createElement('span');name.textContent=label;box.append(num,name);events.append(box);
 }
}
async function loadTrafficReport(){
 const status=$('trafficStatus');status.textContent='Загружаем посещаемость сайта…';
 $('siteStatsRefresh').disabled=true;
 try{
  if(!token)throw Error('Необходимо войти в админку с GitHub-ключом');
  const url=STATS_URL+'?view=site&days='+trafficPeriod;
  const result=await fetch(url,{headers:{authorization:'Bearer '+token},credentials:'omit',cache:'no-store'});
  if(!result.ok)throw Error(result.status===403?'Недостаточно прав для аналитики':'HTTP '+result.status);
  const parsed=await result.json();
  if(!parsed.ok||!parsed.stats)throw Error('Неверный ответ сервера');
  drawTrafficReport(parsed.stats);
  status.textContent='Обновлено '+new Date().toLocaleString('ru-RU')+' · данные по московскому времени';
 }catch(e){
  status.textContent='Не удалось загрузить статистику: '+String(e.message||e);
  if(!trafficReport){for(const id of ['trafficTrend','trafficCities','trafficCountries','trafficSources','trafficDevices','trafficTopPages'])trafficEmpty(id,'Статистика недоступна');}
 }finally{$('siteStatsRefresh').disabled=false}
}
function openTrafficDashboard(){screen('visitors');loadTrafficReport()}

function renderList(){
  renderStats();
  $('workList').innerHTML=works.length?'':'<div class="empty">Картины не найдены</div>';
  for(let i=0;i<works.length;i++){
    const w=works[i],row=document.createElement('div');row.className='work'+(w.visible===false?' dim':'');
    const img=document.createElement('img');img.alt=w.title||'Картина';img.loading='lazy';setupArtworkThumbFallback(img,w.thumb||w.img);
    const meta=document.createElement('div');meta.innerHTML='<h4>'+esc(w.title||'Без названия')+'</h4><small>'+esc(CATS[w.cat]||'Категория')+' · '+esc(w.id||'')+'</small>'+(w.visible===false?'<span class="tag">Скрыта из каталога</span>':'');
    const actions=document.createElement('div');actions.className='actions';
    const controls=[['↑','Поднять',()=>move(i,-1)],['↓','Опустить',()=>move(i,1)],['✎','Редактировать',()=>edit(w.id)],[(w.visible===false?'◉':'◌'),(w.visible===false?'Показать':'Скрыть из каталога'),()=>toggle(w.id)]];
    for(const [symbol,label,fn] of controls){const b=document.createElement('button');b.className='action';b.textContent=symbol;b.title=label;b.setAttribute('aria-label',label);b.addEventListener('click',fn);actions.append(b)}
    row.append(img,meta,actions);$('workList').append(row);
  }
}
function move(i,d){const j=i+d;if(j<0||j>=works.length)return;[works[i],works[j]]=[works[j],works[i]];markDirty();renderList()}
function toggle(id){const w=works.find(w=>w.id===id);if(!w)return;w.visible=w.visible===false?true:false;markDirty();renderList()}
function newWork(){let n=Math.max(18,...works.map(numberOf))+1;current='art-'+n;draft={id:current,title:'',cat:'plastic',visible:true,description:'',size:'От 40 × 60 до 120 × 100 см, на заказ',photos:[],interiors:[],videoFile:'',img:'',thumb:'',page:'kartiny/work-'+n+'/'};paintDraft(true)}
function edit(id){const w=works.find(w=>w.id===id);if(!w)return;current=id;draft=Object.assign({},w,{photos:[...(w.photos||[])],interiors:[...(w.interiors||[])]});paintDraft(false)}
function paintDraft(fresh){
  $('editorHeading').textContent=fresh?'Новая картина':'Редактирование · '+(draft.title||draft.id);
  $('titleInput').value=draft.title||'';$('catInput').value=draft.cat||'plastic';$('descInput').value=draft.description||'';$('sizeInput').value=draft.size||'От 40 × 60 до 120 × 100 см, на заказ';$('videoUrlInput').value=draft.videoUrl||'';$('visibleInput').checked=draft.visible!==false;
  $('mainPhoto').value='';$('detailPhotos').value='';$('interiorPhotos').value='';$('videoFile').value='';$('removeVideoInput').checked=false;showPreview();screen('editor');window.scrollTo({top:0,behavior:'smooth'});
}
function showPreview(){
  const p=pending.get(current)||{},src=p.main?URL.createObjectURL(p.main):draft.thumb?fileURL(draft.thumb):'';
  const img=$('mainPreview');if(src){img.src=src;img.classList.remove('hide');$('uploadCaption').classList.add('hide')}else{img.removeAttribute('src');img.classList.add('hide');$('uploadCaption').classList.remove('hide')}
  $('detailPreviews').innerHTML='';
  const entries=(draft.photos||[]).slice(1).map(p=>({url:fileURL(p)})).concat((p.extras||[]).map(file=>({url:URL.createObjectURL(file)})));
  for(const entry of entries){const image=document.createElement('img');image.src=entry.url;image.alt='Фрагмент картины';$('detailPreviews').append(image)}
  $('interiorPreviews').replaceChildren();
  const interiors=(draft.interiors||[]).map((path,index)=>({url:assetLink(path),index,saved:true}))
    .concat((p.interiors||[]).map((file,index)=>({url:localPreviewURL(file),index,saved:false})));
  for(const entry of interiors){
    const thumb=document.createElement('div');thumb.className='interior-thumb';
    const image=document.createElement('img');image.className='interiors-photo';image.src=entry.url;image.alt='Фото картины в интерьере';
    const remove=document.createElement('button');remove.type='button';remove.className='interior-thumb-remove';
    remove.textContent='×';remove.title='Удалить интерьер';remove.setAttribute('aria-label','Удалить интерьерное фото '+(entry.index+1));
    remove.addEventListener('click',()=>{
      if(entry.saved){
        if(!window.confirm('Удалить это фото из раздела «В интерьере»? После сохранения в GitHub оно исчезнет с сайта.'))return;
        draft.interiors.splice(entry.index,1);
      }else{
        const upload=pending.get(current);
        if(upload&&upload.interiors)upload.interiors.splice(entry.index,1);
        $('interiorPhotos').value='';
      }
      showPreview();
      toast('Фото убрано из карточки. Нажмите «Сохранить в подборке», затем «Сохранить в GitHub».');
    });
    thumb.append(image,remove);$('interiorPreviews').append(thumb);
  }
  const video=$('videoPreview'),source=p.video?localPreviewURL(p.video):draft.videoFile?assetLink(draft.videoFile):'';
  if(source){if(video.getAttribute('src')!==source){video.pause();video.src=source}video.classList.remove('hide')}
  else{video.pause();video.removeAttribute('src');video.load();video.classList.add('hide')}
  $('videoUploadStatus').textContent=p.video?'Выбрано: '+p.video.name+' · '+(p.video.size/1048576).toFixed(1)+' МБ. Будет загружено после сохранения в GitHub.':
   draft.videoFile?'Видео уже добавлено. Можно загрузить другое MP4/WebM (до 25 МБ).':
   draft.videoUrl?'Ранее добавлено видео по ссылке. Выберите файл MP4/WebM, чтобы заменить его.':
   'MP4 или WebM, до 25 МБ. Выбери ролик с компьютера и нажми «Сохранить в GitHub».';
}
function saveDraft(){
  if(!draft)return;
  draft.title=shortText($('titleInput').value);
  draft.cat=$('catInput').value;draft.description=shortText($('descInput').value);
  draft.size=shortText($('sizeInput').value);draft.visible=$('visibleInput').checked;
  const rawVideo=shortText($('videoUrlInput').value);
  if(rawVideo){
    try{const u=new URL(rawVideo);if(u.protocol!=='https:'||!u.hostname||u.username||u.password)throw Error('url')}
    catch{toast('Введите безопасную ссылку на видео, начинающуюся с https://');$('videoUrlInput').focus();return}
  }
  draft.videoUrl=rawVideo;
  const files=pending.get(current)||{};
  if($('removeVideoInput').checked&&!files.video){draft.videoFile='';draft.videoUrl='';}
  if(files.video){draft.videoUrl='';draft.videoFile='';}
  if(!draft.title){toast('Введите название картины');$('titleInput').focus();return}
  if(!(draft.img || files.main)){toast('Загрузите главное фото новой картины');return}
  const idx=works.findIndex(w=>w.id===current);
  if(idx<0)works.unshift(draft);else works[idx]=draft;
  touched.add(current);markDirty();renderList();screen('catalog');toast('Работа добавлена в подборку. Теперь сохраните изменения в GitHub или скачайте ZIP.');
}
async function request(path,method='GET',body){
  const headers={'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'};
  if(token)headers.Authorization='Bearer '+token;
  if(body!==undefined)headers['Content-Type']='application/json';
  const r=await fetch(ROOT+path,{method,headers,body:body===undefined?undefined:JSON.stringify(body),cache:'no-store',referrerPolicy:'no-referrer'});
  let json;try{json=await r.json()}catch{throw Error('GitHub: HTTP '+r.status)}
  if(!r.ok){throw Error('GitHub '+r.status+': '+(json.message||'ошибка')+(r.status===401?' — проверьте токен':''))}
  return json;
}
function decodeBase64(s){const binary=atob(String(s).replace(/\s/g,''));const bytes=new Uint8Array(binary.length);for(let i=0;i<binary.length;i++)bytes[i]=binary.charCodeAt(i);return new TextDecoder().decode(bytes)}
function toB64(bytes){let out='';const step=0x8000;for(let i=0;i<bytes.length;i+=step)out+=String.fromCharCode.apply(null,bytes.subarray(i,i+step));return btoa(out)}
async function loadText(path){const doc=await request('/contents/'+path.split('/').map(encodeURIComponent).join('/')+'?ref='+BRANCH);return decodeBase64(doc.content)}
async function load(){
 busyState(true);
 try{
  const ps=['public/assets/catalog/manifest.json','public/index.html','public/kartiny/index.html','public/sitemap.xml','public/assets/catalog/video-links.json','public/assets/catalog/interior-media.json','public/kartiny-v-interere/index.html'];
  const out=await Promise.all(ps.map(p=>loadText(p).catch(e=>{if(p==='public/sitemap.xml')return '';if(p==='public/kartiny-v-interere/index.html'&&/404/.test(String(e)))return '';if((p.endsWith('video-links.json')||p.endsWith('interior-media.json'))&&/404/.test(String(e)))return '{}';throw e})));
  const videoLinks=JSON.parse(out[4]||'{}'),mediaLinks=JSON.parse(out[5]||'{}');
  if(!videoLinks||Array.isArray(videoLinks)||typeof videoLinks!=='object'||!mediaLinks||Array.isArray(mediaLinks)||typeof mediaLinks!=='object')throw Error('Некорректные данные галереи');
  originals={manifest:out[0],index:out[1],catalog:out[2],sitemap:out[3],videoLinks:out[4],interiorMedia:out[5],interiorsPage:out[6]};
  works=JSON.parse(out[0]).map(w=>{
    const item=mediaLinks[w.id]||{};
    return Object.assign({visible:true,description:'',size:''},w,{videoUrl:videoLinks[w.id]||w.videoUrl||'',interiors:Array.isArray(item.photos)?item.photos:(w.interiors||[]),videoFile:item.video||w.videoFile||''});
  });
  resetDirty();renderList();screen('catalog');
  $('loginMask').classList.add('hide');$('connStatus').textContent=token?'GitHub · подключено':'Предпросмотр / без доступа на запись';$('publishBtn').disabled=!token;
  toast('Каталог загружен: '+works.length+' картин');
  return true;
 }catch(e){toast(e.message);$('connStatus').textContent='Не удалось загрузить каталог';$('loginMask').classList.remove('hide');return false}finally{busyState(false)}
}

/* Optional on-device encrypted token vault. The password never leaves the browser. */
const VAULT_KEY='zykina-art-vault-v1',VAULT_ITERATIONS=310000;
function savedVault(){
 try{
  const raw=localStorage.getItem(VAULT_KEY);
  if(!raw)return null;
  const v=JSON.parse(raw);
  return v&&v.v===1&&v.iterations===VAULT_ITERATIONS&&typeof v.salt==='string'&&typeof v.iv==='string'&&typeof v.ct==='string'?v:null;
 }catch{return null}
}
function vaultBytes(s){const bin=atob(s),out=new Uint8Array(bin.length);for(let i=0;i<bin.length;i++)out[i]=bin.charCodeAt(i);return out}
async function vaultKey(password,salt){
 const material=await crypto.subtle.importKey('raw',new TextEncoder().encode(password),'PBKDF2',false,['deriveKey']);
 return crypto.subtle.deriveKey({name:'PBKDF2',salt,iterations:VAULT_ITERATIONS,hash:'SHA-256'},material,{name:'AES-GCM',length:256},false,['encrypt','decrypt']);
}
async function rememberToken(secret,password){
 if(!globalThis.isSecureContext||!crypto||!crypto.subtle)throw Error('Для защищённого хранения требуется HTTPS');
 const salt=crypto.getRandomValues(new Uint8Array(16)),iv=crypto.getRandomValues(new Uint8Array(12));
 const key=await vaultKey(password,salt),ct=new Uint8Array(await crypto.subtle.encrypt({name:'AES-GCM',iv},key,new TextEncoder().encode(secret)));
 localStorage.setItem(VAULT_KEY,JSON.stringify({v:1,iterations:VAULT_ITERATIONS,salt:toB64(salt),iv:toB64(iv),ct:toB64(ct)}));
}
function displayLoginView(){
 const exists=!!savedVault();
 $('vaultLogin').classList.toggle('hide',!exists);
 $('tokenLogin').classList.toggle('hide',exists);
 $('loginMask').classList.remove('hide');
 $('newPassFields').classList.toggle('hide',!$('rememberBrowser').checked);
}
async function unlockVault(){
 const vault=savedVault(),password=$('vaultPassword').value;
 if(!vault){displayLoginView();toast('Сохранённый вход не найден. Подключите GitHub-токен снова.');return}
 if(!password){toast('Введите свой пароль');return}
 const button=$('unlockBtn');button.disabled=true;
 try{
  const key=await vaultKey(password,vaultBytes(vault.salt));
  token=new TextDecoder().decode(await crypto.subtle.decrypt({name:'AES-GCM',iv:vaultBytes(vault.iv)},key,vaultBytes(vault.ct)));
  preview=false;
  const ok=await load();
  if(!ok){token='';toast('Токен мог истечь. Нажмите «Войти по токену» и подключите новый.');return}
  $('vaultPassword').value='';
 }catch{
  token='';
  toast('Неверный пароль или повреждённый сохранённый вход');
 }finally{button.disabled=false}
}
async function login(value){
 const newToken=String(value||'').trim();
 if(!newToken){toast('Введите GitHub-токен');return}
 const shouldRemember=$('rememberBrowser').checked;
 const pass=$('newVaultPassword').value,confirmPass=$('confirmVaultPassword').value;
 if(shouldRemember&&(pass.length<12||pass!==confirmPass)){
  toast(pass.length<12?'Пароль должен быть не короче 12 символов':'Пароли не совпадают');
  return;
 }
 token=newToken;preview=false;
 const ok=await load();
 if(!ok){token='';return}
 $('loginToken').value='';$('connectToken').value='';
 if(shouldRemember){
  try{await rememberToken(newToken,pass);toast('Вход настроен: на этом устройстве теперь достаточно пароля')}
  catch{toast('Вход выполнен, но браузер не смог сохранить зашифрованный токен')}
 }
 $('newVaultPassword').value='';$('confirmVaultPassword').value='';
}

function showConnect(){screen('connect');$('loginMask').classList.add('hide')}
function visibleWorks(){return works.filter(w=>w.visible!==false)}
function cleanWorks(){return works.map(w=>{const c={};for(const key of ['id','title','cat','img','thumb','photos','page','description','size','visible','videoUrl','videoFile','interiors'])if(w[key]!==undefined)c[key]=w[key];return c})}
function buildHome(ws){
  const source=originals.index;
  const pattern=/const works=\[[\s\S]*?\];\s*\nconst catNames=/;
  if(!pattern.test(source))throw Error('Не удалось найти список картин на главной странице. Ничего не опубликовано.');
  const data=JSON.stringify(ws).replace(/</g,'\\u003c').replace(/[\u2028\u2029]/g,'');
  return source.replace(pattern,'const works='+data+';\nconst catNames=');
}
function buildCatalog(ws){
  let html=originals.catalog;
  const list=ws.map(w=>'<article><a href="/'+esc(w.page)+'"><img src="/assets/'+esc(w.thumb||w.img)+'" loading="lazy" alt="'+esc(w.title)+'"><h2>'+esc(w.title)+'</h2></a><p>'+esc(CATS[w.cat]||'Авторская работа')+'</p></article>').join('');
  const grid=/<div class="grid">[\s\S]*?<\/div><\/main>/;
  if(!grid.test(html))throw Error('Не удалось найти каталог. Изменения не сохранены.');
  html=html.replace(grid,'<div class="grid">'+list+'</div></main>');
  const ld={'@context':'https://schema.org','@type':'CollectionPage',name:'Каталог авторских работ Екатерины Зыкиной',url:'https://zykina-art.ru/kartiny/',inLanguage:'ru_RU',mainEntity:{'@type':'ItemList',itemListElement:ws.map((w,i)=>({'@type':'ListItem',position:i+1,url:'https://zykina-art.ru/'+w.page}))}};
  const ldRegex=/<script type="application\/ld\+json">[\s\S]*?<\/script>/;
  if(!ldRegex.test(html))throw Error('Не удалось обновить SEO каталога.');
  html=html.replace(ldRegex,'<script type="application/ld+json">'+JSON.stringify(ld).replace(/</g,'\\u003c')+'</script>');
  return html;
}

function buildInteriorsPage(ws){
 if(!originals.interiorsPage)return null;
 const list=[];
 for(const w of ws){if(w.visible===false)continue;(w.interiors||[]).forEach((path,index)=>{if(path)list.push({w,path,index})});}
 const card=({w,path,index})=>
 '<a class="zi-work" href="/'+esc(w.page)+'" aria-label="'+esc(w.title)+' — открыть страницу картины">'+
 '<span class="zi-work-image"><img src="'+assetLink(esc(path))+'" loading="lazy" decoding="async" alt="'+esc(w.title)+' — '+(index?'другой ракурс интерьера':'картина в интерьере')+'"></span>'+
 '<span class="zi-work-label"><strong>'+esc(w.title)+'</strong><span>'+(index?'Дополнительный вид':'Смотреть работу')+' ↗</span></span></a>';
 let html=originals.interiorsPage;
 const grid=/<div class="zi-page-grid">[\s\S]*?<\/div><\/section>/;
 if(!grid.test(html))throw Error('Не найдена галерея интерьеров для обновления.');
 html=html.replace(grid,'<div class="zi-page-grid">'+(list.length?list.map(card).join('\n'):'<p>Интерьерные композиции скоро появятся.</p>')+'</div></section>');
 html=html.replace(/<p>\d+ интерьерных композиций<\/p>/,'<p>'+list.length+' интерьерных композиций</p>');
 if(list.length){
  const first=list[0];
  html=html.replace(/(<section class="zi-page-feature"[^>]*><img src=")[^"]*(" alt=")[^"]*"/,
   (_,a,b)=>a+assetLink(esc(first.path))+b+esc(first.w.title)+' — пример картины в интерьере"');
  html=html.replace(/(<meta property="og:image" content=")[^"]*"/,
   (_,a)=>a+'https://zykina-art.ru'+assetLink(esc(first.path))+'"');
 }else{
  html=html.replace(/<section class="zi-page-feature"[\s\S]*?<\/section>/,'');
 }
 return html;
}

function pageHTML(w){
 const cat=CATS[w.cat]||'Авторская картина',title=esc(w.title),desc=esc(w.description||('«'+w.title+'» — авторская работа Екатерины Зыкиной. Фотографии и детали.')),url='https://zykina-art.ru/'+w.page;
 const kind=({plastic:'Фактурная картина',abstract:'Абстрактная картина',images:'Интерьерная картина',stories:'Сюжетная картина'})[w.cat]||'Авторская картина';
 const seoTitle=esc(kind+' «'+String(w.title).replace(/^«|»$/g,'')+'» — Екатерина Зыкина | ZYKINA ART');
 const seoDesc=esc((w.description||('Авторская интерьерная картина Екатерины Зыкиной «'+w.title+'». Фотографии и детали.')).replace(/\s+/g,' ').trim().slice(0,180));
 const photos=(w.photos&&w.photos.length?w.photos:[w.img]).map(p=>'/assets/'+esc(p));
 const cover=photos[0]||'';
 const ld={'@context':'https://schema.org','@type':'VisualArtwork',name:w.title,image:(w.photos||[w.img]).map(p=>'https://zykina-art.ru/assets/'+p),url,description:w.description||'Авторская работа Екатерины Зыкиной',inLanguage:'ru',genre:kind,creator:{'@type':'Person',name:'Екатерина Зыкина'}};
 const thumbs=photos.slice(1).map((src,i)=>'<a href="'+src+'" target="_blank" rel="noopener"><img src="'+src+'" alt="'+title+' — деталь '+(i+1)+'" loading="lazy"></a>').join('');
 return '<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="'+(w.visible===false?'noindex,follow':'index,follow')+'">'+
 '<title>'+seoTitle+'</title><meta name="description" content="'+seoDesc+'"><link rel="canonical" href="'+esc(url)+'"><meta property="og:title" content="'+title+' — ZYKINA ART"><meta property="og:description" content="'+desc+'"><meta property="og:type" content="article"><meta property="og:image" content="https://zykina-art.ru'+cover+'"><script type="application/ld+json">'+JSON.stringify(ld).replace(/</g,'\\u003c')+'</script>'+
 '<style>body{margin:0;background:#f4f0e9;color:#44352b;font:16px/1.75 Arial,sans-serif}main{max-width:1000px;margin:30px auto;padding:0 24px}a{color:inherit}header{display:flex;flex-wrap:wrap;gap:24px;font-size:13px;color:#806c5a}h1{font:400 clamp(44px,7vw,76px)/1.1 Georgia,serif;margin:30px 0}figure{margin:0}figure img{max-width:100%;max-height:86vh;object-fit:contain;margin:auto;display:block}.type{color:#897666;font-size:12px;letter-spacing:.15em;text-transform:uppercase;margin-top:55px}.details{display:flex;gap:18px;flex-wrap:wrap;margin:38px 0}.details img{width:180px;height:180px;object-fit:contain;border:1px solid #ddd1c1}.contact{display:inline-block;padding:14px 19px;border:1px solid #655241;text-decoration:none;margin:25px 0 65px}.size{color:#796c60}</style></head><body><main><header><a href="/">ZYKINA ART</a><a href="/kartiny/">Все работы</a></header><p class="type">'+esc(cat)+'</p><h1>'+title+'</h1><figure><img src="'+cover+'" alt="'+title+' — общий вид"></figure><p>'+desc+'</p><div class="details">'+thumbs+'</div><p class="size"><strong>Размер:</strong> '+esc(w.size||'Уточняется индивидуально')+'</p><a class="contact" href="/#order">Обсудить заказ</a></main><script src="/assets/artwork-view-tracker.js?v=20261124-met1" data-artwork="'+esc(w.id)+'" defer></script></body></html>';
}
function buildSitemap(ws){
 const base='https://zykina-art.ru';
 const xmlEsc=v=>String(v).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&apos;');
 const node=(url,images=[])=>'<url><loc>'+xmlEsc(base+url)+'</loc>'+[...new Set(images.filter(Boolean))].map(p=>'<image:image><image:loc>'+xmlEsc(base+'/assets/'+p)+'</image:loc></image:image>').join('')+'</url>';
 const visible=ws.filter(w=>w.visible!==false);
 const urls=[node('/'),node('/kartiny/')];
 if(originals.interiorsPage)urls.push(node('/kartiny-v-interere/',visible.flatMap(w=>w.interiors||[])));
 for(const w of visible)urls.push(node('/'+w.page,[w.img,...(w.photos||[])]));
 // Keep independently maintained editorial URLs when the artwork catalog is published.
 for(const match of String(originals.sitemap||'').matchAll(/<url>[\s\S]*?<\/url>/g)){if(/<loc>https:\/\/zykina-art\.ru\/journal\/(?:[a-z0-9-]+\/)?<\/loc>/.test(match[0]))urls.push(match[0]);}
 return '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">\n'+urls.join('\n')+'\n</urlset>\n';
}
async function compress(file,maxEdge,quality){
 const bitmap=await createImageBitmap(file);const scale=Math.min(1,maxEdge/Math.max(bitmap.width,bitmap.height));
 const width=Math.max(1,Math.round(bitmap.width*scale)),height=Math.max(1,Math.round(bitmap.height*scale));
 const canvas=document.createElement('canvas');canvas.width=width;canvas.height=height;const ctx=canvas.getContext('2d',{alpha:true});
 if(!ctx)throw Error('Не удалось обработать фотографию');
 ctx.drawImage(bitmap,0,0,width,height);bitmap.close();
 const blob=await new Promise(resolve=>canvas.toBlob(resolve,'image/webp',quality));
 if(!blob)throw Error('Не удалось преобразовать фотографию в WebP');return new Uint8Array(await blob.arrayBuffer());
}
function utf8(s){return new TextEncoder().encode(s)}
async function prepare(){
 if(!originals.index||!originals.catalog)throw Error('Сначала загрузите каталог с GitHub.');
 const staged=works.map(w=>Object.assign({},w,{photos:[...(w.photos||[])],interiors:[...(w.interiors||[])]}));const files=new Map();
 const now=Date.now().toString(36);
 for(const w of staged){
   const p=pending.get(w.id);if(!p)continue;
   const n=numberOf(w);
   if(p.main){
     const path='картины/'+n+'/main-'+now+'.webp';const img=await compress(p.main,2400,.88);
     files.set('public/assets/'+path,img);w.img=encodeURI(path);w.thumb='catalog/'+n+'-'+now+'.webp';
     files.set('public/assets/'+w.thumb,await compress(p.main,980,.83));
     w.photos=[w.img,...(w.photos||[]).filter(x=>x!==w.img)];
   }
   for(let i=0;i<(p.extras||[]).length;i++){
      const path='картины/'+n+'/detail-'+now+'-'+(i+1)+'.webp';
      files.set('public/assets/'+path,await compress(p.extras[i],2200,.88));
      w.photos.push(encodeURI(path));
   }
   for(let i=0;i<(p.interiors||[]).length;i++){
      const path='interiors/'+n+'/interior-'+now+'-'+(i+1)+'.webp';
      files.set('public/assets/'+path,await compress(p.interiors[i],2200,.86));
      w.interiors.push(encodeURI(path));
   }
   if(p.video){
      if(p.video.size>VIDEO_MAX_BYTES)throw Error('Видео больше 25 МБ. Сожмите MP4 или WebM перед загрузкой.');
      const ext=/\.webm$/i.test(p.video.name)?'webm':/\.mp4$/i.test(p.video.name)?'mp4':null;
      if(!ext)throw Error('Поддерживаются видео только MP4 и WebM.');
      const path='videos/'+n+'/interior-'+now+'.'+ext;
      files.set('public/assets/'+path,new Uint8Array(await p.video.arrayBuffer()));
      w.videoFile=path;w.videoUrl='';
   }
   if(!w.img&&w.photos.length)w.img=w.photos[0];
   if(!w.thumb)w.thumb=w.img;
   w.page=w.page||'kartiny/work-'+n+'/';
 }
 const show=staged.filter(w=>w.visible!==false);
 const serialized=staged.map(w=>{const obj={};for(const key of ['id','title','cat','img','thumb','photos','page','description','size','visible'])if(w[key]!==undefined)obj[key]=w[key];return obj});
 // MCHost's scheduled publisher builds work pages from per-folder metadata.
 // Save it together with every edited artwork to keep names, categories and descriptions stable.
 for(const w of staged){
   if(!touched.has(w.id))continue;
   const n=numberOf(w);
   if(!Number.isInteger(n)||n<1||!w.img)throw Error('Не удалось сохранить данные картины '+(w.id||''));
   const photoPath=decodeURIComponent(w.img),prefix='картины/'+n+'/';
   if(!photoPath.startsWith(prefix)||photoPath.slice(prefix.length).includes('/'))throw Error('Неверный путь главной фотографии: '+w.id);
   const metadata={
     title:w.title,category:w.cat,main:photoPath.slice(prefix.length),
     thumbnail:decodeURIComponent(w.thumb||w.img),
     description:w.description||'',size:w.size||'',
     video:w.videoUrl||'',
     published:w.visible!==false
   };
   files.set('public/assets/картины/'+n+'/работа.json',utf8(JSON.stringify(metadata,null,2)+'\n'));
 }
 const videoLinks={},interiorMedia={};
 for(const w of staged){
   if(w.videoUrl)videoLinks[w.id]=w.videoUrl;
   if((w.interiors||[]).length||w.videoFile)interiorMedia[w.id]={photos:[...(w.interiors||[])],video:w.videoFile||''};
 }
 files.set('public/assets/catalog/video-links.json',utf8(JSON.stringify(videoLinks,null,2)+'\n'));
 files.set('public/assets/catalog/interior-media.json',utf8(JSON.stringify(interiorMedia,null,2)+'\n'));
 files.set('public/assets/catalog/manifest.json',utf8(JSON.stringify(serialized,null,2)+'\n'));
 const archive=buildInteriorsPage(staged);if(archive)files.set('public/kartiny-v-interere/index.html',utf8(archive));
 files.set('public/index.html',utf8(buildHome(show)));
 files.set('public/kartiny/index.html',utf8(buildCatalog(show)));
 for(const id of touched){const w=staged.find(w=>w.id===id);if(w)files.set('public/'+w.page+'index.html',utf8(pageHTML(w)))}
 const sitemap=buildSitemap(show);if(sitemap)files.set('public/sitemap.xml',utf8(sitemap));
 return {files,staged};
}
async function publish(){
 if(!token){toast('Для сохранения нужен GitHub-токен. Можно скачать ZIP для ручной публикации.');return}
 if(!dirty){toast('Нет изменений для сохранения');return}
 busyState(true);$('pendingText').textContent='Подготовка файлов и фотографий...';
 try{
  const built=await prepare();$('pendingText').textContent='Отправка в GitHub · '+built.files.size+' файлов...';
  const ref=await request('/git/ref/heads/'+BRANCH);const oldCommit=await request('/git/commits/'+ref.object.sha);
  const items=[];
  for(const [path,bytes] of built.files){
    const blob=await request('/git/blobs','POST',{content:toB64(bytes),encoding:'base64'});
    items.push({path,mode:'100644',type:'blob',sha:blob.sha});
  }
  const tree=await request('/git/trees','POST',{base_tree:oldCommit.tree.sha,tree:items});
  const newCommit=await request('/git/commits','POST',{message:'ZYKINA ART: update artwork catalog via admin panel',tree:tree.sha,parents:[ref.object.sha]});
  await request('/git/refs/heads/'+BRANCH,'PATCH',{sha:newCommit.sha,force:false});
  works=built.staged;originals.videoLinks=new TextDecoder().decode(built.files.get('public/assets/catalog/video-links.json'));originals.interiorMedia=new TextDecoder().decode(built.files.get('public/assets/catalog/interior-media.json'));originals.manifest=new TextDecoder().decode(built.files.get('public/assets/catalog/manifest.json'));originals.index=new TextDecoder().decode(built.files.get('public/index.html'));originals.catalog=new TextDecoder().decode(built.files.get('public/kartiny/index.html'));if(built.files.has('public/kartiny-v-interere/index.html'))originals.interiorsPage=new TextDecoder().decode(built.files.get('public/kartiny-v-interere/index.html'));if(built.files.has('public/sitemap.xml'))originals.sitemap=new TextDecoder().decode(built.files.get('public/sitemap.xml'));
  resetDirty();renderList();toast('Готово! Картины сохранены в GitHub. Для появления на основном сайте необходима синхронизация MCHost.');
 }catch(e){toast('Не удалось сохранить: '+e.message)}finally{busyState(false);if(dirty)$('pendingText').textContent='Изменения ещё не сохранены'}
}
function crc32(bytes){let crc=0xffffffff;for(const byte of bytes){crc^=byte;for(let j=0;j<8;j++)crc=(crc>>>1)^((crc&1)?0xedb88320:0)}return (crc^0xffffffff)>>>0}
function put16(d,o,x){d.setUint16(o,x,true)}function put32(d,o,x){d.setUint32(o,x>>>0,true)}
function zipFiles(files){
 const chunks=[],centers=[];let offset=0;
 for(const [path,data] of files){
   const name=utf8(path.replace(/^public\//,'')),len=data.length,crc=crc32(data);
   const loc=new Uint8Array(30+name.length),ld=new DataView(loc.buffer);
   put32(ld,0,0x04034b50);put16(ld,4,20);put16(ld,6,0x0800);put16(ld,8,0);
   put32(ld,14,crc);put32(ld,18,len);put32(ld,22,len);put16(ld,26,name.length);loc.set(name,30);
   const central=new Uint8Array(46+name.length),cd=new DataView(central.buffer);
   put32(cd,0,0x02014b50);put16(cd,4,20);put16(cd,6,20);put16(cd,8,0x0800);put16(cd,10,0);
   put32(cd,16,crc);put32(cd,20,len);put32(cd,24,len);put16(cd,28,name.length);put32(cd,42,offset);central.set(name,46);
   chunks.push(loc,data);centers.push(central);offset+=loc.length+len;
 }
 const centeroffset=offset;for(const c of centers){chunks.push(c);offset+=c.length}
 const end=new Uint8Array(22),ed=new DataView(end.buffer);
 put32(ed,0,0x06054b50);put16(ed,8,centers.length);put16(ed,10,centers.length);put32(ed,12,offset-centeroffset);put32(ed,16,centeroffset);
 chunks.push(end);return new Blob(chunks,{type:'application/zip'});
}
async function exportZip(){
 if(!dirty){toast('Сначала внесите изменения в каталог');return}
 busyState(true);$('pendingText').textContent='Создание ZIP-архива для MCHost...';
 try{const {files}=await prepare(),zip=zipFiles(files),url=URL.createObjectURL(zip),a=document.createElement('a');a.href=url;a.download='zykina-art-update-'+new Date().toISOString().slice(0,10)+'.zip';document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),30000);toast('ZIP создан. Распакуйте его в корне сайта www/zykina-art.ru (после резервного копирования).')}
 catch(e){toast('ZIP не создан: '+e.message)}finally{busyState(false);$('pendingText').textContent='Есть несохранённые изменения'}
}
$('rememberBrowser').addEventListener('change',()=>$('newPassFields').classList.toggle('hide',!$('rememberBrowser').checked));
$('unlockBtn').addEventListener('click',unlockVault);
$('vaultPassword').addEventListener('keydown',e=>{if(e.key==='Enter')unlockVault()});
$('showTokenBtn').addEventListener('click',()=>{$('vaultLogin').classList.add('hide');$('tokenLogin').classList.remove('hide');$('loginToken').focus()});
$('forgetVaultBtn').addEventListener('click',()=>{
 if(!window.confirm('Удалить сохранённый зашифрованный ключ на этом устройстве? Для следующего входа потребуется GitHub-токен.'))return;
 try{localStorage.removeItem(VAULT_KEY)}catch{}
 token='';$('vaultPassword').value='';$('rememberBrowser').checked=false;
 displayLoginView();toast('Сохранённый вход удалён на этом устройстве');
});
$('loginBtn').addEventListener('click',()=>login($('loginToken').value));
$('loginToken').addEventListener('keydown',e=>{if(e.key==='Enter')login($('loginToken').value)});
$('previewBtn').addEventListener('click',()=>{token='';preview=true;load()});
$('connectBtn').addEventListener('click',()=>login($('connectToken').value));
$('disconnectBtn').addEventListener('click',()=>{token='';$('connStatus').textContent='GitHub отключён';$('publishBtn').disabled=true;displayLoginView();toast('Вы вышли из админ-панели. Зашифрованный ключ на устройстве сохранён, если вы его включали.')});
$('navList').addEventListener('click',()=>screen('catalog'));
$('navCreate').addEventListener('click',newWork);
$('navConnect').addEventListener('click',showConnect);
$('navAnalytics').addEventListener('click',openArtworkStats);
$('navVisitors').addEventListener('click',openTrafficDashboard);
$('siteStatsRefresh').addEventListener('click',loadTrafficReport);
document.querySelectorAll('[data-site-period]').forEach(button=>button.addEventListener('click',()=>{
 trafficPeriod=Number(button.dataset.sitePeriod);
 document.querySelectorAll('[data-site-period]').forEach(b=>{const active=b===button;b.classList.toggle('is-active',active);b.setAttribute('aria-pressed',String(active))});
 loadTrafficReport();
}));
$('analyticsRefresh').addEventListener('click',fetchArtworkStats);
document.querySelectorAll('[data-stat-period]').forEach(button=>button.addEventListener('click',()=>{
 statsPeriod=button.dataset.statPeriod;
 document.querySelectorAll('[data-stat-period]').forEach(b=>{const active=b===button;b.classList.toggle('is-active',active);b.setAttribute('aria-pressed',String(active));});
 if(statsLoaded)renderStatsBoard();
}));
$('newArtwork').addEventListener('click',newWork);
$('cancelEditor').addEventListener('click',()=>screen('catalog'));
$('discardArtwork').addEventListener('click',()=>screen('catalog'));
$('saveArtwork').addEventListener('click',saveDraft);
$('mainPhoto').addEventListener('change',e=>{if(!e.target.files.length||!current)return;const p=pending.get(current)||{extras:[]};p.main=e.target.files[0];pending.set(current,p);showPreview()});
$('detailPhotos').addEventListener('change',e=>{if(!e.target.files.length||!current)return;const p=pending.get(current)||{extras:[]};p.extras=(p.extras||[]).concat([...e.target.files]);pending.set(current,p);showPreview()});
$('interiorPhotos').addEventListener('change',e=>{if(!e.target.files.length||!current)return;const p=pending.get(current)||{};p.interiors=(p.interiors||[]).concat([...e.target.files]);pending.set(current,p);showPreview()});
$('videoFile').addEventListener('change',e=>{
 if(!current||!e.target.files.length)return;
 const file=e.target.files[0];
 if(!/\.(mp4|webm)$/i.test(file.name)){toast('Выберите видео MP4 или WebM');e.target.value='';return}
 if(file.size>VIDEO_MAX_BYTES){toast('Видео больше 25 МБ. Сожмите его и загрузите снова.');e.target.value='';return}
 const p=pending.get(current)||{};p.video=file;pending.set(current,p);
 $('removeVideoInput').checked=false;showPreview();
});
$('removeVideoInput').addEventListener('change',e=>{if(e.target.checked){const p=pending.get(current);if(p&&p.video){delete p.video;$('videoFile').value=''} }showPreview()});
$('publishBtn').addEventListener('click',publish);
$('exportBtn').addEventListener('click',exportZip);
window.addEventListener('beforeunload',e=>{if(dirty&&!busy){e.preventDefault();e.returnValue=''}});
displayLoginView();
})();