// ============================================================
// AI Humanizer — Shared Navigation & Site JS
// ============================================================

// Active nav link highlighting
(function () {
  const path = window.location.pathname;
  document.querySelectorAll('.nav-links a').forEach(a => {
    if (a.getAttribute('href') === path ||
        (path.startsWith(a.getAttribute('href')) && a.getAttribute('href') !== '/')) {
      a.classList.add('active');
    }
  });
})();

// Mobile hamburger toggle
const hamburger = document.getElementById('navHamburger');
const navLinks  = document.getElementById('navLinks');
if (hamburger && navLinks) {
  hamburger.addEventListener('click', () => {
    navLinks.classList.toggle('open');
    hamburger.setAttribute('aria-expanded', navLinks.classList.contains('open'));
  });
}
