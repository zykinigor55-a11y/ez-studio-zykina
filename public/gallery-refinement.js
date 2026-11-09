/* E·Z STUDIO — restrained 3D-gallery motion + compact portfolio expansion */
(() => {
  'use strict';
  const byId = id => document.getElementById(id);
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
  const initialLimit = () => window.innerWidth <= 700 ? 4 : window.innerWidth <= 1150 ? 6 : 8;
  let activeFilter = 'all';
  let visibleLimit = initialLimit();
  let wasExpanded = false;
  let refreshPortfolio = () => {};

  // Extend the existing filter, rather than replacing its lightbox/category logic.
  if (typeof selectFilter === 'function') {
    const originalSelectFilter = selectFilter;
    selectFilter = function (filter) {
      originalSelectFilter(filter);
      activeFilter = filter;
      wasExpanded = false;
      visibleLimit = initialLimit();
      refreshPortfolio();
    };
  }

  window.addEventListener('DOMContentLoaded', () => {
    const grid = byId('artGrid');
    if (grid) {
      const cards = [...grid.querySelectorAll('.art-card')];
      cards.forEach((card, i) => card.style.setProperty('--portfolio-delay', `${(i % 4) * 64}ms`));

      const wrap = document.createElement('div');
      wrap.className = 'portfolio-more';
      wrap.id = 'portfolioMoreWrap';
      wrap.innerHTML = `<button class="portfolio-more-button" id="portfolioMore" type="button" aria-controls="artGrid" aria-label="Показать следующие произведения"><span>Показать ещё</span><span class="portfolio-more-remaining" id="portfolioRemaining"></span><svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M12 4v16m-6-6 6 6 6-6" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/></svg></button>`;
      grid.insertAdjacentElement('afterend', wrap);
      const more = byId('portfolioMore');
      const remainingText = byId('portfolioRemaining');
      refreshPortfolio = () => {
        let count = 0;
        cards.forEach(card => {
          const matches = activeFilter === 'all' || card.dataset.category === activeFilter;
          if (!matches) { card.hidden = true; return; }
          card.hidden = count++ >= visibleLimit;
        });
        const remaining = Math.max(0, count - visibleLimit);
        wrap.hidden = remaining === 0;
        remainingText.textContent = remaining ? `+${remaining}` : '';
        more.setAttribute('aria-label', `Показать ещё произведения, осталось ${remaining}`);
      };
      more.addEventListener('click', () => {
        wasExpanded = true;
        visibleLimit += initialLimit();
        refreshPortfolio();
      });
      window.addEventListener('resize', () => {
        if (!wasExpanded) visibleLimit = initialLimit();
        refreshPortfolio();
      }, { passive: true });
      refreshPortfolio();
    }

    const viewport = byId('stageViewport');
    if (!viewport) return;
    const cards = [...viewport.querySelectorAll('.stage-canvas')];
    if (!cards.length) return;
    let scheduled = false;
    const updateDepth = () => {
      scheduled = false;
      const box = viewport.getBoundingClientRect();
      if (!box.width) return;
      const center = box.left + box.width / 2;
      const half = Math.max(1, box.width / 2);
      cards.forEach(card => {
        if (reduced.matches) {
          card.style.removeProperty('--stage-rotation');
          card.style.removeProperty('--stage-rise');
          card.style.removeProperty('--stage-size');
          card.style.removeProperty('--stage-visibility');
          return;
        }
        // Derive the untransformed center from layout offsets rather than the animated bounding rect.
        const cardCenter = box.left + card.offsetLeft - viewport.scrollLeft + card.offsetWidth / 2;
        const relative = Math.max(-1, Math.min(1, (cardCenter - center) / half));
        const edge = Math.abs(relative);
        card.style.setProperty('--stage-rotation', `${(relative * -10).toFixed(2)}deg`);
        card.style.setProperty('--stage-rise', `${(edge * 11).toFixed(1)}px`);
        card.style.setProperty('--stage-size', (1 - edge * .055).toFixed(3));
        card.style.setProperty('--stage-visibility', (1 - edge * .25).toFixed(3));
      });
    };
    const queue = () => {
      if (!scheduled) {
        scheduled = true;
        requestAnimationFrame(updateDepth);
      }
    };
    viewport.addEventListener('scroll', queue, { passive: true });
    window.addEventListener('resize', queue, { passive: true });
    reduced.addEventListener?.('change', queue);
    queue();
  });
})();
