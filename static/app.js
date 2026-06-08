function trackEvent(name, params = {}) {
  if (typeof window.gtag === 'function') {
    window.gtag('event', name, params);
  }
}

document.addEventListener('DOMContentLoaded', function() {
  const pageMeta = window.CAREERSDNA_PAGE || {};
  trackEvent('page_view_custom', {
    page_path: window.location.pathname,
    page_type: pageMeta.type || 'standard'
  });
  if (pageMeta.type) {
    trackEvent('view_' + pageMeta.type, pageMeta);
  }

  const scrollMarks = [25, 50, 75, 90];
  const seenScrollMarks = new Set();
  function trackScrollDepth() {
    const doc = document.documentElement;
    const scrollable = Math.max(1, doc.scrollHeight - window.innerHeight);
    const depth = Math.round((window.scrollY / scrollable) * 100);
    scrollMarks.forEach(mark => {
      if (depth >= mark && !seenScrollMarks.has(mark)) {
        seenScrollMarks.add(mark);
        trackEvent('scroll_depth', {
          page_path: window.location.pathname,
          page_type: pageMeta.type || 'standard',
          percent: mark
        });
      }
    });
  }
  window.addEventListener('scroll', trackScrollDepth, { passive: true });

  [15, 45, 90].forEach(seconds => {
    window.setTimeout(() => {
      trackEvent('engaged_time', {
        page_path: window.location.pathname,
        page_type: pageMeta.type || 'standard',
        seconds: seconds
      });
    }, seconds * 1000);
  });

  const tabBtns = document.querySelectorAll('.tab-btn');
  const tabContents = document.querySelectorAll('.tab-content');

  tabBtns.forEach(btn => {
    btn.addEventListener('click', function() {
      const target = this.dataset.tab;
      tabBtns.forEach(b => b.classList.remove('active'));
      tabContents.forEach(c => c.classList.remove('active'));
      this.classList.add('active');
      document.getElementById('tab-' + target)?.classList.add('active');
      trackEvent('result_tab_open', { tab_name: target || 'unknown' });
    });
  });

  document.querySelectorAll('.career-card-header').forEach(header => {
    header.addEventListener('click', function() {
      const detail = this.nextElementSibling;
      if (detail) detail.classList.toggle('open');
      trackEvent('result_career_expand');
    });
  });

  const copyBtn = document.getElementById('copy-url-btn');
  if (copyBtn) {
    copyBtn.textContent = 'Copy';
    copyBtn.addEventListener('click', function() {
      const input = document.getElementById('share-url-input');
      if (input) {
        navigator.clipboard.writeText(input.value).then(() => {
          copyBtn.textContent = 'Copied';
          trackEvent('copy_share_url');
          setTimeout(() => copyBtn.textContent = 'Copy', 2000);
        });
      }
    });
  }

  const nativeShareBtn = document.getElementById('native-share-btn');
  if (nativeShareBtn) {
    if (!navigator.share) {
      nativeShareBtn.style.display = 'none';
    } else {
      nativeShareBtn.addEventListener('click', function() {
        const input = document.getElementById('share-url-input');
        navigator.share({
          title: document.title,
          text: 'My career assessment result',
          url: input ? input.value : window.location.href
        }).then(() => trackEvent('native_share')).catch(() => {});
      });
    }
  }

  const catFilter = document.getElementById('category-filter-select');
  if (catFilter) {
    catFilter.addEventListener('change', function() {
      const selected = this.value;
      document.querySelectorAll('.career-card[data-category]').forEach(card => {
        card.style.display = (selected === 'all' || card.dataset.category === selected) ? 'block' : 'none';
      });
      trackEvent('result_category_filter', { category: selected });
    });
  }

  document.querySelectorAll('[data-track]').forEach(el => {
    el.addEventListener('click', function() {
      trackEvent(this.dataset.track, {
        target_path: this.getAttribute('href') || window.location.pathname
      });
    });
  });

  document.querySelectorAll('a[href="/info"]').forEach(el => {
    el.addEventListener('click', () => trackEvent('start_assessment'));
  });
});
