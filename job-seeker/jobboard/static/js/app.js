(() => {
  const key = 'jb-theme';
  const html = document.documentElement;
  const btn = document.getElementById('themeToggle');
  const saved = localStorage.getItem(key);
  if (saved) html.setAttribute('data-bs-theme', saved);
  if (btn) {
    btn.addEventListener('click', () => {
      const next = html.getAttribute('data-bs-theme') === 'dark' ? 'light' : 'dark';
      html.setAttribute('data-bs-theme', next);
      localStorage.setItem(key, next);
    });
  }
})();
