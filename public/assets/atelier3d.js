/* Approved static exhibition; source image is the approved concept art crop, hotspots open genuine artworks. */
(()=>{const rail=document.querySelector('#artRail'),stage=document.querySelector('#artStage');if(!rail||!stage||typeof works==='undefined')return;
 const ids=['abstract','light','gold','wings','wings','horse','abstract','feather'];
 rail.innerHTML=ids.map((id,i)=>`<button class="canvas-card" style="--ry:0deg" type="button" data-work-id="${id}" aria-label="Открыть работу ${works.find(w=>w.id===id)?.title||'из галереи'}"><span class="canvas-face"></span></button>`).join('');
 stage.addEventListener('click',e=>{const c=e.target.closest('[data-work-id]');if(c&&typeof openArtwork==='function')openArtwork(c.dataset.workId)});
 document.querySelector('#galleryLaunch')?.addEventListener('click',()=>{document.querySelector('#catalog')?.classList.add('is-open');document.querySelector('#catalog')?.scrollIntoView({behavior:'smooth'})});
 document.querySelectorAll('a[href="#catalog"]').forEach(a=>a.addEventListener('click',()=>document.querySelector('#catalog')?.classList.add('is-open')));
})();