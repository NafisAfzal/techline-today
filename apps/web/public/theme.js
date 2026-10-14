try {
  var preferences = JSON.parse(localStorage.getItem('ti:v1:preferences') || '{}');
  var choice = preferences.theme || 'system';
  document.documentElement.dataset.theme = choice === 'system' ? (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light') : choice;
  document.documentElement.dataset.density = preferences.density || 'comfortable';
} catch (_) {}
document.querySelectorAll('meta[name="theme-color"]').forEach(function (meta) {
  if (document.documentElement.dataset.theme) {
    meta.removeAttribute('media');
    meta.content = document.documentElement.dataset.theme === 'dark' ? '#101c2d' : '#f4f2eb';
  }
});
