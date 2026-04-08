(function () {
  const THEME_KEY = 'attendance-theme';

  function getPreferredTheme() {
    const stored = window.localStorage.getItem(THEME_KEY);
    if (stored === 'light' || stored === 'dark') {
      return stored;
    }
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }

  function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
  }

  function updateToggleState(button, theme) {
    const isDark = theme === 'dark';
    button.setAttribute('aria-pressed', String(isDark));
    button.textContent = isDark ? 'Light mode' : 'Dark mode';
  }

  function toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme') || getPreferredTheme();
    const next = current === 'dark' ? 'light' : 'dark';
    applyTheme(next);
    window.localStorage.setItem(THEME_KEY, next);
    document.querySelectorAll('[data-theme-toggle]').forEach((button) => {
      updateToggleState(button, next);
    });
  }

  function initThemeToggle() {
    const theme = document.documentElement.getAttribute('data-theme') || getPreferredTheme();
    applyTheme(theme);
    document.querySelectorAll('[data-theme-toggle]').forEach((button) => {
      updateToggleState(button, theme);
      button.addEventListener('click', toggleTheme);
    });
  }

  applyTheme(getPreferredTheme());

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initThemeToggle);
  } else {
    initThemeToggle();
  }
})();

