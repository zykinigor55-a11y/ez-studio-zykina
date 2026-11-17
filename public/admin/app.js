'use strict';
/* ZYKINA ART editor — no backend, no stored token. All repo changes require a user token. */
(function(){
const OWNER='zykinigor55-a11y', REPO='ez-studio-zykina', BRANCH='main';
const ROOT='https://api.github.com/repos/'+OWNER+'/'+REPO;
const ASSETS='https://zykina-art.ru/assets/';
const CATS={plastic:'Пластика',abstract:'Абстракция',images:'Образы',stories:'Истории'};
let token='', works=[], originals={}, pending=new Map(), touched=new Set(), dirty=false, current=null, draft=null, preview=false, busy=false;
const $=id=>document.getElementById(id);
const esc=s=>String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const numberOf=w=>Number(String(w.id||'').replace(/^art-/,''))||0;
const fileURL=p=>ASSETS+(p||'');
const shortText=s=>String(s||'').trim();
function toast(s){$('toast').textContent=s;$('toast').classList.remove('hide');clearTimeout(toast.timer);toast.timer=setTimeout(()=>$('toast').classList.add('hide'),5500)}
function screen(name){for(const id of ['catalogView','editorView','connectView'])$(id).classList.toggle('hide',id!==name+'View');$('navList').classList.toggle('active',name==='catalog');$('navCreate').classList.toggle('active',name==='editor');$('navConnect').classList.toggle('active',name==='connect')}
function busyState(b){busy=b;$('publishBtn').disabled=b||!token;$('exportBtn').disabled=b;$('saveArtwork').disabled=b;$('loginBtn').disabled=b;$('connectBtn').disabled=b;}
function markDirty(){dirty=true;$('saveBar').classList.remove('hide');$('pendingText').textContent='Есть несохранённые изменения · '+works.length+' работ';$('publishBtn').disabled=!token;renderStats()}
function resetDirty(){dirty=false;$('saveBar').classList.add('hide');pending.clear();touched.clear()}
function renderStats(){$('countAll').textContent=works.length;$('countShown').textContent=works.filter(w=>w.visible!==false).length;$('countHidden').textContent=works.filter(w=>w.visible===false).length}
function renderList(){
  renderStats();
  $('workList').innerHTML=works.length?'':'<div class="empty">Картины не найдены</div>';
  for(let i=0;i<works.length;i++){
    const w=works[i],row=document.createElement('div');row.className='work'+(w.visible===false?' dim':'');
    const img=document.createElement('img');img.src=fileURL(w.thumb||w.img);img.alt='';img.loading='lazy';
    const meta=document.createElement('div');meta.innerHTML='<h4>'+esc(w.title||'Без названия')+'</h4><small>'+esc(CATS[w.cat]||'Категория')+' · '+esc(w.id||'')+'</small>'+(w.visible===false?'<span class="tag">Скрыта из каталога</span>':'');
    const actions=document.createElement('div');actions.className='actions';
    const controls=[['↑','Поднять',()=>move(i,-1)],['↓','Опустить',()=>move(i,1)],['✎','Редактировать',()=>edit(w.id)],[(w.visible===false?'◉':'◌'),(w.visible===false?'Показать':'Скрыть из каталога'),()=>toggle(w.id)]];
    for(const [symbol,label,fn] of controls){const b=document.createElement('button');b.className='action';b.textContent=symbol;b.title=label;b.setAttribute('aria-label',label);b.addEventListener('click',fn);actions.append(b)}
    row.append(img,meta,actions);$('workList').append(row);
  }
}
function move(i,d){const j=i+d;if(j<0||j>=works.length)return;[works[i],works[j]]=[works[j],works[i]];markDirty();renderList()}
function toggle(id){const w=works.find(w=>w.id===id);if(!w)return;w.visible=w.visible===false?true:false;markDirty();renderList()}
function newWork(){let n=Math.max(18,...works.map(numberOf))+1;current='art-'+n;draft={id:current,title:'',cat:'plastic',visible:true,description:'',size:'От 40 × 60 до 120 × 100 см, на заказ',photos:[],img:'',thumb:'',page:'kartiny/work-'+n+'/'};paintDraft(true)}
function edit(id){const w=works.find(w=>w.id===id);if(!w)return;current=id;draft=Object.assign({},w,{photos:[...(w.photos||[])]});paintDraft(false)}
function paintDraft(fresh){
  $('editorHeading').textContent=fresh?'Новая картина':'Редактирование · '+(draft.title||draft.id);
  $('titleInput').value=draft.title||'';$('catInput').value=draft.cat||'plastic';$('descInput').value=draft.description||'';$('sizeInput').value=draft.size||'От 40 × 60 до 120 × 100 см, на заказ';$('visibleInput').checked=draft.visible!==false;
  $('mainPhoto').value='';$('detailPhotos').value='';showPreview();screen('editor');window.scrollTo({top:0,behavior:'smooth'});
}
function showPreview(){
  const p=pending.get(current)||{},src=p.main?URL.createObjectURL(p.main):draft.thumb?fileURL(draft.thumb):'';
  const img=$('mainPreview');if(src){img.src=src;img.classList.remove('hide');$('uploadCaption').classList.add('hide')}else{img.removeAttribute('src');img.classList.add('hide');$('uploadCaption').classList.remove('hide')}
  $('detailPreviews').innerHTML='';
  const entries=(draft.photos||[]).slice(1).map(p=>({url:fileURL(p)})).concat((p.extras||[]).map(file=>({url:URL.createObjectURL(file)})));
  for(const entry of entries){const image=document.createElement('img');image.src=entry.url;image.alt='Фрагмент картины';$('detailPreviews').append(image)}
}
function saveDraft(){
  if(!draft)return;
  draft.title=shortText($('titleInput').value);
  draft.cat=$('catInput').value;draft.description=shortText($('descInput').value);
  draft.size=shortText($('sizeInput').value);draft.visible=$('visibleInput').checked;
  const files=pending.get(current)||{};
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
  const ps=['public/assets/catalog/manifest.json','public/index.html','public/kartiny/index.html','public/sitemap.xml'];
  const out=await Promise.all(ps.map(p=>loadText(p).catch(e=>{if(p==='public/sitemap.xml')return '';throw e})));
  originals={manifest:out[0],index:out[1],catalog:out[2],sitemap:out[3]};works=JSON.parse(out[0]).map(w=>Object.assign({visible:true,description:'',size:''},w));resetDirty();renderList();screen('catalog');
  $('loginMask').classList.add('hide');$('connStatus').textContent=token?'GitHub · подключено':'Предпросмотр / без доступа на запись';$('publishBtn').disabled=!token;
  toast('Каталог загружен: '+works.length+' картин');
 }catch(e){toast(e.message);$('connStatus').textContent='Не удалось загрузить каталог';if(!token)$('loginMask').classList.remove('hide')}finally{busyState(false)}
}
function login(value){token=String(value||'').trim();if(!token){toast('Введите GitHub-токен');return}preview=false;$('loginToken').value='';$('connectToken').value='';load()}
function showConnect(){screen('connect');$('loginMask').classList.add('hide')}
function visibleWorks(){return works.filter(w=>w.visible!==false)}
function cleanWorks(){return works.map(w=>{const c={};for(const key of ['id','title','cat','img','thumb','photos','page','description','size','visible'])if(w[key]!==undefined)c[key]=w[key];return c})}
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
function pageHTML(w){
 const cat=CATS[w.cat]||'Авторская картина',title=esc(w.title),desc=esc(w.description||('«'+w.title+'» — авторская работа Екатерины Зыкиной. Фотографии и детали.')),url='https://zykina-art.ru/'+w.page;
 const photos=(w.photos&&w.photos.length?w.photos:[w.img]).map(p=>'/assets/'+esc(p));
 const cover=photos[0]||'';
 const ld={'@context':'https://schema.org','@type':'VisualArtwork',name:w.title,image:(w.photos||[w.img]).map(p=>'https://zykina-art.ru/assets/'+p),url,description:w.description||'Авторская работа Екатерины Зыкиной',creator:{'@type':'Person',name:'Екатерина Зыкина'}};
 const thumbs=photos.slice(1).map((src,i)=>'<a href="'+src+'" target="_blank" rel="noopener"><img src="'+src+'" alt="'+title+' — деталь '+(i+1)+'" loading="lazy"></a>').join('');
 return '<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="index,follow">'+
 '<title>'+title+' — '+esc(cat)+' | ZYKINA ART</title><meta name="description" content="'+desc+'"><link rel="canonical" href="'+esc(url)+'"><meta property="og:title" content="'+title+' — ZYKINA ART"><meta property="og:description" content="'+desc+'"><meta property="og:type" content="article"><meta property="og:image" content="https://zykina-art.ru'+cover+'"><script type="application/ld+json">'+JSON.stringify(ld).replace(/</g,'\\u003c')+'</script>'+
 '<style>body{margin:0;background:#f4f0e9;color:#44352b;font:16px/1.75 Arial,sans-serif}main{max-width:1000px;margin:30px auto;padding:0 24px}a{color:inherit}header{display:flex;flex-wrap:wrap;gap:24px;font-size:13px;color:#806c5a}h1{font:400 clamp(44px,7vw,76px)/1.1 Georgia,serif;margin:30px 0}figure{margin:0}figure img{max-width:100%;max-height:86vh;object-fit:contain;margin:auto;display:block}.type{color:#897666;font-size:12px;letter-spacing:.15em;text-transform:uppercase;margin-top:55px}.details{display:flex;gap:18px;flex-wrap:wrap;margin:38px 0}.details img{width:180px;height:180px;object-fit:contain;border:1px solid #ddd1c1}.contact{display:inline-block;padding:14px 19px;border:1px solid #655241;text-decoration:none;margin:25px 0 65px}.size{color:#796c60}</style></head><body><main><header><a href="/">ZYKINA ART</a><a href="/kartiny/">Все работы</a></header><p class="type">'+esc(cat)+'</p><h1>'+title+'</h1><figure><img src="'+cover+'" alt="'+title+' — общий вид"></figure><p>'+desc+'</p><div class="details">'+thumbs+'</div><p class="size"><strong>Размер:</strong> '+esc(w.size||'От 40 × 60 до 120 × 100 см, на заказ')+'</p><a class="contact" href="/#order">Обсудить заказ</a></main></body></html>';
}
function buildSitemap(ws){
 let xml=originals.sitemap||'';
 if(!xml||!xml.includes('</urlset>'))return null;
 for(const w of ws){const url='https://zykina-art.ru/'+w.page;if(!xml.includes('<loc>'+url+'</loc>'))xml=xml.replace('</urlset>','<url><loc>'+url+'</loc></url></urlset>')}
 return xml;
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
 const staged=works.map(w=>Object.assign({},w,{photos:[...(w.photos||[])]}));const files=new Map();
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
     published:w.visible!==false
   };
   files.set('public/assets/картины/'+n+'/работа.json',utf8(JSON.stringify(metadata,null,2)+'\\n'));
 }
 files.set('public/assets/catalog/manifest.json',utf8(JSON.stringify(serialized,null,2)+'\n'));
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
  works=built.staged;originals.manifest=new TextDecoder().decode(built.files.get('public/assets/catalog/manifest.json'));originals.index=new TextDecoder().decode(built.files.get('public/index.html'));originals.catalog=new TextDecoder().decode(built.files.get('public/kartiny/index.html'));if(built.files.has('public/sitemap.xml'))originals.sitemap=new TextDecoder().decode(built.files.get('public/sitemap.xml'));
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
$('loginBtn').addEventListener('click',()=>login($('loginToken').value));
$('loginToken').addEventListener('keydown',e=>{if(e.key==='Enter')login($('loginToken').value)});
$('previewBtn').addEventListener('click',()=>{token='';preview=true;load()});
$('connectBtn').addEventListener('click',()=>login($('connectToken').value));
$('disconnectBtn').addEventListener('click',()=>{token='';$('connStatus').textContent='GitHub отключён';$('publishBtn').disabled=true;toast('Токен удалён из памяти вкладки')});
$('navList').addEventListener('click',()=>screen('catalog'));
$('navCreate').addEventListener('click',newWork);
$('navConnect').addEventListener('click',showConnect);
$('newArtwork').addEventListener('click',newWork);
$('cancelEditor').addEventListener('click',()=>screen('catalog'));
$('discardArtwork').addEventListener('click',()=>screen('catalog'));
$('saveArtwork').addEventListener('click',saveDraft);
$('mainPhoto').addEventListener('change',e=>{if(!e.target.files.length||!current)return;const p=pending.get(current)||{extras:[]};p.main=e.target.files[0];pending.set(current,p);showPreview()});
$('detailPhotos').addEventListener('change',e=>{if(!e.target.files.length||!current)return;const p=pending.get(current)||{extras:[]};p.extras=(p.extras||[]).concat([...e.target.files]);pending.set(current,p);showPreview()});
$('publishBtn').addEventListener('click',publish);
$('exportBtn').addEventListener('click',exportZip);
window.addEventListener('beforeunload',e=>{if(dirty&&!busy){e.preventDefault();e.returnValue=''}});
})();