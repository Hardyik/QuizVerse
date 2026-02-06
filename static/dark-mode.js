// ============================================
// GLOBAL DARK MODE SCRIPT
// Include this in all pages except login/signup
// ============================================

(function() {
  'use strict';

  // Initialize dark mode from localStorage on page load
  const htmlElement = document.documentElement;
  const savedTheme = localStorage.getItem('theme') || 'light';
  htmlElement.setAttribute('data-theme', savedTheme);

  // Wait for DOM to be ready
  document.addEventListener('DOMContentLoaded', function() {
    
    // Create dark mode toggle button if it doesn't exist
    const darkModeToggle = document.getElementById('darkModeToggle');
    
    if (darkModeToggle) {
      const sunIcon = document.getElementById('sunIcon');
      const moonIcon = document.getElementById('moonIcon');
      
      // Update icon based on current theme
      if (savedTheme === 'dark') {
        if (sunIcon) sunIcon.style.display = 'none';
        if (moonIcon) moonIcon.style.display = 'block';
      } else {
        if (sunIcon) sunIcon.style.display = 'block';
        if (moonIcon) moonIcon.style.display = 'none';
      }

      // Toggle dark mode
      darkModeToggle.addEventListener('click', function() {
        const currentTheme = htmlElement.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';

        htmlElement.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);

        // Toggle icons
        if (newTheme === 'dark') {
          if (sunIcon) sunIcon.style.display = 'none';
          if (moonIcon) moonIcon.style.display = 'block';
        } else {
          if (sunIcon) sunIcon.style.display = 'block';
          if (moonIcon) moonIcon.style.display = 'none';
        }
      });
    }
  });
})();
