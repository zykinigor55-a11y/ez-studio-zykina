/* Mobile cinematic hero playback recovery for Android/Yandex/Chrome.
   Only the mobile video is handled; desktop video remains untouched. */
(() => {
  'use strict';
  const video=document.querySelector('.hero-video--mobile');
  const button=document.getElementById('ezHeroPlay');
  if(!video || !button)return;
  let alternative=false, pending=false, lastUserGesture=0;
  const isMobile=()=>window.matchMedia('(max-width:700px)').matches;
  const show=()=>{if(isMobile())button.hidden=false};
  const hide=()=>{button.hidden=true};
  video.muted=true;
  video.defaultMuted=true;
  video.loop=true;
  video.autoplay=true;
  video.playsInline=true;
  video.setAttribute('playsinline','');
  video.setAttribute('webkit-playsinline','');

  function switchToFallback(){
    if(alternative)return false;
    alternative=true;
    // A second existing H.264 file from the same studio repository.
    video.src='assets/hero-mobile.mp4';
    video.load();
    return true;
  }
  async function attempt(){
    if(!isMobile() || document.hidden || pending)return;
    pending=true;
    try{
      video.muted=true;
      if(video.error && switchToFallback())video.load();
      const result=video.play();
      if(result && typeof result.then==='function')await result;
      hide();
    }catch(err){
      if(video.error && switchToFallback()){
        pending=false;
        return attempt();
      }
      show(); // Some Android in-app browsers require one tap.
    }finally{pending=false;}
  }
  video.addEventListener('error',()=>{
    if(switchToFallback())attempt();else show();
  });
  video.addEventListener('playing',hide);
  video.addEventListener('stalled',()=>{
    if(video.readyState<2 && video.networkState===3 && switchToFallback())attempt();
  });
  video.addEventListener('loadeddata',attempt);
  video.addEventListener('pause',()=>{
    if(isMobile() && !document.hidden)button.hidden=false;
  });
  button.addEventListener('click',()=>{
    lastUserGesture=Date.now();
    attempt();
  });
  // A page opened from Yandex/Telegram/VK may postpone autoplay until interaction.
  document.addEventListener('pointerdown',e=>{
    if(e.target===button || !isMobile() || !video.paused)return;
    lastUserGesture=Date.now();attempt();
  },{passive:true});
  document.addEventListener('visibilitychange',()=>{
    if(!document.hidden)attempt();
  });
  window.addEventListener('pageshow',attempt);
  window.addEventListener('focus',attempt);
  window.addEventListener('resize',attempt,{passive:true});
  if(document.readyState==='loading')
    document.addEventListener('DOMContentLoaded',attempt,{once:true});
  else attempt();
})();