// Tab switching
document.addEventListener('DOMContentLoaded', function() {
  const tabBtns = document.querySelectorAll('.tab-btn');
  const tabContents = document.querySelectorAll('.tab-content');

  tabBtns.forEach(btn => {
    btn.addEventListener('click', function() {
      const target = this.dataset.tab;
      tabBtns.forEach(b => b.classList.remove('active'));
      tabContents.forEach(c => c.classList.remove('active'));
      this.classList.add('active');
      document.getElementById('tab-' + target)?.classList.add('active');
    });
  });

  // Career card expand/collapse
  document.querySelectorAll('.career-card-header').forEach(header => {
    header.addEventListener('click', function() {
      const detail = this.nextElementSibling;
      if (detail) detail.classList.toggle('open');
    });
  });

  // Copy share URL
  const copyBtn = document.getElementById('copy-url-btn');
  if (copyBtn) {
    copyBtn.addEventListener('click', function() {
      const input = document.getElementById('share-url-input');
      if (input) {
        navigator.clipboard.writeText(input.value).then(() => {
          copyBtn.textContent = '복사됨!';
          setTimeout(() => copyBtn.textContent = '복사', 2000);
        });
      }
    });
  }

  // Category filter on result page
  const catFilter = document.getElementById('category-filter-select');
  if (catFilter) {
    catFilter.addEventListener('change', function() {
      const selected = this.value;
      document.querySelectorAll('.career-card[data-category]').forEach(card => {
        if (selected === 'all' || card.dataset.category === selected) {
          card.style.display = 'block';
        } else {
          card.style.display = 'none';
        }
      });
    });
  }
});
