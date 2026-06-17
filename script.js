// ── Mobile hamburger menu ──

const nav = document.getElementById('nav');
const toggle = document.querySelector('.nav__toggle');
const navLinks = document.querySelectorAll('.nav__links a');

if (toggle) {
  toggle.addEventListener('click', () => {
    nav.classList.toggle('nav--open');
    const isOpen = nav.classList.contains('nav--open');
    toggle.setAttribute('aria-expanded', isOpen);
  });

  const closeMenu = () => {
    nav.classList.remove('nav--open');
    toggle.setAttribute('aria-expanded', false);
  };

  navLinks.forEach(link => {
    link.addEventListener('click', closeMenu);
  });

  // Tap outside the drawer (anywhere not in the nav) closes it
  document.addEventListener('click', (e) => {
    if (nav.classList.contains('nav--open') && !nav.contains(e.target)) {
      closeMenu();
    }
  });

  // Escape key closes it
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && nav.classList.contains('nav--open')) {
      closeMenu();
    }
  });
}

// ── Scroll-triggered fade-in animations ──

const fadeEls = document.querySelectorAll('.fade-in');
if (fadeEls.length) {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('fade-in--visible');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.15 });

  fadeEls.forEach(el => observer.observe(el));
}

// ── Nav background on scroll ──
// Guarded: sub-pages (resume, tandem) use the .resume-bar header and have no #nav.

if (nav) {
  window.addEventListener('scroll', () => {
    if (window.scrollY > 50) {
      nav.classList.add('nav--scrolled');
    } else {
      nav.classList.remove('nav--scrolled');
    }
  });
}
