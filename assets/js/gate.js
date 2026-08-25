/* Password gate — protects brand work from casual/unauthorised viewing.
   To change the password: replace HASH below with the SHA-256 hex of the new
   password (e.g. run in any browser console:
   crypto.subtle.digest('SHA-256', new TextEncoder().encode('newpassword'))
     .then(b => console.log([...new Uint8Array(b)].map(x => x.toString(16).padStart(2,'0')).join('')))
*/
(function () {
  var HASH = '686b21176f29479dea2af97f10acc92a4b3c17793d3e3a6d26160cc754668069';
  var KEY = 'rm_gate_ok';

  /* The 'locked' class ships in the markup so the page is hidden before any
     script runs, and stays hidden if this file never loads. Unlocking is the
     act of removing it. */
  if (sessionStorage.getItem(KEY) === '1') {
    document.documentElement.classList.remove('locked');
    return;
  }

  function sha256hex(str) {
    return crypto.subtle.digest('SHA-256', new TextEncoder().encode(str)).then(function (buf) {
      return Array.prototype.map.call(new Uint8Array(buf), function (x) {
        return ('0' + x.toString(16)).slice(-2);
      }).join('');
    });
  }

  function unlock(gate) {
    sessionStorage.setItem(KEY, '1');
    document.documentElement.classList.remove('locked');
    gate.parentNode.removeChild(gate);
  }

  document.addEventListener('DOMContentLoaded', function () {
    var gate = document.createElement('div');
    gate.id = 'gate';
    gate.innerHTML =
      '<div class="gate-card">' +
      '<div class="gate-mark">Richard Morland<span>.</span></div>' +
      '<h2>Private portfolio</h2>' +
      '<p>This site contains confidential client work. Enter the password you were given to continue.</p>' +
      '<form class="gate-form">' +
      '<input type="password" autocomplete="current-password" placeholder="Password" aria-label="Password">' +
      '<button type="submit">Enter</button>' +
      '</form>' +
      '<div class="gate-err" role="alert"></div>' +
      '<a class="gate-contact" href="mailto:richardmorland@gmail.com">Request access</a>' +
      '</div>';
    document.body.appendChild(gate);

    var form = gate.querySelector('form');
    var input = gate.querySelector('input');
    var err = gate.querySelector('.gate-err');
    input.focus();

    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var val = input.value;
      if (!val) return;
      if (window.crypto && crypto.subtle) {
        sha256hex(val).then(function (h) {
          if (h === HASH) { unlock(gate); }
          else { err.textContent = 'Incorrect password — please try again.'; input.select(); }
        });
      } else {
        err.textContent = 'This browser cannot verify the password. Please use a modern browser.';
      }
    });
  });
})();
