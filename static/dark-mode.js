// ============================================
// GLOBAL DARK MODE SCRIPT
// ============================================

(function () {
  'use strict';

  // Initialize dark mode from localStorage on page load (immediately to avoid flicker)
  const savedTheme = localStorage.getItem('theme') || 'light';
  document.documentElement.setAttribute('data-theme', savedTheme);

  // Sync function to update all toggles on the page
  function updateAllToggles(theme) {
    const allToggles = document.querySelectorAll('#darkModeToggle, #darkModeToggleMobile, .dark-mode-toggle');

    allToggles.forEach(toggle => {
      const sunIcon = toggle.querySelector('.fa-sun, [data-feather="sun"], #sunIcon, #sunIconMobile');
      const moonIcon = toggle.querySelector('.fa-moon, [data-feather="moon"], #moonIcon, #moonIconMobile');
      const textSpan = toggle.querySelector('span'); // For mobile text like "Dark Mode"

      if (theme === 'dark') {
        if (sunIcon) sunIcon.style.display = 'none';
        if (moonIcon) moonIcon.style.display = 'block';
        if (textSpan && textSpan.textContent.includes('Dark Mode')) textSpan.textContent = 'Light Mode';
      } else {
        if (sunIcon) sunIcon.style.display = 'block';
        if (moonIcon) moonIcon.style.display = 'none';
        if (textSpan && textSpan.textContent.includes('Mode')) textSpan.textContent = 'Dark Mode';
      }
    });
  }

  // Initialization after DOM is ready
  function init() {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    updateAllToggles(currentTheme);

    // Delegate click events to handle any toggle button
    document.addEventListener('click', function (e) {
      const toggle = e.target.closest('#darkModeToggle, #darkModeToggleMobile, .dark-mode-toggle');
      if (!toggle) return;

      e.preventDefault();
      const theme = document.documentElement.getAttribute('data-theme');
      const newTheme = theme === 'dark' ? 'light' : 'dark';

      document.documentElement.setAttribute('data-theme', newTheme);
      localStorage.setItem('theme', newTheme);
      updateAllToggles(newTheme);

      // If feather icons are used, we might need to re-replace them if they were hidden/shown
      if (window.feather) feather.replace();
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
