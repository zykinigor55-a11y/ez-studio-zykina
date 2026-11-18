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
 try{
   fetch(ENDPOINT,{
     method:'POST',mode:'cors',credentials:'omit',keepalive:true,
     headers:{'content-type':'application/json'},
     body:JSON.stringify({artwork,session})
   }).catch(()=>{});
 }catch(_){}
}
window.ZykinaArtworkStats=Object.freeze({track});
const direct=document.currentScript?.dataset?.artwork;
if(direct){
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',()=>track(direct),{once:true});
  else track(direct);
}
})();