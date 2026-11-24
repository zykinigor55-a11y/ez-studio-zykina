/* Yandex.Metrika — public production pages only. */
(function(){
    if (!/^(www\.)?zykina-art\.ru$/i.test(location.hostname) || /^\/admin(?:\/|$)/i.test(location.pathname)) return;
    document.querySelectorAll('input:not([type="range"]),textarea,[contenteditable="true"]').forEach(el=>el.classList.add('ym-disable-keys'));
    (function(m,e,t,r,i,k,a){
        m[i]=m[i]||function(){(m[i].a=m[i].a||[]).push(arguments)};
        m[i].l=1*new Date();
        for (var j = 0; j < document.scripts.length; j++) {if (document.scripts[j].src === r) { return; }}
        k=e.createElement(t),a=e.getElementsByTagName(t)[0],k.async=1,k.src=r,a.parentNode.insertBefore(k,a)
    })(window, document,'script','https://mc.yandex.ru/metrika/tag.js?id=114650410', 'ym');

    ym(114650410, 'init', {ssr:true, webvisor:true, clickmap:true, ecommerce:"dataLayer", referrer: document.referrer, url: location.href, accurateTrackBounce:true, trackLinks:true});
})();

/* ZYKINA ART anonymous artwork open tracking. No cookies, IP addresses or names collected. */
(function(){
'use strict';
const ENDPOINT='https://lxwqpoakdsbpshfyfqih.supabase.co/functions/v1/zykina-art-analytics';
const SESSION_KEY='zykina-art-view-session';
let session='';
try{
 session=sessionStorage.getItem(SESSION_KEY)||'';
 if(!/^[a-f0-9-]{32,40}$/i.test(session)){
   session=crypto.randomUUID?crypto.randomUUID():Array.from(crypto.getRandomValues(new Uint8Array(16)),x=>x.toString(16).padStart(2,'0')).join('');
   sessionStorage.setItem(SESSION_KEY,session);
 }
}catch(_){
 try{session=crypto.randomUUID?crypto.randomUUID():Array.from(crypto.getRandomValues(new Uint8Array(16)),x=>x.toString(16).padStart(2,'0')).join('')}catch(_){return}
}
function track(artwork){
 if(!/^art-[0-9]{1,4}$/.test(String(artwork||'')))return;
 siteEvent('art_open');
 try{
   fetch(ENDPOINT,{
     method:'POST',mode:'cors',credentials:'omit',keepalive:true,
     headers:{'content-type':'application/json'},
     body:JSON.stringify({artwork,session})
   }).catch(()=>{});
 }catch(_){}
}

/* Site-wide counters; browser-session pseudonym, no cookie or raw IP stored. */
const PATH=(location.pathname.replace(/\/+/g,'/').toLowerCase()||'/');
const PAGE=PATH.replace(/\/index\.html$/,'/').slice(0,138);
const SITE_KEY='zykina-art-traffic-source';
let originalSource='direct';
try{
 const savedSource=sessionStorage.getItem(SITE_KEY);
 if(savedSource&&/^(direct|search|social|referral)$/.test(savedSource))originalSource=savedSource;
 else{
   const query=new URLSearchParams(location.search);
   const campaign=String(query.get('utm_source')||'').toLowerCase();
   const ref=document.referrer?new URL(document.referrer).hostname.toLowerCase():'';
   const own=ref===location.hostname.toLowerCase()||ref==='zykina-art.ru'||ref==='www.zykina-art.ru'||ref==='ez-studio-zykina.onrender.com';
   const hostname=own?'':ref;
   if(/(yandex|google|bing|duckduckgo|mail\.ru|search)/.test(campaign+' '+hostname))originalSource='search';
   else if(/(vk|vkontakte|instagram|facebook|tiktok|youtube|telegram|pinterest|ok\.ru|social)/.test(campaign+' '+hostname))originalSource='social';
   else if(hostname)originalSource='referral';
   else originalSource='direct';
   sessionStorage.setItem(SITE_KEY,originalSource);
 }
}catch(_){}
const ua=navigator.userAgent||'';
const DEVICE=/ipad|tablet|playbook|silk/i.test(ua)?'tablet':
 /mobile|iphone|android/i.test(ua)?'mobile':'desktop';
function metrikaGoal(goal){
 if(!/^(www\.)?zykina-art\.ru$/i.test(location.hostname)||/^\/admin(?:\/|$)/i.test(PAGE))return;
 try{if(typeof window.ym==='function')window.ym(114650410,'reachGoal',goal);}catch(_){}
}
function siteEvent(event){
 if(!/^(page|art_open|interior|macro|order|contact|gallery)$/.test(String(event))||!/^\/[a-z0-9./-]{0,138}$/.test(PAGE)||/^\/admin(?:\/|$)/.test(PAGE))return;
 const goals={art_open:'art_open',interior:'interior_view',macro:'macro_view',order:'order_interest',contact:'contact_click'};
 if(goals[event])metrikaGoal(goals[event]);
 try{
   fetch(ENDPOINT,{
     method:'POST',mode:'cors',credentials:'omit',keepalive:true,
     headers:{'content-type':'application/json'},
     body:JSON.stringify({kind:'site',event,page:PAGE,session,device:DEVICE,source:originalSource})
   }).catch(()=>{});
 }catch(_){}
}
window.ZykinaSiteStats=Object.freeze({event:siteEvent});
function trackSiteClick(e){
 const target=e.target instanceof Element?e.target:null;
 if(!target)return;
 const gallery=target.closest('[data-work]');
 const tab=target.closest('[data-gallery-tab="interior"]');
 const thumbnail=target.closest('[data-photo]');
 const anchor=target.closest('a[href]');
 if(gallery){siteEvent('gallery');return;}
 if(tab){siteEvent('interior');return;}
 if(thumbnail){
   const isPhoto=document.querySelector('[data-gallery-tab="photos"][aria-pressed="true"]');
   const photoIndex=Number(thumbnail.dataset.photo);
   if(isPhoto&&photoIndex>0)siteEvent('macro');
   return;
 }
 if(anchor){
  const href=String(anchor.getAttribute('href')||'');
  if(href==='#order'||href.endsWith('/#order')||href.includes('order?'))siteEvent('order');
  else if(href==='#contact'||href.endsWith('/#contact'))metrikaGoal('contact_section');
  else if(/(?:vk\.ru|vkontakte|max\.ru|mailto:|tel:)/i.test(href)){
   siteEvent('contact');
   if(/(?:vk\.ru|vkontakte)/i.test(href))metrikaGoal('contact_vk');
   else if(/max\.ru/i.test(href))metrikaGoal('contact_max');
  }
  else if(anchor.closest('.details')&&/\.(?:png|jpe?g|webp)(?:$|[?#])/i.test(href))siteEvent('macro');
 }
}
document.addEventListener('click',trackSiteClick,{capture:true,passive:true});
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',()=>siteEvent('page'),{once:true});
else siteEvent('page');

window.ZykinaArtworkStats=Object.freeze({track});
const direct=document.currentScript?.dataset?.artwork;
if(direct){
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',()=>track(direct),{once:true});
  else track(direct);
}
})();

