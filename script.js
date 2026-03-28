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

  navLinks.forEach(link => {
    link.addEventListener('click', () => {
      nav.classList.remove('nav--open');
      toggle.setAttribute('aria-expanded', false);
    });
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

window.addEventListener('scroll', () => {
  if (window.scrollY > 50) {
    nav.classList.add('nav--scrolled');
  } else {
    nav.classList.remove('nav--scrolled');
  }
});
