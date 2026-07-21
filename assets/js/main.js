document.addEventListener('DOMContentLoaded', function () {
  // Case study filter (index page only)
  var filterBtns = document.querySelectorAll('.filter-btn');
  var cards = document.querySelectorAll('.case-card');
  filterBtns.forEach(function (btn) {
    btn.addEventListener('click', function () {
      filterBtns.forEach(function (b) { b.classList.remove('active'); });
      btn.classList.add('active');
      var f = btn.getAttribute('data-filter');
      cards.forEach(function (c) {
        var show = f === 'all' || c.getAttribute('data-cat') === f;
        c.style.display = show ? '' : 'none';
      });
    });
  });

  // Mobile hamburger menu
  var navEl = document.querySelector('.nav');
  var toggle = document.querySelector('.nav-toggle');
  if (navEl && toggle) {
    toggle.addEventListener('click', function () {
      var isOpen = navEl.classList.toggle('open');
      toggle.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
    });
    navEl.querySelectorAll('.nav-mobile a').forEach(function (a) {
      a.addEventListener('click', function () {
        navEl.classList.remove('open');
        toggle.setAttribute('aria-expanded', 'false');
      });
    });
  }
});
