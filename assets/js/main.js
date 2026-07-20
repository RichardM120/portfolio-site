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

  // Mobile nav fallback: simple anchor smooth scroll already via CSS
});
